from __future__ import annotations

from typing import Any, cast

import aiohttp
import discord
import pytest

from src.handler.message_handler import (
    MessageHandler,
    _is_already_exists,
    _is_single_id,
)
from src.handler.router import Router
from src.reporting.discord_reporter import DiscordReporter


@pytest.fixture
def deps(mocker: Any) -> dict[str, Any]:
    """Build a MessageHandler with all dependencies mocked."""
    router = Router(radarr_channel_id=111, sonarr_channel_id=222)

    radarr = mocker.AsyncMock()
    sonarr = mocker.AsyncMock()
    reporter = mocker.AsyncMock(spec=DiscordReporter)

    handler = MessageHandler(
        router=router,
        radarr=radarr,
        sonarr=sonarr,
        reporter=reporter,
        radarr_quality_profile_id=1,
        radarr_root_folder="/movies",
        sonarr_quality_profile_id=2,
        sonarr_root_folder="/tv",
    )

    return {
        "handler": handler,
        "radarr": radarr,
        "sonarr": sonarr,
        "reporter": reporter,
    }


def _msg(
    mocker: Any,
    content: str,
    channel_id: int = 111,
    author_is_bot: bool = False,
) -> discord.Message:
    """Create a mock Discord message."""
    msg = cast(discord.Message, mocker.MagicMock(spec=discord.Message))
    msg.content = content
    msg.channel.id = channel_id
    msg.author.bot = author_is_bot
    return msg


# ------------------------------------------------------------------
# Handler tests
# ------------------------------------------------------------------


async def test_ignores_bot_messages(mocker: Any, deps: dict[str, Any]) -> None:
    msg = _msg(mocker, "tt1234567", author_is_bot=True)
    await deps["handler"].handle(msg)
    deps["reporter"].send_validation_error.assert_not_called()
    deps["reporter"].send_success.assert_not_called()


async def test_ignores_unknown_channel(mocker: Any, deps: dict[str, Any]) -> None:
    msg = _msg(mocker, "tt1234567", channel_id=999)
    await deps["handler"].handle(msg)
    deps["radarr"].lookup.assert_not_called()
    deps["sonarr"].lookup.assert_not_called()


async def test_reports_empty_message(mocker: Any, deps: dict[str, Any]) -> None:
    msg = _msg(mocker, "")
    await deps["handler"].handle(msg)
    deps["reporter"].send_validation_error.assert_called_once()
    call_kwargs = deps["reporter"].send_validation_error.call_args[1]
    assert call_kwargs["reason"] == "empty"


async def test_reports_no_imdb_id(mocker: Any, deps: dict[str, Any]) -> None:
    msg = _msg(mocker, "hello world")
    await deps["handler"].handle(msg)
    deps["reporter"].send_validation_error.assert_called_once()
    call_kwargs = deps["reporter"].send_validation_error.call_args[1]
    assert call_kwargs["reason"] == "no_id"


async def test_reports_multiple_ids(mocker: Any, deps: dict[str, Any]) -> None:
    msg = _msg(mocker, "tt1234567 and tt7654321")
    await deps["handler"].handle(msg)
    deps["reporter"].send_validation_error.assert_called_once()
    call_kwargs = deps["reporter"].send_validation_error.call_args[1]
    assert call_kwargs["reason"] == "multiple_ids"


async def test_successful_add_radarr(mocker: Any, deps: dict[str, Any]) -> None:
    deps["radarr"].lookup.return_value = {
        "title": "Inception",
        "year": 2010,
        "remotePoster": "https://example.com/poster.jpg",
        "overview": "A dream within a dream.",
    }
    deps["radarr"].add.return_value = {"status": "added"}

    msg = _msg(mocker, "tt1375666", channel_id=111)
    await deps["handler"].handle(msg)

    deps["radarr"].lookup.assert_called_once_with("tt1375666")
    deps["radarr"].add.assert_called_once_with(
        deps["radarr"].lookup.return_value,
        1,
        "/movies",
    )
    deps["reporter"].send_success.assert_called_once()
    call_kwargs = deps["reporter"].send_success.call_args[1]
    assert call_kwargs["title"] == "Inception"
    assert call_kwargs["imdb_id"] == "tt1375666"
    assert call_kwargs["media_type"] == "movie"
    assert call_kwargs["year"] == 2010


async def test_successful_add_sonarr(mocker: Any, deps: dict[str, Any]) -> None:
    deps["sonarr"].lookup.return_value = {
        "title": "Breaking Bad",
        "year": 2008,
    }
    deps["sonarr"].add.return_value = {"status": "added"}

    msg = _msg(mocker, "tt0903747", channel_id=222)
    await deps["handler"].handle(msg)

    deps["sonarr"].lookup.assert_called_once_with("tt0903747")
    deps["sonarr"].add.assert_called_once_with(
        deps["sonarr"].lookup.return_value,
        2,
        "/tv",
    )
    deps["reporter"].send_success.assert_called_once()
    call_kwargs = deps["reporter"].send_success.call_args[1]
    assert call_kwargs["media_type"] == "series"


async def test_reports_not_found_on_lookup_error(mocker: Any, deps: dict[str, Any]) -> None:
    deps["radarr"].lookup.side_effect = LookupError("No movie found")
    deps["radarr"].find_in_library.return_value = None

    msg = _msg(mocker, "tt0000000", channel_id=111)
    await deps["handler"].handle(msg)

    deps["reporter"].send_not_found.assert_called_once()
    deps["radarr"].add.assert_not_called()


async def test_reports_already_exists(mocker: Any, deps: dict[str, Any]) -> None:
    deps["radarr"].lookup.return_value = {"title": "Inception"}
    err = aiohttp.ClientResponseError(
        request_info=mocker.Mock(),
        history=(),
        status=400,
        message="Movie already exists in database",
    )
    deps["radarr"].add.side_effect = err

    msg = _msg(mocker, "tt1375666", channel_id=111)
    await deps["handler"].handle(msg)

    deps["reporter"].send_already_exists.assert_called_once()


async def test_reports_not_found_on_add_error(mocker: Any, deps: dict[str, Any]) -> None:
    deps["radarr"].lookup.return_value = {"title": "Inception"}
    deps["radarr"].add.side_effect = RuntimeError("unexpected")

    msg = _msg(mocker, "tt1375666", channel_id=111)
    await deps["handler"].handle(msg)

    deps["reporter"].send_not_found.assert_called_once()


# ------------------------------------------------------------------
# Helper: _is_single_id
# ------------------------------------------------------------------


def test_is_single_id_true() -> None:
    assert _is_single_id("tt1234567") is True


def test_is_single_id_false_multiple() -> None:
    assert _is_single_id("tt1234567 tt7654321") is False


def test_is_single_id_false_none() -> None:
    assert _is_single_id("no id here") is False


# ------------------------------------------------------------------
# Helper: _is_already_exists
# ------------------------------------------------------------------


def test_is_already_exists_true(mocker: Any) -> None:
    exc = aiohttp.ClientResponseError(
        request_info=mocker.Mock(),
        history=(),
        status=400,
        message="Movie already exists in database",
    )
    assert _is_already_exists(exc) is True


def test_is_already_exists_false_other_400(mocker: Any) -> None:
    exc = aiohttp.ClientResponseError(
        request_info=mocker.Mock(),
        history=(),
        status=400,
        message="Invalid root folder",
    )
    assert _is_already_exists(exc) is False


def test_is_already_exists_false_500(mocker: Any) -> None:
    exc = aiohttp.ClientResponseError(
        request_info=mocker.Mock(),
        history=(),
        status=500,
        message="already",
    )
    assert _is_already_exists(exc) is False
