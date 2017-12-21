# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         boll_2.py
time:         2017/12/4 上午10:41
description: 

'''

__author__ = 'Jimmy'
from trade.tradeStrategy import *
from utils.ta import *
from datetime import datetime as dt

class BollStrategy_2(TradeStrategy):
    def initialize(self):
        self.context.universe = ['SR805']
        self.context.strategy_name = 'boll_2S_v4.0'
        self.context.strategy_id = 'boll_2S'
        self.context.bar_frequency = '2S'
        self.context.init_cash = 100000

        self.context.user_id = '104749'
        self.context.password = 'jinmi1'

        self.context.boll = Boll(cycle=35)
        self.context.ma = MA()

        self.context.bar_n_2 = None
        self.context.bar_n_1 = None

        self.context.boll_n_2 = None
        self.context.boll_n_1 = None

        self.context.boll_t = None # 最新的boll

        self.context.open_price = 0
        self.context.direction = ''
        self.context.limit_vol = 1
        self.context.open_vol = 0
        self.context.pre_bar_direction_flag = ''

        self.context.gain_over_flag =False
        self.context.max_gain =0
        self.context.close_count=0
        self.context.signal_count=0


        self.context.spread_thres = 0.006  # 上下轨价差阈值
        self.context.open_thres = 0.01  # 开仓close-open阈值
        self.context.tick_open_thres = 0.005  # 第2bar 按tick开仓阈值
        self.context.ma_thres = -0.006  # 与ma差值阈值
        self.context.stop_loss_thres = 0.01  # 止损阈值
        self.context.gain_thres = 0.01  # 止盈开始阈值
        self.context.stop_gain_thres = 0.618  # 止盈回吐阈值



    def on_trade(self, trade):
        if trade.offset == OPEN:
            self.context.direction = trade.direction
            self.context.open_vol += trade.vol
            self.context.open_price = trade.price
        else:
            self.context.open_vol -= trade.vol
            if self.context.open_vol == 0:
                self.context.open_price = 0
                self.context.direction = ''
                self.context.pre_bar_direction_flag = ''
                self.context.gain_over_flag = False
                self.context.max_gain = 0
                self.context.close_count = 0

    def handle_tick(self, tick):
        if self.pre_close(tick.symbol):
            # 止损
            self.stop_loss(tick, self.context.boll_t)
            # 止盈
            self.stop_gain(tick)

        if self.pre_open(tick.symbol):
            self.long_open_by_tick(tick)
            self.short_open_by_tick(tick)


    def handle_bar(self, bar):

        for sys_id, order in self.context.orders.items():
            if order.symbol == bar.symbol:
                self.cancel_order(order)


        boll = self.context.boll.compute(bar)
        ma = self.context.ma.compute(bar)
        self.context.boll_t = boll

        print('=========================')
        print('****bar %s' % bar)
        print('****boll %s' % boll)
        print('****ma %s' % ma)
        print('bar n2 %s' % self.context.bar_n_2)
        print('bar n1 %s' % self.context.bar_n_1)
        print('boll n2 %s' % self.context.boll_n_2)
        print('boll n1 %s' % self.context.boll_n_1)
        print('signal_count %s '% self.context.signal_count)

        if ma is not None and boll is not None:
            self.pre_bar_direction_flag(bar, boll)

            print('pre_bar_direction_flag %s ' % self.context.pre_bar_direction_flag)

            self.long_close_signal(bar, boll)

            self.short_close_signal(bar, boll)

            self.long_open_signal(bar, ma, boll)

            self.short_open_signal(bar, ma, boll)


    def stop_gain(self, tick):
        if self.context.direction != '':
            delta = self.context.open_price - tick.last_price
            if self.context.direction == LONG:
                delta = tick.last_price - self.context.open_price

            if self.context.gain_over_flag and (self.context.max_gain - delta) / self.context.max_gain > self.context.stop_gain_thres:
                symbol_obj = self.context.symbol_infos[tick.symbol]
                if self.context.direction == LONG:
                    print('多单止盈')
                    self.order(tick.symbol,LONG,CLOSE,self.context.open_vol,limit_price=tick.last_price - symbol_obj.tick_size)
                else:
                    print('空单止盈')
                    self.order(tick.symbol,SHORT,CLOSE,self.context.open_vol,limit_price=tick.last_price + symbol_obj.tick_size)

            if delta / self.context.open_price > self.context.gain_thres:
                self.context.gain_over_flag = True
                if delta > self.context.max_gain:
                    self.context.max_gain = delta

    def stop_loss(self, tick, boll):
        if self.context.direction != '':
            symbol_obj = self.context.symbol_infos[tick.symbol]
            if self.context.direction == LONG:
                if self.context.open_price - tick.last_price > self.context.stop_loss_thres * boll.mid or tick.last_price < boll.bot:
                    print('多单止损')
                    self.order(tick.symbol, LONG, CLOSE, self.context.open_vol,
                               limit_price=tick.last_price - symbol_obj.tick_size)
            elif self.context.direction == SHORT:
                if tick.last_price - self.context.open_price > self.context.stop_loss_thres * boll.mid or tick.last_price > boll.top:
                    print('空单止损')
                    self.order(tick.symbol, SHORT, CLOSE, self.context.open_vol,
                               limit_price=tick.last_price + symbol_obj.tick_size)

    def pre_bar_direction_flag(self, bar, boll):
        if (boll.top - boll.bot)/boll.mid > self.context.spread_thres and self.context.signal_count == 0:
            if bar.close < boll.bot:
                self.context.pre_bar_direction_flag = LONG
            elif bar.close > boll.top:
                self.context.pre_bar_direction_flag = SHORT

    def short_close_signal(self, bar, boll):
        if self.context.direction == SHORT:
            symbol_obj = self.context.symbol_infos[bar.symbol]
            if self.context.close_count >= 3:
                if not self.pre_close(bar.symbol):
                    print('平空2')
                    self.order(bar.symbol,SHORT,CLOSE,self.context.open_vol,limit_price=bar.close + symbol_obj.tick_size)

            else:
                if bar.close > boll.mid and bar.close > bar.open and (boll.top - boll.bot) / boll.mid > self.context.spread_thres:
                    self.context.close_count += 1
                    if self.context.close_count >= 3:
                        if not self.pre_close(bar.symbol):
                            print('平空1')
                            self.order(bar.symbol, SHORT, CLOSE, self.context.open_vol,limit_price=bar.close + symbol_obj.tick_size)

    def long_close_signal(self, bar, boll):
        if self.context.direction == LONG:
            symbol_obj = self.context.symbol_infos[bar.symbol]
            if self.context.close_count >= 3:
                if not self.pre_close(bar.symbol):
                    print('平多2')
                    self.order(bar.symbol,LONG,CLOSE,self.context.open_vol,limit_price=bar.close - symbol_obj.tick_size)

            else:
                if bar.close < boll.mid and bar.close < bar.open and (boll.top - boll.bot) / boll.mid > self.context.spread_thres:
                    self.context.close_count += 1
                    if self.context.close_count >= 3:
                        if not self.pre_close(bar.symbol):
                            print('平多1')
                            self.order(bar.symbol, LONG, CLOSE, self.context.open_vol,limit_price=bar.close - symbol_obj.tick_size)

    def short_open_signal(self, bar, ma, boll):
        if self.context.direction == '' and self.context.pre_bar_direction_flag == SHORT:
            if self.context.signal_count == 0:
                if (boll.top - boll.bot) / boll.mid > self.context.spread_thres:
                    cond_1_1 = boll.top > bar.open > boll.mid > bar.close > boll.bot
                    cond_1_2 = boll.mid - bar.close <= self.context.open_thres * boll.mid
                    if cond_1_1 and cond_1_2:
                        self.context.signal_count += 1
                        self.context.bar_n_2 = bar
                        self.context.boll_n_2 = boll

            elif self.context.signal_count == 1:
                if (boll.top - boll.bot) / boll.mid > self.context.spread_thres:
                    cond_1_3 = bar.close < boll.mid
                    cond_1_4 = bar.open - bar.close <= self.context.open_thres * boll.mid
                    if cond_1_3 and cond_1_4:
                        self.context.signal_count += 1
                        self.context.bar_n_1 = bar
                        self.context.boll_n_1 = boll
                else:
                    self.context.pre_bar_direction_flag = ''
                    self.context.signal_count = 0
                    self.context.bar_n_2 = None
                    self.context.boll_n_2 = None

            elif self.context.signal_count == 2:
                if (boll.top - boll.bot) / boll.mid > self.context.spread_thres:
                    cond_1_5 = bar.close < boll.mid
                    cond_1_6 = bar.open - bar.close <= self.context.open_thres * boll.mid
                    if cond_1_5 and cond_1_6:
                        # 3
                        b2, b1 = self.context.bar_n_2, self.context.bar_n_1
                        mn = (b2.close + b1.close + bar.close) / 3.00
                        cond_3 = ma - mn > -self.context.ma_thres * boll.mid

                        if cond_3:
                            if self.pre_open(bar.symbol):
                                print('开空')
                                symbol_obj = self.context.symbol_infos[bar.symbol]
                                self.order(bar.symbol, SHORT, OPEN, self.context.limit_vol,limit_price=bar.close - symbol_obj.tick_size)
                # 放弃所有信号
                self.context.pre_bar_direction_flag = ''
                self.context.signal_count = 0
                self.context.bar_n_2 = None
                self.context.bar_n_1 = None
                self.context.boll_n_2 = None
                self.context.boll_n_1 = None

    def long_open_signal(self, bar, ma, boll):
        if self.context.direction == '' and self.context.pre_bar_direction_flag == LONG:
            if self.context.signal_count == 0:
                if (boll.top - boll.bot) / boll.mid > self.context.spread_thres:
                    cond_1_1 = boll.top > bar.close > boll.mid > bar.open > boll.bot
                    cond_1_2 = bar.close - boll.mid <= self.context.open_thres * boll.mid
                    if cond_1_1 and cond_1_2:
                        self.context.signal_count += 1
                        self.context.bar_n_2 = bar
                        self.context.boll_n_2 = boll
            elif self.context.signal_count == 1:
                if (boll.top - boll.bot) / boll.mid > self.context.spread_thres:
                    cond_1_3 = bar.close > boll.mid
                    cond_1_4 = bar.close - bar.open <= self.context.open_thres * boll.mid
                    if cond_1_3 and cond_1_4:
                        self.context.signal_count += 1
                        self.context.bar_n_1 = bar
                        self.context.boll_n_1 = boll
                else:
                    self.context.pre_bar_direction_flag = ''
                    self.context.signal_count = 0
                    self.context.bar_n_2 = None
                    self.context.boll_n_2 = None

            elif self.context.signal_count == 2:
                if (boll.top - boll.bot) / boll.mid > self.context.spread_thres:
                    cond_1_5 = bar.close > boll.mid
                    cond_1_6 = bar.close - bar.open <= self.context.open_thres * boll.mid
                    if cond_1_5 and cond_1_6:
                         # 3
                        b2, b1 = self.context.bar_n_2, self.context.bar_n_1
                        mn = (b2.close + b1.close + bar.close) / 3.00
                        cond_3 = mn - ma > -self.context.ma_thres * boll.mid

                        if cond_3:
                            if self.pre_open(bar.symbol):
                                print('开多')
                                symbol_obj = self.context.symbol_infos[bar.symbol]
                                self.order(bar.symbol, LONG, OPEN, self.context.limit_vol,limit_price=bar.close + symbol_obj.tick_size)

                self.context.pre_bar_direction_flag = ''
                self.context.signal_count = 0
                self.context.bar_n_2 = None
                self.context.bar_n_1 = None
                self.context.boll_n_2 = None
                self.context.boll_n_1 = None

    def long_open_by_tick(self, tick):
        if self.context.signal_count == 1 and self.context.pre_bar_direction_flag == LONG:
            if tick.last_price - self.context.bar_n_2.close >= 0.05 * self.context.boll_n_2.mid:
                print('按tick 开多')
                symbol_obj = self.context.symbol_infos[tick.symbol]
                self.order(tick.symbol, LONG, OPEN, self.context.limit_vol, limit_price=tick.last_price + symbol_obj.tick_size)

    def short_open_by_tick(self, tick):
        if self.context.signal_count == 1 and self.context.pre_bar_direction_flag == SHORT:
            if self.context.bar_n_2.close - tick.last_price >= 0.05 * self.context.boll_n_2.mid:
                print('按tick 开空')
                symbol_obj = self.context.symbol_infos[tick.symbol]
                self.order(tick.symbol, SHORT, OPEN, self.context.limit_vol, limit_price=tick.last_price - symbol_obj.tick_size)

    def pre_close(self, symbol):
        flag = True
        # 无持仓 忽略
        if self.context.open_vol == 0:
            flag = False
        # 已有挂单 忽略
        for sys_id, order in self.context.orders.items():
            if order.symbol == symbol and order.offset != OPEN:
                flag = False
        return flag

    def pre_open(self, symbol):
        flag = True
        # 已有持仓 忽略
        if self.context.open_vol > 0:
            flag = False
        # 已有挂单 忽略
        for sys_id, order in self.context.orders.items():
            if order.symbol == symbol and order.offset == OPEN:
                flag = False
        return flag

class BollStrategy_x(TradeStrategy):
    def initialize(self):
        self.context.universe = ['rb1805','TA805']
        self.context.strategy_name = 'boll_15M_v4.0'
        self.context.strategy_id = 'boll_15M'
        self.context.bar_frequency = '15M'
        self.context.init_cash = 100000

        self.context.user_id = '104749'
        self.context.password = 'jinmi1'

        self.context.vars = {}
        for symbol in self.context.universe:
            var = Variables(symbol)
            self.context.vars[symbol] = var

    def on_trade(self, trade):
        var = self.context.vars[trade.symbol]
        if trade.offset == OPEN:
            var.direction = trade.direction
            var.open_vol += trade.vol
            var.open_price = trade.price
        else:
            var.open_vol -= trade.vol
            if var.open_vol == 0:
                var.initialize()

    def handle_tick(self, tick):
        var = self.context.vars[tick.symbol]
        if self.pre_close(var, tick.symbol):
            # 止损
            self.stop_loss(var, tick)
            # 止盈
            self.stop_gain(var, tick)

        if self.pre_open(var, tick.symbol):
            self.long_open_by_tick(var, tick)

            self.short_open_by_tick(var, tick)


    def handle_bar(self, bar):

        for sys_id, order in self.context.orders.items():
            if order.symbol == bar.symbol:
                self.cancel_order(order)

        var = self.context.vars[bar.symbol]

        boll = var.boll.compute(bar)
        ma = var.ma.compute(bar)
        var.boll_t = boll
        if bar.symbol == 'rb1805':
            print('=====================')
        print('***bar %s' % bar)
        print('***boll %s' % boll)
        print('***ma %s' % ma)
        print('bar n2 %s' % var.bar_n_2)
        print('bar n1 %s' % var.bar_n_1)
        print('boll n2 %s' % var.boll_n_2)
        print('boll n1 %s' % var.boll_n_1)
        print('signal_count %s '% var.signal_count)

        if ma is not None and boll is not None:
            self.pre_bar_direction_flag(var, bar, boll)

            print('pre_bar_direction_flag %s' % var.pre_bar_direction_flag)

            self.long_close_signal(var, bar, boll)

            self.short_close_signal(var, bar, boll)

            self.long_open_signal(var, bar, ma, boll)

            self.short_open_signal(var, bar, ma, boll)


    def stop_gain(self, var, tick):
        if var.direction != '':
            delta = var.open_price - tick.last_price
            if var.direction == LONG:
                delta = tick.last_price - var.open_price

            if var.gain_over_flag and (var.max_gain - delta) / var.max_gain > var.stop_gain_thres:
                symbol_obj = self.context.symbol_infos[tick.symbol]
                if var.direction == LONG:
                    print('多单止盈')
                    self.order(tick.symbol,LONG,CLOSE,var.open_vol,limit_price=tick.last_price -  var.slippage * symbol_obj.tick_size)
                else:
                    print('空单止盈')
                    self.order(tick.symbol,SHORT,CLOSE,var.open_vol,limit_price=tick.last_price +  var.slippage * symbol_obj.tick_size)

            if delta / var.open_price > var.gain_thres:
                var.gain_over_flag = True
                if delta > var.max_gain:
                    var.max_gain = delta

    def stop_loss(self, var, tick):
        if var.direction != '':
            symbol_obj = self.context.symbol_infos[tick.symbol]
            if var.direction == LONG:
                if var.open_price - tick.last_price > var.stop_loss_thres * var.boll_t.mid or tick.last_price < var.boll_t.bot:
                    print('多单止损')
                    self.order(tick.symbol, LONG, CLOSE, var.open_vol,
                               limit_price=tick.last_price -  var.slippage * symbol_obj.tick_size)
            elif var.direction == SHORT:
                if tick.last_price - var.open_price > var.stop_loss_thres * var.boll_t.mid or tick.last_price > var.boll_t.top:
                    print('空单止损')
                    self.order(tick.symbol, SHORT, CLOSE, var.open_vol,
                               limit_price=tick.last_price + var.slippage * symbol_obj.tick_size)

    def pre_bar_direction_flag(self, var, bar, boll):
        if (boll.top - boll.bot)/boll.mid > var.spread_thres and var.signal_count == 0:
            if bar.close < boll.bot:
                var.pre_bar_direction_flag = LONG
            elif bar.close > boll.top:
                var.pre_bar_direction_flag = SHORT

    def short_close_signal(self, var, bar, boll):
        if var.direction == SHORT:
            symbol_obj = self.context.symbol_infos[bar.symbol]
            if var.close_count >= 3:
                if not self.pre_close(var, bar.symbol):
                    print('平空2')
                    self.order(bar.symbol,SHORT,CLOSE,var.open_vol,limit_price=bar.close + symbol_obj.tick_size)
            else:
                if bar.close > boll.mid and bar.close > bar.open and (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    var.close_count += 1
                    if var.close_count >= 3:
                        if not self.pre_close(var, bar.symbol):
                            print('平空1')
                            self.order(bar.symbol, SHORT, CLOSE, var.open_vol,limit_price=bar.close + var.slippage * symbol_obj.tick_size)

    def long_close_signal(self, var, bar, boll):
        if var.direction == LONG:
            symbol_obj = self.context.symbol_infos[bar.symbol]
            if var.close_count >= 3:
                if not self.pre_close(var, bar.symbol):
                    print('平多2')
                    self.order(bar.symbol,LONG,CLOSE,var.open_vol,limit_price=bar.close - symbol_obj.tick_size)
            else:
                if bar.close < boll.mid and bar.close < bar.open and (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    var.close_count += 1
                    if var.close_count >= 3:
                        if not self.pre_close(var, bar.symbol):
                            print('平多1')
                            self.order(bar.symbol, LONG, CLOSE, var.open_vol,limit_price=bar.close -var.slippage * symbol_obj.tick_size)

    def short_open_signal(self, var, bar, ma, boll):
        if var.direction == '' and var.pre_bar_direction_flag == SHORT:
            if var.signal_count == 0:
                if (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    cond_1_1 = boll.top > bar.open > boll.mid > bar.close > boll.bot
                    cond_1_2 = boll.mid - bar.close <= var.open_thres * boll.mid
                    if cond_1_1 and cond_1_2:
                        var.signal_count += 1
                        var.bar_n_2 = bar
                        var.boll_n_2 = boll

            elif var.signal_count == 1:
                if (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    cond_1_3 = bar.close < boll.mid
                    cond_1_4 = bar.open - bar.close <= var.open_thres * boll.mid
                    if cond_1_3 and cond_1_4:
                        var.signal_count += 1
                        var.bar_n_1 = bar
                        var.boll_n_1 = boll
                else:
                    var.pre_bar_direction_flag = ''
                    var.signal_count = 0
                    var.bar_n_2 = None
                    var.boll_n_2 = None

            elif var.signal_count == 2:
                if (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    cond_1_5 = bar.close < boll.mid
                    cond_1_6 = bar.open - bar.close <= var.open_thres * boll.mid
                    if cond_1_5 and cond_1_6:
                        # 3
                        b2, b1 = var.bar_n_2, var.bar_n_1
                        mn = (b2.close + b1.close + bar.close) / 3.00
                        cond_3 = ma - mn > - var.ma_thres * boll.mid

                        if cond_3:
                            if self.pre_open(var, bar.symbol):
                                print('开空')
                                symbol_obj = var.symbol_infos[bar.symbol]
                                self.order(bar.symbol, SHORT, OPEN, var.limit_vol,limit_price=bar.close - var.slippage * symbol_obj.tick_size)
                # 放弃所有信号
                var.pre_bar_direction_flag = ''
                var.signal_count = 0
                var.bar_n_2 = None
                var.bar_n_1 = None
                var.boll_n_2 = None
                var.boll_n_1 = None



    def long_open_signal(self,var, bar, ma, boll):
        if var.direction == '' and var.pre_bar_direction_flag == LONG:
            if var.signal_count == 0:
                if (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    cond_1_1 = boll.top > bar.close > boll.mid > bar.open > boll.bot
                    cond_1_2 = bar.close - boll.mid <= var.open_thres * boll.mid
                    if cond_1_1 and cond_1_2:
                        var.signal_count += 1
                        var.bar_n_2 = bar
                        var.boll_n_2 = boll
            elif var.signal_count == 1:
                if (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    cond_1_3 = bar.close > boll.mid
                    cond_1_4 = bar.close - bar.open <= var.open_thres * boll.mid
                    if cond_1_3 and cond_1_4:
                        var.signal_count += 1
                        var.bar_n_1 = bar
                        var.boll_n_1 = boll
                else:
                    var.pre_bar_direction_flag = ''
                    var.signal_count = 0
                    var.bar_n_2 = None
                    var.boll_n_2 = None

            elif var.signal_count == 2:
                if (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    cond_1_5 = bar.close > boll.mid
                    cond_1_6 = bar.close - bar.open <= var.open_thres * boll.mid
                    if cond_1_5 and cond_1_6:
                         # 3
                        b2, b1 = var.bar_n_2, var.bar_n_1
                        mn = (b2.close + b1.close + bar.close) / 3.00
                        cond_3 = mn - ma > -var.ma_thres * boll.mid

                        if cond_3:
                            if self.pre_open(var, bar.symbol):
                                print('开多')
                                symbol_obj = self.context.symbol_infos[bar.symbol]
                                self.order(bar.symbol, LONG, OPEN, var.limit_vol,limit_price=bar.close + var.slippage * symbol_obj.tick_size)
                # 放弃所有信号
                var.pre_bar_direction_flag = ''
                var.signal_count = 0
                var.bar_n_2 = None
                var.bar_n_1 = None
                var.boll_n_2 = None
                var.boll_n_1 = None

    def long_open_by_tick(self, var, tick):
        if var.signal_count == 1 and var.pre_bar_direction_flag == LONG:
            if tick.last_price - var.bar_n_2.close >= var.tick_open_thres * var.boll_n_2.mid:
                print('按tick 开多')
                symbol_obj = self.context.symbol_infos[tick.symbol]
                self.order(tick.symbol, LONG, OPEN, var.limit_vol,limit_price=tick.last_price + var.slippage * symbol_obj.tick_size)

    def short_open_by_tick(self, var, tick):
        if var.signal_count == 1 and var.pre_bar_direction_flag == SHORT:
            if var.bar_n_2.close - tick.last_price >= var.tick_open_thres * var.boll_n_2.mid:
                print('按tick 开空')
                symbol_obj = self.context.symbol_infos[tick.symbol]
                self.order(tick.symbol, SHORT, OPEN, var.limit_vol,limit_price=tick.last_price - var.slippage * symbol_obj.tick_size)

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

        self.gain_over_flag = False
        self.max_gain = 0
        self.close_count = 0