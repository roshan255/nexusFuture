from __future__ import annotations
import hashlib,hmac,time
from urllib.parse import urlencode
import httpx
from .config import Settings

class BinanceError(RuntimeError): pass
class BinanceClient:
    """All Binance REST I/O. Signed writes are hard-blocked outside confirmed production."""
    def __init__(self, settings: Settings): self.s=settings; self.http=httpx.Client(base_url=settings.base_url,timeout=20); self.last_private_request_ok=True
    def close(self): self.http.close()
    def _request(self, method, path, params=None, signed=False, trading=False):
        if trading and not self.s.may_trade: raise PermissionError('Live orders require MODE=PRODUCTION and ENABLE_LIVE_TRADING=true')
        params=dict(params or {})
        headers={}
        if signed:
            if not self.s.api_key or not self.s.api_secret: raise BinanceError('BINANCE_API_KEY and BINANCE_API_SECRET are required for account access')
            params.update(timestamp=int(time.time()*1000),recvWindow=5000)
            params['signature']=hmac.new(self.s.api_secret.encode(),urlencode(params).encode(),hashlib.sha256).hexdigest(); headers['X-MBX-APIKEY']=self.s.api_key
        try: r=self.http.request(method,path,params=params,headers=headers)
        except httpx.TimeoutException as e: raise TimeoutError(f'Binance timeout on {path}; reconcile state before retrying') from e
        if r.is_error: raise BinanceError(f'{method} {path}: {r.status_code} {r.text}')
        return r.json()
    def exchange_info(self): return self._request('GET','/fapi/v1/exchangeInfo')
    def ticker_24h(self): return self._request('GET','/fapi/v1/ticker/24hr')
    def latest_price(self,symbol): return float(self._request('GET','/fapi/v1/ticker/price',{'symbol':symbol})['price'])
    def klines(self,symbol,interval,limit=100): return self._request('GET','/fapi/v1/klines',{'symbol':symbol,'interval':interval,'limit':limit})
    def depth(self,symbol,limit=20): return self._request('GET','/fapi/v1/depth',{'symbol':symbol,'limit':limit})
    def funding(self,symbol): return self._request('GET','/fapi/v1/fundingRate',{'symbol':symbol,'limit':1})
    def oi_history(self,symbol): return self._request('GET','/futures/data/openInterestHist',{'symbol':symbol,'period':'5m','limit':2})
    def taker_volume(self,symbol): return self._request('GET','/futures/data/takerlongshortRatio',{'symbol':symbol,'period':'5m','limit':1})
    def positions(self): return self._request('GET','/fapi/v3/positionRisk',signed=True)
    def account(self): return self._request('GET','/fapi/v3/account',signed=True)
    def open_algo_orders(self,symbol=None): return self._request('GET','/fapi/v1/openAlgoOrders',({'symbol':symbol} if symbol else {}),signed=True)
    def change_leverage(self,symbol,leverage): return self._request('POST','/fapi/v1/leverage',{'symbol':symbol,'leverage':leverage},signed=True,trading=True)
    def market_order(self,symbol,side,quantity,client_id): return self._request('POST','/fapi/v1/order',{'symbol':symbol,'side':side,'type':'MARKET','quantity':quantity,'newClientOrderId':client_id,'newOrderRespType':'RESULT'},signed=True,trading=True)
    def algo_close(self,symbol,side,kind,trigger_price,client_id):
        p={'algoType':'CONDITIONAL','symbol':symbol,'side':side,'type':kind,'triggerPrice':trigger_price,'closePosition':'true','workingType':'CONTRACT_PRICE','clientAlgoId':client_id}
        return self._request('POST','/fapi/v1/algoOrder',p,signed=True,trading=True)
    def cancel_algo(self,symbol,algo_id): return self._request('DELETE','/fapi/v1/algoOrder',{'symbol':symbol,'algoId':algo_id},signed=True,trading=True)
    def close_market(self,symbol,side,quantity): return self.market_order(symbol,side,quantity,f'failsafe-{int(time.time()*1000)}')
