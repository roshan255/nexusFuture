from .models import Candidate
def _clamp(x): return max(0,min(100,x))
def score(symbol, price, change, quote_volume, latest, oi_change, funding, taker_ratio, imbalance, spread, weights):
    trend=100 if latest.ema9>latest.ema21 else 0; momentum=_clamp(50+latest.return_5*5000); volume=_clamp(latest.volume_ratio*50); oi=_clamp(50+oi_change*1000); taker=_clamp(50+(taker_ratio-1)*100); book=_clamp(50+imbalance*100)
    long={'trend':trend,'momentum':momentum,'volume':volume,'open_interest':oi,'taker':taker,'orderbook':book,'funding':_clamp(50-funding*100000)}; short={'trend':100-trend,'momentum':100-momentum,'volume':volume,'open_interest':oi,'taker':100-taker,'orderbook':100-book,'funding':_clamp(50+funding*100000)}
    total=sum(weights.values()); ls=sum(long[k]*weights[k] for k in weights)/total; ss=sum(short[k]*weights[k] for k in weights)/total; direction='LONG' if ls>=ss else 'SHORT'; parts=long if direction=='LONG' else short
    parts={k:round(v,2) for k,v in parts.items()}; parts.update(long_score=round(ls,2),short_score=round(ss,2)); return Candidate(symbol,direction,round(max(ls,ss),2),price,change,quote_volume,float(latest.rsi),float(latest.atr),oi_change,funding,taker_ratio,spread,parts)
