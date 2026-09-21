from __future__ import annotations
import pandas as pd
from .models import SymbolRules
class MarketData:
    def __init__(self, client): self.client=client; self.rules=self._rules()
    def _rules(self):
        result={}
        for s in self.client.exchange_info()['symbols']:
            if s['status']!='TRADING' or s['contractType']!='PERPETUAL' or s['quoteAsset']!='USDT': continue
            f={x['filterType']:x for x in s['filters']}; lot=f.get('LOT_SIZE',{}); price=f.get('PRICE_FILTER',{}); minimum=f.get('MIN_NOTIONAL',f.get('NOTIONAL',{}))
            result[s['symbol']]=SymbolRules(s['symbol'],float(price['tickSize']),float(lot['stepSize']),float(lot['minQty']),float(minimum.get('notional',minimum.get('minNotional',0))))
        return result
    def candles(self,symbol,interval):
        rows=self.client.klines(symbol,interval,101)[:-1] # open candle is never a signal
        return pd.DataFrame(rows,columns=['time','open','high','low','close','volume','close_time','quote_volume','trades','tb_base','tb_quote','ignore']).astype({'open':float,'high':float,'low':float,'close':float,'volume':float})
    def prefilter(self,limit):
        rows=[r for r in self.client.ticker_24h() if r['symbol'] in self.rules]
        return sorted(rows,key=lambda r:float(r['quoteVolume'])*max(abs(float(r['priceChangePercent'])),.1),reverse=True)[:limit]
