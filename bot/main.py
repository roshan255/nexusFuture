from __future__ import annotations
import argparse
import time
from bot.api.binance import BinanceClient
from bot.config import configure_interactively, load_settings
from bot.logger import get_logger
from bot.market_data import MarketData
from bot.services.execution import TradeExecutor
from bot.services.positions import PositionService, PositionStateUnknown
from bot.strategies import RuleBasedStrategy
from bot.risk_manager import TradeSizeError

def format_candidate(c) -> str:
    return f"{c.symbol:12} {c.direction:5} score={c.score:5.2f} change={c.price_change:7.2f}% volume={c.quote_volume:.0f} RSI={c.rsi:.1f} ATR={c.atr:.8f} OI={c.oi_change:.2%} funding={c.funding:.6f} taker={c.taker_ratio:.3f} spread={c.spread:.4%} parts={c.breakdown}"

def run_cycle(settings, scan_only: bool) -> None:
    log = get_logger(); client = BinanceClient(settings)
    try:
        if not scan_only: client.sync_time()
        market = MarketData(client); positions = PositionService(client)
        if not (scan_only and not settings.api_key):
            try: position = positions.current_position()
            except PositionStateUnknown as exc:
                log.error("position_state_unknown detail=%s", exc); return
            if position:
                log.info("position_exists symbol=%s quantity=%s entry=%s; monitoring only", position.symbol, position.quantity, position.entry_price); return
        decision, candidates = RuleBasedStrategy(client, market, settings).choose()
        for candidate in candidates[:5]: log.info("candidate %s", format_candidate(candidate))
        if not decision or decision.direction == "WAIT": log.info("decision=WAIT"); return
        log.info("decision=%s symbol=%s score=%s strategy=rule_based", decision.direction, decision.symbol, decision.score)
        if not scan_only:
            try:
                protection = TradeExecutor(client, market, settings, positions).enter_with_protection(decision)
            except TradeSizeError as exc:
                log.warning("decision=WAIT reason=trade_size_invalid detail=%s", exc)
                return
            log.info("trade_protected symbol=%s tp=%s sl=%s", decision.symbol, protection.take_profit, protection.stop_loss)
    finally: client.close()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-once", action="store_true", help="Scan without orders.")
    parser.add_argument("--configure", action="store_true", help="Prompt for settings and write .env.")
    parser.add_argument("--check-connection", action="store_true", help="Read-only credentials and Binance clock test.")
    args = parser.parse_args()
    if args.configure: configure_interactively(); return
    settings = load_settings(); log = get_logger()
    if args.check_connection:
        client = BinanceClient(settings)
        try: log.info("connection_check_ok %s", client.check_credentials())
        finally: client.close()
        return
    log.info("starting mode=%s base_url=%s trading_enabled=%s", settings.mode, settings.base_url, settings.may_trade)
    if args.scan_once: run_cycle(settings, True); return
    while True:
        started = time.monotonic()
        try: run_cycle(settings, False)
        except Exception as exc: log.exception("cycle_failed error=%s", exc)
        time.sleep(max(0, 60 - (time.monotonic() - started)))

if __name__ == "__main__": main()
