from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

Direction = Literal["LONG", "SHORT", "WAIT"]


@dataclass(frozen=True)
class SymbolRules:
    symbol: str
    tick_size: float
    step_size: float
    min_qty: float
    min_notional: float


@dataclass
class Candidate:
    symbol: str
    direction: Direction
    score: float
    price: float
    price_change: float
    quote_volume: float
    rsi: float
    atr: float
    oi_change: float
    funding: float
    taker_ratio: float
    spread: float
    breakdown: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    # Estimated number of 5-minute candles to reach TP.
    # Lower = faster. Set to a large number when velocity is too weak to estimate.
    tp_eta_bars: float = 9999.0


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float
    entry_price: float


@dataclass(frozen=True)
class Protection:
    take_profit: float
    stop_loss: float
