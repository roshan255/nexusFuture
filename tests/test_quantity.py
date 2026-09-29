import pytest

from bot.models import SymbolRules
from bot.risk_manager import (
    LeverageUnavailable,
    TradeSizeError,
    quantity_for_margin,
    resolve_leverage,
    selected_margin,
)


def test_quantity_is_rounded_and_valid():
    rules = SymbolRules("X", 0.01, 0.01, 0.01, 5)
    assert quantity_for_margin(10, 5, 100, rules) == 0.5


def test_percent_margin_uses_available_balance():
    assert selected_margin("PERCENT", 10, 100, 37.5) == 37.5


def test_small_margin_reports_exchange_minimum():
    rules = SymbolRules("X", 0.01, 0.1, 0.1, 5)
    with pytest.raises(TradeSizeError, match="configured margin"):
        quantity_for_margin(10, 5, 1000, rules)


def test_leverage_can_fall_back_to_symbol_maximum():
    assert resolve_leverage(20, 10, "USE_MAX") == 10


def test_leverage_skip_is_safe():
    with pytest.raises(LeverageUnavailable):
        resolve_leverage(20, 10, "SKIP")
