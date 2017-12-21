# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         turtle_strategy.py
time:         2017/9/13 上午11:04
description: 

'''

__author__ = 'Jimmy'
from trade.tradeStrategy import *
from utils.ta import *
from datetime import datetime

class Turtle(TradeStrategy):


    def initialize(self):
        self.context.universe = ['j1801']
        self.context.strategy_id = 'Jimmy_000001'
        self.context.strategy_name = '海龟策略'
        self.context.bar_frequency = '1M'


        self.context.user_id = '100867'
        self.context.password = '1'
        self.context.broker_id = '9999'


        self.context.atr = ATR(400000, cycle=10,dpp=50,coe=0.15)
        self.context.bl = BreakLimit(cycle=10)
        self.context.sl = StopLimit(cycle=5)

        self.context.open_direction = ''
        self.context.unit_count = 0
        self.context.unit = 0
        self.context.last_price = 0
        self.context.slippage = 2

        self.context.stop_flag = False # 是否正在止盈止损


    def order_change(self,order):

        print('时间:%s 报单变化 %s' % (datetime.now(),order))
        if order.status == AT:
            if order.offset == OPEN:# 开
                self.context.unit_count = self.context.unit_count + int(order.vol_traded/self.context.unit)
            elif order.offset == CLOSE_TODAY: # 平今
                self.context.unit_count = self.context.unit_count - int(order.vol_traded/self.context.unit)
                self.context.stop_flag = False
                if self.context.unit_count < 0:
                    self.context.unit_count = 0
        elif order.status == CAN:
            print('时间:%s 撤单' % datetime.now())
        print('时间:%s 当前unit: %d %d ' % (datetime.now(), self.context.unit, self.context.unit_count))


    def handle_bar(self, bar):

        open_signal = self.context.bl.compute(bar)
        atr = self.context.atr.compute(bar)
        sl = self.context.sl.compute(bar)

        print('时间:%s 收到bar数据：bar: %s ; atr: %s ; signal:%s-%s ' % (datetime.now(), bar, atr, self.context.open_direction, self.context.last_price))

        # 下单前先撤销所有未成交的单
        for k, v in self.context.orders.items():
            self.cancel_order(v)


        # 止盈止损
        if self.context.unit > 0 and self.context.unit_count > 0:
            high_bound = self.context.last_price + 2 * atr.n
            low_bound = self.context.last_price - 2 * atr.n
            if self.context.open_direction == LONG:
                if bar.close < low_bound or sl == 'BUY_STOP':
                    print('时间:%s 多单止损止盈' % datetime.now())
                    self.context.stop_flag = True
                    self._order(LONG, CLOSE_TODAY, self.context.unit * self.context.unit_count, bar.close, -self.context.slippage)
            if self.context.open_direction == SHORT:
                if bar.close > high_bound or sl == 'SELL_STOP':
                    print('时间:%s 空单止损止盈' % datetime.now())
                    self.context.stop_flag = True
                    self._order(SHORT, CLOSE_TODAY, self.context.unit * self.context.unit_count, bar.close, +self.context.slippage)


        # 开仓
        # 有开仓信号 且 当前无持仓 且unit 至少为1手
        if open_signal is not None and self.context.unit_count == 0 and atr.unit > 0:
            # 开仓 一个unit手 市价单
            self.context.open_direction = open_signal.direction
            self.context.unit = atr.unit

            if self.context.open_direction == LONG:
                self._order(self.context.open_direction, OPEN, self.context.unit, open_signal.price, self.context.slippage)
            else:
                self._order(self.context.open_direction, OPEN, self.context.unit, open_signal.price, -self.context.slippage)

        # 加仓减仓
        # 0 < 当前持仓计数器 < 4 ，开仓unit至少为1手
        if self.context.unit_count < 4 and self.context.unit_count > 0 and self.context.unit > 0 and self.context.stop_flag == False:
            high_bound = self.context.last_price + 0.5 * atr.n
            low_bound = self.context.last_price - 0.5 * atr.n
            # 如果第一个unit开仓是多单
            if self.context.open_direction == LONG:
                if bar.close > high_bound:
                    print('时间:%s 多开一个unit' % datetime.now())
                    # 当前bar.close > 开仓价+1/2 * N，则多开一个unit
                    self._order(LONG, OPEN, self.context.unit, high_bound, self.context.slippage)
                elif bar.close < low_bound :
                    print('时间:%s 多平一个unit' % datetime.now())
                    # 当前bar.close < 开仓价-1/2 * N，则多平一个unit
                    self._order(LONG, CLOSE_TODAY, self.context.unit, low_bound,-self.context.slippage)
            else:
                # 当前bar.close > 开仓价+1/2 * N，则卖平一个unit
                if bar.close > high_bound:
                    print('时间:%s 卖平一个unit' % datetime.now())
                    self._order(SHORT, CLOSE_TODAY, self.context.unit, high_bound,self.context.slippage)
                # 当前bar.close < 开仓价-1/2 * N，则卖开一个unit
                elif bar.close < low_bound:
                    print('时间:%s 卖开一个unit' % datetime.now())
                    self._order(SHORT, OPEN, self.context.unit, low_bound, -self.context.slippage)



    def _order(self, direction, offset, unit, last_price, slippage):
        self.order(self.context.universe[0], direction, offset, unit,limit_price= int(last_price + slippage))
        self.context.last_price = last_price


class TurtleOpposite(TradeStrategy):


    def initialize(self):
        self.context.universe = ['j1801']
        self.context.strategy_id = 'Jimmy_000001'
        self.context.strategy_name = '海龟策略'
        self.context.bar_frequency = '30S'


        self.context.user_id = '100867'
        self.context.password = '1'
        self.context.broker_id = '9999'


        self.context.atr = ATR(400000, cycle=10,dpp=50,coe=0.15)
        self.context.bl = BreakLimit(cycle=10)
        self.context.sl = StopLimit(cycle=5)

        self.context.open_direction = ''
        self.context.unit_count = 0
        self.context.unit = 0
        self.context.last_price = 0
        self.context.slippage = 2

        self.context.stop_flag = False # 是否正在止盈止损


    def order_change(self,order):

        print('时间:%s 报单变化 %s' % (datetime.now(),order))
        if order.status == AT:
            if order.offset == OPEN:# 开
                self.context.unit_count = self.context.unit_count + int(order.vol_traded/self.context.unit)
            elif order.offset == CLOSE_TODAY: # 平今
                self.context.unit_count = self.context.unit_count - int(order.vol_traded/self.context.unit)
                self.context.stop_flag = False
                if self.context.unit_count < 0:
                    self.context.unit_count = 0
        elif order.status == CAN:
            print('时间:%s 撤单' % datetime.now())
        print('时间:%s 当前unit: %d %d ' % (datetime.now(), self.context.unit, self.context.unit_count))


    def handle_bar(self, data):

        open_signal = self.context.bl.compute(data)
        atr = self.context.atr.compute(data)
        sl = self.context.sl.compute(data)

        print('时间:%s 收到bar数据：bar: %s ; atr: %s ; signal:%s-%s ' % (datetime.now(), data, atr, self.context.open_direction, self.context.last_price))

        # 下单前先撤销所有未成交的单
        for k, v in self.context.orders.items():
            self.cancel_order(v)


        # 止盈止损
        if self.context.unit > 0 and self.context.unit_count > 0:
            high_bound = self.context.last_price + 2 * atr.n
            low_bound = self.context.last_price - 2 * atr.n
            if self.context.open_direction == LONG:
                if data.close < low_bound or sl == 'BUY_STOP':
                    print('时间:%s 多单止损止盈' % datetime.now())
                    self.context.stop_flag = True
                    self._order(SHORT, CLOSE_TODAY, self.context.unit * self.context.unit_count, data.close, -self.context.slippage)
            if self.context.open_direction == SHORT:
                if data.close > high_bound or sl == 'SELL_STOP':
                    print('时间:%s 空单止损止盈' % datetime.now())
                    self.context.stop_flag = True
                    self._order(LONG, CLOSE_TODAY, self.context.unit * self.context.unit_count, data.close, +self.context.slippage)


        # 开仓
        # 有开仓信号 且 当前无持仓 且unit 至少为1手
        if open_signal is not None and self.context.unit_count == 0 and atr.unit > 0:
            # 开仓 一个unit手 市价单
            self.context.open_direction = open_signal.direction
            self.context.unit = atr.unit

            if self.context.open_direction == LONG:
                self._order(SHORT, OPEN, self.context.unit, open_signal.price, self.context.slippage)
            else:
                self._order(LONG, OPEN, self.context.unit, open_signal.price, -self.context.slippage)

        # 加仓减仓
        # 0 < 当前持仓计数器 < 4 ，开仓unit至少为1手
        if self.context.unit_count < 4 and self.context.unit_count > 0 and self.context.unit > 0 and self.context.stop_flag == False:
            high_bound = self.context.last_price + 0.5 * atr.n
            low_bound = self.context.last_price - 0.5 * atr.n
            # 如果第一个unit开仓是多单
            if self.context.open_direction == LONG:
                if data.close > high_bound:
                    print('时间:%s 多开一个unit' % datetime.now())
                    # 当前bar.close > 开仓价+1/2 * N，则多开一个unit
                    self._order(SHORT, OPEN, self.context.unit, high_bound, self.context.slippage)
                elif data.close < low_bound :
                    print('时间:%s 多平一个unit' % datetime.now())
                    # 当前bar.close < 开仓价-1/2 * N，则多平一个unit
                    self._order(SHORT, CLOSE_TODAY, self.context.unit, low_bound,-self.context.slippage)
            else:
                # 当前bar.close > 开仓价+1/2 * N，则卖平一个unit
                if data.close > high_bound:
                    print('时间:%s 卖平一个unit' % datetime.now())
                    self._order(LONG, CLOSE_TODAY, self.context.unit, high_bound,self.context.slippage)
                # 当前bar.close < 开仓价-1/2 * N，则卖开一个unit
                elif data.close < low_bound:
                    print('时间:%s 卖开一个unit' % datetime.now())
                    self._order(LONG, OPEN, self.context.unit, low_bound, -self.context.slippage)



    def _order(self, direction, offset, unit, last_price, slippage):
        self.order(self.context.universe[0], direction, offset, unit,limit_price= int(last_price + slippage))
        self.context.last_price = last_price


if __name__ == '__main__':
    t = Turtle()
    t.run()