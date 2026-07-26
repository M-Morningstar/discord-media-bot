from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast

import aiohttp


class BaseArrService(ABC):
    """Abstract base for Radarr and Sonarr API clients.

    Provides shared HTTP infrastructure (session, auth, timeouts).
    Subclasses must implement :meth:`lookup` and :meth:`add`.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        api_key: str,
        timeout: int = 30,
    ) -> None:
        self._session = session
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Abstract — subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    async def lookup(self, imdb_id: str) -> dict[str, Any]:
        """Look up media by IMDB ID.

        Args:
            imdb_id: Lowercase IMDB ID like ``"tt1234567"``.

        Returns:
            The parsed JSON response from the API's lookup endpoint.

        Raises:
            LookupError: If no results are found for the given IMDB ID.
            aiohttp.ClientError: If the HTTP request fails.
        """
        ...

    @abstractmethod
    async def add(
        self,
        data: dict[str, Any],
        quality_profile_id: int,
        root_folder: str,
    ) -> dict[str, Any]:
        """Add media for download.

        Args:
            data: The result from :meth:`lookup`, modified with quality
                  profile and root folder settings.
            quality_profile_id: The quality profile ID to use.
            root_folder: The root folder path for downloads.

        Returns:
            The parsed JSON response from the API's add endpoint.

        Raises:
            aiohttp.ClientError: If the HTTP request fails.
        """
        ...

    # ------------------------------------------------------------------
    # Shared helpers — usable by subclasses
    # ------------------------------------------------------------------

    async def _get(self, path: str) -> dict[str, Any]:
        """Perform a GET request and return parsed JSON."""
        url = f"{self._base_url}{path}"
        async with self._session.get(
            url,
            headers={"X-Api-Key": self._api_key},
            timeout=aiohttp.ClientTimeout(total=self._timeout),
        ) as resp:
            resp.raise_for_status()
            return cast(dict[str, Any], await resp.json())

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Perform a POST request with a JSON body and return parsed JSON."""
        url = f"{self._base_url}{path}"
        async with self._session.post(
            url,
            headers={"X-Api-Key": self._api_key},
            json=body,
            timeout=aiohttp.ClientTimeout(total=self._timeout),
        ) as resp:
            resp.raise_for_status()
            return cast(dict[str, Any], await resp.json())


__all__ = ["BaseArrService"]
