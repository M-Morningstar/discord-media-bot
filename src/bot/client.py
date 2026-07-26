from __future__ import annotations

import logging

import aiohttp
import discord

from src.handler.message_handler import MessageHandler
from src.reporting.discord_reporter import DiscordReporter

_logger = logging.getLogger(__name__)


class MediaBot(discord.Client):
    """Discord client that delegates messages to MessageHandler.

    Owns the aiohttp sessions for Radarr and Sonarr — closes them on shutdown.
    Sends a startup message to each configured channel on first on_ready only.
    """

    def __init__(
        self,
        message_handler: MessageHandler,
        radarr_session: aiohttp.ClientSession,
        sonarr_session: aiohttp.ClientSession,
        radarr_channel_id: int,
        sonarr_channel_id: int,
        reporter: DiscordReporter,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents)

        self._handler = message_handler
        self._radarr_session = radarr_session
        self._sonarr_session = sonarr_session
        self._radarr_channel_id = radarr_channel_id
        self._sonarr_channel_id = sonarr_channel_id
        self._reporter = reporter
        self._startup_sent = False

    async def on_ready(self) -> None:
        """Log connected guilds and send a one-shot startup message.

        Discord can fire on_ready multiple times after transient Gateway
        reconnects.  The _startup_sent flag prevents duplicate startup
        messages and noisy re-logging.
        """
        if self._startup_sent:
            _logger.debug("Skipping startup message (already sent this session)")
            return
        self._startup_sent = True

        _logger.info(
            "Connected as %s (id=%s)",
            self.user,
            self.user.id if self.user else "?",
        )
        for guild in self.guilds:
            _logger.info("Guild: %s (id=%s)", guild.name, guild.id)

        for ch_id in (self._radarr_channel_id, self._sonarr_channel_id):
            channel = self.get_channel(ch_id)
            if channel is not None and isinstance(channel, discord.TextChannel):
                try:
                    await self._reporter.send_startup_message(channel)
                except discord.Forbidden:
                    _logger.warning(
                        "No permission to send startup message in channel %s",
                        ch_id,
                    )
                except Exception:
                    _logger.exception(
                        "Failed to send startup message in chanel %s",
                        ch_id,
                    )

    async def on_message(self, message: discord.Message) -> None:
        """Delegate non-bot guild messages to the handler.

        Bot messages and DMs (guild is None) are silently ignored.
        All exceptions are caught inside MessageHandler.handle() — the
        bot stays online regardless of what users post.
        """
        if message.author.bot:
            return
        if message.guild is None:
            return
        await self._handler.handle(message)

    async def close(self) -> None:
        """Close HTTP sessions before disconnecting from Discord."""
        await self._radarr_session.close()
        await self._sonarr_session.close()
        await super().close()
