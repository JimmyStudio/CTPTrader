# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         boll_strategy.py
time:         2017/10/24 下午1:42
description:

'''

__author__ = 'Jimmy'
from trade.tradeStrategy import *
from utils.ta import *
from datetime import datetime as dt
from utils import tools as tl
import logging as log

class BollOppositeMix(TradeStrategy):
    def initialize(self):
        self.context.universe = ['SR801','TA801','al1801','v1801','OI805','m1801']

        self.context.strategy_id = 'boll_00305188'
        self.context.strategy_name = '布林策略_原始指标'
        self.context.bar_frequency = '30S'
        self.context.force_close_minutes = {'SR801':5, 'al1801':5,'TA801':5,'v1801':5,'OI805':5,'m1801':5}
        self.context.init_cash = 590134.7  # 初始资金

        self.context.user_id = '00305188'
        self.context.password = 'Jinmi123'
        self.context.broker_id = '6000'
        self.context.trade_front = 'tcp://101.231.162.58:41205'
        self.context.market_front = 'tcp://101.231.162.58:41213'

        # self.context.user_id = '104749'
        # self.context.password = 'jinmi1'
        # self.context.market_front = 'tcp://218.202.237.33 :10012'
        # self.context.trade_front = 'tcp://218.202.237.33 :10002'

        # 限制开单数
        self.context.limit_vols = {'SR801': 2, 'v1801': 5, 'TA801':2,'al1801':2,'OI805':2,'m1801':3}

        self.context.bolls = {}
        self.context.slippages = {}
        self.context.directions = {}
        self.context.open_vols = {}  # 当前开仓手数
        self.context.close_counts = {}  # 平仓计数器
        self.context.open_prices = {}

        for symbol in self.context.universe:
            self.context.bolls[symbol] = Boll()
            self.context.slippages[symbol] = 0
            self.context.directions[symbol] = ''
            self.context.open_vols[symbol] = 0  # 当前开仓手数
            self.context.close_counts[symbol] = 0  # 平仓计数器
            self.context.open_prices[symbol] = 0

        tl.config_logging()

    def handle_force_close(self, symbol):
        log.info('%s提前强制平仓' % (symbol))
        self.clear(symbol)
        # 重新初始化
        self.context.bolls[symbol] = Boll()
        self.context.directions[symbol] = ''
        self.context.open_vols[symbol] = 0  # 当前开仓手数
        self.context.close_counts[symbol] = 0  # 平仓计数器
        self.context.open_prices[symbol] = 0

    def on_trade(self, trade):
        if trade.offset == OPEN:
            self.context.open_prices[trade.symbol] = trade.price
            self.context.open_vols[trade.symbol] += trade.vol
        else:

            self.context.open_vols[trade.symbol] -= trade.vol
            if self.context.open_vols[trade.symbol] == 0:
                self.context.close_counts[trade.symbol] = 0
                self.context.directions[trade.symbol] = ''
                self.context.open_prices[trade.symbol] = 0

        log.info('%s %s成交回报: 方向: %s ; 开手: %s; 计数: %s; 成交价：%s' %(trade.symbol, trade.offset, self.context.directions,self.context.open_vols,self.context.close_counts,self.context.open_prices))

    def handle_tick(self, tick):
        # print('时间:%s 收到tick数据：tick: %s ' % (dt.now(), tick))
        if self.context.open_vols[tick.symbol] > 0:
            if self.context.open_prices[tick.symbol] != 0:
                # 15 * symbol_info.tick_size个点平仓止损
                symbol_info = self.context.symbol_infos[tick.symbol]
                if self.context.directions[tick.symbol] == LONG and tick.last_price <= self.context.open_prices[tick.symbol] - 15 * symbol_info.tick_size:
                    log.info('%s多单止损：持仓价: %s tick: %s' % (tick.symbol,self.context.open_prices[tick.symbol], tick.last_price))
                    self.clear(tick.symbol)
                if self.context.directions[tick.symbol] == SHORT and tick.last_price >= self.context.open_prices[tick.symbol] + 15 * symbol_info.tick_size:
                    log.info('%s空单止损：持仓价: %s tick: %s' % (tick.symbol,self.context.open_prices[tick.symbol], tick.last_price))
                    self.clear(tick.symbol)

    def handle_bar(self, bar):
        boll = self.context.bolls[bar.symbol].compute(bar)
        # print('时间:%s %s收到bar数据：bar: %s ' % (dt.now(), bar.symbol,bar))

        # 下单前先撤销所有未成交的单
        for sys_id, order in self.context.orders.items():
            if order.symbol == bar.symbol:
                log.info('%s撤单：方向: %s ; 总手: %s ; 剩余: %s' % (bar.symbol,order.direction, order.vol_total_original, order.vol_left))
                self.cancel_order(order)

        if boll is not None:
            # 突破上轨后跌破中轨开空单
            if bar.close < boll.mb and self.context.directions[bar.symbol] == SHORT:
                # print('时间:%s %s突破上轨后跌破中轨开空单' % (dt.now(), bar.symbol))
                self._open(bar)

            # 突破下轨后涨破中轨开多单
            if bar.close > boll.mb and self.context.directions[bar.symbol] == LONG:
                # print('时间:%s %s突破下轨后涨破中轨开多单' % (dt.now(), bar.symbol))
                self._open(bar)

            # 开过空单后 收盘价超过中轨 平仓计数器 + 1 超过3次平仓
            if bar.close > boll.mb and self.context.directions[bar.symbol] == SHORT:
                # print('时间:%s %s开过空单后 收盘价超过中轨 平仓计数器 + 1 超过3次平仓' % (dt.now(),bar.symbol))
                self._close(bar)

            # 开过多单后 收盘价跌破中轨 平仓计数器 + 1 超过3次平仓
            if bar.close < boll.mb and self.context.directions[bar.symbol] == LONG:
                # print('时间:%s %s开过多单后 收盘价跌破中轨 平仓计数器 + 1 超过3次平仓' % (dt.now(), bar.symbol))
                self._close(bar)

            # 如果没有开过仓
            if self._signal_flag(bar.symbol):
                if bar.close > boll.up and self.context.directions[bar.symbol] == '':
                    log.info('%s突破上轨' % (bar.symbol))
                    self.context.directions[bar.symbol] = SHORT
                elif bar.close < boll.dn and self.context.directions[bar.symbol] == '':
                    log.info('%s突破下轨' % (bar.symbol))
                    self.context.directions[bar.symbol] = LONG

        # print('时间:%s %s计算boll参数：boll: %s ' % (dt.now(), bar.symbol,boll))
        # print('时间:%s 方向: %s ; 开手: %s; 计数: %s; 成交价：%s' %(dt.now(), self.context.directions,self.context.open_vols,self.context.close_counts,self.context.open_prices))

    def _open(self, bar):
        # 开空
        can_open_flag = self._signal_flag(bar.symbol)
        if can_open_flag:
            # open_price = bar.close - self.context.slippages[bar.symbol]
            # direction = LONG
            # if self.context.directions[bar.symbol] == LONG:
                # 开多
                # direction = SHORT
                # open_price = bar.close + self.context.slippages[bar.symbol]
            # 计算当前bar的close价下最多能开多少手
            # 开仓手数 = (总资金 * 资金利用率）/(开仓价 * 保证金比例 * 每手吨数）
            open_vol = self.context.limit_vols[bar.symbol]
            # symbol_info = self.context.symbol_infos[self.context.universe[0]]
            # open_vol = int((self.context.init_cash * self.context.cash_rate )/ (open_price * symbol_info.broker_margin * 0.01 * symbol_info.contract_size))
            log.info('%s %s开%s手' % (bar.symbol, self.context.directions[bar.symbol], open_vol))
            self.log({'desc':'open tick','tick':bar.ticks[-1]})
            self.order(bar.symbol, self.context.directions[bar.symbol], OPEN, open_vol, limit_price=bar.close)

    def _close(self, bar):
        can_close_flag = self._signal_flag2(bar.symbol)
        if can_close_flag:
            self.context.close_counts[bar.symbol] += 1
            if self.context.close_counts[bar.symbol] >= 3:
                # 平空
                # open_price = bar.close + self.context.slippages[bar.symbol]
                # direction = LONG
                # if self.context.directions[bar.symbol] == LONG:
                    # 平多
                    # direction = SHORT
                    # open_price = bar.close - self.context.slippages[bar.symbol]
                log.info('%s %s平%s手' % (bar.symbol, self.context.directions[bar.symbol], self.context.open_vols[bar.symbol]))
                self.log({'desc': 'close tick', 'tick': bar.ticks[-1]})
                self.order(bar.symbol, self.context.directions[bar.symbol], CLOSE, self.context.open_vols[bar.symbol], limit_price=bar.close)

    def _signal_flag(self, symbol):
        flag = True
        # 当前合约无持仓 则不平
        if self.context.open_vols[symbol] > 0:
            flag = False
        # 当前挂单中有该合约 则不平
        for sys_id, order in self.context.orders.items():
            if order.symbol == symbol:
                flag = False
        return flag

    def _signal_flag2(self, symbol):
        flag = True
        # 当前合约无持仓 则不平
        if self.context.open_vols[symbol] == 0:
            flag = False
        # 当前挂单中有该合约 则不平
        for sys_id, order in self.context.orders.items():
            if order.symbol == symbol:
                flag = False
        return flag
