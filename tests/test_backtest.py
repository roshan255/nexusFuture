import pandas as pd

from bot.backtest import target_first


def _candles(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


def test_target_first_records_target_before_stop_for_long():
    candles = _candles([[100, 100, 100, 100], [100, 102, 99.5, 101]])
    assert target_first(candles, 0, "LONG", 1.5, 1.0, 1).outcome == "TARGET"


def test_target_first_marks_same_candle_collision_ambiguous():
    candles = _candles([[100, 100, 100, 100], [100, 102, 98, 100]])
    assert target_first(candles, 0, "LONG", 1.5, 1.0, 1).outcome == "AMBIGUOUS"
