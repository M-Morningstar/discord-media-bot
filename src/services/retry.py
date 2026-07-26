from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

import aiohttp

_F = TypeVar("_F", bound=Callable[..., Awaitable[Any]])

_RETRYABLE: tuple[type[Exception], ...] = (
    aiohttp.ClientConnectionError,  # DNS failures, refused connections
    aiohttp.ServerTimeoutError,  # server didn't respond in time
    aiohttp.ClientResponseError,  # check status code below
    asyncio.TimeoutError,  # our own timeout wrapping
)

_logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
) -> Callable[[_F], _F]:
    """Decorate an async function with exponential-backoff retry.

    Retries on :exc:`aiohttp.ClientConnectionError`,
    :exc:`aiohttp.ServerTimeoutError`, :exc:`asyncio.TimeoutError`,
    and server errors (5xx) from :exc:`aiohttp.ClientResponseError`.

    The delay between attempts is ``base_delay * (backoff_factor ** attempt)``,
    capped at ``max_delay``.

    Args:
        max_attempts: Total attempts including the initial call (default 3).
        base_delay: Initial delay in seconds before the first retry (default 1).
        max_delay: Maximum delay between retries in seconds (default 60).
        backoff_factor: Multiplier applied on each successive retry (default 2).

    Returns:
        A decorator that wraps the target async function.
    """

    def decorator(func: _F) -> _F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except _RETRYABLE as exc:
                    # Only retry on 5xx server errors, not 4xx client errors
                    if isinstance(exc, aiohttp.ClientResponseError) and exc.status < 500:
                        raise
                    last_exception = exc
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(
                        base_delay * (backoff_factor**attempt),
                        max_delay,
                    )
                    _logger.warning(
                        "Retry %d/%d for %s after %.1fs: %s",
                        attempt + 1,
                        max_attempts - 1,
                        func.__name__,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
            # Should be unreachable, but pyright/mypy appreciate it
            assert last_exception is not None
            raise last_exception

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = ["retry"]
