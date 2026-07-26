from __future__ import annotations

import logging

import aiohttp
import discord

from src.handler.router import Router
from src.reporting.discord_reporter import DiscordReporter
from src.services.base import BaseArrService
from src.validators.imdb import extract_imdb_id

_logger = logging.getLogger(__name__)


class MessageHandler:
    """Orchestrates the full IMDB-ID → media-add pipeline.

    Grabs an IMDB ID from a Discord message, resolves the target service,
    looks up the media, adds it, and reports the result back as an embed.
    All exceptions are caught internally — this handler never propagates.
    """

    def __init__(
        self,
        router: Router,
        radarr: BaseArrService,
        sonarr: BaseArrService,
        reporter: DiscordReporter,
        radarr_quality_profile_id: int,
        radarr_root_folder: str,
        sonarr_quality_profile_id: int,
        sonarr_root_folder: str,
    ) -> None:
        self._router = router
        self._radarr = radarr
        self._sonarr = sonarr
        self._reporter = reporter
        self._radarr_quality_profile_id = radarr_quality_profile_id
        self._radarr_root_folder = radarr_root_folder
        self._sonarr_quality_profile_id = sonarr_quality_profile_id
        self._sonarr_root_folder = sonarr_root_folder

    async def handle(self, message: discord.Message) -> None:
        """Process an incoming Discord message.

        Silently ignores bot messages, non-configured channels, and any
        unexpected errors (logged at ERROR).  Never raises — the bot must
        stay online regardless of what users post.
        """
        # 1. Ignore bot's own messages
        if message.author.bot:
            return

        # 2. Resolve channel -> service
        svc = self._router.resolve(message.channel.id)
        if svc is None:
            return  # not a configured channel, silently ignore

        # 3. Pick the concrete service and media type label
        if svc.value == "radarr":
            service: BaseArrService = self._radarr
            media_type = "movie"
            quality_profile_id = self._radarr_quality_profile_id
            root_folder = self._radarr_root_folder
        else:
            service = self._sonarr
            media_type = "series"
            quality_profile_id = self._sonarr_quality_profile_id
            root_folder = self._sonarr_root_folder

        # 4. Extract IMDB ID
        content = message.content.strip()
        if not content:
            await self._reporter.send_validation_error(message, reason="empty")
            return

        imdb_id = extract_imdb_id(content)
        if imdb_id is None:
            await self._reporter.send_validation_error(message, reason="no_id")
            return

        if not _is_single_id(content):
            await self._reporter.send_validation_error(message, reason="multiple_ids")
            return

        # 5. Lookup -> add -> report (with full error handling)
        try:
            data = await service.lookup(imdb_id)
        except LookupError:
            # Fallback: check if the item already exists in the library
            existing = await service.find_in_library(imdb_id)
            if existing is not None:
                title = existing.get("title", imdb_id)
                await self._reporter.send_already_exists(
                    message,
                    title=str(title),
                    imdb_id=imdb_id,
                    media_type=media_type,
                )
                return
            await _report_not_found(self._reporter, message, imdb_id, media_type)
            return
        except Exception:
            _logger.exception("Lookup failed for IMDB ID %s", imdb_id)
            await _report_not_found(self._reporter, message, imdb_id, media_type)
            return

        try:
            await service.add(data, quality_profile_id, root_folder)
        except aiohttp.ClientResponseError as exc:
            if _is_already_exists(exc):
                title = data.get("title", imdb_id)
                await self._reporter.send_already_exists(
                    message,
                    title=str(title),
                    imdb_id=imdb_id,
                    media_type=media_type,
                )
                return
            _logger.exception("Add failed for IMDB ID %s", imdb_id)
            await _report_not_found(self._reporter, message, imdb_id, media_type)
            return
        except Exception:
            _logger.exception("Add failed for IMDB ID %s", imdb_id)
            await _report_not_found(self._reporter, message, imdb_id, media_type)
            return

        # 6. Success
        title = data.get("title", imdb_id)
        year = data.get("year")
        poster = data.get("remotePoster")
        overview = data.get("overview")
        await self._reporter.send_success(
            message,
            title=str(title),
            imdb_id=imdb_id,
            media_type=media_type,
            year=year,
            poster_url=poster,
            overview=overview,
        )


def _is_single_id(content: str) -> bool:
    """Check that *content* contains exactly one IMDB ID."""
    from src.validators.imdb import _find_all_imdb_ids

    ids = _find_all_imdb_ids(content)
    return len(ids) == 1


def _is_already_exists(exc: aiohttp.ClientResponseError) -> bool:
    """True if the Radarr/Sonarr 400 error is an 'already exists' response."""
    if exc.status != 400:
        return False
    message = str(exc).lower()
    return "already" in message


async def _report_not_found(
    reporter: DiscordReporter,
    message: discord.Message,
    imdb_id: str,
    media_type: str,
) -> None:
    """Report that a media item could not be found or added."""
    await reporter.send_not_found(
        message,
        imdb_id=imdb_id,
        media_type=media_type,
    )


__all__ = ["MessageHandler", "_is_single_id", "_is_already_exists"]
