from .models import Position
class PositionManager:
    def __init__(self,client): self.client=client
    def reconcile(self):
        try: rows=self.client.positions()
        except Exception: return None,False
        open_=[r for r in rows if abs(float(r['positionAmt']))>0]
        if len(open_)>1:return None,False
        if not open_:return None,True
        r=open_[0];return Position(r['symbol'],float(r['positionAmt']),float(r['entryPrice'])),True
    def cleanup_protection(self,symbol):
        for order in self.client.open_algo_orders(symbol):self.client.cancel_algo(symbol,order['algoId'])
