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
import utils.tools as tl
import logging as log
from utils import message as msg

class BollStrategy_x(TradeStrategy):
    def initialize(self):
        self.context.universe = ['rb1805','i1805','SR805','FG805','y1805','m1805','SF805','TA805','jm1805','ZC805']
        self.context.strategy_name = 'sp_boll_15M_v4.0'
        self.context.strategy_id = 'sp_boll_15M'
        self.context.bar_frequency = '15M'
        self.context.init_cash = 100000

        self.context.user_id = '00305188'
        self.context.password = 'Jinmi123'
        self.context.broker_id = '6000'
        self.context.trade_front = 'tcp://101.231.162.58:41205'
        self.context.market_front = 'tcp://101.231.162.58:41213'

        # self.context.user_id = '104749'
        # self.context.password = 'jinmi1'

        self.context.vars = {}
        for symbol in self.context.universe:
            var = Variables(symbol)
            self.context.vars[symbol] = var

        tl.config_logging()

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
        print('close_count %s' % var.close_count)

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
                    log.info('%s 多单止盈 max_gain %s gain_now %s' % (tick.symbol,var.max_gain, delta))
                    msg.send('%s 多单止盈 max_gain %s gain_now %s' % (tick.symbol,var.max_gain, delta))
                    self.order(tick.symbol,LONG,CLOSE,var.open_vol,limit_price=tick.last_price -  var.slippage * symbol_obj.tick_size)
                else:
                    log.info('%s 空单止盈 max_gain %s gain_now %s' % (tick.symbol,var.max_gain, delta))
                    msg.send('%s 空单止盈 max_gain %s gain_now %s' % (tick.symbol,var.max_gain, delta))
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
                    log.info('%s 多单止损' % tick.symbol)
                    msg.send('%s 多单止损' % tick.symbol)

                    self.order(tick.symbol, LONG, CLOSE, var.open_vol,
                               limit_price=tick.last_price -  var.slippage * symbol_obj.tick_size)
            elif var.direction == SHORT:
                if tick.last_price - var.open_price > var.stop_loss_thres * var.boll_t.mid or tick.last_price > var.boll_t.top:
                    log.info('%s 空单止损' % tick.symbol)
                    msg.send('%s 空单止损' % tick.symbol)
                    self.order(tick.symbol, SHORT, CLOSE, var.open_vol,
                               limit_price=tick.last_price + var.slippage * symbol_obj.tick_size)

    def pre_bar_direction_flag(self, var, bar, boll):
        if (boll.top - boll.bot)/boll.mid > var.spread_thres and var.signal_count == 0 and var.open_vol == 0:
            if bar.close < boll.bot:
                var.pre_bar_direction_flag = LONG
            elif bar.close > boll.top:
                var.pre_bar_direction_flag = SHORT

    def short_close_signal(self, var, bar, boll):
        if var.direction == SHORT:
            symbol_obj = self.context.symbol_infos[bar.symbol]
            if var.close_count >= 3:
                if self.pre_close(var, bar.symbol):
                    log.info('%s 平空 *' % bar.symbol)
                    msg.send('%s 平空 *' % bar.symbol)

                    self.order(bar.symbol,SHORT,CLOSE,var.open_vol,limit_price=bar.close + symbol_obj.tick_size)
            else:
                if bar.close > boll.mid and bar.close > bar.open and (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    var.close_count += 1
                    log.info('%s 平空计数器+1 close_count %s' % (bar.symbol, var.close_count))
                    if var.close_count >= 3:
                        if self.pre_close(var, bar.symbol):
                            log.info('%s 平空' % bar.symbol)
                            msg.send('%s 平空' % bar.symbol)

                            self.order(bar.symbol, SHORT, CLOSE, var.open_vol,limit_price=bar.close + var.slippage * symbol_obj.tick_size)

    def long_close_signal(self, var, bar, boll):
        if var.direction == LONG:
            symbol_obj = self.context.symbol_infos[bar.symbol]
            if var.close_count >= 3:
                if self.pre_close(var, bar.symbol):
                    log.info('%s 平多 *' % bar.symbol)
                    msg.send('%s 平多 *' % bar.symbol)

                    self.order(bar.symbol,LONG,CLOSE,var.open_vol,limit_price=bar.close - symbol_obj.tick_size)
            else:
                if bar.close < boll.mid and bar.close < bar.open and (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    var.close_count += 1
                    log.info('%s 平多计数器+1 close_count %s' % (bar.symbol, var.close_count))
                    if var.close_count >= 3:
                        if self.pre_close(var, bar.symbol):
                            log.info('%s 平多' % bar.symbol)
                            msg.send('%s 平多' % bar.symbol)

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
                        log.info('%s 空单第1根突破' % bar.symbol)
                        msg.send('%s 空单第1根突破' % bar.symbol)

            elif var.signal_count == 1:
                if (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    cond_1_3 = bar.close < boll.mid
                    cond_1_4 = bar.open - bar.close <= var.open_thres * boll.mid
                    if cond_1_3 and cond_1_4:
                        var.signal_count += 1
                        var.bar_n_1 = bar
                        var.boll_n_1 = boll
                        log.info('%s 空单第2根突破' % bar.symbol)
                    else:
                        var.pre_bar_direction_flag = ''
                        var.signal_count = 0
                        var.bar_n_2 = None
                        var.boll_n_2 = None

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
                        cond_3 = ma - mn > var.ma_thres * boll.mid

                        if cond_3:
                            if self.pre_open(var, bar.symbol):
                                log.info('%s 连续3根满足条件开空' % bar.symbol)
                                msg.send('%s 连续3根满足条件开空' % bar.symbol)

                                symbol_obj = self.context.symbol_infos[bar.symbol]
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
                        log.info('%s 多单第1根突破' % bar.symbol)
                        msg.send('%s 多单第1根突破' % bar.symbol)

            elif var.signal_count == 1:
                if (boll.top - boll.bot) / boll.mid > var.spread_thres:
                    cond_1_3 = bar.close > boll.mid
                    cond_1_4 = bar.close - bar.open <= var.open_thres * boll.mid
                    if cond_1_3 and cond_1_4:
                        var.signal_count += 1
                        var.bar_n_1 = bar
                        var.boll_n_1 = boll
                        log.info('%s 多单第2根突破' % bar.symbol)
                    else:
                        var.pre_bar_direction_flag = ''
                        var.signal_count = 0
                        var.bar_n_2 = None
                        var.boll_n_2 = None

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
                        cond_3 = mn - ma > var.ma_thres * boll.mid

                        if cond_3:
                            if self.pre_open(var, bar.symbol):
                                log.info('%s 连续3根满足条件开多' % bar.symbol)
                                msg.send('%s 连续3根满足条件开多' % bar.symbol)

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
                log.info('%s 按tick 开多' % tick.symbol)
                msg.send('%s 按tick 开多' % tick.symbol)

                symbol_obj = self.context.symbol_infos[tick.symbol]
                self.order(tick.symbol, LONG, OPEN, var.limit_vol,limit_price=tick.last_price + var.slippage * symbol_obj.tick_size)
                var.pre_bar_direction_flag = ''
                var.signal_count = 0
                var.bar_n_2 = None
                var.boll_n_2 = None

    def short_open_by_tick(self, var, tick):
        if var.signal_count == 1 and var.pre_bar_direction_flag == SHORT:
            if var.bar_n_2.close - tick.last_price >= var.tick_open_thres * var.boll_n_2.mid:
                log.info('%s 按tick 开空' % tick.symbol)
                msg.send('%s 按tick 开空' % tick.symbol)

                symbol_obj = self.context.symbol_infos[tick.symbol]
                self.order(tick.symbol, SHORT, OPEN, var.limit_vol,limit_price=tick.last_price - var.slippage * symbol_obj.tick_size)
                var.pre_bar_direction_flag = ''
                var.signal_count = 0
                var.bar_n_2 = None
                var.boll_n_2 = None

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

        # self.spread_thres = 0.00006  # 上下轨价差阈值
        # self.open_thres = 0.01  # 开仓close-open阈值
        # self.tick_open_thres = 0.00005  # 第2bar 按tick开仓阈值
        # self.ma_thres = -0.00006  # 与ma差值阈值
        # self.stop_loss_thres = 0.001  # 止损阈值
        # self.gain_thres = 0.001  # 止盈开始阈值
        # self.stop_gain_thres = 0.618  # 止盈回吐阈值

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

if __name__ == '__main__':
    pass
    # s = BollStrategy_x()
    # db = pymongo.MongoClient(host='192.168.1.10', port=27017).futures
    # symbols = s.context.universe
    # for symbol in symbols:
    #     res = db.history_bar.find({'InstrumentID': symbol, 'type': '15m', 'TradingDay': {'$gte': 20171219}}).sort(
    #         [('TradingDay', -1), ('levelNo', -1)]).limit(74)
    #     res = list(res)
    #     res.reverse()
    #     print('计算',symbol)
    #     print(len(res))
    #     for bar in res:
    #         bar =Bar(bar['InstrumentID'],op=bar['OpenPrice'],cl=bar['ClosePrice'],high=bar['HighPrice'],low=bar['LowPrice'])
    #         s.handle_bar(bar)
    #
    # db = bs.SharedDatabase.tradeDatabase
    # result = db.contexts.find(
    #     {'user_id': '00305188', 'broker_id': '6000', 'strategy_id': 'sp_boll_15M',
    #      'strategy_name': 'sp_boll_15M_v4.0'}).limit(1)
    # res = result.next()['context']
    # ctx = pkl.loads(res)
    #
    # # ctx.universe = ['rb1805','i1805','SR805','FG805','y1805','m1805','SF805','TA805','jm1805','ZC805']
    #
    # # 保存 vars变量
    # for k,v in s.context.vars.items():
    #     ctx.vars[k] = v
    #
    # # 添加Symbol属性和tick收集器
    # for symbol in s.context.universe:
    #     ctx.symbol_infos[symbol] = Symbol(symbol)
    #     ctx.tick_convers[symbol] = ta.TickConver(symbol, ctx.bar_frequency)
    #
    # ctx.portfolio.symbol_infos = ctx.symbol_infos
    #
    # ts.update_context_with_context(ctx)