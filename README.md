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

The scanner uses closed 1m/5m/15m/1h candles and `exchangeInfo`, 24h ticker, klines, funding, OI history, taker buy/sell data, and depth. It prints the top five candidates and all score components. The active execution path uses `/fapi/v1/order` for market entries and Binance's current `/fapi/v1/algoOrder` for close-position TP/SL orders; legacy conditional orders are deliberately not used.

### Fast-moving market gate

`MIN_24H_ABS_CHANGE_PERCENT` requires a minimum absolute 24-hour move. `MIN_SHORT_TERM_MOVE_PERCENT` requires a minimum move across five closed 5-minute candles (25 minutes). A coin must pass both gates before it is scored. Start with `3` and `0.25`; raise them for fewer, faster-moving candidates.

## Structure

- `bot/api/` — only Binance HTTP requests and time synchronization.
- `bot/services/` — position reconciliation and protected execution.
- `bot/strategies/` — trading algorithms. Add a new strategy by implementing `Strategy.analyse()`; execution and risk controls do not need changes.
- `bot/indicators.py`, `bot/scorer.py`, `bot/risk_manager.py` — reusable strategy and risk primitives.

This is software, not financial advice. Test UAT thoroughly before enabling production.
