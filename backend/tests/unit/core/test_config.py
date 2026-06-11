from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.config import Settings, get_settings


def test_defaults() -> None:
    s = Settings()
    assert s.database_url.startswith("postgresql")
    assert s.t_amount == Decimal("10000")


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IC_T_AMOUNT", "5000")
    s = Settings()
    assert s.t_amount == Decimal("5000")


def test_get_settings_cached() -> None:
    assert get_settings() is get_settings()
