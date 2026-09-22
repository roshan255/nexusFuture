from __future__ import annotations
import time
from bot.risk_manager import protective_prices, quantity_for_margin, selected_margin

class TradeExecutor:
    """Entry plus mandatory protection; a protection failure closes the confirmed position."""
    def __init__(self, client, market, settings, positions) -> None:
        self.client, self.market, self.settings, self.positions = client, market, settings, positions

    def enter_with_protection(self, candidate):
        rules = self.market.rules[candidate.symbol]
        available = self.client.available_usdt()
        margin = selected_margin(self.settings.margin_mode, self.settings.margin_per_trade_usdt, self.settings.margin_percent, available)
        quantity = quantity_for_margin(margin, self.settings.leverage, candidate.price, rules)
        entry_side = "BUY" if candidate.direction == "LONG" else "SELL"
        exit_side = "SELL" if entry_side == "BUY" else "BUY"
        self.client.change_leverage(candidate.symbol, self.settings.leverage)
        self.client.market_order(candidate.symbol, entry_side, quantity, f"entry-{int(time.time() * 1000)}")
        position = self.positions.confirmed_position(candidate.symbol)
        protection = protective_prices(position.entry_price, candidate.direction, self.settings.take_profit_percent, self.settings.stop_loss_percent, rules.tick_size)
        try:
            current = self.client.latest_price(candidate.symbol)
            valid = ((candidate.direction == "LONG" and protection.take_profit > current and protection.stop_loss < current) or (candidate.direction == "SHORT" and protection.take_profit < current and protection.stop_loss > current))
            if not valid: raise RuntimeError(f"TP/SL would immediately trigger at current price {current}")
            tp = self.client.algo_close(candidate.symbol, exit_side, "TAKE_PROFIT_MARKET", protection.take_profit, f"tp-{int(time.time() * 1000)}")
            sl = self.client.algo_close(candidate.symbol, exit_side, "STOP_MARKET", protection.stop_loss, f"sl-{int(time.time() * 1000)}")
            expected = {str(tp["algoId"]), str(sl["algoId"])}
            found = {str(order["algoId"]) for order in self.client.open_algo_orders(candidate.symbol)}
            if not expected <= found: raise RuntimeError("Binance did not confirm both TP and SL orders")
            return protection
        except Exception:
            self.client.market_order(candidate.symbol, exit_side, abs(position.quantity), f"failsafe-{int(time.time() * 1000)}")
            raise
