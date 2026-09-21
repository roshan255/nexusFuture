from __future__ import annotations
import pandas as pd
def ema(s: pd.Series, period: int) -> pd.Series: return s.ewm(span=period, adjust=False).mean()
def rsi(close: pd.Series, period: int=14) -> pd.Series:
    d=close.diff(); gain=d.clip(lower=0).ewm(alpha=1/period,adjust=False).mean(); loss=(-d.clip(upper=0)).ewm(alpha=1/period,adjust=False).mean()
    return 100 - 100/(1+gain/loss.replace(0,float('nan')))
def atr(frame: pd.DataFrame, period: int=14) -> pd.Series:
    prev=frame.close.shift(); tr=pd.concat([frame.high-frame.low,(frame.high-prev).abs(),(frame.low-prev).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/period,adjust=False).mean()
def enrich(frame: pd.DataFrame) -> pd.DataFrame:
    x=frame.copy(); x['ema9']=ema(x.close,9); x['ema21']=ema(x.close,21); x['rsi']=rsi(x.close); x['atr']=atr(x); x['return_5']=x.close.pct_change(5); x['volume_ratio']=x.volume/x.volume.rolling(20).mean(); return x
