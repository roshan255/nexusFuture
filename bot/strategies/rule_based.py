from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from bot.indicators import enrich
from bot.scorer import score
from bot.services.news import NewsSignalService

from .base import Strategy


class RuleBasedStrategy(Strategy):
    """Ranks independent LONG/SHORT evidence; it does not invert signals heuristically."""
    name = "rule_based"

    def __init__(self, client, market, settings) -> None:
        self.client = client
        self.market = market
        self.settings = settings
        self.news = NewsSignalService(settings)
        self.log = logging.getLogger("futures_bot")

    def _technical_extras(self, frames: dict, price: float, symbol: str) -> tuple[dict, list[str]]:
        five_minute = frames["5m"]
        latest = five_minute.iloc[-1]
        lookback = five_minute.iloc[-(self.settings.breakout_lookback + 1):-1]
        prior_high = float(lookback.high.max())
        prior_low = float(lookback.low.min())
        range_width = max(prior_high - prior_low, price * 0.000001)
        structure_long = max(0.0, min(100.0, (price - prior_low) / range_width * 100))
        bullish_frames = sum(frame.iloc[-1].ema9 > frame.iloc[-1].ema21 for frame in frames.values())
        multi_timeframe_long = 100 * bullish_frames / len(frames)
        atr_percent = float(latest.atr) / price * 100
        target_atr = self.settings.target_percent / max(atr_percent, 0.0001)
        target_quality = max(0.0, 100 - max(0.0, target_atr - 4.0) * 18)
        news_bonus, news_reasons = self.news.score(symbol)
        extras = {
            "long": {"market_structure": structure_long, "multi_timeframe": multi_timeframe_long, "target_reachability": target_quality, "news": 50 + news_bonus},
            "short": {"market_structure": 100 - structure_long, "multi_timeframe": 100 - multi_timeframe_long, "target_reachability": target_quality, "news": 50 - news_bonus},
        }
        diagnostics = [f"mtf={bullish_frames}/{len(frames)}", f"target={target_atr:.1f}ATR"] + news_reasons
        return extras, diagnostics

    def _analyse_symbol(self, ticker):
        """Fetch and score one symbol. A failed symbol never aborts the scan."""
        symbol = ticker["symbol"]
        frames = {interval: enrich(self.market.candles(symbol, interval)) for interval in ("1m", "5m", "15m", "1h")}
        latest = frames["5m"].iloc[-1]
        price = float(ticker["lastPrice"])
        atr_percent = float(latest.atr) / price * 100
        short_move = abs(float(latest.return_5) * 100)
        if short_move < self.settings.min_short_term_move_percent or float(latest.volume_ratio) < self.settings.min_relative_volume:
            return None
        if not self.settings.min_atr_percent <= atr_percent <= self.settings.max_atr_percent or float(latest.adx) < self.settings.min_adx:
            return None
        depth = self.client.depth(symbol)
        if not depth.get("bids") or not depth.get("asks"):
            return None
        bid_quantity = sum(float(level[1]) for level in depth["bids"])
        ask_quantity = sum(float(level[1]) for level in depth["asks"])
        imbalance = (bid_quantity - ask_quantity) / (bid_quantity + ask_quantity) if bid_quantity + ask_quantity else 0.0
        spread_percent = (float(depth["asks"][0][0]) - float(depth["bids"][0][0])) / price * 100
        if spread_percent > self.settings.max_spread_percent:
            return None
        funding_rows = self.client.funding(symbol)
        funding = float(funding_rows[-1]["fundingRate"]) if funding_rows else 0.0
        oi_rows = self.client.oi_history(symbol)
        oi_change = float(oi_rows[-1]["sumOpenInterestValue"]) / float(oi_rows[0]["sumOpenInterestValue"]) - 1 if len(oi_rows) > 1 and float(oi_rows[0]["sumOpenInterestValue"]) else 0.0
        taker_rows = self.client.taker_volume(symbol)
        taker_ratio = float(taker_rows[-1]["buySellRatio"]) if taker_rows else 1.0
        extras, diagnostics = self._technical_extras(frames, price, symbol)
        candidate = score(symbol, price, float(ticker["priceChangePercent"]), float(ticker["quoteVolume"]), latest, oi_change, funding, taker_ratio, imbalance, spread_percent / 100, self.settings.weights, extras)
        candidate.reasons.extend(diagnostics)
        return candidate

    def analyse(self):
        tickers = self.market.prefilter()[:self.settings.deep_analysis_limit]
        candidates = []
        # Independent reads use bounded concurrency: fast enough for a minute scan,
        # while retaining a conservative number of public API calls in flight.
        with ThreadPoolExecutor(max_workers=min(self.settings.analysis_workers, len(tickers) or 1)) as pool:
            jobs = {pool.submit(self._analyse_symbol, ticker): ticker["symbol"] for ticker in tickers}
            for job in as_completed(jobs):
                symbol = jobs[job]
                try:
                    candidate = job.result()
                    if candidate:
                        candidates.append(candidate)
                except Exception as exc:
                    self.log.debug("candidate_skipped symbol=%s detail=%s", symbol, exc)
        self.log.info("analysis_complete prefiltered=%s qualified=%s", len(tickers), len(candidates))
        return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)

    def choose(self):
        candidates = self.analyse()
        if not candidates:
            return None, candidates
        best = candidates[0]
        direction_gap = abs(best.breakdown["long_score"] - best.breakdown["short_score"])
        if best.score < self.settings.min_score or direction_gap < self.settings.min_direction_gap:
            best.direction = "WAIT"
        return best, candidates
