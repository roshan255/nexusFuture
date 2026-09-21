from __future__ import annotations
from dataclasses import dataclass, field
import os
from getpass import getpass
from pathlib import Path
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    mode: str = "UAT"; api_key: str = ""; api_secret: str = ""
    leverage: int = 5; margin_per_trade_usdt: float = 10; margin_mode: str = "FIXED"; margin_percent: float = 100
    take_profit_percent: float = .50; stop_loss_percent: float = .30
    min_score: float = 70; min_direction_gap: float = 5
    pre_filter_limit: int = 50; deep_analysis_limit: int = 20; enable_live_trading: bool = False
    uat_base_url: str = "https://demo-fapi.binance.com"
    weights: dict[str, float] = field(default_factory=lambda: {"trend":20,"momentum":15,"volume":15,"open_interest":15,"taker":15,"orderbook":10,"funding":10})
    @property
    def base_url(self) -> str: return "https://fapi.binance.com" if self.mode == "PRODUCTION" else self.uat_base_url.rstrip("/")
    @property
    def may_trade(self) -> bool: return self.mode == "UAT" or (self.mode == "PRODUCTION" and self.enable_live_trading)

def _bool(v: str) -> bool: return v.strip().lower() in {"1","true","yes","on"}
def load_settings() -> Settings:
    load_dotenv(); g=lambda k,d="": os.getenv(k,d)
    mode=g("MODE","UAT").upper()
    if mode not in {"UAT","PRODUCTION"}: raise ValueError("MODE must be UAT or PRODUCTION")
    margin_mode=g("MARGIN_MODE","FIXED").upper()
    if margin_mode not in {"FIXED","PERCENT"}: raise ValueError("MARGIN_MODE must be FIXED or PERCENT")
    percent=float(g("MARGIN_PERCENT","100"))
    if not 0 < percent <= 100: raise ValueError("MARGIN_PERCENT must be greater than 0 and at most 100")
    return Settings(mode=mode,api_key=g("BINANCE_API_KEY"),api_secret=g("BINANCE_API_SECRET"),leverage=int(g("LEVERAGE","5")),margin_per_trade_usdt=float(g("MARGIN_PER_TRADE_USDT","10")),margin_mode=margin_mode,margin_percent=percent,take_profit_percent=float(g("TAKE_PROFIT_PERCENT",".50")),stop_loss_percent=float(g("STOP_LOSS_PERCENT",".30")),min_score=float(g("MIN_SCORE","70")),min_direction_gap=float(g("MIN_DIRECTION_GAP","5")),pre_filter_limit=int(g("PRE_FILTER_LIMIT","50")),deep_analysis_limit=int(g("DEEP_ANALYSIS_LIMIT","20")),enable_live_trading=_bool(g("ENABLE_LIVE_TRADING","false")),uat_base_url=g("UAT_BASE_URL","https://demo-fapi.binance.com"))

def configure_interactively(path: str = ".env") -> None:
    mode=input("Mode [UAT/PRODUCTION] (UAT): ").strip().upper() or "UAT"
    if mode not in {"UAT","PRODUCTION"}: raise ValueError("Mode must be UAT or PRODUCTION")
    key=input("Binance Futures API key: ").strip(); secret=getpass("Binance Futures API secret: ").strip()
    leverage=input("Leverage (5): ").strip() or "5"; sizing=input("Margin mode [FIXED/PERCENT] (FIXED): ").strip().upper() or "FIXED"
    if sizing not in {"FIXED","PERCENT"}: raise ValueError("Margin mode must be FIXED or PERCENT")
    margin=input("Fixed margin per trade USDT (10): ").strip() or "10" if sizing=="FIXED" else "0"
    percent=input("Available USDT margin percent (100): ").strip() or "100" if sizing=="PERCENT" else "0"
    tp=input("Take profit percent (0.50): ").strip() or "0.50"; sl=input("Stop loss percent (0.30): ").strip() or "0.30"
    minimum=input("Minimum score (70): ").strip() or "70"; gap=input("Minimum direction gap (5): ").strip() or "5"; live="false"
    if mode=="PRODUCTION": live="true" if input("Enable REAL live trading? Type YES to confirm: ").strip()=="YES" else "false"
    Path(path).write_text(f"MODE={mode}\nBINANCE_API_KEY={key}\nBINANCE_API_SECRET={secret}\nLEVERAGE={leverage}\nMARGIN_MODE={sizing}\nMARGIN_PER_TRADE_USDT={margin}\nMARGIN_PERCENT={percent}\nTAKE_PROFIT_PERCENT={tp}\nSTOP_LOSS_PERCENT={sl}\nMIN_SCORE={minimum}\nMIN_DIRECTION_GAP={gap}\nPRE_FILTER_LIMIT=50\nDEEP_ANALYSIS_LIMIT=20\nENABLE_LIVE_TRADING={live}\nUAT_BASE_URL=https://demo-fapi.binance.com\n",encoding="utf-8")
