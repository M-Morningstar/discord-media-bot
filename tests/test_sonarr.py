from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import aiohttp
import pytest

from src.services.sonarr import SonarrService

# ------------------------------------------------------------------
# Helper: mock session factory
# ------------------------------------------------------------------


def _mock_session(
    mocker: Any,
    gets: dict[str, dict[str, Any] | list[dict[str, Any]]] | None = None,
    posts: dict[str, dict[str, Any]] | None = None,
) -> AsyncMock:
    """Build a mock ClientSession that returns pre-set JSON for GET/POST paths."""
    session = mocker.AsyncMock(spec=aiohttp.ClientSession)

    def _make_ctx(body: Any) -> AsyncMock:
        """Build an async context manager mock wrapping a response with the given body."""
        resp = mocker.AsyncMock()
        resp.json.return_value = body
        resp.raise_for_status = mocker.Mock()
        ctx = mocker.AsyncMock()
        ctx.__aenter__.return_value = resp
        return ctx

    def _get_side_effect(url: str, **kwargs: Any) -> AsyncMock:
        for path, body in (gets or {}).items():
            if url.endswith(path):
                return _make_ctx(body)
        err = aiohttp.ClientResponseError(
            request_info=mocker.Mock(),
            history=(),
            status=404,
        )
        resp = mocker.AsyncMock()
        resp.status = 404
        resp.raise_for_status = mocker.Mock(side_effect=err)
        ctx = mocker.AsyncMock()
        ctx.__aenter__.return_value = resp
        return ctx

    def _post_side_effect(url: str, **kwargs: Any) -> AsyncMock:
        for path, body in (posts or {}).items():
            if url.endswith(path):
                return _make_ctx(body)
        err = aiohttp.ClientResponseError(
            request_info=mocker.Mock(),
            history=(),
            status=500,
        )
        resp = mocker.AsyncMock()
        resp.status = 500
        resp.raise_for_status = mocker.Mock(side_effect=err)
        ctx = mocker.AsyncMock()
        ctx.__aenter__.return_value = resp
        return ctx

    session.get.side_effect = _get_side_effect
    session.post.side_effect = _post_side_effect

    return session


# ------------------------------------------------------------------
# Tests: lookup
# ------------------------------------------------------------------


async def test_lookup_returns_series(mocker: Any) -> None:
    series = {"title": "Breaking Bad", "tvdbId": 81189, "year": 2008}
    session = _mock_session(
        mocker,
        gets={"/api/v3/series/lookup?term=imdb:tt0903747": [series]},
    )
    svc = SonarrService(
        session=session,
        base_url="http://sonarr:8989",
        api_key="test-key",
    )
    result = await svc.lookup("tt0903747")
    assert result == series


async def test_lookup_raises_on_empty_results(mocker: Any) -> None:
    session = _mock_session(
        mocker,
        gets={"/api/v3/series/lookup?term=imdb:tt0000000": []},
    )
    svc = SonarrService(
        session=session,
        base_url="http://sonarr:8989",
        api_key="test-key",
    )
    with pytest.raises(LookupError, match="tt0000000"):
        await svc.lookup("tt0000000")


# ------------------------------------------------------------------
# Tests: add
# ------------------------------------------------------------------


async def test_add_posts_correct_payload(mocker: Any) -> None:
    post_response = {"id": 1, "title": "Breaking Bad", "status": "added"}
    session = _mock_session(
        mocker,
        posts={"/api/v3/series": post_response},
    )
    svc = SonarrService(
        session=session,
        base_url="http://sonarr:8989",
        api_key="test-key",
    )
    series_data = {"title": "Breaking Bad", "tvdbId": 81189}
    result = await svc.add(series_data, quality_profile_id=4, root_folder="/tv")
    assert result == post_response

    post_call = session.post.call_args
    payload = post_call[1]["json"]
    assert payload["title"] == "Breaking Bad"
    assert payload["qualityProfileId"] == 4
    assert payload["rootFolderPath"] == "/tv"
    assert payload["monitored"] is True
    assert payload["addOptions"] == {"searchForMissingEpisodes": True}
