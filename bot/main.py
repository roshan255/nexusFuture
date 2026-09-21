import argparse,time
from .config import load_settings,configure_interactively
from .binance_client import BinanceClient
from .logger import get_logger
from .market_data import MarketData
from .scanner import Scanner
from .position_manager import PositionManager
from .trade_executor import TradeExecutor
def fmt(c): return f'{c.symbol:12} {c.direction:5} score={c.score:5.2f} change={c.price_change:7.2f}% volume={c.quote_volume:.0f} RSI={c.rsi:.1f} ATR={c.atr:.8f} OI={c.oi_change:.2%} funding={c.funding:.6f} taker={c.taker_ratio:.3f} spread={c.spread:.4%} parts={c.breakdown}'
def cycle(s,scan_only):
    log=get_logger();client=BinanceClient(s)
    try:
        market=MarketData(client)
        # Public scan smoke tests work without credentials. A trading cycle always reconciles.
        if not (scan_only and not s.api_key):
            pos,known=PositionManager(client).reconcile()
            if not known:log.error('position_state_unknown; refusing to trade');return
            if pos:log.info('position_exists symbol=%s quantity=%s; monitoring only',pos.symbol,pos.quantity);return
        candidate,choices=Scanner(client,market,s).decision()
        for c in choices[:5]:log.info('candidate %s',fmt(c))
        if not candidate or candidate.direction=='WAIT':log.info('decision=WAIT');return
        log.info('decision=%s symbol=%s score=%s',candidate.direction,candidate.symbol,candidate.score)
        if not scan_only:TradeExecutor(client,market,s).enter_with_protection(candidate)
    finally:client.close()
def main():
    p=argparse.ArgumentParser();p.add_argument('--scan-once',action='store_true');p.add_argument('--configure',action='store_true');a=p.parse_args()
    if a.configure:configure_interactively();return
    s=load_settings();get_logger().info('starting mode=%s trading_enabled=%s',s.mode,s.may_trade)
    if a.scan_once:cycle(s,True);return
    while True:
        t=time.monotonic()
        try:cycle(s,False)
        except Exception as e:get_logger().exception('cycle_failed error=%s',e)
        time.sleep(max(0,60-(time.monotonic()-t)))
if __name__=='__main__':main()
