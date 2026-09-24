from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bot.indicators import enrich


@dataclass(frozen=True)
class TargetFirstResult:
    outcome: str
    bars_to_outcome: int | None


def target_first(candles: pd.DataFrame, entry_index: int, direction: str, target_percent: float, stop_percent: float, horizon_bars: int) -> TargetFirstResult:
    """Checks intra-candle highs/lows in order, excluding ambiguous bars that touch both."""
    entry = float(candles.close.iloc[entry_index])
    target = entry * (1 + target_percent / 100) if direction == "LONG" else entry * (1 - target_percent / 100)
    stop = entry * (1 - stop_percent / 100) if direction == "LONG" else entry * (1 + stop_percent / 100)
    end = min(len(candles), entry_index + horizon_bars + 1)
    for index in range(entry_index + 1, end):
        high, low = float(candles.high.iloc[index]), float(candles.low.iloc[index])
        hit_target = high >= target if direction == "LONG" else low <= target
        hit_stop = low <= stop if direction == "LONG" else high >= stop
        if hit_target and hit_stop:
            return TargetFirstResult("AMBIGUOUS", index - entry_index)
        if hit_target:
            return TargetFirstResult("TARGET", index - entry_index)
        if hit_stop:
            return TargetFirstResult("STOP", index - entry_index)
    return TargetFirstResult("NO_HIT", None)


def technical_direction(frame: pd.DataFrame) -> str | None:
    latest = frame.iloc[-1]
    long_votes = sum((latest.ema9 > latest.ema21, latest.sma20 > latest.sma50, latest.macd_histogram > 0, latest.close > latest.vwap, latest.plus_di > latest.minus_di, latest.rsi >= 55))
    short_votes = 6 - long_votes
    if long_votes == short_votes:
        return None
    return "LONG" if long_votes > short_votes else "SHORT"


def compare_direction_bias(candles: pd.DataFrame, target_percent: float, stop_percent: float, horizon_bars: int, step: int) -> dict[str, int | float]:
    enriched = enrich(candles)
    original_wins = original_losses = opposite_wins = opposite_losses = ambiguous = no_hit = samples = 0
    for index in range(200, len(enriched) - horizon_bars, step):
        direction = technical_direction(enriched.iloc[:index + 1])
        if not direction:
            continue
        opposite = "SHORT" if direction == "LONG" else "LONG"
        original = target_first(enriched, index, direction, target_percent, stop_percent, horizon_bars)
        inverse = target_first(enriched, index, opposite, target_percent, stop_percent, horizon_bars)
        if original.outcome == "AMBIGUOUS" or inverse.outcome == "AMBIGUOUS":
            ambiguous += 1
            continue
        if original.outcome == "NO_HIT" or inverse.outcome == "NO_HIT":
            no_hit += 1
            continue
        samples += 1
        original_wins += original.outcome == "TARGET"
        original_losses += original.outcome == "STOP"
        opposite_wins += inverse.outcome == "TARGET"
        opposite_losses += inverse.outcome == "STOP"
    original_rate = original_wins / samples * 100 if samples else 0.0
    opposite_rate = opposite_wins / samples * 100 if samples else 0.0
    return {"samples": samples, "original_wins": original_wins, "original_losses": original_losses, "original_win_rate": round(original_rate, 2), "opposite_wins": opposite_wins, "opposite_losses": opposite_losses, "opposite_win_rate": round(opposite_rate, 2), "opposite_minus_original": round(opposite_rate - original_rate, 2), "ambiguous": ambiguous, "no_hit": no_hit}
