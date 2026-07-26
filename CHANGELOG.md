# Changelog

## v1.0.0 — 2026-07-26

### Added

- Initial release of Discord Media Bot
- IMDB ID extraction and validation via `\btt\d{7,8}\b` regex
- Radarr API client: movie lookup and add with retry
- Sonarr API client: series lookup and add with retry
- Two-channel routing (one for Radarr, one for Sonarr)
- Discord embed responses (success, already-exists, not-found, validation-error, service-unavailable, unexpected-error)
- Exponential backoff retry decorator (1s, 2s, 4s) for transient HTTP failures
- Content-Type safety for API responses (guards against proxy HTML error pages)
- Structured JSON logging in Docker, human-readable in terminal
- Health check HTTP endpoint (`:8080/health`) with Radarr/Sonarr status reporting, used by Docker HEALTHCHECK (stdlib `urllib`, no curl needed)
- Graceful shutdown on SIGTERM/SIGINT with 10s timeout
- Immutable configuration dataclass with masked `__repr__`
- Multi-stage Dockerfile running as `nobody` user
- `docker-compose.yml` and `docker-compose.prod.yml` with external network support
- `.env.example` with all environment variables documented
- GitHub Actions CI: lint, type-check, test (≥80% coverage), lockfile verification, Docker build
- 69 unit tests across validators, services, retry, router, reporter, and message handler
- `pyproject.toml` with ruff, mypy, and pytest configuration
- `Makefile` with convenience targets
- MIT license
