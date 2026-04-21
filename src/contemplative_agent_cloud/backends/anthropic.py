"""Anthropic Claude backend for contemplative-agent.

Maps the ``LLMBackend`` protocol onto the Anthropic ``messages.create``
API. Sanitization and circuit breaker handling live in the main
repository's ``core/llm.py`` — this module only produces raw text.
"""

from __future__ import annotations

import json
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

_DEFAULT_MODEL = "claude-opus-4-7"


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
    ) -> Optional[str]:
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

        def _call() -> Optional[str]:
            response = client.messages.create(
                model=self.model,
                system=system,
                max_tokens=num_predict,
                messages=[{"role": "user", "content": user_content}],
            )
            return _extract_text(response)

        return run_with_retries(
            _call,
            retryable_types=_retryable_types(),
            max_retries=self.max_retries,
            base_delay=RETRY_BASE_DELAY_SECONDS,
            label="Anthropic",
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
