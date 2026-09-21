import time
from .risk_manager import quantity_for_margin,protective_prices,selected_margin
class TradeExecutor:
    def __init__(self,client,market,settings):self.client=client;self.market=market;self.s=settings
    def enter_with_protection(self,candidate):
        if not self.s.may_trade:raise PermissionError('Live execution requires MODE=PRODUCTION and ENABLE_LIVE_TRADING=true')
        rules=self.market.rules[candidate.symbol]
        available=float(self.client.account()['availableBalance'])
        margin=selected_margin(self.s.margin_mode,self.s.margin_per_trade_usdt,self.s.margin_percent,available)
        q=quantity_for_margin(margin,self.s.leverage,candidate.price,rules);self.client.change_leverage(candidate.symbol,self.s.leverage)
        side='BUY' if candidate.direction=='LONG' else 'SELL';exit_side='SELL' if side=='BUY' else 'BUY';order=self.client.market_order(candidate.symbol,side,q,f'entry-{int(time.time()*1000)}');filled=float(order.get('executedQty',0));entry=float(order.get('avgPrice',0) or candidate.price)
        if filled<=0:raise RuntimeError('Market order not confirmed filled; reconcile Binance before any action')
        p=protective_prices(entry,candidate.direction,self.s.take_profit_percent,self.s.stop_loss_percent,rules.tick_size)
        try:
            tp=self.client.algo_close(candidate.symbol,exit_side,'TAKE_PROFIT_MARKET',p.take_profit,f'tp-{int(time.time()*1000)}');sl=self.client.algo_close(candidate.symbol,exit_side,'STOP_MARKET',p.stop_loss,f'sl-{int(time.time()*1000)}');ids={str(tp.get('algoId')),str(sl.get('algoId'))};found={str(x.get('algoId')) for x in self.client.open_algo_orders(candidate.symbol)}
            if not ids<=found:raise RuntimeError('Protection orders not visible after placement')
            return order,p
        except Exception:self.client.close_market(candidate.symbol,exit_side,filled);raise
