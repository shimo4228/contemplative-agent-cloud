"""OpenAI GPT backend for contemplative-agent.

Maps the ``LLMBackend`` protocol onto the OpenAI ``chat.completions``
API and returns a :class:`~contemplative_agent.core.llm.BackendResult`
that the main repository's ``core/llm.py`` sanitizes, truncation-gates,
and circuit-breaks uniformly with the Ollama path. Native JSON Schema
structured output is used when the caller passes ``format``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from contemplative_agent.core.llm import BackendResult

from contemplative_agent_cloud.backends._base import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    RETRY_BASE_DELAY_SECONDS,
    coerce_int,
    load_sdk_symbol,
    resolve_context_window,
    run_with_retries,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-5"

# Provider context windows (input + output share the budget) keyed by model-id
# prefix for the pre-flight budget guard (ADR-0066, audit C2). Only families
# whose window exceeds the default need an entry; the conservative 128K default
# covers the 128K-class models (gpt-4o, gpt-4-turbo). Under-reporting is the
# safe direction — the guard skips an over-budget call rather than letting an
# oversized prompt reach the API and 400. Longest-prefix match, so a dated id
# like ``gpt-5-2025-08-07`` still resolves to the gpt-5 window.
_DEFAULT_CONTEXT_WINDOW = 128_000
_CONTEXT_WINDOWS: Dict[str, int] = {
    # gpt-5 / -mini / -nano total 400K, but the *input* cap is 272K (output
    # 128K is a separate budget). The guard spends context_window as its
    # whole input+output budget, so report the input cap: declaring 400K
    # would let the guard pass an oversized prompt the API rejects with a
    # 400 — the opposite of the under-reporting-is-safe direction above.
    "gpt-5": 272_000,
    "gpt-4.1": 1_000_000,  # gpt-4.1 / -mini / -nano all share ~1M
}


@dataclass
class OpenAIBackend:
    """LLMBackend implementation backed by the OpenAI API.

    Construct with an explicit API key, or leave ``api_key`` as ``None``
    to read ``OPENAI_API_KEY`` from the environment when the backend is
    first used.

    Args:
        api_key: OpenAI API key. ``None`` defers to ``OPENAI_API_KEY``.
        model: Chat-completions model identifier. Defaults to ``gpt-5``.
        timeout_seconds: Per-request socket timeout.
        max_retries: Number of retries on transient failures
            (network, rate limits, 5xx).
    """

    api_key: Optional[str] = None
    model: str = _DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES

    def __post_init__(self) -> None:
        self._client: Any = None

    @property
    def context_window(self) -> int:
        """Provider context limit for the configured model (ADR-0066 guard)."""
        return resolve_context_window(
            self.model, _CONTEXT_WINDOWS, _DEFAULT_CONTEXT_WINDOW
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        OpenAI = load_sdk_symbol("openai", "OpenAI")
        key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set and no api_key was provided.")
        self._client = OpenAI(api_key=key, timeout=self.timeout_seconds)
        return self._client

    def generate(
        self,
        prompt: str,
        system: str,
        num_predict: int,
        format: Optional[Dict],
        *,
        temperature: float = 1.0,
        think: bool = False,
    ) -> Optional[BackendResult]:
        """Generate via OpenAI chat completions; return a :class:`BackendResult`.

        The caller (``core.llm._generate_via_backend``) applies sanitization,
        the ``drop_truncated`` gate (from ``finish_reason``), and circuit
        accounting, so this method neither sanitizes nor gates.

        ``temperature`` is forwarded (OpenAI accepts [0.0, 2.0], covering the
        outward COMMENT_TEMPERATURE of 1.3). ``think`` is accepted for protocol
        conformance but ignored — this backend requests no reasoning trace, so
        ``BackendResult.thinking`` is always ``None``.
        """
        # Configuration errors (missing key, missing SDK) propagate — those
        # are not transient and the caller should fix the setup.
        client = self._get_client()

        # The core's SAMPLING_TOP_P / SAMPLING_TOP_K (forwarded on the Ollama
        # and mlx paths) are deliberately NOT sent here. They guard a local
        # quantized model on a server with no sampling defaults against
        # repetition-loop degeneration; OpenAI's hosted API applies its own
        # defaults (and exposes no top_k at all), and overriding them would
        # work against this package's purpose of comparing a provider's
        # native behavior.
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": num_predict,
            "temperature": temperature,
        }
        if format is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": format,
                    "strict": True,
                },
            }

        def _call() -> Optional[BackendResult]:
            response = client.chat.completions.create(**kwargs)
            return _extract_result(response)

        return run_with_retries(
            _call,
            retryable_types=_retryable_types(),
            max_retries=self.max_retries,
            base_delay=RETRY_BASE_DELAY_SECONDS,
            label="OpenAI",
        )


def _extract_result(response: Any) -> Optional[BackendResult]:
    """Map a ChatCompletion response onto a :class:`BackendResult`.

    Returns ``None`` when the response carries no usable message content —
    the caller treats that as an empty generation (circuit failure),
    matching the pre-contract behavior.
    """
    choices = getattr(response, "choices", None)
    if not choices:
        logger.warning(
            "OpenAI response carried no choices; returning None "
            "(caller records outcome=empty)"
        )
        return None
    choice = choices[0]
    # OpenAI's finish_reason already uses "length" for output truncation, so
    # it feeds the core's drop_truncated gate directly (no translation). Read
    # it before the content checks so an empty response can say WHY it was
    # empty (e.g. a reasoning model spending max_completion_tokens before any
    # visible content ends with finish_reason="length" and content=None).
    finish_reason = getattr(choice, "finish_reason", None)
    message = getattr(choice, "message", None)
    if message is None:
        logger.warning(
            "OpenAI response choice carried no message (finish_reason=%r); "
            "returning None (caller records outcome=empty)",
            finish_reason,
        )
        return None
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content:
        # Log the *type*, never the value — refusal / content-filter payloads
        # are untrusted model output.
        logger.warning(
            "OpenAI response message carried no text content "
            "(finish_reason=%r, content type=%s); returning None "
            "(caller records outcome=empty)",
            finish_reason,
            type(content).__name__,
        )
        return None

    usage = getattr(response, "usage", None)
    eval_count = coerce_int(getattr(usage, "completion_tokens", None))
    prompt_tokens = coerce_int(getattr(usage, "prompt_tokens", None))
    details = getattr(usage, "prompt_tokens_details", None)
    cached_tokens = coerce_int(getattr(details, "cached_tokens", None))

    return BackendResult(
        text=content,
        finish_reason=finish_reason,
        eval_count=eval_count,
        prompt_tokens=prompt_tokens,
        cached_tokens=cached_tokens,
    )


def _retryable_types() -> Tuple[type, ...]:
    """Error classes the retry helper should treat as transient."""
    try:
        import openai
    except ImportError:
        return ()
    return (
        openai.APIConnectionError,
        openai.APITimeoutError,
        openai.RateLimitError,
        openai.InternalServerError,
    )
