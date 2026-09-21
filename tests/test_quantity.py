from bot.risk_manager import quantity_for_margin,selected_margin
from bot.models import SymbolRules
def test_quantity_is_rounded_and_valid():assert quantity_for_margin(10,5,100,SymbolRules('X',.01,.01,.01,5))==.5
def test_percent_margin_uses_available_balance():assert selected_margin('PERCENT',10,100,37.5)==37.5
