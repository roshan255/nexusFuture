from __future__ import annotations

import time

from bot.risk_manager import floor_to, protective_prices, quantity_for_margin, resolve_leverage, selected_margin


class TradeExecutor:
    """Uses market entries for SMALL mode and resting limits for LARGE mode."""

    def __init__(self, client, market, settings, positions) -> None:
        self.client = client
        self.market = market
        self.settings = settings
        self.positions = positions

    def _effective_leverage(self, symbol: str) -> int:
        supported = self.client.max_leverage(symbol)
        return resolve_leverage(self.settings.leverage, supported, self.settings.leverage_fallback)

    def _quantity(self, candidate, leverage: int) -> float:
        rules = self.market.rules[candidate.symbol]
        available = self.client.available_usdt()
        margin = selected_margin(self.settings.margin_mode, self.settings.margin_per_trade_usdt, self.settings.margin_percent, available)
        return quantity_for_margin(margin, leverage, candidate.price, rules)

    def enter(self, candidate) -> dict:
        leverage = self._effective_leverage(candidate.symbol)
        quantity = self._quantity(candidate, leverage)
        entry_side = "BUY" if candidate.direction == "LONG" else "SELL"
        self.client.change_leverage(candidate.symbol, leverage)
        if self.settings.target_mode == "SMALL":
            self.client.market_order(candidate.symbol, entry_side, quantity, f"entry-{int(time.time() * 1000)}")
            position = self.positions.confirmed_position(candidate.symbol)
            protection = self.protect_position(position, candidate.direction)
            return {"mode": "SMALL", "leverage": leverage, "quantity": quantity, "protection": protection}
        rules = self.market.rules[candidate.symbol]
        offset = self.settings.large_limit_offset_percent / 100
        raw_price = candidate.price * (1 - offset if candidate.direction == "LONG" else 1 + offset)
        limit_price = floor_to(raw_price, rules.tick_size)
        expiry = int(time.time() * 1000) + max(601, self.settings.large_limit_expiry_minutes * 60) * 1000
        order = self.client.limit_order(candidate.symbol, entry_side, quantity, limit_price, f"large-entry-{int(time.time() * 1000)}", expiry)
        return {"mode": "LARGE", "leverage": leverage, "quantity": quantity, "limit_price": limit_price, "order_id": order.get("orderId"), "status": order.get("status", "NEW")}

    def protect_position(self, position, direction: str | None = None):
        direction = direction or ("LONG" if position.quantity > 0 else "SHORT")
        rules = self.market.rules[position.symbol]
        exit_side = "SELL" if direction == "LONG" else "BUY"
        protection = protective_prices(position.entry_price, direction, self.settings.target_percent, self.settings.stop_loss_percent, rules.tick_size)
        current = self.client.latest_price(position.symbol)
        valid = ((direction == "LONG" and protection.take_profit > current and protection.stop_loss < current) or (direction == "SHORT" and protection.take_profit < current and protection.stop_loss > current))
        if not valid:
            raise RuntimeError(f"TP/SL would immediately trigger at current price {current}")
        try:
            tp = self.client.algo_close(position.symbol, exit_side, "TAKE_PROFIT_MARKET", protection.take_profit, f"tp-{int(time.time() * 1000)}")
            sl = self.client.algo_close(position.symbol, exit_side, "STOP_MARKET", protection.stop_loss, f"sl-{int(time.time() * 1000)}")
            expected = {str(tp["algoId"]), str(sl["algoId"])}
            if self.settings.target_mode == "LARGE" and self.settings.large_trailing_enabled:
                activation = position.entry_price * (1 + self.settings.trailing_activation_percent / 100 if direction == "LONG" else 1 - self.settings.trailing_activation_percent / 100)
                trail = self.client.trailing_stop(position.symbol, exit_side, abs(position.quantity), floor_to(activation, rules.tick_size), self.settings.trailing_callback_percent, f"trail-{int(time.time() * 1000)}")
                expected.add(str(trail["algoId"]))
            found = {str(order["algoId"]) for order in self.client.open_algo_orders(position.symbol)}
            if not expected <= found:
                raise RuntimeError("Binance did not confirm all protection orders")
            return protection
        except Exception:
            self.client.reduce_only_market_order(position.symbol, exit_side, abs(position.quantity), f"failsafe-{int(time.time() * 1000)}")
            raise
