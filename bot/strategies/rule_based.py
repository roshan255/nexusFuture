from bot.indicators import enrich
from bot.scorer import score
from .base import Strategy

class RuleBasedStrategy(Strategy):
    """Default technical-and-futures-data strategy. Add siblings for new algorithms."""
    name = "rule_based"
    def __init__(self, client, market, settings): self.client, self.market, self.settings = client, market, settings

    def analyse(self):
        candidates = []
        for ticker in self.market.prefilter(self.settings.pre_filter_limit)[:self.settings.deep_analysis_limit]:
            symbol = ticker["symbol"]
            if abs(float(ticker["priceChangePercent"])) < self.settings.min_24h_abs_change_percent:
                continue
            try:
                latest = enrich(self.market.candles(symbol, "5m")).iloc[-1]
                recent_move_percent = abs(float(latest.return_5) * 100)
                if recent_move_percent < self.settings.min_short_term_move_percent:
                    continue
                depth = self.client.depth(symbol); bids = sum(float(x[1]) for x in depth["bids"]); asks = sum(float(x[1]) for x in depth["asks"])
                imbalance = (bids - asks) / (bids + asks) if bids + asks else 0; spread = (float(depth["asks"][0][0]) - float(depth["bids"][0][0])) / float(ticker["lastPrice"])
                funding = self.client.funding(symbol); funding = float(funding[-1]["fundingRate"]) if funding else 0
                oi = self.client.oi_history(symbol); oi_change = float(oi[-1]["sumOpenInterestValue"]) / float(oi[0]["sumOpenInterestValue"]) - 1 if len(oi) > 1 and float(oi[0]["sumOpenInterestValue"]) else 0
                taker = self.client.taker_volume(symbol); ratio = float(taker[-1]["buySellRatio"]) if taker else 1
                candidates.append(score(symbol, float(ticker["lastPrice"]), float(ticker["priceChangePercent"]), float(ticker["quoteVolume"]), latest, oi_change, funding, ratio, imbalance, spread, self.settings.weights))
            except Exception: continue
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def choose(self):
        candidates = self.analyse()
        if not candidates: return None, candidates
        best = candidates[0]; gap = abs(best.breakdown["long_score"] - best.breakdown["short_score"])
        if best.score < self.settings.min_score or gap < self.settings.min_direction_gap: best.direction = "WAIT"
        return best, candidates
