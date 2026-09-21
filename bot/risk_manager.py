from __future__ import annotations
from decimal import Decimal, ROUND_DOWN
from .models import SymbolRules, Protection
def selected_margin(mode: str, fixed_usdt: float, percent: float, available_usdt: float) -> float:
    if mode == "FIXED": return fixed_usdt
    if mode == "PERCENT": return available_usdt * percent / 100
    raise ValueError("Margin mode must be FIXED or PERCENT")
def floor_to(value: float, increment: float) -> float:
    return float((Decimal(str(value))/Decimal(str(increment))).to_integral_value(rounding=ROUND_DOWN)*Decimal(str(increment)))
def quantity_for_margin(margin: float, leverage: int, price: float, rules: SymbolRules) -> float:
    q=floor_to(margin*leverage/price, rules.step_size)
    if q < rules.min_qty or q*price < rules.min_notional: raise ValueError("Trade size does not satisfy exchange minimums")
    return q
def protective_prices(entry: float, direction: str, tp_pct: float, sl_pct: float, tick: float) -> Protection:
    e,p,s=Decimal(str(entry)),Decimal(str(tp_pct))/100,Decimal(str(sl_pct))/100
    if direction == 'LONG': tp,sl=e*(1+p),e*(1-s)
    elif direction == 'SHORT': tp,sl=e*(1-p),e*(1+s)
    else: raise ValueError('direction must be LONG or SHORT')
    return Protection(floor_to(float(tp),tick), floor_to(float(sl),tick))
