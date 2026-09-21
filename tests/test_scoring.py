from types import SimpleNamespace
from bot.scorer import score
def test_scoring():
 x=SimpleNamespace(ema9=2,ema21=1,return_5=.02,volume_ratio=2,rsi=55,atr=1);c=score('X',1,1,1,x,.01,0,1.2,.1,.001,{'trend':20,'momentum':15,'volume':15,'open_interest':15,'taker':15,'orderbook':10,'funding':10});assert c.direction=='LONG' and c.breakdown['long_score']>c.breakdown['short_score']
