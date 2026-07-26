from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import aiohttp
import pytest

from src.services.retry import retry


async def test_success_on_first_attempt() -> None:
    calls = 0

    @retry(max_attempts=3)
    async def work() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await work()
    assert result == "ok"
    assert calls == 1


async def test_retries_on_connection_error_and_succeeds() -> None:
    side_effects = [
        aiohttp.ClientConnectionError("connection refused"),
        aiohttp.ClientConnectionError("connection refused"),
        "ok",
    ]

    @retry(max_attempts=3, base_delay=0.001)
    async def work() -> str:
        result = side_effects.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    result = await work()
    assert result == "ok"
    assert side_effects == []


async def test_retries_on_5xx_but_not_4xx() -> None:
    side_effects_5xx = [
        aiohttp.ClientResponseError(
            request_info=AsyncMock(),
            history=(),
            status=502,
        ),
        aiohttp.ClientResponseError(
            request_info=AsyncMock(),
            history=(),
            status=503,
        ),
        "ok",
    ]

    @retry(max_attempts=3, base_delay=0.001)
    async def work_5xx() -> str:
        result = side_effects_5xx.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    result = await work_5xx()
    assert result == "ok"
    assert side_effects_5xx == []


async def test_does_not_retry_on_4xx() -> None:
    calls = 0

    @retry(max_attempts=3)
    async def work() -> str:
        nonlocal calls
        calls += 1
        raise aiohttp.ClientResponseError(
            request_info=AsyncMock(),
            history=(),
            status=404,
        )

    with pytest.raises(aiohttp.ClientResponseError) as exc_info:
        await work()
    assert exc_info.value.status == 404
    assert calls == 1


async def test_raises_last_error_after_max_attempts() -> None:
    calls = 0

    @retry(max_attempts=3, base_delay=0.001)
    async def work() -> str:
        nonlocal calls
        calls += 1
        raise aiohttp.ClientConnectionError("fail")

    with pytest.raises(aiohttp.ClientConnectionError, match="fail"):
        await work()
    assert calls == 3


async def test_retries_on_asyncio_timeout() -> None:
    side_effects = [
        TimeoutError(),
        "ok",
    ]

    @retry(max_attempts=3, base_delay=0.001)
    async def work() -> str:
        result = side_effects.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    result = await work()
    assert result == "ok"


async def test_backoff_delay_increases() -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    @retry(max_attempts=4, base_delay=1.0, backoff_factor=2.0)
    async def work() -> str:
        raise aiohttp.ClientConnectionError("fail")

    with pytest.raises(aiohttp.ClientConnectionError), pytest.MonkeyPatch.context() as mp:
        mp.setattr(asyncio, "sleep", fake_sleep)
        await work()

    # 4 attempts = 3 sleeps: 1.0, 2.0, 4.0
    assert sleep_calls == [1.0, 2.0, 4.0]


async def test_backoff_capped_at_max_delay() -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    @retry(max_attempts=5, base_delay=10.0, max_delay=25.0, backoff_factor=2.0)
    async def work() -> str:
        raise aiohttp.ClientConnectionError("fail")

    with pytest.raises(aiohttp.ClientConnectionError), pytest.MonkeyPatch.context() as mp:
        mp.setattr(asyncio, "sleep", fake_sleep)
        await work()

    # 5 attempts = 4 sleeps: 10.0, 20.0, 25.0 (capped), 25.0 (capped)
    assert sleep_calls == [10.0, 20.0, 25.0, 25.0]
