# Discord Media Bot

[![CI](https://github.com/M-Morningstar/discord-media-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/M-Morningstar/discord-media-bot/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A Discord bot that automates adding movies and TV shows to **Radarr** and **Sonarr** via IMDB ID. Just paste an IMDB link (or `ttXXXXXXX` ID) in a Discord channel, and the bot handles the rest.

## Features

- **Movie requests** — Paste an IMDB link in the Radarr channel → bot looks it up on Radarr and adds it
- **TV series requests** — Same for Sonarr in the TV channel
- **Duplicate detection** — Won't re-add something already in your library
- **Rich embeds** — Replies with a pretty embed showing title, year, poster, and overview
- **Retry with backoff** — Transient API failures are retried (exponential backoff: 1s, 2s, 4s)
- **Health check** — HTTP endpoint on `:8080/health` for Docker HEALTHCHECK and monitoring
- **Structured logging** — JSON logs in Docker, human-readable in terminal

## Setup

### Prerequisites

- Python 3.12+
- A running [Radarr](https://radarr.video/) instance
- A running [Sonarr](https://sonarr.tv/) instance
- A [Discord bot application](https://discord.com/developers/applications)

### Quick start

```bash
# Clone and enter the directory
git clone https://github.com/M-Morningstar/discord-media-bot.git && cd discord-media-bot

# Create a virtual environment with uv
uv venv && source .venv/bin/activate

# Install with dev dependencies
uv pip install -e ".[dev]"

# Copy and fill in your config
cp .env.example .env
# Edit .env with your Discord token, Radarr/Sonarr URLs, API keys, etc.

# Run
python -m src.main
```

### Docker

```bash
# Build
docker build -t discord-media-bot .

# Run
docker run -d \
  --name discord-media-bot \
  --restart unless-stopped \
  --env-file .env \
  discord-media-bot
```

See `docker-compose.yml` and `docker-compose.prod.yml` for production deployment.

## Configuration

All configuration is via environment variables (see `.env.example` for full docs).

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | ✅ | Discord bot token |
| `DISCORD_RADARR_CHANNEL_ID` | ✅ | Channel ID for movie requests (17-20 digit snowflake) |
| `DISCORD_SONARR_CHANNEL_ID` | ✅ | Channel ID for TV series requests (17-20 digit snowflake) |
| `RADARR_URL` | ✅ | Radarr API URL (e.g. `http://192.168.1.100:7878`) |
| `RADARR_API_KEY` | ✅ | Radarr API key |
| `RADARR_QUALITY_PROFILE_ID` | ✅ | Quality profile ID from Radarr |
| `RADARR_ROOT_FOLDER_PATH` | ✅ | Root folder path (e.g. `/movies`) |
| `SONARR_URL` | ✅ | Sonarr API URL (e.g. `http://192.168.1.100:8989`) |
| `SONARR_API_KEY` | ✅ | Sonarr API key |
| `SONARR_QUALITY_PROFILE_ID` | ✅ | Quality profile ID from Sonarr |
| `SONARR_ROOT_FOLDER_PATH` | ✅ | Root folder path (e.g. `/tv`) |
| `LOG_LEVEL` | — | `DEBUG`, `INFO`, `WARNING`, or `ERROR` (default: `INFO`) |
| `HTTP_TIMEOUT` | — | HTTP request timeout in seconds (default: `30`) |
| `HTTP_MAX_RETRIES` | — | Max retries for transient failures (default: `3`) |
| `RADARR_SEARCH_ON_ADD` | — | Search for movie immediately after adding (default: `true`) |
| `SONARR_SEARCH_ON_ADD` | — | Search for episodes immediately after adding (default: `true`) |
| `SONARR_SEASON_FOLDER` | — | Create season folders for TV series (default: `true`) |
| `HEALTH_CHECK_PORT` | — | Port for the health check HTTP server (default: `8080`) |

## Discord Setup

1. Go to https://discord.com/developers/applications → New Application → "Media Bot"
2. Bot tab → Add Bot → **enable Message Content Intent** (Privileged Gateway Intents)
3. Reset Token → copy it (`DISCORD_BOT_TOKEN`)
4. OAuth2 → URL Generator → scopes: `bot`, permissions: `Read Messages`, `Send Messages`, `Embed Links`, `Read Message History`
5. Open the generated URL to invite the bot to your server
6. Enable Developer Mode (User Settings → Advanced), right-click your channels → Copy ID

## Usage

Post an IMDB ID in the configured channel:

```
tt37287335
```

Or a full URL — the bot extracts the ID automatically:

```
https://www.imdb.com/title/tt37287335/
```

The bot replies with a Discord embed:

- **Green** — media added successfully (title, year, poster, overview)
- **Yellow** — already in your library
- **Red** — error (not found, service unavailable, invalid ID)

**One IMDB ID per message.** Multi-ID messages are rejected.

## Docker Networking

| Scenario | Config |
|---|---|
| Radarr/Sonarr on same Docker host | Join an external network, use container name as URL |
| Radarr/Sonarr on bare metal (same host) | `extra_hosts: ["host.docker.internal:host-gateway"]`, use `host.docker.internal` |
| Radarr/Sonarr on remote server | Use their real IP/domain — no Docker network config needed |

A production compose override (`docker-compose.prod.yml`) is included for joining an existing network.

## Health Check

```bash
curl http://localhost:8080/health
# {"status": "ok", "radarr": true, "sonarr": true}
```

Returns HTTP 200 when all services are reachable, 503 if degraded. Docker HEALTHCHECK uses Python `urllib.request` (stdlib, no curl needed in the container).

## Architecture

```
Discord message → MediaBot.on_message()
  → Router (channel → Radarr/Sonarr)
  → IMDB validator (extract & validate ID)
  → RadarrService / SonarrService (lookup + add with retry)
  → DiscordReporter (embed reply)
```

| Component | File | Role |
|---|---|---|
| Config | `src/config.py` | Frozen dataclass, env var loading with full validation |
| Validator | `src/validators/imdb.py` | IMDB ID extraction (`\btt\d{7,8}\b` regex) |
| Retry | `src/services/retry.py` | Exponential backoff decorator (1s, 2s, 4s) |
| Services | `src/services/radarr.py`, `src/services/sonarr.py` | API clients with Content-Type safety |
| Router | `src/handler/router.py` | Channel ID → Service mapping |
| Handler | `src/handler/message_handler.py` | Orchestrator — catches all exceptions |
| Reporter | `src/reporting/discord_reporter.py` | Discord embed builders |
| Bot | `src/bot/client.py` | Discord client (on_ready, on_message) |
| Main | `src/main.py` | Wiring, health check server, signal handlers |

## Troubleshooting

**Bot doesn't respond** → Enable **Message Content Intent** in Discord Developer Portal (Bot → Privileged Gateway Intents). The bot exits at startup if this is missing.

**"Invalid Discord bot token"** → Regenerate the token in the Developer Portal. Old tokens stop working after reset.

**"Service unavailable"** → Verify Radarr/Sonarr are running and reachable. Test: `curl <url>/api/v3/system/status?apikey=<key>`.

**"No media found" for a valid ID** → Some IMDB entries aren't in TMDB/TVDB. Verify the ID is `tt` + 7-8 digits. Try searching manually in Radarr/Sonarr.

**Docker HEALTHCHECK fails** → `curl http://localhost:8080/health` directly. No curl in the container image — the health check uses Python stdlib.

## Development

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/ --strict

# Test
pytest -v --cov=src

# Regenerate lockfile
uv pip compile --output-file=requirements.txt pyproject.toml
```

## Disclaimer

> This bot is a tool for automating media requests through Radarr and Sonarr — legitimate applications for managing your personal media library. It is designed for use with content you have legally acquired or have the rights to access.
>
> The developers do not condone, encourage, or support copyright infringement or the downloading of copyrighted material without permission. Users are solely responsible for complying with all applicable laws in their jurisdiction.
>
> **THE SOFTWARE IS PROVIDED "AS IS"**, without warranty of any kind, as stated in the [MIT License](LICENSE).

## License

[MIT](LICENSE)
