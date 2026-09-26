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

Set `REVERSE_SIGNAL_DIRECTION=true` only to reverse an actionable decision (`LONG` becomes `SHORT`, and vice versa); `WAIT` remains `WAIT`.

`ANALYSIS_WORKERS=4` keeps up to four independent public-data symbol analyses in flight. Increase it only cautiously; Binance still applies request-weight limits.

`LEVERAGE_FALLBACK=USE_MAX` automatically falls back to the exchange maximum for the selected symbol. `LEVERAGE_FALLBACK=SKIP` emits a safe wait decision instead.

### Complete `.env` reference

| Setting | Meaning |
| --- | --- |
| `MODE` | `UAT` for Binance demo; `PRODUCTION` for real Binance Futures. |
| `BINANCE_API_KEY`, `BINANCE_API_SECRET` | Futures API credentials. Keep them private; never commit them. |
| `UAT_BASE_URL` | Demo Futures URL. Usually leave unchanged. |
| `ENABLE_LIVE_TRADING` | Must be `true` before production orders are permitted. |
| `LOG_LEVEL` | `INFO` for normal output; `DEBUG` also reports skipped-symbol/API details. |
| `SCAN_INTERVAL_SECONDS` | Seconds between completed scan cycles; minimum is 30. |
| `REVERSE_SIGNAL_DIRECTION` | When `true`, swaps only actionable LONG/SHORT decisions; WAIT is unchanged. |
| `TARGET_MODE` | `SMALL` uses market entry; `LARGE` uses one limit entry. |
| `TARGET_PERCENT` | Take-profit distance from entry. SMALL permits 0.5–5%; LARGE requires 20% or more. |
| `STOP_LOSS_PERCENT` | Stop distance from entry. |
| `LARGE_LIMIT_OFFSET_PERCENT` | Limit price offset from the current price in LARGE mode. |
| `LARGE_LIMIT_EXPIRY_MINUTES` | How long a LARGE GTD entry may remain open. |
| `LARGE_TRAILING_ENABLED` | Adds a trailing stop after a confirmed LARGE entry. |
| `TRAILING_CALLBACK_PERCENT` | Trailing-stop distance; Binance accepts 0.1–10. |
| `TRAILING_ACTIVATION_PERCENT` | Profit movement required before the LARGE trailing stop activates. |
| `LEVERAGE` | Requested leverage for a selected symbol. |
| `LEVERAGE_FALLBACK` | `USE_MAX` uses the symbol's permitted maximum; `SKIP` skips it instead. |
| `MARGIN_MODE` | `FIXED` uses a fixed USDT amount; `PERCENT` uses a percent of available USDT. |
| `MARGIN_PER_TRADE_USDT` | Margin amount when `MARGIN_MODE=FIXED`. |
| `MARGIN_PERCENT` | Available-balance percentage when `MARGIN_MODE=PERCENT` (1–100). |
| `MIN_SCORE` | Minimum combined score required for a trade. Higher means fewer, stricter entries. |
| `MIN_DIRECTION_GAP` | Required difference between LONG and SHORT scores. Prevents weak/unclear calls. |
| `MIN_24H_ABS_CHANGE_PERCENT` | Minimum absolute 24-hour move to consider a symbol. |
| `MIN_SHORT_TERM_MOVE_PERCENT` | Minimum absolute movement over five closed 5-minute candles. |
| `MIN_QUOTE_VOLUME_USDT` | Minimum 24-hour USDT quote volume. |
| `MIN_RELATIVE_VOLUME` | Minimum current volume divided by its recent 20-bar average. |
| `MIN_ATR_PERCENT`, `MAX_ATR_PERCENT` | Accepted 5-minute ATR range as a percent of price. |
| `MIN_ADX` | Minimum trend-strength reading; higher reduces sideways markets. |
| `MAX_SPREAD_PERCENT` | Maximum bid/ask spread permitted for an entry. |
| `BREAKOUT_LOOKBACK` | Legacy market-structure range length; retained for strategy extensions. |
| `SUPPORT_RESISTANCE_LOOKBACK` | Closed 5-minute bars used for recent support/resistance; 48 is roughly four hours. |
| `SUPPORT_RESISTANCE_ZONE_ATR` | Distance from a level, measured in ATR, considered “near” that level. |
| `BREAKOUT_CONFIRM_ATR` | ATR buffer required beyond support/resistance to treat a move as a confirmed break. |
| `REJECTION_WICK_BODY_RATIO` | Wick/body ratio needed to recognise a rejection candle at support or resistance. |
| `PRE_FILTER_LIMIT` | Number of liquid/moving symbols kept after the cheap ticker filter. |
| `DEEP_ANALYSIS_LIMIT` | Number of prefiltered symbols that receive full multi-timeframe analysis. |
| `ANALYSIS_WORKERS` | Concurrent public-data analyses (1–10); higher can increase API pressure. |
| `COOLDOWN_SECONDS` | Minimum wait after an entry before another entry; use `0` to disable. |
| `MAX_TRADES_PER_DAY` | In-process daily entry cap; use a very large value to effectively disable. |
| `METADATA_CACHE_SECONDS` | How long exchange symbol/leverage rules stay cached. |
| `BACKTEST_LOOKBACK_BARS` | Number of historical 5-minute candles used by `--backtest-symbol`. |
| `BACKTEST_HORIZON_BARS` | Future 5-minute bars inspected to decide target-first vs stop-first. |
| `BACKTEST_SIGNAL_STEP` | Bars skipped between backtest entries; higher gives fewer, less-overlapping samples. |
| `NEWS_ENABLED` | Enables the optional news score modifier; it never independently starts a trade. |
| `NEWS_API_URL`, `NEWS_API_KEY` | Endpoint and optional credential for the news feed. |
| `NEWS_MAX_BONUS` | Largest directional score adjustment news can contribute. |
| `WEIGHT_*` | Relative importance for a signal. `0` disables it. `WEIGHT_SUPPORT_RESISTANCE` controls the new level/rebound signal. |

### Support, resistance, and rebound handling

The strategy derives recent support and resistance from closed 5-minute highs/lows. It no longer awards a high LONG score simply because price is near the top of that range. Near resistance, LONG evidence is reduced and a bearish upper-wick rejection favours SHORT; near support the mirror image applies. A move is rewarded as a breakout only after its close clears the level by `BREAKOUT_CONFIRM_ATR` times ATR. Each ranked result logs its `level`, `support`, and `resistance` context.

### Fast-moving market gate

`MIN_24H_ABS_CHANGE_PERCENT` requires a minimum absolute 24-hour move. `MIN_SHORT_TERM_MOVE_PERCENT` requires a minimum move across five closed 5-minute candles (25 minutes). A coin must pass both gates before it is scored. Start with `3` and `0.25`; raise them for fewer, faster-moving candidates.

## Structure

- `bot/api/` — Binance HTTP requests, metadata cache, rate-limit handling, and time synchronization.
- `bot/services/` — position reconciliation, protected execution, news modifier, and trade limits.
- `bot/strategies/` — trading algorithms. Add a new strategy by implementing `Strategy.analyse()`; execution and risk controls do not need changes.
- `bot/backtest.py` — target-first historical direction and inverse-bias comparison.
- `bot/indicators.py`, `bot/scorer.py`, `bot/risk_manager.py` — reusable strategy and risk primitives.

This is software, not financial advice. Test UAT thoroughly before enabling production.
