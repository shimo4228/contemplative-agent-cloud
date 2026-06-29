"""Anthropic Claude backend for contemplative-agent.

Maps the ``LLMBackend`` protocol onto the Anthropic ``messages.create``
API and returns a :class:`~contemplative_agent.core.llm.BackendResult`
that the main repository's ``core/llm.py`` sanitizes, truncation-gates,
and circuit-breaks uniformly with the Ollama path — this module only
produces the raw result.
"""

from __future__ import annotations

import json
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

_DEFAULT_MODEL = "claude-opus-4-7"

# Anthropic's sampling temperature is constrained to [0.0, 1.0]; the core
# forwards higher values (e.g. COMMENT_TEMPERATURE=1.3 for outward reflective
# generation). Forwarding 1.3 verbatim would 400 → non-retryable → a spurious
# circuit failure, so the request clamps to this ceiling instead.
_MAX_TEMPERATURE = 1.0

# Claude 3/4 models all expose a 200K-token context window (input + output
# share it). The pre-flight budget guard (ADR-0066, audit C2) reads this via
# the LLMBackend.context_window contract. Keyed by model-id prefix; the flat
# default covers every current Claude id, with the table reserved for future
# exceptions (e.g. a 1M-token beta).
_DEFAULT_CONTEXT_WINDOW = 200_000
_CONTEXT_WINDOWS: Dict[str, int] = {}


@dataclass
class AnthropicBackend:
    """LLMBackend implementation backed by the Anthropic API.

    Construct with an explicit API key, or leave ``api_key`` as ``None``
    to read ``ANTHROPIC_API_KEY`` from the environment when the backend
    is first used.

    Args:
        api_key: Anthropic API key. ``None`` defers to ``ANTHROPIC_API_KEY``.
        model: Claude model identifier. Defaults to ``claude-opus-4-7``.
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

        Anthropic = load_sdk_symbol("anthropic", "Anthropic")
        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set and no api_key was provided."
            )
        self._client = Anthropic(api_key=key, timeout=self.timeout_seconds)
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
        """Generate via Anthropic Messages; return a :class:`BackendResult`.

        The caller (``core.llm._generate_via_backend``) applies sanitization,
        the ``drop_truncated`` gate (from ``finish_reason``), and circuit
        accounting, so this method neither sanitizes nor gates.

        ``temperature`` is clamped to Anthropic's [0.0, 1.0] range. ``think``
        is accepted for protocol conformance but ignored — this backend does
        not request an extended-thinking trace, so ``BackendResult.thinking``
        is always ``None``.
        """
        # Configuration errors (missing key, missing SDK) propagate — those
        # are not transient and the caller should fix the setup.
        client = self._get_client()

        user_content = prompt
        if format is not None:
            user_content = (
                f"{prompt}\n\n"
                "Respond with a single JSON object that matches this schema "
                "exactly. Output only the JSON — no prose, no code fences.\n"
                f"Schema: {json.dumps(format)}"
            )

        clamped_temperature = max(0.0, min(temperature, _MAX_TEMPERATURE))

        # The core's SAMPLING_TOP_P / SAMPLING_TOP_K (forwarded on the Ollama
        # and mlx paths) are deliberately NOT sent here. They exist to stop a
        # local quantized model on a server with no sampling defaults from
        # degenerating into repetition loops at high temperature; Anthropic's
        # hosted API applies its own robust defaults, and overriding them would
        # make Claude sample less like itself — counter to this package's
        # purpose of comparing a provider's native behavior.
        def _call() -> Optional[BackendResult]:
            response = client.messages.create(
                model=self.model,
                system=system,
                max_tokens=num_predict,
                temperature=clamped_temperature,
                messages=[{"role": "user", "content": user_content}],
            )
            return _extract_result(response)

        return run_with_retries(
            _call,
            retryable_types=_retryable_types(),
            max_retries=self.max_retries,
            base_delay=RETRY_BASE_DELAY_SECONDS,
            label="Anthropic",
        )


def _extract_result(response: Any) -> Optional[BackendResult]:
    """Map a Messages response onto a :class:`BackendResult`.

    Returns ``None`` when the response carries no text block — the caller
    treats that as an empty generation (circuit failure), matching the
    pre-contract behavior.
    """
    text = _extract_text(response)
    if text is None:
        return None

    # Anthropic's ``stop_reason == "max_tokens"`` is the output-truncation
    # signal; the core's drop_truncated gate keys on the literal "length"
    # (Ollama's done_reason vocabulary), so translate it. Other stop reasons
    # pass through as informational telemetry (the gate ignores them).
    stop_reason = getattr(response, "stop_reason", None)
    finish_reason = "length" if stop_reason == "max_tokens" else stop_reason

    usage = getattr(response, "usage", None)
    eval_count = coerce_int(getattr(usage, "output_tokens", None))
    # Anthropic splits input tokens into fresh + cache-read + cache-creation.
    # BackendResult wants total input as ``prompt_tokens`` and cache hits as
    # ``cached_tokens`` (cached/prompt = the hit rate), so sum the components
    # that are present. The agent sets no cache_control today, so the cache
    # fields are normally absent and prompt_tokens == input_tokens.
    components = [
        c
        for c in (
            coerce_int(getattr(usage, "input_tokens", None)),
            coerce_int(getattr(usage, "cache_read_input_tokens", None)),
            coerce_int(getattr(usage, "cache_creation_input_tokens", None)),
        )
        if c is not None
    ]
    prompt_tokens = sum(components) if components else None
    cached_tokens = coerce_int(getattr(usage, "cache_read_input_tokens", None))

    return BackendResult(
        text=text,
        finish_reason=finish_reason,
        eval_count=eval_count,
        prompt_tokens=prompt_tokens,
        cached_tokens=cached_tokens,
    )


def _extract_text(response: Any) -> Optional[str]:
    """Pull the first text block out of a Messages response."""
    content = getattr(response, "content", None)
    if not content:
        return None
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text:
            return text
    return None


def _retryable_types() -> Tuple[type, ...]:
    """Error classes the retry helper should treat as transient."""
    try:
        import anthropic
    except ImportError:
        return ()
    return (
        anthropic.APIConnectionError,
        anthropic.APITimeoutError,
        anthropic.RateLimitError,
        anthropic.InternalServerError,
    )
