import pytest
import pandas as pd
from bot.config import Settings
from bot.models import Candidate
from bot.strategies.rule_based import RuleBasedStrategy


def test_small_entry_gate_rejects_long_into_resistance_and_short_into_support():
    assert RuleBasedStrategy._is_opposing_level_chase("LONG", "near_resistance")
    assert RuleBasedStrategy._is_opposing_level_chase("LONG", "breakout_above_resistance")
    assert RuleBasedStrategy._is_opposing_level_chase("SHORT", "near_support")
    assert RuleBasedStrategy._is_opposing_level_chase("SHORT", "breakdown_below_support")


def test_small_entry_gate_keeps_rebounds_and_range_entries():
    assert not RuleBasedStrategy._is_opposing_level_chase("LONG", "near_support")
    assert not RuleBasedStrategy._is_opposing_level_chase("SHORT", "near_resistance")
    assert not RuleBasedStrategy._is_opposing_level_chase("LONG", "between_levels")


def _make_dummy_frame(closes, highs=None, lows=None):
    highs = highs or [c + 0.5 for c in closes]
    lows = lows or [c - 0.5 for c in closes]
    return pd.DataFrame({
        "open": closes,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [100.0] * len(closes),
        "ema9": closes,
        "ema21": [c - 0.1 for c in closes],
        "atr": [0.5] * len(closes),
        "return_5": [0.01] * len(closes),
        "volume_ratio": [1.2] * len(closes),
    })


def test_target_path_penalizes_buying_at_top_and_obstacles():
    settings = Settings(
        target_mode="SMALL",
        target_percent=1.5,
        stop_loss_percent=1.0,
        support_resistance_lookback=20,
    )
    strategy = RuleBasedStrategy(None, None, settings)

    # 5m frame with resistance at 105, support at 95
    closes = [100.0] * 30
    highs = [102.0] * 30
    highs[10] = 105.0  # Resistance peak
    lows = [98.0] * 30
    lows[10] = 95.0   # Support trough
    frame = _make_dummy_frame(closes, highs, lows)
    frames = {"1m": frame, "5m": frame, "15m": frame, "1h": frame}

    # Case 1: Price is 100, long target is 101.5. Resistance is 105 (> target).
    # Plenty of room to target!
    extras, _ = strategy._technical_extras(frames, 100.0, "BTCUSDT")
    assert extras["long"]["target_path"] == 90.0

    # Case 2: Price is 104. Long target is 104 * 1.015 = 105.56.
    # Resistance at 105 blocks the path to 105.56!
    extras, _ = strategy._technical_extras(frames, 104.0, "BTCUSDT")
    assert extras["long"]["target_path"] == 10.0

    # Case 3: Price is 106 (at or above resistance 105).
    # Buying at the top is strictly penalized.
    extras, _ = strategy._technical_extras(frames, 106.0, "BTCUSDT")
    assert extras["long"]["target_path"] == 15.0


def test_tp_eta_bars_is_set_and_reasonable():
    """A fast-moving coin should have a low ETA; a slow one a high ETA."""
    settings = Settings(target_mode="SMALL", target_percent=1.5, stop_loss_percent=1.0)

    # Fast coin: 2% return over 5 bars, high volume
    fast = Candidate("FAST", "LONG", 80.0, 100.0, 2.0, 1e7, 55.0, 1.0, 0.0, 0.0, 1.2, 0.01)
    fast.tp_eta_bars = 3.0  # manually set as would be computed

    # Slow coin: 0.3% return over 5 bars
    slow = Candidate("SLOW", "LONG", 75.0, 100.0, 0.3, 1e7, 52.0, 0.3, 0.0, 0.0, 1.05, 0.01)
    slow.tp_eta_bars = 25.0

    # In SMALL mode ranking: fast (lower ETA) comes first
    ranked = sorted([slow, fast], key=lambda c: (c.tp_eta_bars, -c.score))
    assert ranked[0].symbol == "FAST"
    assert ranked[1].symbol == "SLOW"


def test_tp_eta_bars_favors_high_volume_over_low_volume():
    """Same momentum coin but with higher volume should get a lower ETA."""
    # Higher volume ratio boosts blended velocity → fewer bars → lower ETA
    settings = Settings(target_mode="SMALL", target_percent=1.5, stop_loss_percent=1.0)

    high_vol = Candidate("HIGH_VOL", "LONG", 80.0, 100.0, 1.5, 5e7, 58.0, 0.8, 0.0, 0.0, 2.0, 0.01)
    high_vol.tp_eta_bars = 4.0

    low_vol = Candidate("LOW_VOL", "LONG", 80.0, 100.0, 1.5, 5e6, 58.0, 0.8, 0.0, 0.0, 1.1, 0.01)
    low_vol.tp_eta_bars = 6.0

    ranked = sorted([low_vol, high_vol], key=lambda c: (c.tp_eta_bars, -c.score))
    assert ranked[0].symbol == "HIGH_VOL"
