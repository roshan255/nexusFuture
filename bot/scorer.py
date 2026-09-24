from __future__ import annotations

import math

from bot.models import Candidate


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _number(row, name: str, default: float = 0.0) -> float:
    value = getattr(row, name, default)
    return default if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)


def score(symbol, price, change, quote_volume, latest, oi_change, funding, taker_ratio, imbalance, spread, weights, extra=None) -> Candidate:
    ema_bullish = _number(latest, "ema9") > _number(latest, "ema21")
    sma_bullish = _number(latest, "sma20", price) > _number(latest, "sma50", price)
    macro_bullish = _number(latest, "sma50", price) > _number(latest, "sma200", price)
    trend = 25 * sum((ema_bullish, sma_bullish, macro_bullish, _number(latest, "close", price) > _number(latest, "vwap", price)))
    momentum = _clamp(50 + _number(latest, "return_5") * 5000)
    volume = _clamp(_number(latest, "volume_ratio", 1) * 50)
    open_interest = _clamp(50 + oi_change * 1000)
    taker = _clamp(50 + (taker_ratio - 1) * 100)
    orderbook = _clamp(50 + imbalance * 100)
    macd = 100 if _number(latest, "macd_histogram") > 0 else 0
    stochastic = _clamp(50 + (_number(latest, "stoch_rsi_k", 50) - _number(latest, "stoch_rsi_d", 50)))
    vwap = 100 if _number(latest, "close", price) > _number(latest, "vwap", price) else 0
    bollinger = _clamp(50 + ((_number(latest, "close", price) - _number(latest, "bb_middle", price)) / max(price, 1e-12)) * 5000)
    adx = _clamp(_number(latest, "adx") * 2.5)
    long = {"trend": trend, "momentum": momentum, "volume": volume, "open_interest": open_interest, "taker": taker, "orderbook": orderbook, "funding": _clamp(50 - funding * 100000), "macd": macd, "stoch_rsi": stochastic, "vwap": vwap, "bollinger": bollinger, "adx": adx}
    short = {"trend": 100 - trend, "momentum": 100 - momentum, "volume": volume, "open_interest": open_interest, "taker": 100 - taker, "orderbook": 100 - orderbook, "funding": _clamp(50 + funding * 100000), "macd": 100 - macd, "stoch_rsi": 100 - stochastic, "vwap": 100 - vwap, "bollinger": 100 - bollinger, "adx": adx}
    if extra:
        long.update(extra.get("long", {}))
        short.update(extra.get("short", {}))
    active = {name: weight for name, weight in weights.items() if name in long and name in short and weight > 0}
    total_weight = sum(active.values())
    if not total_weight:
        raise ValueError("At least one signal weight must be positive")
    long_score = sum(long[name] * active[name] for name in active) / total_weight
    short_score = sum(short[name] * active[name] for name in active) / total_weight
    direction = "LONG" if long_score >= short_score else "SHORT"
    selected = long if direction == "LONG" else short
    contributions = sorted(((name, selected[name] * active[name] / total_weight) for name in active), key=lambda item: item[1], reverse=True)
    reasons = [f"{name}={selected[name]:.0f}" for name, _ in contributions[:5]]
    breakdown = {name: round(value, 2) for name, value in selected.items()}
    breakdown.update(long_score=round(long_score, 2), short_score=round(short_score, 2))
    return Candidate(symbol, direction, round(max(long_score, short_score), 2), price, change, quote_volume, _number(latest, "rsi", 50), _number(latest, "atr"), oi_change, funding, taker_ratio, spread, breakdown, reasons)
