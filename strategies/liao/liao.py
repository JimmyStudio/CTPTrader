# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         liao.py
time:         2017/12/25 上午11:22
description: 

'''

__author__ = 'Jimmy'
from trade.tradeStrategy import *
from utils.ta import *
import utils.tools as tl
import logging as log
from utils import message as msg


class Liao(TradeStrategy):
    def initialize(self):
        self.context.universe = ['rb1805']
        self.context.strategy_name = 'liao_trend'
        self.context.strategy_id = 'liao_trend_v1.0'
        self.context.bar_frequency = '30M'
        self.context.init_cash = 100000
        self.context.vars = {}
        for symbol in self.context.universe:
            var = Variables(symbol)
            self.context.vars[symbol] = var


    def on_trade(self, trade):
        pass

    def handle_tick(self, tick):
        pass

    def handle_bar(self, bar):
        for sys_id, order in self.context.orders.items():
            if order.symbol == bar.symbol:
                self.cancel_order(order)
        var = self.context.vars[bar.symbol]
        symbol_obj = self.context.symbol_infos[var.symbol]
        if var.pre_bar_direction_flag == LONG:
            if var.num_from_big_bar ==0 :
                if bar.close - bar.open > var.open_thres * symbol_obj.tick_size:
                    print('%s 按barj+1.close开仓' % bar.symbol)
                    if self.pre_open(var, bar.symbol):
                        var.clear_signal()
                    else:
                        print('%s 按barj+1.close开仓 有持仓或挂单舍弃开仓信号' % bar.symbol)
                else:
                    var.exchange_peak(bar.close)
                    var.num_from_big_bar += 1
            elif var.num_from_big_bar < var.open_num_from_big_bar:
                var.exchange_peak(bar.close)
                var.num_from_big_bar += 1
            elif var.num_from_big_bar < var.max_open_num_from_big_bar:
                var.exchange_peak(bar.close)
                var.num_from_big_bar += 1
                if bar.close > var.big_bar_close and var.min_price > var.big_bar_open and var.max_price > var.big_bar_close:
                    print('%s 大阳线开多' % bar.symbol)
                    if self.pre_open(var, bar.symbol):
                        var.clear_signal()
                    else:
                        print('%s 大阳线开多仓 有持仓或挂单舍弃开仓信号' % bar.symbol)

                elif var.score < 0 and var.min_price < var.big_bar_open and var.max_price < var.big_bar_close and bar.close < var.big_bar_close:
                    print('%s 大阳线开空' % bar.symbol)
                    if self.pre_open(var, bar.symbol):
                        var.clear_signal()
                    else:
                        print('%s 大阳线开多空 有持仓或挂单舍弃开仓信号' % bar.symbol)

                if var.num_from_big_bar == 25:
                    print('%s 大阳线第25个bar重置清空信号' % bar.symbol)
                    var.clear_signal()
        elif var.pre_bar_direction_flag == SHORT:
            if var.num_from_big_bar ==0 :
                if bar.open - bar.close > var.open_thres * symbol_obj.tick_size:
                    print('%s 大阴线按barj+1.close开仓' % bar.symbol)
                    if self.pre_open(var, bar.symbol):
                        var.clear_signal()
                    else:
                        print('%s 大阴线按barj+1.close开仓 有持仓或挂单舍弃开仓信号' % bar.symbol)
                else:
                    var.exchange_peak(bar.close)
                    var.num_from_big_bar += 1
            elif var.num_from_big_bar < var.open_num_from_big_bar:
                var.exchange_peak(bar.close)
                var.num_from_big_bar += 1
            elif var.num_from_big_bar < var.max_open_num_from_big_bar:
                var.exchange_peak(bar.close)
                var.num_from_big_bar += 1
                if bar.close < var.big_bar_close and var.min_price < var.big_bar_close and var.max_price < var.big_bar_open:
                    print('%s 大阴线开空' % bar.symbol)
                    if self.pre_open(var, bar.symbol):
                        var.clear_signal()
                    else:
                        print('%s 大阴线开空 有持仓或挂单舍弃开仓信号' % bar.symbol)
                elif var.score > 0 and var.min_price > var.big_bar_close and var.max_price > var.big_bar_open and bar.close > var.big_bar_open:
                    print('%s 大阴线开多' % bar.symbol)
                    if self.pre_open(var, bar.symbol):
                        var.clear_signal()
                    else:
                        print('%s 大阴线开多 有持仓或挂单舍弃开仓信号' % bar.symbol)

                if var.num_from_big_bar == 25:
                    print('%s 大阴线第25个bar重置清空信号' % bar.symbol)
                    var.clear_signal()
        print('%s check 是否要转变信号' % bar.symbol)
        self.pre_bar_direction_flag(var,bar,symbol_obj)


    # 开仓方向判断
    def pre_bar_direction_flag(self, var, bar, symbol_obj):
        # check 是否要转变信号
        if bar.close - bar.open > var.open_thres * symbol_obj.tick_size:
            var.clear_signal()
            var.pre_bar_direction_flag = LONG
            var.big_bar_close = bar.close
            var.big_bar_open = bar.open
        elif bar.open - bar.close > var.open_thres * symbol_obj.tick_size:
            var.clear_signal()
            var.pre_bar_direction_flag = SHORT
            var.big_bar_close = bar.close
            var.big_bar_open = bar.open


    def pre_close(self, var, symbol):
        flag = True
        # 无持仓 忽略
        if var.open_vol == 0:
            flag = False
        # 已有挂单 忽略
        for sys_id, order in self.context.orders.items():
            if order.symbol == symbol and order.offset != OPEN:
                flag = False
        return flag

    def pre_open(self, var, symbol):
        flag = True
        # 已有持仓 忽略
        if var.open_vol > 0:
            flag = False
        # 已有挂单 忽略
        for sys_id, order in self.context.orders.items():
            if order.symbol == symbol and order.offset == OPEN:
                flag = False
        return flag


class Variables(object):
    def __init__(self, symbol, limit_vol=1):
        self.symbol = symbol
        self.limit_vol = limit_vol
        self.num_from_big_bar=0
        self.big_bar_close = 0
        self.big_bar_open = 0
        self.score = 0
        self.max_price=-999999999
        self.min_price=999999999
        self.pre_bar_direction_flag = ''

        self.open_price = 0
        self.direction = ''
        self.open_vol = 0

        self.gain_over_flag = False
        self.max_gain = 0
        self.close_count = 0
        self.signal_count=0

        self.slippage = 2 # 开仓价上下浮动1个变动单位

        self.open_thres = 10  # 开仓tick倍数
        self.open_num_from_big_bar = 4 # 从大阳线后第5个开始判断是否开仓
        self.max_open_num_from_big_bar = 24 # 最多判断连续25个

    def exchange_peak(self, price):
        if price > self.max_price:
            self.max_price = price
        if price < self.min_price:
            self.min_price = price

    def clear_signal(self):
        self.min_price = 999999999
        self.max_price = -999999999
        self.num_from_big_bar = 0
        self.big_bar_close = 0
        self.big_bar_open = 0
        self.pre_bar_direction_flag = ''


