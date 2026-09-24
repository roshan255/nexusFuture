# Binance USDⓈ-M Futures Bot

Rule-based, restart-safe USDⓈ-M Futures scanner. `--scan-once` never submits orders. UAT uses the Binance demo URL; production always uses Binance's official `https://fapi.binance.com` URL and requires `MODE=PRODUCTION` plus `ENABLE_LIVE_TRADING=true`.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m bot.main --configure
python -m bot.main --scan-once
pytest
```

Run continually with `python -m bot.main`. Before trading, run the read-only diagnostic: `python -m bot.main --check-connection`. It confirms API signing, the server-clock offset, and position access while never placing an order. API secrets are only read from `.env`, which is ignored by Git.

The scanner uses closed 1m/5m/15m/1h candles and `exchangeInfo`, 24h ticker, klines, funding, OI history, taker buy/sell data, and depth. It ranks the top five candidates with readable reasons. The active execution path uses `/fapi/v1/order` for entries and Binance's current `/fapi/v1/algoOrder` for close-position TP/SL and optional trailing stops; legacy conditional orders are deliberately not used.

### Target-first validation

Run `python -m bot.main --backtest-symbol BTCUSDT` before trusting a configuration. It tests each historical technical direction and its opposite from the same entry, then records which reaches the configured target or stop first. A bar touching both is marked `AMBIGUOUS`, not counted as a win. A higher opposite win rate is a bias warning to investigate—not an automatic instruction to flip all signals.

### Execution modes

`TARGET_MODE=SMALL` accepts targets from 0.5% to 5% and submits a market entry, then verifies position state and places TP/SL. `TARGET_MODE=LARGE` requires a target of at least 20%, places one GTD limit entry, and waits for it rather than stacking entries. Enable `LARGE_TRAILING_ENABLED=true` to add a trailing stop after the entry is confirmed.

### Configuration

Copy `.env.example` to `.env` and tune the documented groups there: target/stop and mode; leverage/sizing; liquidity, volatility and signal thresholds; cooldown and daily-entry caps; target-first backtest window; optional news modifier; and per-signal weights. Set any `WEIGHT_*` value to `0` to disable that signal.

`ANALYSIS_WORKERS=4` keeps up to four independent public-data symbol analyses in flight. Increase it only cautiously; Binance still applies request-weight limits.

`LEVERAGE_FALLBACK=USE_MAX` automatically falls back to the exchange maximum for the selected symbol. `LEVERAGE_FALLBACK=SKIP` emits a safe wait decision instead.

### Fast-moving market gate

`MIN_24H_ABS_CHANGE_PERCENT` requires a minimum absolute 24-hour move. `MIN_SHORT_TERM_MOVE_PERCENT` requires a minimum move across five closed 5-minute candles (25 minutes). A coin must pass both gates before it is scored. Start with `3` and `0.25`; raise them for fewer, faster-moving candidates.

## Structure

- `bot/api/` — Binance HTTP requests, metadata cache, rate-limit handling, and time synchronization.
- `bot/services/` — position reconciliation, protected execution, news modifier, and trade limits.
- `bot/strategies/` — trading algorithms. Add a new strategy by implementing `Strategy.analyse()`; execution and risk controls do not need changes.
- `bot/backtest.py` — target-first historical direction and inverse-bias comparison.
- `bot/indicators.py`, `bot/scorer.py`, `bot/risk_manager.py` — reusable strategy and risk primitives.

This is software, not financial advice. Test UAT thoroughly before enabling production.
