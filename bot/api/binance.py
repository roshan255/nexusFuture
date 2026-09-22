from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from bot.config import Settings


class BinanceError(RuntimeError):
    """An exchange response with enough detail to diagnose configuration issues."""


class BinanceClient:
    """USDⓈ-M REST client. Production URL is deliberately not configurable."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.Client(base_url=settings.base_url, timeout=20)
        self.time_offset_ms = 0

    def close(self) -> None:
        self.http.close()

    def server_time(self) -> int:
        return int(self._request("GET", "/fapi/v1/time")["serverTime"])

    def sync_time(self) -> int:
        self.time_offset_ms = self.server_time() - int(time.time() * 1000)
        return self.time_offset_ms

    def check_credentials(self) -> dict[str, Any]:
        """Read-only diagnostic; raises the exact Binance failure instead of hiding it."""
        offset = self.sync_time()
        positions = self.positions()
        return {"base_url": self.settings.base_url, "time_offset_ms": offset, "position_rows": len(positions)}

    def _request(self, method: str, path: str, params: dict | None = None, *, signed: bool = False, trading: bool = False) -> Any:
        if trading and not self.settings.may_trade:
            raise PermissionError("Production orders require ENABLE_LIVE_TRADING=true")
        request_params = dict(params or {})
        headers: dict[str, str] = {}
        if signed:
            if not self.settings.api_key or not self.settings.api_secret:
                raise BinanceError("BINANCE_API_KEY and BINANCE_API_SECRET must be set")
            request_params["timestamp"] = int(time.time() * 1000) + self.time_offset_ms
            request_params["recvWindow"] = 10_000
            query = urlencode(request_params)
            request_params["signature"] = hmac.new(self.settings.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
            headers["X-MBX-APIKEY"] = self.settings.api_key
        try:
            response = self.http.request(method, path, params=request_params, headers=headers)
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Binance timeout on {method} {path}; reconcile before retrying") from exc
        if response.is_error:
            raise BinanceError(f"{method} {path} failed ({response.status_code}): {response.text}")
        return response.json()

    # Public market data
    def exchange_info(self): return self._request("GET", "/fapi/v1/exchangeInfo")
    def ticker_24h(self): return self._request("GET", "/fapi/v1/ticker/24hr")
    def latest_price(self, symbol: str): return float(self._request("GET", "/fapi/v1/ticker/price", {"symbol": symbol})["price"])
    def klines(self, symbol: str, interval: str, limit: int = 100): return self._request("GET", "/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    def depth(self, symbol: str, limit: int = 20): return self._request("GET", "/fapi/v1/depth", {"symbol": symbol, "limit": limit})
    def funding(self, symbol: str): return self._request("GET", "/fapi/v1/fundingRate", {"symbol": symbol, "limit": 1})
    def oi_history(self, symbol: str): return self._request("GET", "/futures/data/openInterestHist", {"symbol": symbol, "period": "5m", "limit": 2})
    def taker_volume(self, symbol: str): return self._request("GET", "/futures/data/takerlongshortRatio", {"symbol": symbol, "period": "5m", "limit": 1})

    # Signed account data
    def positions(self): return self._request("GET", "/fapi/v3/positionRisk", signed=True)
    def available_usdt(self) -> float:
        balances = self._request("GET", "/fapi/v3/balance", signed=True)
        usdt = next((row for row in balances if row["asset"] == "USDT"), None)
        if not usdt: raise BinanceError("USDT Futures balance was not returned by Binance")
        return float(usdt["availableBalance"])
    def open_algo_orders(self, symbol: str | None = None): return self._request("GET", "/fapi/v1/openAlgoOrders", ({"symbol": symbol} if symbol else {}), signed=True)

    # Trading. Do not retry market entries after errors/timeouts.
    def change_leverage(self, symbol: str, leverage: int): return self._request("POST", "/fapi/v1/leverage", {"symbol": symbol, "leverage": leverage}, signed=True, trading=True)
    def market_order(self, symbol: str, side: str, quantity: float, client_id: str): return self._request("POST", "/fapi/v1/order", {"symbol": symbol, "side": side, "type": "MARKET", "quantity": quantity, "newClientOrderId": client_id, "newOrderRespType": "RESULT"}, signed=True, trading=True)
    def algo_close(self, symbol: str, side: str, order_type: str, trigger_price: float, client_id: str):
        return self._request("POST", "/fapi/v1/algoOrder", {"algoType": "CONDITIONAL", "symbol": symbol, "side": side, "type": order_type, "triggerPrice": trigger_price, "closePosition": "true", "workingType": "CONTRACT_PRICE", "clientAlgoId": client_id}, signed=True, trading=True)
    def cancel_algo(self, symbol: str, algo_id: str): return self._request("DELETE", "/fapi/v1/algoOrder", {"symbol": symbol, "algoId": algo_id}, signed=True, trading=True)
