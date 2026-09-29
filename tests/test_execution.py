import pytest

from bot.config import Settings
from bot.models import Candidate, Position, Protection, SymbolRules
from bot.services.execution import TradeExecutor


class MockMarketData:
    def __init__(self):
        self.rules = {
            "BTCUSDT": SymbolRules("BTCUSDT", tick_size=0.1, step_size=0.001, min_qty=0.001, min_notional=5.0)
        }


class MockBinanceClient:
    def __init__(self):
        self.time_offset_ms = 500
        self.orders = []
        self.algo_orders = []
        self._max_leverage = 50
        self._available_usdt = 1000.0
        self._latest_price = 50000.0

    def max_leverage(self, symbol: str):
        return self._max_leverage

    def available_usdt(self):
        return self._available_usdt

    def latest_price(self, symbol: str):
        return self._latest_price

    def change_leverage(self, symbol: str, leverage: int):
        return {"symbol": symbol, "leverage": leverage}

    def market_order(self, symbol: str, side: str, quantity: float, client_id: str):
        order = {"symbol": symbol, "side": side, "origQty": quantity, "orderId": 101}
        self.orders.append(order)
        return order

    def limit_order(self, symbol: str, side: str, quantity: float, price: float, client_id: str, good_till_date: int = None):
        order = {"symbol": symbol, "side": side, "origQty": quantity, "price": price, "orderId": 102, "goodTillDate": good_till_date, "status": "NEW"}
        self.orders.append(order)
        return order

    def algo_close(self, symbol: str, side: str, order_type: str, trigger_price: float, client_id: str):
        algo = {"algoId": len(self.algo_orders) + 1, "symbol": symbol, "type": order_type, "triggerPrice": trigger_price}
        self.algo_orders.append(algo)
        return algo

    def open_algo_orders(self, symbol: str = None):
        return list(self.algo_orders)

    def reduce_only_market_order(self, symbol: str, side: str, quantity: float, client_id: str):
        order = {"symbol": symbol, "side": side, "origQty": quantity, "reduceOnly": True, "orderId": 999}
        self.orders.append(order)
        return order


class MockPositionService:
    def __init__(self, position: Position | None):
        self._position = position

    def current_position(self):
        return self._position

    def confirmed_position(self, symbol: str):
        return self._position


def test_executor_small_market_entry():
    client = MockBinanceClient()
    market = MockMarketData()
    settings = Settings(target_mode="SMALL", target_percent=1.5, stop_loss_percent=1.0, margin_per_trade_usdt=50.0, leverage=10)
    pos = Position("BTCUSDT", quantity=0.01, entry_price=50000.0)
    positions = MockPositionService(pos)
    executor = TradeExecutor(client, market, settings, positions)

    cand = Candidate("BTCUSDT", "LONG", 80.0, 50000.0, 2.0, 10000000.0, 55.0, 500.0, 0.02, 0.0001, 1.2, 0.01)
    result = executor.enter(cand)

    assert result["mode"] == "SMALL"
    assert result["leverage"] == 10
    assert result["quantity"] == 0.01
    assert isinstance(result["protection"], Protection)
    assert len(client.algo_orders) == 2  # TP and SL placed


def test_executor_large_limit_entry():
    client = MockBinanceClient()
    market = MockMarketData()
    settings = Settings(target_mode="LARGE", target_percent=25.0, large_limit_offset_percent=0.5, margin_per_trade_usdt=50.0, leverage=10)
    positions = MockPositionService(None)
    executor = TradeExecutor(client, market, settings, positions)

    cand = Candidate("BTCUSDT", "LONG", 80.0, 50000.0, 2.0, 10000000.0, 55.0, 500.0, 0.02, 0.0001, 1.2, 0.01)
    result = executor.enter(cand)

    assert result["mode"] == "LARGE"
    assert result["status"] == "NEW"
    # Limit buy price offset 0.5% below 50000 = 49750
    assert result["limit_price"] == 49750.0
    # Good-till-date incorporates time offset
    assert client.orders[0]["goodTillDate"] > 0


def test_failsafe_market_close_on_protection_failure():
    client = MockBinanceClient()
    # Mock algo_close to fail
    def failing_algo(*args, **kwargs):
        raise RuntimeError("Algo service down")
    client.algo_close = failing_algo

    market = MockMarketData()
    settings = Settings(target_percent=1.5, stop_loss_percent=1.0)
    pos = Position("BTCUSDT", quantity=0.01, entry_price=50000.0)
    positions = MockPositionService(pos)
    executor = TradeExecutor(client, market, settings, positions)

    with pytest.raises(RuntimeError, match="Algo service down"):
        executor.protect_position(pos, "LONG")

    # Verify failsafe reduce-only market order was submitted to close position
    failsafe_orders = [o for o in client.orders if o.get("reduceOnly") is True]
    assert len(failsafe_orders) == 1
    assert failsafe_orders[0]["side"] == "SELL"
