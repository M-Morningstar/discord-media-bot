from __future__ import annotations

from enum import StrEnum


class Service(StrEnum):
    RADARR = "radarr"
    SONARR = "sonarr"


class Router:
    """Maps Discord channel IDs to media services."""

    def __init__(self, radarr_channel_id: int, sonarr_channel_id: int) -> None:
        if radarr_channel_id == sonarr_channel_id:
            raise ValueError(
                f"Radarr and Sonarr channel IDs must differ: both are {radarr_channel_id}"
            )
        self._map: dict[int, Service] = {
            radarr_channel_id: Service.RADARR,
            sonarr_channel_id: Service.SONARR,
        }

    def resolve(self, channel_id: int) -> Service | None:
        """Return the service for *channel_id*, or ``None`` if not a configured channel."""
        return self._map.get(channel_id)


__all__ = ["Router", "Service"]
