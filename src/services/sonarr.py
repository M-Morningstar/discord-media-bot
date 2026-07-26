from __future__ import annotations

from typing import Any

from src.services.base import BaseArrService
from src.services.retry import retry


class SonarrService(BaseArrService):
    """Sonarr API client for TV series lookup and download requests."""

    @retry(max_attempts=3)
    async def lookup(self, imdb_id: str) -> dict[str, Any]:
        """Look up a TV series by IMDB ID via the Sonarr API.

        Args:
            imdb_id: Lowercase IMDB ID like ``"tt1234567"``.

        Returns:
            The first series object from the lookup response.

        Raises:
            LookupError: If no series is found for the given IMDB ID.
        """
        path = f"/api/v3/series/lookup?term=imdb:{imdb_id}"
        series_list = await self._get_list(path)
        if not series_list:
            raise LookupError(f"No series found for IMDB ID: {imdb_id!r}")
        return series_list[0]

    async def find_in_library(self, imdb_id: str) -> dict[str, Any] | None:
        """Check if a series with the given IMDB ID is already in Sonarr's library.

        Args:
            imdb_id: Lowercase IMDB ID like ``"tt1234567"``.

        Returns:
            The existing series entry if found, ``None`` otherwise.
        """
        series_list = await self._get_list("/api/v3/series")
        for series in series_list:
            if series.get("imdbId") == imdb_id:
                return series
        return None

    @retry(max_attempts=3)
    async def add(
        self,
        data: dict[str, Any],
        quality_profile_id: int,
        root_folder: str,
    ) -> dict[str, Any]:
        """Add a TV series for download via the Sonarr API.

        Args:
            data: The series object returned by :meth:`lookup`.
            quality_profile_id: The quality profile ID to use.
            root_folder: The root folder path for downloads.

        Returns:
            The parsed JSON response from the ``/api/v3/series`` POST endpoint.
        """
        payload = {
            **data,
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": root_folder,
            "monitored": True,
            "addOptions": {
                "searchForMissingEpisodes": True,
            },
        }
        return await self._post("/api/v3/series", payload)


__all__ = ["SonarrService"]
