from __future__ import annotations

import math

from bot.models import Candidate


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _number(row, name: str, default: float = 0.0) -> float:
    value = getattr(row, name, default)
    return default if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)


def score(symbol, price, change, quote_volume, latest, oi_change, funding, taker_ratio, imbalance, spread, weights, extra=None) -> Candidate:
    price_delta = _number(latest, "return_5", change / 100.0 if change else 0.0)
    ema_bullish = _number(latest, "ema9") > _number(latest, "ema21")
    sma_bullish = _number(latest, "sma20", price) > _number(latest, "sma50", price)
    macro_bullish = _number(latest, "sma50", price) > _number(latest, "sma200", price)
    price_above_ema = _number(latest, "close", price) > _number(latest, "ema21", price)
    trend = 25 * sum((ema_bullish, sma_bullish, macro_bullish, price_above_ema))
    momentum = _clamp(50 + _number(latest, "return_5") * 5000)

    # Direction-confirmed volume: volume surge reinforces current candle/trend direction
    vol_ratio = _number(latest, "volume_ratio", 1.0)
    vol_boost = (vol_ratio - 1.0) * 40.0
    vol_long = _clamp(50 + vol_boost if price_delta >= 0 else 50 - vol_boost)
    vol_short = 100 - vol_long

    # Direction-confirmed open interest: rising OI + rising price = long accumulation;
    # rising OI + falling price = short accumulation
    oi_long = _clamp(50 + oi_change * 1000 if price_delta >= 0 else 50 - oi_change * 1000)
    oi_short = 100 - oi_long

    taker = _clamp(50 + (taker_ratio - 1) * 100)
    orderbook = _clamp(50 + imbalance * 100)
    macd = 100 if _number(latest, "macd_histogram") > 0 else 0
    stochastic = _clamp(50 + (_number(latest, "stoch_rsi_k", 50) - _number(latest, "stoch_rsi_d", 50)))
    vwap = 100 if _number(latest, "close", price) > _number(latest, "vwap", price) else 0
    bollinger = _clamp(50 + ((_number(latest, "close", price) - _number(latest, "bb_middle", price)) / max(price, 1e-12)) * 5000)

    # Directional ADX using directional movement indicators (+DI vs -DI) when present
    has_di = hasattr(latest, "plus_di") and hasattr(latest, "minus_di")
    if has_di:
        plus_di = _number(latest, "plus_di", 25.0)
        minus_di = _number(latest, "minus_di", 25.0)
        long_adx = _clamp(50 + (plus_di - minus_di) * 1.5)
        short_adx = 100 - long_adx
    else:
        adx_val = _clamp(_number(latest, "adx") * 2.5)
        long_adx = short_adx = adx_val

    long = {
        "trend": trend,
        "momentum": momentum,
        "volume": vol_long,
        "open_interest": oi_long,
        "taker": taker,
        "orderbook": orderbook,
        "funding": _clamp(50 - funding * 100000),
        "macd": macd,
        "stoch_rsi": stochastic,
        "vwap": vwap,
        "bollinger": bollinger,
        "adx": long_adx,
    }
    short = {
        "trend": 100 - trend,
        "momentum": 100 - momentum,
        "volume": vol_short,
        "open_interest": oi_short,
        "taker": 100 - taker,
        "orderbook": 100 - orderbook,
        "funding": _clamp(50 + funding * 100000),
        "macd": 100 - macd,
        "stoch_rsi": 100 - stochastic,
        "vwap": 100 - vwap,
        "bollinger": 100 - bollinger,
        "adx": short_adx,
    }
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
