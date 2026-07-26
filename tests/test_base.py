from __future__ import annotations

from typing import Any

import pytest
from aiohttp import ClientSession

from src.services.base import BaseArrService


class ConcreteService(BaseArrService):
    async def lookup(self, imdb_id: str) -> dict[str, Any]:
        return {"title": "test"}

    async def add(
        self,
        data: dict[str, Any],
        quality_profile_id: int,
        root_folder: str,
    ) -> dict[str, Any]:
        return {"status": "added"}


async def test_cannot_instantiate_abstract_class() -> None:
    with pytest.raises(TypeError):
        BaseArrService(  # type: ignore[abstract]
            session=ClientSession(),
            base_url="http://example.com",
            api_key="test-key",
        )


async def test_concrete_subclass_can_be_instantiated() -> None:
    svc = ConcreteService(
        session=ClientSession(),
        base_url="http://example.com",
        api_key="test-key",
    )
    assert isinstance(svc, BaseArrService)


async def test_stores_constructor_args() -> None:
    session = ClientSession()
    svc = ConcreteService(
        session=session,
        base_url="http://example.com",
        api_key="test-key",
        timeout=60,
    )
    assert svc._session is session
    assert svc._base_url == "http://example.com"
    assert svc._api_key == "test-key"
    assert svc._timeout == 60


async def test_default_timeout() -> None:
    svc = ConcreteService(
        session=ClientSession(),
        base_url="http://example.com",
        api_key="test-key",
    )
    assert svc._timeout == 30


async def test_get_builds_correct_request(mocker: Any) -> None:
    mock_session = mocker.AsyncMock(spec=ClientSession)
    svc = ConcreteService(
        session=mock_session,
        base_url="http://example.com",
        api_key="test-key",
    )

    # Set up the mock chain: session.get -> __aenter__ -> resp
    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"key": "value"}
    mock_resp.raise_for_status = mocker.Mock()

    mock_ctx = mocker.AsyncMock()
    mock_ctx.__aenter__.return_value = mock_resp
    mock_session.get.return_value = mock_ctx

    result = await svc._get("/api/v3/test")

    assert result == {"key": "value"}
    mock_session.get.assert_called_once()
    call_args = mock_session.get.call_args[0]
    assert call_args[0] == "http://example.com/api/v3/test"
    assert mock_session.get.call_args[1]["headers"] == {"X-Api-Key": "test-key"}


async def test_post_builds_correct_request(mocker: Any) -> None:
    mock_session = mocker.AsyncMock(spec=ClientSession)
    svc = ConcreteService(
        session=mock_session,
        base_url="http://example.com",
        api_key="test-key",
    )

    mock_resp = mocker.AsyncMock()
    mock_resp.status = 201
    mock_resp.json.return_value = {"status": "ok"}
    mock_resp.raise_for_status = mocker.Mock()

    mock_ctx = mocker.AsyncMock()
    mock_ctx.__aenter__.return_value = mock_resp
    mock_session.post.return_value = mock_ctx

    body = {"title": "foo"}
    result = await svc._post("/api/v3/add", body)

    assert result == {"status": "ok"}
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args[0]
    assert call_args[0] == "http://example.com/api/v3/add"
    assert mock_session.post.call_args[1]["headers"] == {"X-Api-Key": "test-key"}
    assert mock_session.post.call_args[1]["json"] == body


async def test_get_raises_on_http_error(mocker: Any) -> None:
    from aiohttp import ClientResponseError

    mock_session = mocker.AsyncMock(spec=ClientSession)
    svc = ConcreteService(
        session=mock_session,
        base_url="http://example.com",
        api_key="test-key",
    )

    mock_resp = mocker.AsyncMock()
    mock_resp.status = 404
    mock_resp.raise_for_status = mocker.Mock(
        side_effect=ClientResponseError(
            request_info=mocker.Mock(),
            history=(),
            status=404,
        )
    )

    mock_ctx = mocker.AsyncMock()
    mock_ctx.__aenter__.return_value = mock_resp
    mock_session.get.return_value = mock_ctx

    with pytest.raises(ClientResponseError):
        await svc._get("/api/v3/missing")
