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


def test_small_target_first_settings_are_loaded(monkeypatch):
    monkeypatch.setenv("SMALL_TARGET_MAX_ATR", "2.5")
    monkeypatch.setenv("SMALL_TARGET_MIN_SPEED_SCORE", "70")
    assert load_settings().small_target_max_atr == 2.5
    assert load_settings().small_target_min_speed_score == 70


def test_small_avoid_opposing_level_entries_defaults_to_true(monkeypatch):
    monkeypatch.delenv("SMALL_AVOID_OPPOSING_LEVEL_ENTRIES", raising=False)
    assert load_settings().small_avoid_opposing_level_entries is True


def test_small_anti_top_and_clearance_settings(monkeypatch):
    monkeypatch.setenv("SMALL_MAX_RSI", "62")
    monkeypatch.setenv("SMALL_MIN_RSI", "38")
    monkeypatch.setenv("SMALL_MIN_CLEARANCE_PERCENT", "2.0")
    monkeypatch.setenv("SMALL_MAX_EMA_DISTANCE_ATR", "1.8")
    settings = load_settings()
    assert settings.small_max_rsi == 62.0
    assert settings.small_min_rsi == 38.0
    assert settings.small_min_clearance_percent == 2.0
    assert settings.small_max_ema_distance_atr == 1.8
