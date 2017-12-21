# -*- coding: utf-8 -*-

'''
author:       sj
contact:      songjie1217@hotmail.com
description:
'''

__author__ = 'sj'

import math
from trade.tradeStrategy import *
from utils.ta import *

class KdjStrategy(TradeStrategy):
    def initialize(self):
        self.context.universe = ['v1805']
        self.context.strategy_id = 'kdj1m-v-108436'
        self.context.strategy_name = 'kdj1m-v'
        self.context.bar_frequency = '1M'

        self.context.user_id = '108436'
        self.context.password = 'k123456789'

        self.context.init_cash = 500000
        self.context.cash_rate = 0.8  # 资金利用率
        self.context.direction = ''
        self.context.open_vol = 0  # 当前开仓手数
        self.context.k1 = 51
        self.context.d1 = 47
        self.context.kdj = KDJ()
        self.context.bar_close = 0 # 当前bar收盘价
        self.context.stop_loss_flag = False # 开启止损flag
        self.context.bar_closes = []
        self.context.slippage = 1

    def on_trade(self, trade):
        if trade.offset == OPEN:
            self.context.open_vol += trade.vol
            self.context.direction = trade.direction
        else:
            self.context.open_vol -= trade.vol

            if self.context.open_vol == 0:
                if self.context.stop_loss_flag:
                    self.context.stop_loss_flag = False
                else:
                    symbol_info = self.context.symbol_infos[self.context.universe[0]]
                    open_price = self.context.bar_close
                    if self.context.direction == SHORT:
                        print('反向开多')
                        self.context.direction = LONG
                        open_price += self.context.slippage * symbol_info.tick_size
                    else:
                        print('反向开空')
                        self.context.direction = SHORT
                        open_price -= self.context.slippage * symbol_info.tick_size

                    # 反向开单
                    symbol_info = self.context.symbol_infos[self.context.universe[0]]
                    open_vol = int((self.context.portfolio.avail_cash * self.context.cash_rate) / (
                    self.context.bar_close * symbol_info.broker_margin * 0.01 * symbol_info.contract_size))
                    self.order(self.context.universe[0], self.context.direction, OPEN, open_vol,
                               limit_price=open_price)


    def handle_tick(self, tick):
        # 浮亏超过总权益5%止损
        if self.context.portfolio.upnl < - (self.context.portfolio.dynamic_total_value * 0.05):
            print('浮亏超过总权益0.05止损 %s' % self.context.direction)
            self.context.stop_loss_flag = True  # 开启止损flag
            symbol_info = self.context.symbol_infos[self.context.universe[0]]
            if self.context.direction == LONG:
                self.order(self.context.universe[0], self.context.direction, CLOSE, self.context.open_vol, limit_price=tick.last_price-5*symbol_info.tick_size)
            elif self.context.direction == SHORT:
                self.order(self.context.universe[0], self.context.direction, CLOSE, self.context.open_vol, limit_price=tick.last_price+5*symbol_info.tick_size)


    def handle_bar(self, bar):
        print('时间:%s %s收到bar数据：bar: %s ' % (dt.now(), bar.symbol,bar))
        self.context.bar_close = bar.close
        kdj = self.context.kdj.compute(bar,self.context.k1,self.context.d1)
        symbol_info = self.context.symbol_infos[self.context.universe[0]]
        break_limit_flag = self.stop_loss_of_break_limit(bar.close)
        # 下单前先撤销所有未成交的单
        if not self.context.stop_loss_flag:
            for sys_id, order in self.context.orders.items():
                if order.symbol == bar.symbol:
                    self.cancel_order(order)

        # 超过前7个bar的最高or最低点止损
        if self.stop_loss_of_break_limit_flag(break_limit_flag,bar.close,self.context.direction) and self.signal_flag(bar.symbol) and self.context.open_vol > 0:
            print('超过前7个bar的最高or最低点止损 %s' % self.context.direction)
            self.context.stop_loss_flag = True  # 开启止损flag
            if self.context.direction == LONG:
                self.order(self.context.universe[0], self.context.direction, CLOSE, self.context.open_vol,limit_price=bar.close - 5 * symbol_info.tick_size)
            elif self.context.direction == SHORT:
                self.order(self.context.universe[0], self.context.direction, CLOSE, self.context.open_vol,limit_price=bar.close + 5 * symbol_info.tick_size)

        if kdj is not None:
            if kdj.k1 > kdj.d1 and kdj.k2 < kdj.d2:
                if not self.context.stop_loss_flag:
                    if self.signal_flag(bar.symbol):
                        if self.context.open_vol > 0:
                            print('signal-1-1: 平空 %s 手' % self.context.open_vol)
                            open_price = bar.close + self.context.slippage * symbol_info.tick_size
                            self.order(self.context.universe[0], SHORT, CLOSE, self.context.open_vol,
                                       limit_price=open_price)
                        else:
                            if not self.stop_loss_of_break_limit_flag(break_limit_flag, bar.close, LONG):
                                open_vol = int((self.context.portfolio.avail_cash * self.context.cash_rate) / (
                                    bar.close * symbol_info.broker_margin * 0.01 * symbol_info.contract_size))
                                print('signal-1-2: 开多 %s 手 价格 %s' %(open_vol, bar.close))
                                open_price = bar.close + self.context.slippage * symbol_info.tick_size
                                self.order(self.context.universe[0], LONG, OPEN, open_vol, limit_price=open_price)

            elif kdj.k1 < kdj.d1 and kdj.k2 > kdj.d2:
                if not self.context.stop_loss_flag:
                    if self.signal_flag(bar.symbol):
                        if self.context.open_vol > 0:
                            print('signal-2-1: 平多 %s 手' % self.context.open_vol)
                            open_price = bar.close - self.context.slippage * symbol_info.tick_size
                            self.order(self.context.universe[0], LONG, CLOSE, self.context.open_vol,
                                       limit_price=open_price)
                        else:
                            if not self.stop_loss_of_break_limit_flag(break_limit_flag, bar.close, SHORT):
                                open_vol = int((self.context.portfolio.avail_cash * self.context.cash_rate) / (
                                    bar.close * symbol_info.broker_margin * 0.01 * symbol_info.contract_size))
                                print('signal-2-2: 开空 %s 手 价格 %s' %(open_vol, bar.close))
                                open_price = bar.close - self.context.slippage * symbol_info.tick_size
                                self.order(self.context.universe[0], SHORT, OPEN, open_vol, limit_price=open_price)

            self.context.k1 = kdj.k2
            self.context.d1 = kdj.d2

    def stop_loss_of_break_limit(self, close_price):
        if len(self.context.bar_closes) == 7:
            mx = max(self.context.bar_closes)
            mi = min(self.context.bar_closes)
            print('最高%s 最低%s' %(mx, mi))
            del self.context.bar_closes[0]
            self.context.bar_closes.append(close_price)
            return (mx, mi)
        elif len(self.context.bar_closes) < 7:
            self.context.bar_closes.append(close_price)
            return None

    # false 不满足止损条件 true 满足止损
    def stop_loss_of_break_limit_flag(self,flag, close_price, direction):
        if flag is None:
            return False
        if direction == LONG:
            if flag[1] > close_price:
                print('bar.close 小于前7个最低价 止损多单 或不开多单')
                return True
        elif direction == SHORT:
            if flag[0] < close_price:
                print('bar.close 大于前7个最高价 止损空单 或不开空单')
                return True
        else:
            return False

    def signal_flag(self, symbol):
        for sys_id, order in self.context.orders.items():
            if order.symbol == symbol:
                return False
        return True







