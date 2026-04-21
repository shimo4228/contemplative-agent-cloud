"""Shared scaffolding for cloud LLM backends."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS: float = 600.0
DEFAULT_MAX_RETRIES: int = 3
RETRY_BASE_DELAY_SECONDS: float = 2.0

T = TypeVar("T")


def run_with_retries(
    call: Callable[[], T],
    retryable_types: Tuple[type, ...],
    max_retries: int,
    base_delay: float,
    label: str,
) -> Optional[T]:
    """Run ``call`` with exponential-backoff retry on transient errors.

    Retries only on ``retryable_types`` (network, rate limit, 5xx). Any
    other exception is logged and swallowed as ``None`` so the upstream
    circuit breaker can record a failure without crashing the caller.
    Configuration errors (missing API key, missing SDK) should be raised
    by the caller *before* entering this helper.
    """
    for attempt in range(max_retries + 1):
        try:
            return call()
        except Exception as exc:
            if not isinstance(exc, retryable_types) or attempt >= max_retries:
                logger.error(
                    "%s request failed (attempt %d/%d): %s",
                    label, attempt + 1, max_retries + 1, exc,
                )
                return None
            delay = base_delay * (2**attempt)
            logger.warning(
                "%s transient error (attempt %d/%d): %s — retry in %.1fs",
                label, attempt + 1, max_retries + 1, exc, delay,
            )
            time.sleep(delay)
    return None


def load_sdk_symbol(module_name: str, symbol: str) -> Any:
    """Import ``symbol`` from ``module_name``, raising RuntimeError if missing."""
    try:
        module = __import__(module_name, fromlist=[symbol])
    except ImportError as exc:
        raise RuntimeError(
            f"{module_name} package is not installed. "
            "Install contemplative-agent-cloud to pull it in."
        ) from exc
    return getattr(module, symbol)
