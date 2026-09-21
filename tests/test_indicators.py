import pandas as pd
from bot.indicators import enrich
def test_indicators():
 f=pd.DataFrame({'open':range(1,40),'high':range(2,41),'low':range(0,39),'close':range(1,40),'volume':[10]*39});x=enrich(f);assert x.ema9.iloc[-1]>x.ema21.iloc[-1] and x.atr.iloc[-1]>0
