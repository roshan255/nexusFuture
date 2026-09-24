from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta

from bot.api.binance import BinanceClient, BinanceError, BinanceRateLimitError
from bot.backtest import compare_direction_bias
from bot.config import configure_interactively, load_settings
from bot.logger import get_logger
from bot.market_data import MarketData
from bot.risk_manager import LeverageUnavailable, TradeSizeError
from bot.services.execution import TradeExecutor
from bot.services.positions import PositionService, PositionStateUnknown
from bot.services.trade_limits import TradeLimitService
from bot.strategies import RuleBasedStrategy


def format_candidate(candidate) -> str:
    return f"{candidate.symbol} {candidate.direction} score={candidate.score:.1f} L/S={candidate.breakdown['long_score']:.1f}/{candidate.breakdown['short_score']:.1f} reasons={', '.join(candidate.reasons)}"


def run_backtest(settings, symbol: str) -> None:
    log = get_logger(level=settings.log_level)
    client = BinanceClient(settings)
    try:
        market = MarketData(client, settings)
        candles = market.candles(symbol.upper(), "5m", settings.backtest_lookback_bars)
        report = compare_direction_bias(candles, settings.target_percent, settings.stop_loss_percent, settings.backtest_horizon_bars, settings.backtest_signal_step)
        log.info("backtest symbol=%s interval=5m target=%.2f%% stop=%.2f%% report=%s", symbol.upper(), settings.target_percent, settings.stop_loss_percent, report)
        if report["samples"] and report["opposite_minus_original"] >= 10:
            log.warning("backtest_direction_bias opposite exceeds original by %.2f points; investigate signal components before using any inversion", report["opposite_minus_original"])
    finally:
        client.close()


def run_cycle(settings, scan_only: bool, limits: TradeLimitService) -> None:
    log = get_logger(level=settings.log_level)
    client = BinanceClient(settings)
    try:
        if not scan_only:
            client.sync_time()
        market = MarketData(client, settings)
        positions = PositionService(client)
        executor = TradeExecutor(client, market, settings, positions)
        if not scan_only:
            try:
                position = positions.current_position()
            except PositionStateUnknown as exc:
                log.error("position_state_unknown detail=%s", exc)
                return
            if position:
                if positions.protection_missing(position.symbol):
                    protection = executor.protect_position(position)
                    log.warning("protection_restored symbol=%s tp=%s sl=%s", position.symbol, protection.take_profit, protection.stop_loss)
                else:
                    log.info("position_open symbol=%s quantity=%s entry=%s", position.symbol, position.quantity, position.entry_price)
                return
            if settings.target_mode == "LARGE":
                pending_entries = [order for order in client.open_orders() if order.get("reduceOnly") is not True]
                if pending_entries:
                    log.info("pending_large_entry symbol=%s status=%s; waiting", pending_entries[0].get("symbol"), pending_entries[0].get("status"))
                    return
        decision, candidates = RuleBasedStrategy(client, market, settings).choose()
        for candidate in candidates[:5]:
            log.info("rank %s", format_candidate(candidate))
        if not decision or decision.direction == "WAIT":
            log.info("decision=WAIT reason=no_clear_high_quality_direction")
            return
        if scan_only:
            log.info("decision=%s symbol=%s score=%.1f scan_only=true", decision.direction, decision.symbol, decision.score)
            return
        allowed, reason = limits.allow_entry()
        if not allowed:
            log.info("decision=WAIT reason=%s", reason)
            return
        result = executor.enter(decision)
        limits.record_entry()
        log.info("trade_submitted symbol=%s direction=%s mode=%s leverage=%sx quantity=%s details=%s", decision.symbol, decision.direction, result["mode"], result["leverage"], result["quantity"], {key: value for key, value in result.items() if key not in {"mode", "leverage", "quantity"}})
    except TradeSizeError as exc:
        log.warning("decision=WAIT reason=trade_size_invalid detail=%s", exc)
    except LeverageUnavailable as exc:
        log.warning("decision=WAIT reason=leverage_unavailable detail=%s", exc)
    except BinanceRateLimitError as exc:
        log.warning("binance_rate_limited detail=%s", exc)
    except (BinanceError, TimeoutError) as exc:
        log.error("binance_error detail=%s", exc)
    except RuntimeError as exc:
        log.error("cycle_error detail=%s", exc)
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-once", action="store_true", help="Scan and rank only; never submit an order.")
    parser.add_argument("--configure", action="store_true", help="Prompt for minimal settings and write .env.")
    parser.add_argument("--check-connection", action="store_true", help="Read-only Binance credential and clock test.")
    parser.add_argument("--backtest-symbol", metavar="SYMBOL", help="Target-first technical direction comparison on 5m candles.")
    args = parser.parse_args()
    if args.configure:
        configure_interactively()
        return
    settings = load_settings()
    log = get_logger(level=settings.log_level)
    if args.check_connection:
        client = BinanceClient(settings)
        try:
            log.info("connection_check_ok %s", client.check_credentials())
        finally:
            client.close()
        return
    if args.backtest_symbol:
        run_backtest(settings, args.backtest_symbol)
        return
    log.info("starting mode=%s target_mode=%s target=%.2f%% stop=%.2f%% interval=%ss", settings.mode, settings.target_mode, settings.target_percent, settings.stop_loss_percent, settings.scan_interval_seconds)
    limits = TradeLimitService(settings)
    if args.scan_once:
        run_cycle(settings, True, limits)
        return
    while True:
        started = time.monotonic()
        run_cycle(settings, False, limits)
        next_scan = datetime.now() + timedelta(seconds=max(0, settings.scan_interval_seconds - (time.monotonic() - started)))
        log.info("next_scan_at=%s", next_scan.strftime("%H:%M:%S"))
        time.sleep(max(0, settings.scan_interval_seconds - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
