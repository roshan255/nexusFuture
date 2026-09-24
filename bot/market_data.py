from __future__ import annotations

import pandas as pd

from bot.models import SymbolRules


class MarketData:
    """Normalizes Binance market data and applies inexpensive liquidity prefilters."""

    def __init__(self, client, settings) -> None:
        self.client = client
        self.settings = settings
        self.rules = self._symbol_rules()

    def _symbol_rules(self) -> dict[str, SymbolRules]:
        rules: dict[str, SymbolRules] = {}
        for symbol in self.client.exchange_info()["symbols"]:
            if symbol["status"] != "TRADING" or symbol["contractType"] != "PERPETUAL" or symbol["quoteAsset"] != "USDT":
                continue
            filters = {item["filterType"]: item for item in symbol["filters"]}
            lot = filters.get("LOT_SIZE", {})
            price = filters.get("PRICE_FILTER", {})
            minimum = filters.get("MIN_NOTIONAL", filters.get("NOTIONAL", {}))
            rules[symbol["symbol"]] = SymbolRules(symbol["symbol"], float(price["tickSize"]), float(lot["stepSize"]), float(lot["minQty"]), float(minimum.get("notional", minimum.get("minNotional", 0))))
        return rules

    def candles(self, symbol: str, interval: str, limit: int = 250) -> pd.DataFrame:
        rows = self.client.klines(symbol, interval, limit + 1)[:-1]
        columns = ["time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "tb_base", "tb_quote", "ignore"]
        return pd.DataFrame(rows, columns=columns).astype({"open": float, "high": float, "low": float, "close": float, "volume": float, "quote_volume": float})

    def prefilter(self) -> list[dict]:
        rows = []
        for ticker in self.client.ticker_24h():
            if ticker["symbol"] not in self.rules:
                continue
            quote_volume = float(ticker["quoteVolume"])
            move = abs(float(ticker["priceChangePercent"]))
            if quote_volume < self.settings.min_quote_volume_usdt or move < self.settings.min_24h_abs_change_percent:
                continue
            rows.append(ticker)
        return sorted(rows, key=lambda row: float(row["quoteVolume"]) * max(abs(float(row["priceChangePercent"])), 0.1), reverse=True)[:self.settings.pre_filter_limit]
