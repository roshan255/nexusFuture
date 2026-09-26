
import pytest

from bot.config import load_settings


def test_small_mode_rejects_unsafe_target(monkeypatch):
    monkeypatch.setenv("TARGET_MODE", "SMALL")
    monkeypatch.setenv("TARGET_PERCENT", "0.3")
    with pytest.raises(ValueError, match="SMALL TARGET_PERCENT"):
        load_settings()


def test_large_mode_accepts_large_target(monkeypatch):
    monkeypatch.setenv("TARGET_MODE", "LARGE")
    monkeypatch.setenv("TARGET_PERCENT", "25")
    assert load_settings().target_mode == "LARGE"


def test_reverse_signal_direction_is_opt_in(monkeypatch):
    monkeypatch.setenv("REVERSE_SIGNAL_DIRECTION", "true")
    assert load_settings().reverse_signal_direction is True


def test_support_resistance_settings_are_loaded(monkeypatch):
    monkeypatch.setenv("SUPPORT_RESISTANCE_LOOKBACK", "60")
    monkeypatch.setenv("SUPPORT_RESISTANCE_ZONE_ATR", "0.5")
    assert load_settings().support_resistance_lookback == 60
    assert load_settings().support_resistance_zone_atr == 0.5
