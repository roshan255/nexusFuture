import json
from datetime import date, timedelta
import time

from bot.config import Settings
from bot.services.trade_limits import TradeLimitService


def test_trade_limits_persistence(tmp_path):
    state_file = tmp_path / "trade_limits.json"
    settings = Settings(cooldown_seconds=60, max_trades_per_day=3)
    service = TradeLimitService(settings, state_path=state_file)

    allowed, reason = service.allow_entry()
    assert allowed is True
    assert reason == ""

    # Record first entry
    service.record_entry()
    assert service.entries == 1
    assert state_file.exists()

    # Second entry should be blocked by cooldown
    allowed, reason = service.allow_entry()
    assert allowed is False
    assert "cooldown_" in reason

    # Simulate restart by creating a new service instance with same state file
    service_restarted = TradeLimitService(settings, state_path=state_file)
    assert service_restarted.entries == 1
    allowed, reason = service_restarted.allow_entry()
    assert allowed is False
    assert "cooldown_" in reason


def test_trade_limits_max_per_day(tmp_path):
    state_file = tmp_path / "trade_limits.json"
    settings = Settings(cooldown_seconds=0, max_trades_per_day=2)
    service = TradeLimitService(settings, state_path=state_file)

    assert service.allow_entry()[0] is True
    service.record_entry()
    assert service.allow_entry()[0] is True
    service.record_entry()

    allowed, reason = service.allow_entry()
    assert allowed is False
    assert reason == "max_trades_per_day"


def test_trade_limits_date_rollover(tmp_path):
    state_file = tmp_path / "trade_limits.json"
    yesterday = date.today() - timedelta(days=1)
    state_file.write_text(json.dumps({
        "day": yesterday.isoformat(),
        "entries": 5,
        "last_entry_time": time.time() - 3600
    }), encoding="utf-8")

    settings = Settings(cooldown_seconds=60, max_trades_per_day=5)
    service = TradeLimitService(settings, state_path=state_file)

    # When allow_entry is checked, day mismatch triggers reset
    allowed, reason = service.allow_entry()
    assert allowed is True
    assert service.entries == 0
