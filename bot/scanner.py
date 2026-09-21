from __future__ import annotations
from .indicators import enrich
from .scorer import score
class Scanner:
    def __init__(self, client, market, settings): self.client=client; self.market=market; self.s=settings
    def scan(self):
        out=[]
        for ticker in self.market.prefilter(self.s.pre_filter_limit)[:self.s.deep_analysis_limit]:
            symbol=ticker['symbol']
            try:
                frames=[enrich(self.market.candles(symbol,i)) for i in ('1m','5m','15m','1h')]
                latest=frames[1].iloc[-1]; depth=self.client.depth(symbol); bids=sum(float(x[1]) for x in depth['bids']); asks=sum(float(x[1]) for x in depth['asks']); imbalance=(bids-asks)/(bids+asks) if bids+asks else 0
                spread=(float(depth['asks'][0][0])-float(depth['bids'][0][0]))/float(ticker['lastPrice'])
                # Auxiliary data can be temporarily unavailable per symbol; retain
                # the candidate and score the missing component neutrally.
                try: f=self.client.funding(symbol); funding=float(f[-1]['fundingRate']) if f else 0
                except Exception: funding=0
                try:
                    oi=self.client.oi_history(symbol); oi_change=(float(oi[-1]['sumOpenInterestValue'])/float(oi[0]['sumOpenInterestValue'])-1) if len(oi)>1 and float(oi[0]['sumOpenInterestValue']) else 0
                except Exception: oi_change=0
                try: tv=self.client.taker_volume(symbol); taker_ratio=float(tv[-1]['buySellRatio']) if tv else 1
                except Exception: taker_ratio=1
                out.append(score(symbol,float(ticker['lastPrice']),float(ticker['priceChangePercent']),float(ticker['quoteVolume']),latest,oi_change,funding,taker_ratio,imbalance,spread,self.s.weights))
            except Exception: continue
        return sorted(out,key=lambda x:x.score,reverse=True)
    def decision(self):
        choices=self.scan()
        if not choices: return None,choices
        best=choices[0]
        direction_gap=abs(best.breakdown['long_score']-best.breakdown['short_score'])
        if best.score<self.s.min_score or direction_gap<self.s.min_direction_gap: best.direction='WAIT'
        return best,choices
