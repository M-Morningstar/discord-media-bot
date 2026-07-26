from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlparse


class ConfigurationError(Exception):
    """Raised when configuration is invalid at startup.

    Collects all errors before raising so the user sees every issue at once,
    not one-at-a-time fix-and-retry.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = "Configuration errors found:\n  - " + "\n  - ".join(errors)
        super().__init__(message)


@dataclass(frozen=True)
class Config:
    """Immutable configuration loaded from environment variables.

    All required fields are validated at load time.  The dataclass is frozen
    so no part of the application can accidentally mutate config values.
    """

    # -- Discord ------------------------------------------------------------------
    discord_bot_token: str
    discord_radarr_channel_id: int
    discord_sonarr_channel_id: int

    # -- Radarr -------------------------------------------------------------------
    radarr_url: str
    radarr_api_key: str
    radarr_quality_profile_id: int
    radarr_root_folder_path: str

    # -- Sonarr -------------------------------------------------------------------
    sonarr_url: str
    sonarr_api_key: str
    sonarr_quality_profile_id: int
    sonarr_root_folder_path: str

    # -- Optional -----------------------------------------------------------------
    log_level: str = "INFO"
    http_timeout: int = 30
    http_max_retries: int = 3
    radarr_search_on_add: bool = True
    sonarr_search_on_add: bool = True
    sonarr_season_folder: bool = True
    health_check_port: int = 8080

    # -- Internal (not from env) --------------------------------------------------
    _masked_fields: tuple[str, ...] = field(
        default=(
            "discord_bot_token",
            "radarr_api_key",
            "sonarr_api_key",
        ),
        repr=False,
        init=False,
        compare=False,
    )

    # --------------------------------------------------------------------------
    # Factory
    # --------------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> Config:
        errors: list[str] = []

        # --- Discord -----------------------------------------------------------
        token = _get_str("DISCORD_BOT_TOKEN", errors)
        radarr_ch = _get_int("DISCORD_RADARR_CHANNEL_ID", errors)
        sonarr_ch = _get_int("DISCORD_SONARR_CHANNEL_ID", errors)

        # --- Radarr -------------------------------------------------------------
        radarr_url = _get_url("RADARR_URL", errors)
        radarr_key = _get_str("RADARR_API_KEY", errors)
        radarr_profile = _get_int("RADARR_QUALITY_PROFILE_ID", errors)
        radarr_root = _get_str("RADARR_ROOT_FOLDER_PATH", errors)

        # --- Sonarr -------------------------------------------------------------
        sonarr_url = _get_url("SONARR_URL", errors)
        sonarr_key = _get_str("SONARR_API_KEY", errors)
        sonarr_profile = _get_int("SONARR_QUALITY_PROFILE_ID", errors)
        sonarr_root = _get_str("SONARR_ROOT_FOLDER_PATH", errors)

        # --- Optional -----------------------------------------------------------
        log_level = _get_choice("LOG_LEVEL", {"DEBUG", "INFO", "WARNING", "ERROR"}, "INFO", errors)
        timeout = _get_positive_int("HTTP_TIMEOUT", 30, errors)
        retries = _get_positive_int("HTTP_MAX_RETRIES", 3, errors)
        radarr_search = _get_bool("RADARR_SEARCH_ON_ADD", True)
        sonarr_search = _get_bool("SONARR_SEARCH_ON_ADD", True)
        sonarr_folder = _get_bool("SONARR_SEASON_FOLDER", True)
        health_port = _get_port("HEALTH_CHECK_PORT", 8080, errors)

        # --- Channel snowflake validation ---------------------------------------
        if radarr_ch is not None and not _is_snowflake(radarr_ch):
            errors.append("DISCORD_RADARR_CHANNEL_ID is not a valid Discord snowflake")
        if sonarr_ch is not None and not _is_snowflake(sonarr_ch):
            errors.append("DISCORD_SONARR_CHANNEL_ID is not a valid Discord snowflake")

        if errors:
            raise ConfigurationError(errors)

        assert radarr_ch is not None and sonarr_ch is not None  # for type-narrower
        return cls(
            discord_bot_token=token,  # type: ignore[arg-type]
            discord_radarr_channel_id=radarr_ch,
            discord_sonarr_channel_id=sonarr_ch,
            radarr_url=radarr_url,  # type: ignore[arg-type]
            radarr_api_key=radarr_key,  # type: ignore[arg-type]
            radarr_quality_profile_id=radarr_profile,  # type: ignore[arg-type]
            radarr_root_folder_path=radarr_root,  # type: ignore[arg-type]
            sonarr_url=sonarr_url,  # type: ignore[arg-type]
            sonarr_api_key=sonarr_key,  # type: ignore[arg-type]
            sonarr_quality_profile_id=sonarr_profile,  # type: ignore[arg-type]
            sonarr_root_folder_path=sonarr_root,  # type: ignore[arg-type]
            log_level=log_level,
            http_timeout=timeout,
            http_max_retries=retries,
            radarr_search_on_add=radarr_search,
            sonarr_search_on_add=sonarr_search,
            sonarr_season_folder=sonarr_folder,
            health_check_port=health_port,
        )

    # --------------------------------------------------------------------------
    # Safe repr (masks secrets)
    # --------------------------------------------------------------------------

    def __repr__(self) -> str:
        fields = []
        for f_name in self.__dataclass_fields__:
            val = getattr(self, f_name)
            if f_name in self._masked_fields:
                val = "***"
            fields.append(f"{f_name}={val!r}")
        return f"Config({', '.join(fields)})"


# ==============================================================================
# Helper readers — each is responsible for a single env var pattern
# ==============================================================================


def _get_str(key: str, errors: list[str]) -> str | None:
    val = os.environ.get(key, "").strip()
    if not val:
        errors.append(f"{key} is required and must be non-empty")
        return None
    return val


def _get_int(key: str, errors: list[str]) -> int | None:
    raw = os.environ.get(key, "").strip()
    if not raw:
        errors.append(f"{key} is required and must be an integer")
        return None
    try:
        return int(raw)
    except ValueError:
        errors.append(f"{key} must be an integer, got {raw!r}")
        return None


def _get_positive_int(key: str, default: int, errors: list[str]) -> int:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        errors.append(f"{key} must be an integer, got {raw!r}")
        return default  # still return default so parsing can continue
    if val <= 0:
        errors.append(f"{key} must be positive, got {val}")
        return default
    return val


def _get_url(key: str, errors: list[str]) -> str | None:
    val = os.environ.get(key, "").strip()
    if not val:
        errors.append(f"{key} is required and must be a valid URL")
        return None
    # Strip trailing slash for consistency
    val = val.rstrip("/")
    parsed = urlparse(val)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        errors.append(f"{key} is not a valid HTTP(S) URL: {val!r}")
        return None
    return val


def _get_choice(key: str, allowed: set[str], default: str, errors: list[str]) -> str:
    raw = os.environ.get(key, "").strip().upper()
    if not raw:
        return default
    if raw not in allowed:
        errors.append(f"{key} must be one of {sorted(allowed)}, got {raw!r}")
        return default
    return raw


def _get_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if not raw:
        return default
    return raw in ("true", "1", "yes", "on")


def _get_port(key: str, default: int, errors: list[str]) -> int:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        errors.append(f"{key} must be an integer, got {raw!r}")
        return default
    if not 1 <= val <= 65535:
        errors.append(f"{key} must be between 1-65535, got {val}")
        return default
    return val


def _is_snowflake(value: int) -> bool:
    """Discord snowflakes are 17-20 digit integers."""
    return 10**16 <= value < 10**20
