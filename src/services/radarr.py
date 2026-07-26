from __future__ import annotations

from typing import Any

from src.services.base import BaseArrService
from src.services.retry import retry


class RadarrService(BaseArrService):
    """Radarr API client for movie lookup and download requests."""

    @retry(max_attempts=3)
    async def lookup(self, imdb_id: str) -> dict[str, Any]:
        """Look up a movie by IMDB ID via the Radarr API.

        Args:
            imdb_id: Lowercase IMDB ID like ``"tt1234567"``.

        Returns:
            The first movie object from the lookup response.

        Raises:
            LookupError: If no movie is found for the given IMDB ID.
        """
        path = f"/api/v3/movie/lookup?term=imdb:{imdb_id}"
        movies = await self._get_list(path)
        if not movies:
            raise LookupError(f"No movie found for IMDB ID: {imdb_id!r}")
        return movies[0]

    async def find_in_library(self, imdb_id: str) -> dict[str, Any] | None:
        """Check if a movie with the given IMDB ID is already in Radarr's library.

        Args:
            imdb_id: Lowercase IMDB ID like ``"tt1234567"``.

        Returns:
            The existing movie entry if found, ``None`` otherwise.
        """
        movies = await self._get_list("/api/v3/movie")
        for movie in movies:
            if movie.get("imdbId") == imdb_id:
                return movie
        return None

    @retry(max_attempts=3)
    async def add(
        self,
        data: dict[str, Any],
        quality_profile_id: int,
        root_folder: str,
    ) -> dict[str, Any]:
        """Add a movie for download via the Radarr API.

        Args:
            data: The result from :meth:`lookup`, modified with quality
                  profile and root folder settings.
            quality_profile_id: The quality profile ID to use.
            root_folder: The root folder path for downloads.

        Returns:
            The parsed JSON response from the ``/api/v3/movie`` POST endpoint.
        """
        payload = {
            **data,
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": root_folder,
            "monitored": True,
        }
        return await self._post("/api/v3/movie", payload)


__all__ = ["RadarrService"]
