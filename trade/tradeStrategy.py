# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         tradeStrategy.py
time:         2017/9/7 下午1:47
description: 

'''

__author__ = 'Jimmy'


from trade.api import *
from utils.environment import *
from utils.objects import *
from database import tradeStorage as ts
from utils import ta as ta
import gc as gc
import threading
from trade.order import *
from trade.symbol import *
from trade.portfolio import *
from datetime import datetime as dt
import time as tm

class TradeStrategy(object):
    def __init__(self):
        self.context = Context()
        self._lock = threading.Lock()
        self.initialize()
        # check context 关键参数是否正确
        self.context.check_context()

        self.force_close_flags = {}
        for symbol in self.context.universe:
            # 初始化symbol属性
            self.context.symbol_infos[symbol] = Symbol(symbol)
            if self.context.receive_bar_flag:
                # 如果接收bar 初始化TickConver
                self.context.tick_convers[symbol] = ta.TickConver(symbol, self.context.bar_frequency)
            self.force_close_flags[symbol] = False
        # 初始化持仓
        self.context.portfolio = Portfolio(init_cash=self.context.init_cash)
        self.context.portfolio.symbol_infos = self.context.symbol_infos

    # api
    def initialize(self):
        raise NotImplementedError


    def handle_bar(self, bar):
        pass

    # 接收tick方法
    def handle_tick(self, tick):
        pass

    # 交易日开始之前
    # 结算上一个交易日
    def before_trading(self):
        pass

    # order 状态改变了走这个方法 成交、部分成交、撤销、未成交....
    def order_change(self,order):
        pass

    # 成交后走这个方法
    def on_trade(self, trade):
        pass

    # 日内策略截止交易信号发出时
    # 目的在于交易日结束时提前全部平仓
    def handle_force_close(self, symbol):
        pass

    # 交易日结束后可通过此接口操作  比如修改context部分参数的值...
    def trading_end(self):
        pass

    # 撤单
    def cancel_order(self, order):
        event = Event(EVENT_CANCEL)
        event.dict = order
        event.sync_flag = False
        self._engine.sendEvent(event)

    # 便捷API
    # 开多
    def long(self, instrument_id, vol, limit_price = 0):
        symbol_obj = self.context.symbol_infos[instrument_id]
        if symbol_obj.exch_code != 'SHFE':
            self.order_(instrument_id=instrument_id,direction=LONG,offset=OPEN,vol=vol,limit_price=limit_price)
        else:
            if limit_price != 0:
                self.order_(instrument_id=instrument_id, direction=LONG, offset=OPEN, vol=vol, limit_price=limit_price)
            else:
                _open_for_shfe_thread = Thread(target=self._open_for_shfe, args=(LONG, vol, instrument_id,))
                _open_for_shfe_thread.start()
    # 平多
    def close(self, instrument_id, vol, limit_price = 0):
        symbol_obj = self.context.symbol_infos[instrument_id]
        if symbol_obj.exch_code != 'SHFE':
            self.order_(instrument_id=instrument_id, direction=LONG, offset=CLOSE, vol=vol, limit_price=limit_price)
        else:
            if limit_price != 0:
                self.order_(instrument_id=instrument_id, direction=LONG, offset=CLOSE, vol=vol, limit_price=limit_price)
            else:
                _close_for_shfe_thread = Thread(target=self._close_for_shfe, args=(LONG, vol, instrument_id,))
                _close_for_shfe_thread.start()

    # 开空
    def short(self, instrument_id, vol, limit_price = 0):
        symbol_obj = self.context.symbol_infos[instrument_id]
        if symbol_obj.exch_code != 'SHFE':
            self.order_(instrument_id=instrument_id, direction=SHORT, offset=OPEN, vol=vol, limit_price=limit_price)
        else:
            if limit_price != 0:
                self.order_(instrument_id=instrument_id, direction=SHORT, offset=OPEN, vol=vol, limit_price=limit_price)
            else:
                _open_for_shfe_thread = Thread(target=self._open_for_shfe, args=(SHORT, vol, instrument_id,))
                _open_for_shfe_thread.start()
    # 平空
    def cover(self, instrument_id, vol, limit_price = 0):
        symbol_obj = self.context.symbol_infos[instrument_id]
        if symbol_obj.exch_code != 'SHFE':
            self.order_(instrument_id=instrument_id, direction=SHORT, offset=CLOSE, vol=vol, limit_price=limit_price)
        else:
            if limit_price != 0:
                self.order_(instrument_id=instrument_id, direction=SHORT, offset=CLOSE, vol=vol, limit_price=limit_price)
            else:
                _close_for_shfe_thread = Thread(target=self._close_for_shfe, args=(SHORT, vol, instrument_id,))
                _close_for_shfe_thread.start()

    def order(self, instrument_id, direction, offset, vol, limit_price = 0):
        if direction == LONG:
            if offset == OPEN:
                self.long(instrument_id=instrument_id,vol=vol,limit_price=limit_price)
            else:
                self.close(instrument_id=instrument_id,vol=vol,limit_price=limit_price)
        else:
            if offset == OPEN:
                self.short(instrument_id=instrument_id,vol=vol,limit_price=limit_price)
            else:
                self.cover(instrument_id=instrument_id,vol=vol,limit_price=limit_price)

    # 上交所市价平
    def _close_for_shfe(self, direction, vol, instrument_id):
        symbol_obj = self.context.symbol_infos[instrument_id]
        origin_position = self.context.portfolio.positions[instrument_id]
        origin_vol = 0
        if direction == LONG:
            origin_vol = origin_position.long_today.vol + origin_position.long_yesterday.vol
        else:
            origin_vol = origin_position.short_today.vol + origin_position.short_yesterday.vol

        if origin_vol != 0:
            while True:
                position = self.context.portfolio.positions[instrument_id]
                cur_vol = 0
                if direction == LONG:
                    cur_vol = position.long_today.vol + position.long_yesterday.vol
                else:
                    cur_vol = position.short_today.vol + position.short_yesterday.vol

                # 已经平足了 break
                if origin_vol - cur_vol == vol:
                    break

                # 先撤单
                for sys_id, order in self.context.portfolio.orders.items():
                    if order.symbol == instrument_id and order.offset != OPEN and order.direction == direction:
                        if order.vol_left == vol:
                            self.cancel_order(order)

                if direction == LONG:
                    _limit_price = self.context.portfolio.last_prices[instrument_id] - 5 * symbol_obj.tick_size
                    self.close(instrument_id, vol, limit_price=_limit_price)
                else:
                    _limit_price = self.context.portfolio.last_prices[instrument_id] + 5 * symbol_obj.tick_size
                    self.cover(instrument_id, vol, limit_price=_limit_price)

                tm.sleep(3)

    # 上交所市价开
    def _open_for_shfe(self, direction, vol, instrument_id):
        symbol_obj = self.context.symbol_infos[instrument_id]
        origin_position = self.context.portfolio.positions[instrument_id]
        origin_vol = 0
        if direction == LONG:
            origin_vol = origin_position.long_today.vol + origin_position.long_yesterday.vol
        else:
            origin_vol = origin_position.short_today.vol + origin_position.short_yesterday.vol
        while True:
            position = self.context.portfolio.positions[instrument_id]
            cur_vol = 0
            if direction == LONG:
                cur_vol = position.long_today.vol + position.long_yesterday.vol
            else:
                cur_vol = position.short_today.vol + position.short_yesterday.vol
            # 已经开足了 break
            if cur_vol - origin_vol == vol:
                break

            # 先撤单
            for sys_id, order in self.context.portfolio.orders.items():
                if order.symbol == instrument_id and order.offset == OPEN and order.direction == direction:
                    if order.vol_left == vol:
                        self.cancel_order(order)

            if direction == LONG:
                _limit_price = self.context.portfolio.last_prices[instrument_id] + 5 * symbol_obj.tick_size
                self.long(instrument_id, vol, limit_price=_limit_price)
            else:
                _limit_price = self.context.portfolio.last_prices[instrument_id] - 5 * symbol_obj.tick_size
                self.short(instrument_id, vol, limit_price=_limit_price)

            tm.sleep(3)


    # 清空某个symbol的仓位 上期所 限价增量平仓 其余市价平仓
    def clear(self,instrument_id):
        # 先撤所有挂单
        for sys_id, order in self.context.portfolio.orders.items():
            if order.symbol == instrument_id:
                    self.cancel_order(order)
        # 平所有持有仓位
        if instrument_id in self.context.portfolio.positions.keys():
            symbol_obj = self.context.symbol_infos[instrument_id]
            if symbol_obj.exch_code == 'SHFE':
                _clear_for_shfe_thread = Thread(target=self._clear_for_shfe,args=(instrument_id,))
                _clear_for_shfe_thread.start()
            else:
                position = self.context.portfolio.positions[instrument_id]
                long_vol = position.long_today.vol + position.long_yesterday.vol
                short_vol = position.short_today.vol + position.short_yesterday.vol
                if long_vol > 0:
                    self.close(instrument_id, long_vol)
                if short_vol > 0:
                    self.cover(instrument_id, short_vol)

    def _clear_for_shfe(self,instrument_id):
        symbol_obj = self.context.symbol_infos[instrument_id]
        while True:
            position = self.context.portfolio.positions[instrument_id]
            long_vol = position.long_today.vol + position.long_yesterday.vol
            short_vol = position.short_today.vol + position.short_yesterday.vol

            if long_vol == 0 and short_vol == 0:
                break

            # 先撤单
            for sys_id, order in self.context.portfolio.orders.items():
                if order.symbol == instrument_id and order.offset != OPEN:
                    if order.vol_left == long_vol or order.vol_left == short_vol:
                        self.cancel_order(order)

            if long_vol > 0:
                _limit_price = self.context.portfolio.last_prices[instrument_id] - 5 * symbol_obj.tick_size
                self.close(instrument_id, long_vol, limit_price=_limit_price)
            if short_vol > 0:
                _limit_price = self.context.portfolio.last_prices[instrument_id] + 5 * symbol_obj.tick_size
                self.cover(instrument_id, short_vol, limit_price=_limit_price)

            tm.sleep(3)

    def order_(self, instrument_id, direction, offset, vol, limit_price = 0, stop_price=0, contingent_condition = ContingentConditionType.Immediately):
        if vol <= 0:
            raise ValueError('vol 入参有误')
        else:
            symbol_obj = self.context.symbol_infos[instrument_id]
            # 如果大连和郑州品种传入 CLOSE_TODAY or CLOSE_YESTERDAY 转为 CLOSE
            if symbol_obj.exch_code != 'SHFE':
                if offset != OPEN:
                    offset = CLOSE
            # 初步检查报单是否有效
            usefull_order_flag = True
            if offset == CLOSE or offset == CLOSE_TODAY or offset == CLOSE_YESTERDAY:
                vol_of_dir = self.context.portfolio.get_vol(instrument_id, direction)
                vol_in_order = self.context.portfolio.get_vol_in_order(instrument_id, direction)
                if vol_of_dir < vol or vol_in_order + vol > vol_of_dir:
                    usefull_order_flag = False
                    print('平仓手数(%s)和该方向持仓总手数(%s)或相同方向挂单剩余手数(%s)冲突，拒绝报单' % (vol,vol_of_dir,vol_in_order))
            # CLOSE => 按交易所不同 拆分平今平昨 上期所按手续费区分平今平昨
            if offset == CLOSE:
                if usefull_order_flag:
                    position = self.context.portfolio.positions[instrument_id]
                    if symbol_obj.exch_code == 'SHFE':
                        # 先平今再平昨
                        if symbol_obj.compare_close_fee():
                            if direction == LONG:
                                if position.long_today.vol >= vol:
                                    self.__order(instrument_id, LONG, CLOSE_TODAY, vol, limit_price, stop_price,
                                                 contingent_condition)
                                else:
                                    vol_left = vol - position.long_today.vol
                                    print(vol_left)
                                    if vol_left <= position.long_yesterday.vol:
                                        print(position.long_today.vol)
                                        print(position.long_yesterday.vol)
                                        self.__order(instrument_id, LONG, CLOSE_TODAY, position.long_today.vol,
                                                     limit_price, stop_price, contingent_condition)
                                        self.__order(instrument_id, LONG, CLOSE, vol_left, limit_price,
                                                     stop_price, contingent_condition)
                                    else:
                                        raise ValueError('order:平昨多 仓位不足！！！')
                            else:
                                if position.short_today.vol >= vol:
                                    self.__order(instrument_id, SHORT, CLOSE_TODAY, vol, limit_price, stop_price,
                                                 contingent_condition)
                                else:
                                    vol_left = vol - position.short_today.vol
                                    if vol_left <= position.short_yesterday.vol:
                                        self.__order(instrument_id, SHORT, CLOSE_TODAY, position.short_today.vol,
                                                     limit_price, stop_price, contingent_condition)
                                        self.__order(instrument_id, SHORT, CLOSE, vol_left, limit_price,
                                                     stop_price, contingent_condition)
                                    else:
                                        raise ValueError('order:平昨空 仓位不足！！！')
                        # 先平昨再平今
                        else:
                            if direction == LONG:
                                if position.long_yesterday.vol >= vol:
                                    self.__order(instrument_id, LONG, CLOSE, vol, limit_price, stop_price,
                                                 contingent_condition)
                                else:
                                    vol_left = vol - position.long_yesterday.vol
                                    if vol_left <= position.long_today.vol:
                                        self.__order(instrument_id, LONG, CLOSE, position.long_yesterday.vol,
                                                     limit_price, stop_price, contingent_condition)
                                        self.__order(instrument_id, LONG, CLOSE_TODAY, vol_left, limit_price,
                                                     stop_price, contingent_condition)
                                    else:
                                        raise ValueError('order:平今多 仓位不足！！！')
                            else:
                                if position.short_yesterday.vol >= vol:
                                    self.__order(instrument_id, SHORT, CLOSE, vol, limit_price, stop_price,
                                                 contingent_condition)
                                else:
                                    vol_left = vol - position.short_yesterday.vol
                                    if vol_left <= position.short_today.vol:
                                        self.__order(instrument_id, SHORT, CLOSE, position.short_yesterday.vol,
                                                     limit_price, stop_price, contingent_condition)
                                        self.__order(instrument_id, SHORT, CLOSE_TODAY, vol_left, limit_price,
                                                     stop_price, contingent_condition)
                                    else:
                                        raise ValueError('order:平今空 仓位不足！！！')
                    else:
                        self.__order(instrument_id, direction, CLOSE, vol, limit_price, stop_price,
                                     contingent_condition)
            # 上期所
            elif offset == CLOSE_TODAY:
                if usefull_order_flag:
                    self.__order(instrument_id, direction, CLOSE_TODAY, vol, limit_price, stop_price,
                                 contingent_condition)
            # 上期所
            elif offset == CLOSE_YESTERDAY:
                if usefull_order_flag:
                    self.__order(instrument_id, direction, CLOSE_YESTERDAY, vol, limit_price, stop_price,
                                 contingent_condition)

            elif offset == OPEN:
                symbol_obj = self.context.symbol_infos[instrument_id]
                margin =  vol * symbol_obj.contract_size * limit_price * symbol_obj.broker_margin * 0.01
                # 市价开单暂不考虑
                if margin <= self.context.portfolio.avail_cash:
                    self.__order(instrument_id, direction, offset, vol, limit_price, stop_price, contingent_condition)
                else:
                    print('可用资金不足，无法开仓，拒绝报单 可用 %.2f 需要%.2f' %(self.context.portfolio.avail_cash, margin))
            else:
                print('未知报单offset => %s' % offset)

    def __order(self, instrument_id, direction, offset, vol, limit_price = 0, stop_price=0, contingent_condition = ContingentConditionType.Immediately):
        '''
        下单
        :param instrument_id:           合约id: 如'rb1801'
        :param direction:               DirectionType.买:Buy  卖:Sell
        :param offset:                  OffsetFlagType.开:Open.__char__() 平:Close.__char__() 平今:CloseToday.__char__() 平昨:CloseYesterday__char__()
        :param vol:                     数量
        :param limit_price:             限价为0则为市价单 不为0则为限价单
        :param stop_price:              止损价为0则挂单条件为立即触发
        :param contingent_condition:    触发条件 默认立即 可设置stop条件
        :return: 
        '''
        if vol > 0:
            price_type = OrderPriceTypeType.LimitPrice
            if limit_price == 0:
                price_type = OrderPriceTypeType.AnyPrice

            event = Event(EVENT_ORDER)

            # 加入了策略名称 id 报单日期 时间 用户名 broker名
            order = Order(symbol=instrument_id,
                          direction=direction,
                          offset=offset,
                          vol_total_original=vol,
                          price_type=price_type,
                          limit_price=limit_price,
                          stop_price=stop_price,
                          contingent_condition=contingent_condition,
                          user_id=self.context.user_id,
                          broker_id=self.context.broker_id,
                          strategy_id=self.context.strategy_id,
                          strategy_name=self.context.strategy_name
                          )
            # print(order)
            event.dict = order
            event.sync_flag = False
            self._engine.sendEvent(event)

    # 日志插库
    def log(self, log):
        event = Event(EVENT_LOG)
        dict = {
                'message': log,
                'type': 'log',
                'user_id': self.context.user_id,
                'borker_id': self.context.broker_id,
                'strategy_id': self.context.strategy_id,
                'strategy_name': self.context.strategy_name
            }
        event.dict = dict
        self._engine.sendEvent(event)


    def run(self):
        self._login()

    def stop(self):
        # 全局变量中删除策略engine
        # print('时间: %s stop结束' % dt.now())
        # print(self.context)
        # for symbol, dict in self.context.settlement_tick_Flags.items():
        #     print(dict['info']['SettlementPrice'])
        # 全局变量中删除策略engine
        del Environment.strategy_engines[self.context.strategy_id]
        self._engine.stop()
        self._md.logout()
        self._td.logout()
        # 回收内存 似乎不起作用
        del self._engine
        del self._md
        del self._td
        gc.collect()


    # ********************
    # *******private******
    # ********************
    def _login(self):

        # 从数据库恢复context
        ctx = ts.getConext(self.context.user_id, self.context.broker_id,self.context.strategy_id,self.context.strategy_name)
        if ctx is not None:
            self.context = ctx

        self._engine = EventEngine()
        # 保存策略engine
        Environment.strategy_engines[self.context.strategy_id] = self._engine

        self._engine.start()

        self._engine.register(EVENT_BEFORE_TRADING, self._before_trading)           # 交易开始之前
        if self.context.receive_tick_flag:
            self._engine.register(EVENT_ON_TICK, self._handle_tick)                 # 处理tick事件
        if self.context.receive_bar_flag:
            self._engine.register(EVENT_ON_BAR, self._handle_bar)                   # 处理bar事件
        self._engine.register(EVENT_ON_ORDER_CHANGE, self._order_change)            # order成交、撤单回报
        self._engine.register(EVENT_FORCE_CLOSE, self._handle_force_close)          # 日内平仓截止日期前 比如14：55
        self._engine.register(EVENT_TRADING_END, self._trading_end)                 # 交易结束后
        self._engine.register(EVENT_ON_TRADE, self._on_trade)                       # 成交回报
        self._engine.register(EVENT_ON_TRADE_LOG, ts.insertRtnTrade)                # 插入处理后的成交回报

        self._engine.register(EVENT_LOG, ts.insertLog)

        self._md = MApi(self._engine, self.context)
        self._td = TApi(self._engine, self.context)
        self._td.login()
        # 确认结算之后才能进行交易...
        while 1:
            if self.context.settlementInfo_confirm_flag:
                self._md.login()
                break
            tm.sleep(0.1)

    def _handle_bar(self, event):
        self._lock.acquire()
        # 转发bar
        bar = event.dict
        if bar.symbol in self.context.universe:
            # 如果symbol对应的force_close_flag == Flase 发送数据
            if not self.force_close_flags[bar.symbol]:
                self.handle_bar(event.dict)
        self._lock.release()

    def _handle_tick(self, event):
        self._lock.acquire()
        t = event.dict
        if t['InstrumentID'] in self.context.universe:
            # 如果symbol对应的force_close_flag == Flase 发送数据
            if not self.force_close_flags[t['InstrumentID']]:
                tick = Tick(symbol=t['InstrumentID'],
                            last_price=t['LastPrice'],
                            trading_day=t['TradingDay'],
                            time=t['UpdateTime'],
                            millsec=t['UpdateMillisec'],
                            vol=t['Volume'],
                            turnover=t['Turnover'],
                            bid_price1=t['BidPrice1'],
                            bid_vol1=t['BidVolume1'],
                            ask_pric1=t['AskPrice1'],
                            ask_vol1=t['AskVolume1'],
                            open_interest=t['OpenInterest']
                            )
                self.context.portfolio.update_portfolio({'symbol': tick.symbol, 'price': tick.last_price})
                self.handle_tick(tick)

        self._lock.release()

    def _order_change(self, event):
        self._lock.acquire()
        order = event.dict
        print('时间:%s 报单变化 %s' % (dt.now(), order))
        # 过滤一下 只接受订阅合约的交易信息
        if order.symbol in self.context.universe:
            # 按order更新冻结保证金...
            self.context.portfolio.modify_portfolio_on_order_change(order)
            # 四种最终状态的order从context里删除
            if order.status == AT or order.status == CAN or order.status == PTNQ or order.status == NTNQ:
                del (self.context.orders[order.sys_id])
            else:
                self.context.orders[order.sys_id] = order
            self.order_change(order)

        self._lock.release()

    def _before_trading(self, event):
        if self.context.settlement_infos:
            # 结算更新portfolio
            self.context.portfolio.update_portfolio_dayend(self.context.settlement_infos)

        for symbol, symbol_info in self.context.settlement_infos.items():
            print('时间: %s _before_trading交易开始前settlement price: %s update_time: %s' % (dt.now(), symbol_info['pre_settlement_price'],symbol_info['update_time']))

        self.before_trading()


    def _handle_force_close(self, event):
        self._lock.acquire()
        symbol = event.dict
        self.force_close_flags[symbol] = True # 不再发送对应symbol的数据
        # 如果有强制提前平仓 必须要重写该方法 重置symbol对应的策略中的附加中间变量
        self.handle_force_close(symbol)
        self._lock.release()

    def _trading_end(self, event):
        # # 交易日结束
        for symbol, symbol_info in self.context.settlement_infos.items():
            print('时间: %s _trading_end交易结束settlement price: %s update_time: %s' % (dt.now(), symbol_info['pre_settlement_price'],symbol_info['update_time']))
        self.trading_end()


    def _on_trade(self, event):
        self._lock.acquire()
        trade = event.dict
        print('时间: %s 成交回报: %s' % (dt.now(), trade))

        # 过滤一下 只接受订阅合约的交易信息
        if trade.symbol in self.context.universe:
            # 按 trade 更新持仓
            self.context.portfolio.modify_portfolio_on_trade(trade)
            # 插入处理后的成交回报
            event = Event(EVENT_ON_TRADE_LOG)
            event.dict = trade
            self._engine.sendEvent(event)

            self.on_trade(trade)

        self._lock.release()


