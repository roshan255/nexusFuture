from __future__ import annotations
import time

from bot.api.binance import BinanceError
from bot.models import Position


class PositionStateUnknown(RuntimeError):
    pass


class PositionService:
    """Derives bot state only from Binance; no local position cache exists."""

    def __init__(self, client) -> None:
        self.client = client

    def current_position(self) -> Position | None:
        try:
            rows = self.client.positions()
        except (BinanceError, TimeoutError) as exc:
            raise PositionStateUnknown(f"Could not read Binance position state: {exc}") from exc
        open_positions = [row for row in rows if abs(float(row["positionAmt"])) > 0]
        if len(open_positions) > 1:
            raise PositionStateUnknown(f"Binance reports {len(open_positions)} open positions; one-position rule prevents trading")
        if not open_positions:
            return None
        row = open_positions[0]
        return Position(row["symbol"], float(row["positionAmt"]), float(row["entryPrice"]))

    def confirmed_position(self, symbol: str) -> Position:
        for _ in range(15):
            position = self.current_position()
            if position and position.symbol == symbol and position.entry_price > 0:
                return position
            time.sleep(0.2)
        raise PositionStateUnknown("New market entry is not confirmed by positionRisk; no retry will be sent")

    def cancel_protection(self, symbol: str) -> None:
        for order in self.client.open_algo_orders(symbol):
            self.client.cancel_algo(symbol, str(order["algoId"]))
