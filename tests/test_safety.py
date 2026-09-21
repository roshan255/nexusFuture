from bot.config import Settings
def test_uat_allows_demo_orders():assert Settings(mode='UAT').may_trade
def test_production_requires_confirmation():assert not Settings(mode='PRODUCTION',enable_live_trading=False).may_trade
