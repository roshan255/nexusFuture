from __future__ import annotations
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from .models import SymbolRules, Protection
class TradeSizeError(ValueError):
    """The configured margin cannot satisfy a selected contract's exchange rules."""


class LeverageUnavailable(ValueError):
    """The configured leverage cannot be applied to a symbol."""

def selected_margin(mode: str, fixed_usdt: float, percent: float, available_usdt: float) -> float:
    if mode == "FIXED": return fixed_usdt
    if mode == "PERCENT": return available_usdt * percent / 100
    raise ValueError("Margin mode must be FIXED or PERCENT")


def resolve_leverage(requested: int, supported: int, fallback: str) -> int:
    if requested <= supported:
        return requested
    if fallback == "USE_MAX":
        return supported
    raise LeverageUnavailable(f"requested leverage {requested}x exceeds Binance maximum {supported}x")
def floor_to(value: float, increment: float) -> float:
    return float((Decimal(str(value))/Decimal(str(increment))).to_integral_value(rounding=ROUND_DOWN)*Decimal(str(increment)))

def ceil_to(value: float, increment: float) -> float:
    return float((Decimal(str(value))/Decimal(str(increment))).to_integral_value(rounding=ROUND_UP)*Decimal(str(increment)))

def quantity_for_margin(margin: float, leverage: int, price: float, rules: SymbolRules) -> float:
    q=floor_to(margin*leverage/price, rules.step_size)
    if q < rules.min_qty or q*price < rules.min_notional:
        minimum_quantity=ceil_to(max(rules.min_qty, rules.min_notional/price), rules.step_size)
        minimum_margin=minimum_quantity*price/leverage
        raise TradeSizeError(f"{rules.symbol}: configured margin {margin:.8f} USDT at {leverage}x produces {q:.8f}; exchange needs at least {minimum_quantity:.8f} quantity / about {minimum_margin:.8f} USDT margin")
    return q
def protective_prices(entry: float, direction: str, tp_pct: float, sl_pct: float, tick: float) -> Protection:
    e,p,s=Decimal(str(entry)),Decimal(str(tp_pct))/100,Decimal(str(sl_pct))/100
    if direction == 'LONG': tp,sl=e*(1+p),e*(1-s)
    elif direction == 'SHORT': tp,sl=e*(1-p),e*(1+s)
    else: raise ValueError('direction must be LONG or SHORT')
    return Protection(floor_to(float(tp),tick), floor_to(float(sl),tick))
