# Binance USDⓈ-M Futures Bot

Rule-based, restart-safe USDⓈ-M Futures scanner. It is local-first and defaults to UAT (`demo-fapi.binance.com`). `--scan-once` never submits orders. The continuous runner can place demo orders in UAT; production orders require `MODE=PRODUCTION` and `ENABLE_LIVE_TRADING=true`.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m bot.main --configure
python -m bot.main --scan-once
pytest
```

Run continually with `python -m bot.main`. Copy `.env.example` to `.env`; API secrets are only read from environment variables and `.env` is ignored by Git.

The scanner uses closed 1m/5m/15m/1h candles and `exchangeInfo`, 24h ticker, klines, funding, OI history, taker buy/sell data, and depth. It prints the top five candidates and all score components. The active execution path uses `/fapi/v1/order` for market entries and Binance's current `/fapi/v1/algoOrder` for close-position TP/SL orders; legacy conditional orders are deliberately not used.

This is software, not financial advice. Test UAT thoroughly before enabling production.
