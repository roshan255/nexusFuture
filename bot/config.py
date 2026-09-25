from __future__ import annotations

import os
from dataclasses import dataclass, field
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    mode: str = "UAT"
    api_key: str = ""
    api_secret: str = ""
    uat_base_url: str = "https://demo-fapi.binance.com"
    log_level: str = "INFO"
    scan_interval_seconds: int = 60
    reverse_signal_direction: bool = False
    target_mode: str = "SMALL"
    target_percent: float = 1.5
    stop_loss_percent: float = 1.0
    leverage: int = 5
    leverage_fallback: str = "USE_MAX"
    margin_mode: str = "FIXED"
    margin_per_trade_usdt: float = 10.0
    margin_percent: float = 100.0
    large_limit_offset_percent: float = 0.25
    large_limit_expiry_minutes: int = 240
    large_trailing_enabled: bool = False
    trailing_callback_percent: float = 1.0
    trailing_activation_percent: float = 5.0
    min_score: float = 70.0
    min_direction_gap: float = 8.0
    min_24h_abs_change_percent: float = 3.0
    min_short_term_move_percent: float = 0.25
    min_quote_volume_usdt: float = 5_000_000.0
    min_relative_volume: float = 1.1
    min_atr_percent: float = 0.15
    max_atr_percent: float = 5.0
    min_adx: float = 18.0
    max_spread_percent: float = 0.12
    breakout_lookback: int = 20
    pre_filter_limit: int = 50
    deep_analysis_limit: int = 20
    analysis_workers: int = 4
    cooldown_seconds: int = 300
    max_trades_per_day: int = 5
    backtest_lookback_bars: int = 1000
    backtest_horizon_bars: int = 72
    backtest_signal_step: int = 12
    metadata_cache_seconds: int = 3600
    news_enabled: bool = False
    news_api_url: str = "https://cryptocurrency.cv/api/news"
    news_api_key: str = ""
    news_max_bonus: float = 8.0
    enable_live_trading: bool = False
    weights: dict[str, float] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return "https://fapi.binance.com" if self.mode == "PRODUCTION" else self.uat_base_url.rstrip("/")

    @property
    def may_trade(self) -> bool:
        return self.mode == "UAT" or (self.mode == "PRODUCTION" and self.enable_live_trading)

    @property
    def take_profit_percent(self) -> float:
        """Compatibility alias for existing execution and risk helpers."""
        return self.target_percent


def _weights(read) -> dict[str, float]:
    defaults = {"trend": 14, "momentum": 10, "volume": 9, "open_interest": 8, "taker": 8, "orderbook": 7, "funding": 4, "macd": 8, "stoch_rsi": 5, "vwap": 7, "bollinger": 5, "adx": 8, "market_structure": 7, "multi_timeframe": 10, "target_reachability": 5, "news": 0}
    return {name: float(read(f"WEIGHT_{name.upper()}", str(value))) for name, value in defaults.items()}


