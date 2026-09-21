from bot.risk_manager import protective_prices
def test_long_and_short_protection():
 assert protective_prices(100,'LONG',.5,.3,.01).take_profit==100.5
 assert protective_prices(100,'SHORT',.5,.3,.01).stop_loss==100.3
