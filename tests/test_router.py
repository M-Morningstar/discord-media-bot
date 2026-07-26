from __future__ import annotations

import pytest

from src.handler.router import Router, Service


def test_resolve_returns_radarr_for_radarr_channel() -> None:
    router = Router(radarr_channel_id=123, sonarr_channel_id=456)
    assert router.resolve(123) is Service.RADARR


def test_resolve_returns_sonarr_for_sonarr_channel() -> None:
    router = Router(radarr_channel_id=123, sonarr_channel_id=456)
    assert router.resolve(456) is Service.SONARR


def test_resolve_returns_none_for_unknown_channel() -> None:
    router = Router(radarr_channel_id=123, sonarr_channel_id=456)
    assert router.resolve(999) is None


def test_raises_value_error_for_identical_channel_ids() -> None:
    with pytest.raises(ValueError, match="must differ"):
        Router(radarr_channel_id=123, sonarr_channel_id=123)