def load_settings() -> Settings:
    load_dotenv()
    read = lambda name, default="": os.getenv(name, default)
    mode = read("MODE", "UAT").upper()
    target_mode = read("TARGET_MODE", "SMALL").upper()
    margin_mode = read("MARGIN_MODE", "FIXED").upper()
    fallback = read("LEVERAGE_FALLBACK", "USE_MAX").upper()
    target = float(read("TARGET_PERCENT", read("TAKE_PROFIT_PERCENT", "1.5")))
    settings = Settings(
        mode=mode, api_key=read("BINANCE_API_KEY"), api_secret=read("BINANCE_API_SECRET"), uat_base_url=read("UAT_BASE_URL", "https://demo-fapi.binance.com"), log_level=read("LOG_LEVEL", "INFO").upper(),
        scan_interval_seconds=int(read("SCAN_INTERVAL_SECONDS", "60")), reverse_signal_direction=_bool(read("REVERSE_SIGNAL_DIRECTION", "false")), target_mode=target_mode, target_percent=target, stop_loss_percent=float(read("STOP_LOSS_PERCENT", "1")), leverage=int(read("LEVERAGE", "5")), leverage_fallback=fallback,
        margin_mode=margin_mode, margin_per_trade_usdt=float(read("MARGIN_PER_TRADE_USDT", "10")), margin_percent=float(read("MARGIN_PERCENT", "100")), large_limit_offset_percent=float(read("LARGE_LIMIT_OFFSET_PERCENT", "0.25")), large_limit_expiry_minutes=int(read("LARGE_LIMIT_EXPIRY_MINUTES", "240")),
        large_trailing_enabled=_bool(read("LARGE_TRAILING_ENABLED", "false")), trailing_callback_percent=float(read("TRAILING_CALLBACK_PERCENT", "1")), trailing_activation_percent=float(read("TRAILING_ACTIVATION_PERCENT", "5")),
        min_score=float(read("MIN_SCORE", "70")), min_direction_gap=float(read("MIN_DIRECTION_GAP", "8")), min_24h_abs_change_percent=float(read("MIN_24H_ABS_CHANGE_PERCENT", "3")), min_short_term_move_percent=float(read("MIN_SHORT_TERM_MOVE_PERCENT", "0.25")),
        min_quote_volume_usdt=float(read("MIN_QUOTE_VOLUME_USDT", "5000000")), min_relative_volume=float(read("MIN_RELATIVE_VOLUME", "1.1")), min_atr_percent=float(read("MIN_ATR_PERCENT", "0.15")), max_atr_percent=float(read("MAX_ATR_PERCENT", "5")), min_adx=float(read("MIN_ADX", "18")), max_spread_percent=float(read("MAX_SPREAD_PERCENT", "0.12")), breakout_lookback=int(read("BREAKOUT_LOOKBACK", "20")),
        pre_filter_limit=int(read("PRE_FILTER_LIMIT", "50")), deep_analysis_limit=int(read("DEEP_ANALYSIS_LIMIT", "20")), analysis_workers=int(read("ANALYSIS_WORKERS", "4")), cooldown_seconds=int(read("COOLDOWN_SECONDS", "300")), max_trades_per_day=int(read("MAX_TRADES_PER_DAY", "5")), backtest_lookback_bars=int(read("BACKTEST_LOOKBACK_BARS", "1000")), backtest_horizon_bars=int(read("BACKTEST_HORIZON_BARS", "72")), backtest_signal_step=int(read("BACKTEST_SIGNAL_STEP", "12")), metadata_cache_seconds=int(read("METADATA_CACHE_SECONDS", "3600")),
        news_enabled=_bool(read("NEWS_ENABLED", "false")), news_api_url=read("NEWS_API_URL", "https://cryptocurrency.cv/api/news"), news_api_key=read("NEWS_API_KEY"), news_max_bonus=float(read("NEWS_MAX_BONUS", "8")), enable_live_trading=_bool(read("ENABLE_LIVE_TRADING", "false")), weights=_weights(read),
    )
    _validate(settings)
    return settings


def _validate(settings: Settings) -> None:
    if settings.mode not in {"UAT", "PRODUCTION"}: raise ValueError("MODE must be UAT or PRODUCTION")
    if settings.target_mode not in {"SMALL", "LARGE"}: raise ValueError("TARGET_MODE must be SMALL or LARGE")
    if settings.margin_mode not in {"FIXED", "PERCENT"}: raise ValueError("MARGIN_MODE must be FIXED or PERCENT")
    if settings.leverage_fallback not in {"USE_MAX", "SKIP"}: raise ValueError("LEVERAGE_FALLBACK must be USE_MAX or SKIP")
    if settings.scan_interval_seconds < 30: raise ValueError("SCAN_INTERVAL_SECONDS must be at least 30")
    if not 1 <= settings.analysis_workers <= 10: raise ValueError("ANALYSIS_WORKERS must be between 1 and 10")
    if not 0 < settings.margin_percent <= 100: raise ValueError("MARGIN_PERCENT must be in (0, 100]")
    if settings.target_mode == "SMALL" and not 0.5 <= settings.target_percent <= 5: raise ValueError("SMALL TARGET_PERCENT must be between 0.5 and 5")
    if settings.target_mode == "LARGE" and settings.target_percent < 20: raise ValueError("LARGE TARGET_PERCENT must be at least 20")
    if not 0.1 <= settings.trailing_callback_percent <= 10: raise ValueError("TRAILING_CALLBACK_PERCENT must be between 0.1 and 10")


def configure_interactively(path: str = ".env") -> None:
    mode = input("Mode [UAT/PRODUCTION] (UAT): ").strip().upper() or "UAT"
    api_key = input("Binance Futures API key: ").strip()
    api_secret = getpass("Binance Futures API secret: ").strip()
    target_mode = input("Target mode [SMALL/LARGE] (SMALL): ").strip().upper() or "SMALL"
    target = input("Target percent (1.5): ").strip() or "1.5"
    stop = input("Stop-loss percent (1): ").strip() or "1"
    leverage = input("Leverage (5): ").strip() or "5"
    interval = input("Scan interval seconds (60): ").strip() or "60"
    live = "false"
    if mode == "PRODUCTION": live = "true" if input("Enable REAL live trading? Type YES: ").strip() == "YES" else "false"
    Path(path).write_text(f"MODE={mode}\nBINANCE_API_KEY={api_key}\nBINANCE_API_SECRET={api_secret}\nTARGET_MODE={target_mode}\nTARGET_PERCENT={target}\nSTOP_LOSS_PERCENT={stop}\nLEVERAGE={leverage}\nSCAN_INTERVAL_SECONDS={interval}\nENABLE_LIVE_TRADING={live}\n", encoding="utf-8")
