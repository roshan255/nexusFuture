from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from bot.indicators import enrich
from bot.scorer import score
from bot.services.news import NewsSignalService

from .base import Strategy


class RuleBasedStrategy(Strategy):
    """Ranks independent LONG/SHORT evidence with target-first clearance and rebound validation."""
    name = "rule_based"

    def __init__(self, client, market, settings) -> None:
        self.client = client
        self.market = market
        self.settings = settings
        self.news = NewsSignalService(settings)
        self.log = logging.getLogger("futures_bot")

    @staticmethod
    def _is_opposing_level_chase(direction: str, level_reason: str) -> bool:
        return (direction == "LONG" and level_reason in {"near_resistance", "bearish_rejection_resistance", "breakout_above_resistance"}) or (direction == "SHORT" and level_reason in {"near_support", "bullish_rejection_support", "breakdown_below_support"})

    def _technical_extras(self, frames: dict, price: float, symbol: str) -> tuple[dict, list[str]]:
        five_minute = frames["5m"]
        latest = five_minute.iloc[-1]
        lookback = five_minute.iloc[-(self.settings.support_resistance_lookback + 1):-1]
        resistance = float(lookback.high.max())
        support = float(lookback.low.min())
        current_atr = max(float(latest.atr), price * 0.000001)
        zone = current_atr * self.settings.support_resistance_zone_atr
        breakout_buffer = current_atr * self.settings.breakout_confirm_atr
        body = max(abs(float(latest.close) - float(latest.open)), price * 0.000001)
        upper_wick = float(latest.high) - max(float(latest.open), float(latest.close))
        lower_wick = min(float(latest.open), float(latest.close)) - float(latest.low)
        bearish_rejection = upper_wick / body >= self.settings.rejection_wick_body_ratio and latest.close <= latest.open
        bullish_rejection = lower_wick / body >= self.settings.rejection_wick_body_ratio and latest.close >= latest.open

        # Structural level detection: breakouts, rebounds, or between levels
        if price > resistance + breakout_buffer:
            structure_long, support_resistance_long, support_resistance_short, level_reason = 90, 90, 10, "breakout_above_resistance"
        elif price < support - breakout_buffer:
            structure_long, support_resistance_long, support_resistance_short, level_reason = 10, 10, 90, "breakdown_below_support"
        elif price >= resistance - zone:
            structure_long, support_resistance_long, support_resistance_short = 35, (0 if bearish_rejection else 15), (100 if bearish_rejection else 70)
            level_reason = "bearish_rejection_resistance" if bearish_rejection else "near_resistance"
        elif price <= support + zone:
            structure_long, support_resistance_long, support_resistance_short = 65, (100 if bullish_rejection else 70), (0 if bullish_rejection else 15)
            level_reason = "bullish_rejection_support" if bullish_rejection else "near_support"
        else:
            structure_long, support_resistance_long, support_resistance_short, level_reason = 50, 50, 50, "between_levels"

        bullish_frames = sum(frame.iloc[-1].ema9 > frame.iloc[-1].ema21 for frame in frames.values())
        multi_timeframe_long = 100 * bullish_frames / len(frames)
        atr_percent = float(latest.atr) / price * 100
        target_atr = self.settings.target_percent / max(atr_percent, 0.0001)
        target_quality = max(0.0, 100 - max(0.0, target_atr - 4.0) * 18)
        long_target = price * (1 + self.settings.target_percent / 100)
        short_target = price * (1 - self.settings.target_percent / 100)
        long_stop = price * (1 - self.settings.stop_loss_percent / 100)
        short_stop = price * (1 + self.settings.stop_loss_percent / 100)

        # Path-to-target room calculation:
        # If price is at or beyond the opposing level, path is poor (buying at the top or shorting at the bottom).
        # If the level sits between entry and target, path is blocked.
        # If target is reached before the opposing level, path is clear.
        if price >= resistance:
            long_target_path = 15.0
        elif resistance < long_target:
            long_target_path = 10.0
        else:
            long_target_path = 90.0

        if price <= support:
            short_target_path = 15.0
        elif short_target < support:
            short_target_path = 10.0
        else:
            short_target_path = 90.0

        # Adverse path buffer: having support below a long entry buffers against stop-loss;
        # having resistance above a short entry buffers against stop-loss.
        long_adverse_path = 90 if long_stop < support < price else 45
        short_adverse_path = 90 if price < resistance < short_stop else 45

        move_in_atr = float(latest.return_5) * 100 / max(atr_percent, 0.0001)
        volume_boost = min(20.0, max(0.0, (float(latest.volume_ratio) - 1) * 25))
        long_target_speed = max(0.0, min(100.0, 50 + move_in_atr * 35 + volume_boost))
        short_target_speed = max(0.0, min(100.0, 50 - move_in_atr * 35 + volume_boost))
        news_bonus, news_reasons = self.news.score(symbol)
        extras = {
            "long": {"market_structure": structure_long, "support_resistance": support_resistance_long, "target_speed": long_target_speed, "target_path": long_target_path, "adverse_path": long_adverse_path, "multi_timeframe": multi_timeframe_long, "target_reachability": target_quality, "news": 50 + news_bonus},
            "short": {"market_structure": 100 - structure_long, "support_resistance": support_resistance_short, "target_speed": short_target_speed, "target_path": short_target_path, "adverse_path": short_adverse_path, "multi_timeframe": 100 - multi_timeframe_long, "target_reachability": target_quality, "news": 50 - news_bonus},
        }
        diagnostics = [f"level={level_reason}", f"support={support:.8g}", f"resistance={resistance:.8g}", f"mtf={bullish_frames}/{len(frames)}", f"target={target_atr:.1f}ATR"] + news_reasons
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
        weights = dict(self.settings.weights)
        if self.settings.target_mode != "SMALL":
            for name in ("target_speed", "target_path", "adverse_path"):
                weights[name] = 0
        candidate = score(symbol, price, float(ticker["priceChangePercent"]), float(ticker["quoteVolume"]), latest, oi_change, funding, taker_ratio, imbalance, spread_percent / 100, weights, extras)
        if self.settings.target_mode == "SMALL":
            level_reason = next(reason.removeprefix("level=") for reason in diagnostics if reason.startswith("level="))
            if self.settings.small_avoid_opposing_level_entries and self._is_opposing_level_chase(candidate.direction, level_reason):
                self.log.debug("candidate_skipped symbol=%s detail=opposing_level_chase direction=%s level=%s", symbol, candidate.direction, level_reason)
                return None
            target_atr = self.settings.target_percent / max(atr_percent, 0.0001)
            if target_atr > self.settings.small_target_max_atr:
                self.log.debug("candidate_skipped symbol=%s detail=target_too_far target_atr=%.2f", symbol, target_atr)
                return None
            if candidate.breakdown["target_speed"] < self.settings.small_target_min_speed_score or candidate.breakdown["target_path"] < self.settings.small_target_min_path_score:
                self.log.debug("candidate_skipped symbol=%s detail=target_first_gate speed=%.1f path=%.1f", symbol, candidate.breakdown["target_speed"], candidate.breakdown["target_path"])
                return None

            # Anti-top buying and anti-bottom selling gates:
            # Ensure sufficient clearance to the opposing level so 1.5% target can complete before resistance/support
            support_val = float(next(r.removeprefix("support=") for r in diagnostics if r.startswith("support=")))
            resistance_val = float(next(r.removeprefix("resistance=") for r in diagnostics if r.startswith("resistance=")))
            current_atr = max(float(latest.atr), price * 0.000001)

            if candidate.direction == "LONG":
                clearance_pct = (resistance_val - price) / price * 100
                if clearance_pct < self.settings.small_min_clearance_percent:
                    self.log.debug("candidate_skipped symbol=%s detail=insufficient_resistance_clearance clearance=%.2f%%", symbol, clearance_pct)
                    return None
                if float(latest.rsi) > self.settings.small_max_rsi:
                    self.log.debug("candidate_skipped symbol=%s detail=overbought_rsi rsi=%.1f", symbol, float(latest.rsi))
                    return None
                if (price - float(latest.ema21)) > self.settings.small_max_ema_distance_atr * current_atr:
                    self.log.debug("candidate_skipped symbol=%s detail=overextended_above_ema21", symbol)
                    return None
                if hasattr(latest, "bb_upper") and price >= float(latest.bb_upper):
                    self.log.debug("candidate_skipped symbol=%s detail=at_upper_bollinger", symbol)
                    return None

            elif candidate.direction == "SHORT":
                clearance_pct = (price - support_val) / price * 100
                if clearance_pct < self.settings.small_min_clearance_percent:
                    self.log.debug("candidate_skipped symbol=%s detail=insufficient_support_clearance clearance=%.2f%%", symbol, clearance_pct)
                    return None
                if float(latest.rsi) < self.settings.small_min_rsi:
                    self.log.debug("candidate_skipped symbol=%s detail=oversold_rsi rsi=%.1f", symbol, float(latest.rsi))
                    return None
                if (float(latest.ema21) - price) > self.settings.small_max_ema_distance_atr * current_atr:
                    self.log.debug("candidate_skipped symbol=%s detail=overextended_below_ema21", symbol)
                    return None
                if hasattr(latest, "bb_lower") and price <= float(latest.bb_lower):
                    self.log.debug("candidate_skipped symbol=%s detail=at_lower_bollinger", symbol)
                    return None

        candidate.reasons.extend(diagnostics)

        # ------------------------------------------------------------------
        # Speed-to-target estimation (SMALL mode primary sort key)
        # We estimate how many 5m bars the current momentum needs to cover
        # TARGET_PERCENT distance, blended with ATR-based acceleration.
        #
        # velocity_pct:  the current directional momentum per bar (5m return)
        #                aligned to the candidate direction.
        # atr_velocity:  ATR expressed as % of price; a moving market can cover
        #                at least one ATR per bar under sustained momentum.
        # blended:       weighted average so that both candle returns and the
        #                raw ATR contribute, preventing one misleading signal
        #                from dominating.
        # tp_eta_bars:   how many bars at the blended velocity cover target%.
        #                Capped at 9999 when momentum is too weak to estimate.
        # ------------------------------------------------------------------
        if self.settings.target_mode == "SMALL":
            return_5_pct = float(latest.return_5) * 100
            directional_return = return_5_pct if candidate.direction == "LONG" else -return_5_pct
            # Per-bar velocity from the 5-bar return (divided by 5 bars)
            velocity_per_bar = directional_return / 5.0
            # ATR-based velocity: fraction of the ATR that momentum can sustain per bar.
            # We use 0.6 of ATR as a conservative estimate of sustainable directional move.
            atr_velocity_per_bar = atr_percent * 0.6
            # Blend: 60% candle momentum, 40% ATR potential.
            # If directional velocity is negative, fall back entirely to ATR estimate.
            if velocity_per_bar > 0:
                blended_velocity = velocity_per_bar * 0.6 + atr_velocity_per_bar * 0.4
            else:
                blended_velocity = atr_velocity_per_bar * 0.3  # Moving weakly, penalise heavily
            # Further boost by directional volume ratio (high-volume moves sustain longer)
            volume_ratio = max(1.0, float(latest.volume_ratio))
            blended_velocity *= min(1.5, 1.0 + (volume_ratio - 1.0) * 0.25)
            if blended_velocity > 0.001:
                eta = self.settings.target_percent / blended_velocity
                candidate.tp_eta_bars = round(eta, 2)
            else:
                candidate.tp_eta_bars = 9999.0
            candidate.reasons.append(f"eta={candidate.tp_eta_bars:.1f}bars")

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
        if self.settings.target_mode == "SMALL":
            # Primary sort: fastest estimated time to TP (fewer bars = better).
            # Secondary: score descending, so among equally fast coins the
            # one with stronger directional evidence wins.
            return sorted(candidates, key=lambda c: (c.tp_eta_bars, -c.score))
        return sorted(candidates, key=lambda c: c.score, reverse=True)

    def choose(self):
        candidates = self.analyse()
        if not candidates:
            return None, candidates
        best = candidates[0]
        direction_gap = abs(best.breakdown["long_score"] - best.breakdown["short_score"])
        if best.score < self.settings.min_score or direction_gap < self.settings.min_direction_gap:
            best.direction = "WAIT"
        elif self.settings.reverse_signal_direction:
            best.direction = "SHORT" if best.direction == "LONG" else "LONG"
            best.reasons.append("reverse_signal_direction=true")
        return best, candidates

