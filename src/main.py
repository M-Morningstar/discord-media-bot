from __future__ import annotations

import asyncio
import logging
import signal
import sys

import aiohttp
import discord
from aiohttp import web

from src import __version__
from src.bot.client import MediaBot
from src.config import Config, ConfigurationError
from src.handler.message_handler import MessageHandler
from src.handler.router import Router
from src.logging_config import setup_logging
from src.reporting.discord_reporter import DiscordReporter
from src.services.radarr import RadarrService
from src.services.sonarr import SonarrService

_logger = logging.getLogger(__name__)


SHUTDOWN_TIMEOUT = 10.0  # seconds


async def main() -> None:
    # 1. Load & validate config - crash early if invalid
    try:
        config = Config.from_env()
    except ConfigurationError as exc:
        print(f"CONFIGURATION ERROR:\n{exc}", file=sys.stderr)
        sys.exit(1)

    # 2. Configure logging
    setup_logging(config.log_level)
    _logger.info("Starting Discord Media Bot v%s", __version__)
    _logger.info("Config: %r", config)

    # 3. Create aiohttp sessions with connection pooling
    #    Wrap ClientSession creation to fail fast on malformed URLs
    #    that urlparse doesn't catch (e.g. non-ASCII hostnames).
    connector = aiohttp.TCPConnector(limit=5, limit_per_host=2)
    timeout = aiohttp.ClientTimeout(total=config.http_timeout)
    radarr_session: aiohttp.ClientSession | None = None
    sonarr_session: aiohttp.ClientSession | None = None
    try:
        radarr_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        sonarr_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    except ValueError as exc:
        _logger.critical("Invalid service URL: %s", exc)
        if radarr_session is not None:
            await radarr_session.close()
        if sonarr_session is not None:
            await sonarr_session.close()
        sys.exit(1)

    # 4. Create service clients
    radarr = RadarrService(
        session=radarr_session,
        base_url=config.radarr_url,
        api_key=config.radarr_api_key,
        timeout=config.http_timeout,
    )
    sonarr = SonarrService(
        session=sonarr_session,
        base_url=config.sonarr_url,
        api_key=config.sonarr_api_key,
        timeout=config.http_timeout,
    )

    # 5. Wire components
    router = Router(
        radarr_channel_id=config.discord_radarr_channel_id,
        sonarr_channel_id=config.discord_sonarr_channel_id,
    )
    reporter = DiscordReporter()
    handler = MessageHandler(
        router=router,
        radarr=radarr,
        sonarr=sonarr,
        reporter=reporter,
        radarr_quality_profile_id=config.radarr_quality_profile_id,
        radarr_root_folder=config.radarr_root_folder_path,
        sonarr_quality_profile_id=config.sonarr_quality_profile_id,
        sonarr_root_folder=config.sonarr_root_folder_path,
    )
    bot = MediaBot(
        message_handler=handler,
        radarr_session=radarr_session,
        sonarr_session=sonarr_session,
        radarr_channel_id=config.discord_radarr_channel_id,
        sonarr_channel_id=config.discord_sonarr_channel_id,
        reporter=reporter,
    )

    # 6. Start health check HTTP server (for Docker HEALTHCHECK)
    health_app = web.Application()
    health_app.router.add_get("/health", _health_handler)
    health_app["radarr"] = radarr
    health_app["sonarr"] = sonarr
    health_runner = web.AppRunner(health_app)
    await health_runner.setup()
    health_site = web.TCPSite(health_runner, "0.0.0.0", config.health_check_port)
    await health_site.start()
    _logger.info("Health check server on port %d", config.health_check_port)

    # 7. Register signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    for sig in (signal.SIGTERM, signal.SIGINT):

        def _schedule_shutdown(
            signal_: signal.Signals = sig,
            runner: web.AppRunner = health_runner,
        ) -> None:
            asyncio.create_task(_shutdown(signal_, bot, shutdown_event, runner))

        loop.add_signal_handler(sig, _schedule_shutdown)

    # 8. Connect to Discord (blocks until disconnected)
    try:
        async with bot:
            await bot.start(config.discord_bot_token)
    except discord.LoginFailure:
        _logger.critical("Invalid Discord bot token")
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        _logger.critical(
            "Missing Privileged Gateway Intents — enable 'Message Content Intent' "
            "in the Discord Developer Portal for this bot application."
        )
        sys.exit(1)
    finally:
        # Ensure sessions are closed even if bot.start raises
        if radarr_session is not None:
            await radarr_session.close()
        if sonarr_session is not None:
            await sonarr_session.close()
        _logger.info("Shutdown complete")


async def _health_handler(request: web.Request) -> web.Response:
    """Return health status of the bot and its upstream services.

    Used by Docker HEALTHCHECK via ``GET /health``.
    Returns 200 if all services report healthy, 503 otherwise.
    """
    radarr_svc: RadarrService = request.app["radarr"]
    sonarr_svc: SonarrService = request.app["sonarr"]
    try:
        await radarr_svc._get("/api/v3/system/status")
        radarr_ok = True
    except Exception:
        radarr_ok = False
    try:
        await sonarr_svc._get("/api/v3/system/status")
        sonarr_ok = True
    except Exception:
        sonarr_ok = False

    status = "ok" if radarr_ok and sonarr_ok else "degraded"
    http_status = 200 if radarr_ok and sonarr_ok else 503
    return web.json_response(
        {"status": status, "radarr": radarr_ok, "sonarr": sonarr_ok},
        status=http_status,
    )


async def _shutdown(
    signal_: signal.Signals,
    bot: MediaBot,
    shutdown_event: asyncio.Event,
    health_runner: web.AppRunner,
) -> None:
    """Handle SIGTERM/SIGINT — close the bot gracefully with a timeout."""
    if shutdown_event.is_set():
        return  # already shutting down
    shutdown_event.set()

    _logger.info(
        "Received %s, shutting down (timeout: %ss)...",
        signal_.name,
        SHUTDOWN_TIMEOUT,
    )

    try:
        async with asyncio.timeout(SHUTDOWN_TIMEOUT):
            await bot.close()
            await health_runner.cleanup()
    except TimeoutError:
        _logger.warning(
            "Shutdown timed out after %ss — forcing exit. "
            "Docker may send SIGKILL if the process doesn't terminate.",
            SHUTDOWN_TIMEOUT,
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
