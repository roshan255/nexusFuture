from __future__ import annotations

import time

import httpx


class NewsSignalService:
    """Optional, non-blocking headline sentiment modifier; never creates a trade by itself."""

    POSITIVE = ("approval", "approved", "listing", "listed", "partnership", "integrat", "upgrade", "launch", "mainnet", "adoption", "buyback")
    NEGATIVE = ("hack", "exploit", "lawsuit", "delist", "delisting", "unlock", "security", "outage", "ban", "investigation")

    def __init__(self, settings) -> None:
        self.settings = settings
        self._cached_at = 0.0
        self._headlines: list[str] = []

    def _load_headlines(self) -> list[str]:
        if not self.settings.news_enabled:
            return []
        if self._headlines and time.monotonic() - self._cached_at < 300:
            return self._headlines
        try:
            params = {"api_key": self.settings.news_api_key} if self.settings.news_api_key else {}
            response = httpx.get(self.settings.news_api_url, params=params, timeout=4)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("results", payload.get("data", payload.get("articles", payload if isinstance(payload, list) else [])))
            self._headlines = [f"{item.get('title', '')} {item.get('description', '')}".lower() for item in items if isinstance(item, dict)]
            self._cached_at = time.monotonic()
        except Exception:
            return []
        return self._headlines

    def score(self, symbol: str) -> tuple[float, list[str]]:
        base_asset = symbol.removesuffix("USDT").lower()
        headlines = [headline for headline in self._load_headlines() if base_asset in headline or "bitcoin" in headline or "crypto" in headline]
        if not headlines:
            return 0.0, []
        positive = sum(any(word in headline for word in self.POSITIVE) for headline in headlines)
        negative = sum(any(word in headline for word in self.NEGATIVE) for headline in headlines)
        raw = positive - negative
        bonus = max(-self.settings.news_max_bonus, min(self.settings.news_max_bonus, raw * 2.0))
        reasons = [f"news +{positive}/-{negative}"] if raw else ["news mixed"]
        return bonus, reasons
