"""Exponential backoff retry for LLM API calls."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Call *fn* with exponential backoff on failure.

    Args:
        fn: Async callable that takes no arguments.
        max_retries: Maximum number of retry attempts after the first failure.
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum delay between retries.
        backoff_factor: Multiplier applied to the delay on each retry.
        retryable_exceptions: Only retry on these exception types.

    Returns:
        The return value of *fn* on success.

    Raises:
        The last exception raised by *fn* after all retries are exhausted.
    """
    delay = base_delay
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt == max_retries:
                break
            logger.warning(
                "LLM call failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt + 1,
                max_retries + 1,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)

    raise last_exc  # type: ignore[misc]
