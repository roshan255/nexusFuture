
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
