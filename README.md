# Discord Media Bot

A Discord bot that automates adding movies and TV shows to **Radarr** and **Sonarr** via IMDB ID. Just paste an IMDB link (or `ttXXXXXXX` ID) in a Discord channel, and the bot handles the rest.

## Features

- **Movie requests** — Paste an IMDB link in the Radarr channel → bot looks it up on Radarr and adds it
- **TV series requests** — Same for Sonarr in the TV channel
- **Multiple IDs** — Handles one or multiple IMDB IDs in a single message
- **Duplicate detection** — Won't re-add something already in your library
- **Rich embeds** — Replies with a pretty embed showing title, year, poster, and overview

## Setup

### Prerequisites

- Python 3.12+
- A running [Radarr](https://radarr.video/) instance
- A running [Sonarr](https://sonarr.tv/) instance
- A [Discord bot application](https://discord.com/developers/applications)

### Quick start

```bash
# Clone and enter the directory
git clone <your-repo-url> && cd discord-media-bot

# Create a virtual environment
python3 -m venv .venv && source .venv/bin/activate

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
| `DISCORD_RADARR_CHANNEL_ID` | ✅ | Channel ID for movie requests |
| `DISCORD_SONARR_CHANNEL_ID` | ✅ | Channel ID for TV series requests |
| `RADARR_URL` | ✅ | Radarr API URL |
| `RADARR_API_KEY` | ✅ | Radarr API key |
| `SONARR_URL` | ✅ | Sonarr API URL |
| `SONARR_API_KEY` | ✅ | Sonarr API key |

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
```

## Disclaimer

> This bot is a tool for automating media requests through Radarr and Sonarr — legitimate applications for managing your personal media library. It is designed for use with content you have legally acquired or have the rights to access.
>
> The developers do not condone, encourage, or support copyright infringement or the downloading of copyrighted material without permission. Users are solely responsible for complying with all applicable laws in their jurisdiction.
>
> **THE SOFTWARE IS PROVIDED "AS IS"**, without warranty of any kind, as stated in the [MIT License](LICENSE).

## License

[MIT](LICENSE)
