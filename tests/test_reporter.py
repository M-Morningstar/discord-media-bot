from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import discord

from src.reporting.discord_reporter import DiscordReporter


def _make_msg(mocker: Any, channel_send: AsyncMock | None = None) -> discord.Message:
    """Build a mock discord.Message with a mock channel that captures embeds."""
    msg = mocker.MagicMock(spec=discord.Message)
    if channel_send is not None:
        msg.channel.send = channel_send
    else:
        msg.channel.send = mocker.AsyncMock()
    return msg


# ------------------------------------------------------------------
# Tests: send_success
# ------------------------------------------------------------------


async def test_send_success_embed_structure(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    await reporter.send_success(
        msg,
        title="Inception",
        imdb_id="tt1375666",
        media_type="movie",
        year=2010,
        poster_url="https://example.com/poster.jpg",
        overview="A thief who steals corporate secrets.",
    )

    send_mock.assert_called_once()
    call_kwargs = send_mock.call_args[1]
    embed: discord.Embed = call_kwargs["embed"]

    assert embed.title == "Inception"
    assert embed.color is not None
    assert embed.color.value == DiscordReporter.SUCCESS_COLOR
    assert embed.timestamp is not None

    fields = {f.name: f.value for f in embed.fields}
    status_value = fields.get("Status")
    assert status_value is not None
    assert "Added \u2713 (2010)" in status_value

    assert embed.description == "A thief who steals corporate secrets."
    assert embed.thumbnail is not None
    assert embed.thumbnail.url == "https://example.com/poster.jpg"
    assert "movie" in (embed.footer.text or "")
    assert "tt1375666" in (embed.footer.text or "")


async def test_send_success_truncates_long_overview(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    long_overview = "A" * 250
    await reporter.send_success(
        msg,
        title="Test",
        imdb_id="tt1234567",
        media_type="movie",
        overview=long_overview,
    )

    embed = send_mock.call_args[1]["embed"]
    assert len(embed.description) == 203  # 200 chars + "..."
    assert embed.description.endswith("...")


async def test_send_success_short_overview_not_truncated(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    short_overview = "Brief summary."
    await reporter.send_success(
        msg,
        title="Test",
        imdb_id="tt1234567",
        media_type="movie",
        overview=short_overview,
    )

    embed = send_mock.call_args[1]["embed"]
    assert embed.description == "Brief summary."


async def test_send_success_without_optional_fields(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    await reporter.send_success(
        msg,
        title="Inception",
        imdb_id="tt1375666",
        media_type="series",
    )

    embed = send_mock.call_args[1]["embed"]
    assert embed.title == "Inception"
    # When no overview is provided, description should not be set
    assert embed.description is None
    # When no poster_url is provided, thumbnail should not have a URL
    assert embed.thumbnail is None or embed.thumbnail.url is None


# ------------------------------------------------------------------
# Tests: send_already_exists
# ------------------------------------------------------------------


async def test_send_already_exists_embed(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    await reporter.send_already_exists(
        msg,
        title="Breaking Bad",
        imdb_id="tt0903747",
        media_type="series",
    )

    embed = send_mock.call_args[1]["embed"]
    assert "Breaking Bad" in (embed.description or "")
    assert "series" in (embed.description or "")
    assert embed.color is not None
    assert embed.color.value == DiscordReporter.ALREADY_EXISTS_COLOR
    assert embed.timestamp is not None
    assert "tt0903747" in (embed.footer.text or "")


# ------------------------------------------------------------------
# Tests: send_not_found
# ------------------------------------------------------------------


async def test_send_not_found_embed_movie(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    await reporter.send_not_found(
        msg,
        imdb_id="tt9999999",
        media_type="movie",
    )

    embed = send_mock.call_args[1]["embed"]
    assert "tt9999999" in (embed.description or "")
    assert "Radarr" in (embed.description or "")
    assert embed.color is not None
    assert embed.color.value == DiscordReporter.ERROR_COLOR


async def test_send_not_found_embed_series(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    await reporter.send_not_found(
        msg,
        imdb_id="tt9999999",
        media_type="series",
    )

    embed = send_mock.call_args[1]["embed"]
    assert "Sonarr" in (embed.description or "")


# ------------------------------------------------------------------
# Tests: send_validation_error
# ------------------------------------------------------------------


async def test_send_validation_error_empty(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    await reporter.send_validation_error(msg, reason="empty")

    embed = send_mock.call_args[1]["embed"]
    assert "doesn't contain" in (embed.description or "")
    assert "tt1234567" in (embed.description or "")
    assert embed.color is not None
    assert embed.color.value == DiscordReporter.ERROR_COLOR


async def test_send_validation_error_no_id(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    await reporter.send_validation_error(msg, reason="no_id")

    embed = send_mock.call_args[1]["embed"]
    assert "No IMDB ID found" in (embed.description or "")


async def test_send_validation_error_multiple_ids(mocker: Any) -> None:
    send_mock = mocker.AsyncMock()
    msg = _make_msg(mocker, channel_send=send_mock)
    reporter = DiscordReporter()

    await reporter.send_validation_error(msg, reason="multiple_ids")

    embed = send_mock.call_args[1]["embed"]
    assert "only one IMDB ID" in (embed.description or "")
