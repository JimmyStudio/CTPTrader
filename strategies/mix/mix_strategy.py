# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         mix_strategy.py
time:         2017/11/9 下午2:55
description: 

'''

__author__ = 'Jimmy'
from trade.tradeStrategy import *
from utils.ta import *
from datetime import datetime as dt


class Mix(TradeStrategy):
    def initialize(self):
        self.context.universe = ['v1801']
        self.context.strategy_id = 'boll_008105'
        self.context.strategy_name = '布林策略'
        self.context.bar_frequency = '30S'
        self.context.receive_tick_flag = True

        # self.context.user_id = '00305188'
        # self.context.password = 'Jinmi123'
        # self.context.broker_id = '6000'
        # self.context.trade_front = 'tcp://101.231.162.58:41205'
        # self.context.market_front = 'tcp://101.231.162.58:41213'

        # self.context.user_id = '104749'
        # self.context.password = 'jinmi1'

        self.context.boll = Boll()
        self.context.init_cash = 1000000  # 初始资金
        self.context.cash_rate = 0.3 # 资金利用率
        self.context.slippage = 0 # 开仓价 变化幅度 2 个变动单位

        self.context.direction = ''
        self.context.open_vol = 0 # 当前开仓手数
        self.context.open_flag = False # false表示没有开仓 true表示已经开仓了
        self.context.can_open_flag = True # ture 表示能继续开仓 flase 表示已经开足仓了
        self.context.close_count = 0 # 平仓计数器
        self.context.open_price = 0
        self.context.std = 0 # boll标准差
        self.context.open_count = 0


    def before_trading(self):
        pass

    def order_change(self,order):
        pass

    def on_trade(self, trade):
        if trade.offset == OPEN:
            self.context.open_price = trade.price
            self.context.open_vol += trade.vol

            if self.context.open_vol > 0:
                self.context.open_flag = True

                self.context.open_count = 0

        else:

            self.context.open_vol -= trade.vol

            if self.context.open_vol == 0:

                self.context.open_flag = False
                self.context.can_open_flag = True

                self.context.close_count = 0
                self.context.direction = ''
                self.context.open_price = 0


    def handle_tick(self, tick):
        # print('时间:%s 收到tick数据：tick: %s ' % (dt.now(), tick))
        if self.context.open_vol > 0:
            if self.context.open_price != 0:
                # 15 * symbol_info.tick_size个点平仓止损
                # symbol_info = self.context.symbol_infos[self.context.universe[0]]
                if self.context.direction == LONG and tick.last_price >= self.context.open_price + 3 * self.context.std:
                    print('时间:%s 空单止损 trade.price: %s tick: %s' % (dt.now(), self.context.open_price, tick.last_price))
                    self.order(self.context.universe[0],SHORT, CLOSE, self.context.open_vol,limit_price=tick.last_price)
                if self.context.direction == SHORT and tick.last_price <= self.context.open_price - 3 * self.context.std:
                    print('时间:%s 多单止损 trade.price: %s tick: %s' % (dt.now(), self.context.open_price, tick.last_price))
                    self.order(self.context.universe[0],LONG, CLOSE, self.context.open_vol,limit_price=tick.last_price)


    def handle_bar(self, bar):
        boll = self.context.boll.compute(bar)
        print('时间:%s 收到bar数据：bar: %s ' % (dt.now(), bar))

        # 下单前先撤销所有未成交的单
        for symbol, order in self.context.orders.items():
            print('时间:%s 撤单 direction: %s ; vol: %s ; vol_left: %s' % (dt.now(), order.direction, order.vol_total_original, order.vol_left))
            self.cancel_order(order)
            # order 是开仓 并且 未成交的时候 修改can_open_flag 以便继续发出开仓信号
            if order.offset == OPEN and self.context.open_vol == 0:
                self.context.can_open_flag = True

        if boll is not None:
            self.context.std = boll.std

            # 突破上轨后跌破中轨开空单
            if bar.close < boll.mb and self.context.direction == SHORT and self.context.can_open_flag:
                print('时间:%s 突破上轨后跌破中轨开空单' % dt.now())
                self._open(bar)

            # 突破下轨后涨破中轨开多单
            if bar.close > boll.mb and self.context.direction == LONG and self.context.can_open_flag:
                print('时间:%s 突破下轨后涨破中轨开多单' % dt.now())
                self._open(bar)

            # 开过空单后 收盘价超过中轨 平仓计数器 + 1 超过3次平仓
            if bar.close > boll.mb and self.context.direction == SHORT and self.context.open_flag:
                print('时间:%s 开过空单后 收盘价超过中轨 平仓计数器 + 1 超过3次平仓' % dt.now())
                self._close(bar)

            # 开过多单后 收盘价跌破中轨 平仓计数器 + 1 超过3次平仓
            if bar.close < boll.mb and self.context.direction == LONG and self.context.open_flag:
                print('时间:%s 开过多单后 收盘价跌破中轨 平仓计数器 + 1 超过3次平仓' % dt.now())
                self._close(bar)

            # 如果没有开过仓
            if not self.context.open_flag:
                if bar.close > boll.up and self.context.direction == '':
                    print('时间:%s 突破上轨' % dt.now())
                    self.context.direction = SHORT
                elif bar.close < boll.dn and self.context.direction == '':
                    print('时间:%s 突破下轨' % dt.now())
                    self.context.direction = LONG

        print('时间:%s 计算bol参数：boll: %s ; direction: %s ; 是否能开仓: %s ; 是否开过仓: %s; 开仓手数: %s; 平仓计数器: %s; 成交价：%s; 开仓计数器：%s' % (dt.now(), boll, self.context.direction, self.context.can_open_flag,self.context.open_flag,self.context.open_vol,self.context.close_count,self.context.open_price,self.context.open_count))

    def _open(self, bar):
        self.context.open_count += 1
        if self.context.open_count >= 3:
            # 开空
            self.context.can_open_flag = False

            open_price = bar.close + self.context.slippage
            direction = LONG
            if self.context.direction == LONG:
                # 开多
                direction = SHORT
                open_price = bar.close - self.context.slippage
            # 计算当前bar的close价下最多能开多少手
            # 开仓手数 = (总资金 * 资金利用率）/(开仓价 * 保证金比例 * 每手吨数）
            # open_vol = 10
            symbol_info = self.context.symbol_infos[self.context.universe[0]]
            open_vol = int((self.context.init_cash * self.context.cash_rate) / (
            open_price * symbol_info.broker_margin * 0.01 * symbol_info.contract_size))
            print('时间:%s %s 开:%s 手' % (dt.now(), self.context.direction, open_vol))
            print('挂单tick: %s' % bar.ticks[-1])
            self.order(self.context.universe[0], direction, OPEN, open_vol, limit_price=open_price)

    def _close(self, bar):
        self.context.close_count += 1

        if self.context.close_count >= 3:
            # 平空
            open_price = bar.close - self.context.slippage
            direction = LONG
            if self.context.direction == LONG:
                # 平多
                direction = SHORT
                open_price = bar.close + self.context.slippage

            print('时间:%s %s 平:%s 手' % (dt.now(), self.context.direction, self.context.open_vol))
            print('挂单tick: %s' % bar.ticks[-1])
            self.order(self.context.universe[0], direction, CLOSE, self.context.open_vol,limit_price=open_price)
