"""OpenAI GPT backend for contemplative-agent.

Maps the ``LLMBackend`` protocol onto the OpenAI ``chat.completions``
API. Native JSON Schema structured output is used when the caller
passes ``format``. Sanitization and circuit breaker handling live in
the main repository's ``core/llm.py`` — this module only produces raw
text.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from contemplative_agent_cloud.backends._base import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    RETRY_BASE_DELAY_SECONDS,
    load_sdk_symbol,
    run_with_retries,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-5"


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

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        OpenAI = load_sdk_symbol("openai", "OpenAI")
        key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set and no api_key was provided."
            )
        self._client = OpenAI(api_key=key, timeout=self.timeout_seconds)
        return self._client

    def generate(
        self,
        prompt: str,
        system: str,
        num_predict: int,
        format: Optional[Dict],
    ) -> Optional[str]:
        # Configuration errors (missing key, missing SDK) propagate — those
        # are not transient and the caller should fix the setup.
        client = self._get_client()

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": num_predict,
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

        def _call() -> Optional[str]:
            response = client.chat.completions.create(**kwargs)
            return _extract_text(response)

        return run_with_retries(
            _call,
            retryable_types=_retryable_types(),
            max_retries=self.max_retries,
            base_delay=RETRY_BASE_DELAY_SECONDS,
            label="OpenAI",
        )


def _extract_text(response: Any) -> Optional[str]:
    """Pull the first choice's message content from a ChatCompletion."""
    choices = getattr(response, "choices", None)
    if not choices:
        return None
    message = getattr(choices[0], "message", None)
    if message is None:
        return None
    content = getattr(message, "content", None)
    if isinstance(content, str) and content:
        return content
    return None


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
