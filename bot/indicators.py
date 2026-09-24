from __future__ import annotations
import pandas as pd
import numpy as np
def ema(s: pd.Series, period: int) -> pd.Series: return s.ewm(span=period, adjust=False).mean()
def rsi(close: pd.Series, period: int=14) -> pd.Series:
    d=close.diff(); gain=d.clip(lower=0).ewm(alpha=1/period,adjust=False).mean(); loss=(-d.clip(upper=0)).ewm(alpha=1/period,adjust=False).mean()
    return 100 - 100/(1+gain/loss.replace(0,float('nan')))
def atr(frame: pd.DataFrame, period: int=14) -> pd.Series:
    prev=frame.close.shift(); tr=pd.concat([frame.high-frame.low,(frame.high-prev).abs(),(frame.low-prev).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/period,adjust=False).mean()

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = ema(close, 12) - ema(close, 26)
    signal = ema(line, 9)
    return line, signal, line - signal

def stochastic_rsi(close: pd.Series, period: int = 14) -> tuple[pd.Series, pd.Series]:
    value = rsi(close, period)
    lowest = value.rolling(period).min()
    highest = value.rolling(period).max()
    k = 100 * (value - lowest) / (highest - lowest).replace(0, np.nan)
    return k, k.rolling(3).mean()

def bollinger(close: pd.Series, period: int = 20, stddev: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = sma(close, period)
    deviation = close.rolling(period).std()
    return middle, middle + stddev * deviation, middle - stddev * deviation

def adx(frame: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    up_move = frame.high.diff()
    down_move = -frame.low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    average_range = atr(frame, period).replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / average_range
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / average_range
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False).mean(), plus_di, minus_di

def vwap(frame: pd.DataFrame) -> pd.Series:
    typical_price = (frame.high + frame.low + frame.close) / 3
    return (typical_price * frame.volume).cumsum() / frame.volume.cumsum().replace(0, np.nan)
def enrich(frame: pd.DataFrame) -> pd.DataFrame:
    x=frame.copy()
    x['ema9']=ema(x.close,9); x['ema21']=ema(x.close,21)
    x['sma20']=sma(x.close,20); x['sma50']=sma(x.close,50); x['sma200']=sma(x.close,200)
    x['rsi']=rsi(x.close); x['atr']=atr(x)
    x['macd'],x['macd_signal'],x['macd_histogram']=macd(x.close)
    x['stoch_rsi_k'],x['stoch_rsi_d']=stochastic_rsi(x.close)
    x['bb_middle'],x['bb_upper'],x['bb_lower']=bollinger(x.close)
    x['adx'],x['plus_di'],x['minus_di']=adx(x)
    x['vwap']=vwap(x)
    x['return_5']=x.close.pct_change(5); x['return_20']=x.close.pct_change(20)
    x['volume_ratio']=x.volume/x.volume.rolling(20).mean()
    x['bb_width']=(x.bb_upper-x.bb_lower)/x.bb_middle.replace(0,np.nan)
    return x
