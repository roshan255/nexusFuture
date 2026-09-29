import pandas as pd
from bot.indicators import enrich, vwap


def test_indicators():
    f = pd.DataFrame({
        "open": range(1, 40),
        "high": range(2, 41),
        "low": range(0, 39),
        "close": range(1, 40),
        "volume": [10.0] * 39,
    })
    x = enrich(f)
    assert x.ema9.iloc[-1] > x.ema21.iloc[-1]
    assert x.atr.iloc[-1] > 0


def test_daily_anchored_vwap():
    # Timestamps spanning two days: day 1 (1727568000000 = 2024-09-29 00:00 UTC), day 2 (1727654400000 = 2024-09-30 00:00 UTC)
    t1 = 1727568000000
    t2 = 1727654400000
    frame = pd.DataFrame({
        "time": [t1, t1 + 300000, t2, t2 + 300000],
        "high": [100.0, 110.0, 200.0, 210.0],
        "low": [98.0, 108.0, 198.0, 208.0],
        "close": [99.0, 109.0, 199.0, 209.0],
        "volume": [10.0, 10.0, 5.0, 5.0],
    })
    result = vwap(frame)
    # Day 2 VWAP should reset and reflect only Day 2 prices (~200+), not be dragged down by Day 1 (~100)
    assert result.iloc[2] > 190.0
