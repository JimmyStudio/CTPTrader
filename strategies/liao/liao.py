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
        self.context.universe = ['rb1805', 'i1805', 'SR805', 'FG805', 'y1805']
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
        pass


    def long_signal(self, var, bar):
        pass




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
        self.boll = Boll(cycle=35)
        self.ma = MA()

        self.bar_n_2 = None
        self.bar_n_1 = None

        self.boll_n_2 = None
        self.boll_n_1 = None
        self.boll_t = None # 最新的boll


        self.open_price = 0
        self.direction = ''
        self.open_vol = 0
        self.pre_bar_direction_flag = ''

        self.gain_over_flag = False
        self.max_gain = 0
        self.close_count = 0
        self.signal_count=0

        self.slippage = 2 # 开仓价上下浮动1个变动单位

        self.spread_thres = 0.006  # 上下轨价差阈值
        self.open_thres = 0.01  # 开仓close-open阈值
        self.tick_open_thres = 0.005  # 第2bar 按tick开仓阈值
        self.ma_thres = -0.006  # 与ma差值阈值
        self.stop_loss_thres = 0.01  # 止损阈值
        self.gain_thres = 0.01  # 止盈开始阈值
        self.stop_gain_thres = 0.618  # 止盈回吐阈值



    def initialize(self):
        self.open_price = 0
        self.direction = ''
        self.open_vol = 0

        self.pre_bar_direction_flag = ''
        self.signal_count=0
        self.bar_n_2 = None
        self.bar_n_1 = None
        self.boll_n_2 = None
        self.boll_n_1 = None

        self.gain_over_flag = False
        self.max_gain = 0
        self.close_count = 0

