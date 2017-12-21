# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         position.py
time:         2017/10/31 下午2:48
description: 

'''

__author__ = 'Jimmy'
from trade.order import *


class BasePosition(object):
    def __init__(self, symbol_obj, direction):
        self.symbol = symbol_obj            # Symbol Object
        self.direction = direction          # 方向
        self.vol = 0
        self.avg_cost_per_unit = 0.0   # 结算成本价 结算时变成结算价

        self.original_cost = 0.0 # 实际成本
        self.original_avg_cost_per_unit = 0.0 # 实际成本价

        self.cost = 0.0
        self.margin = 0.0
        self.value = 0.0
        self.upnl = 0.0

    def init(self, init_vol, init_price):
        self.vol = init_vol  # 手数
        self.price = init_price  # 价格

        self.avg_cost_per_unit = init_price  # 每手成本
        self.original_avg_cost_per_unit = init_price

        self.cost = init_price * self.vol * self.symbol.contract_size  # 总成本
        self.original_cost = self.cost

        self.value = self.price * self.vol * self.symbol.contract_size
        self.margin = self.value * self.symbol.broker_margin * 0.01  # 保证金比例
        # 浮盈浮亏
        self.upnl = (self.value - self.cost) if self.direction == LONG else (self.cost - self.value)

    # 持仓成本改为结算价
    def update_value_dayend(self, price):
        self.price = price
        self.avg_cost_per_unit = price
        self.cost = self.vol * self.symbol.contract_size * self.avg_cost_per_unit
        self.value = self.cost
        self.margin = self.value * self.symbol.broker_margin * 0.01 # 保证金
        self.upnl = (self.value - self.cost) if self.direction == LONG else (self.cost - self.value)


    # 按价格更新持仓
    def update_value(self, price):
        self.price = price
        self.value = self.price * self.vol * self.symbol.contract_size
        self.upnl = (self.value - self.cost) if self.direction == LONG else (self.cost - self.value)

    # 平仓
    def close_position(self, vol):
        self.vol -= vol
        self.cost -= vol * self.avg_cost_per_unit * self.symbol.contract_size
        self.original_cost -= vol * self.original_avg_cost_per_unit * self.symbol.contract_size

        self.margin = self.cost * self.symbol.broker_margin * 0.01
        if self.vol == 0:
            self.clear_position()

    # 开仓
    def add_position(self, vol, price):
        self.vol += vol
        self.cost += vol * price * self.symbol.contract_size
        self.original_cost += vol * price * self.symbol.contract_size

        self.avg_cost_per_unit = self.cost/(self.vol * self.symbol.contract_size)
        self.original_avg_cost_per_unit = self.original_cost/(self.vol * self.symbol.contract_size)

        self.margin = self.cost * self.symbol.broker_margin * 0.01


    # 清空 持仓
    def clear_position(self):
        self.vol = 0
        self.cost = 0
        self.avg_cost_per_unit = 0
        self.original_avg_cost_per_unit = 0
        self.original_cost = 0
        self.value = 0
        self.margin = 0
        self.upnl = 0

    def __str__(self):
        return '%s %s %s %s' %(self.symbol.instrument_code, self.vol, self.avg_cost_per_unit, self.upnl)



class Position(object):
    def __init__(self, symbol_obj):
        self.symbol = symbol_obj
        self.long_today = BasePosition(symbol_obj=symbol_obj, direction=LONG)
        self.long_yesterday = BasePosition(symbol_obj=symbol_obj, direction=LONG)
        self.short_today = BasePosition(symbol_obj=symbol_obj, direction=SHORT)
        self.short_yesterday = BasePosition(symbol_obj=symbol_obj, direction=SHORT)
        self.commsion = 0   # 手续费
        self.last_price = 0 # 最新价
        self.value = 0      # 总权益


    def update_value(self, price):
        self.long_today.update_value(price)
        self.long_yesterday.update_value(price)
        self.short_today.update_value(price)
        self.short_yesterday.update_value(price)

        self.last_price = price
        self.value = self.long_today.value + self.long_yesterday.value + self.short_today.value + self.short_yesterday.value
        self.margin = self.long_today.margin + self.long_yesterday.margin + self.short_today.margin + self.short_yesterday.margin
        self.upnl = self.long_today.upnl + self.long_yesterday.upnl + self.short_today.upnl + self.short_yesterday.upnl

    def update_value_dayend(self, price):
        self.long_today.update_value_dayend(price)
        self.short_today.update_value_dayend(price)
        self.long_yesterday.update_value_dayend(price)
        self.short_yesterday.update_value_dayend(price)

        self.last_price = price
        self.value = self.long_today.value + self.long_yesterday.value + self.short_today.value + self.short_yesterday.value
        self.margin = self.long_today.margin + self.long_yesterday.margin + self.short_today.margin + self.short_yesterday.margin
        self.upnl = self.long_today.upnl + self.long_yesterday.upnl + self.short_today.upnl + self.short_yesterday.upnl


    def combine_position_dayend(self):
        self._combine_position(self.long_yesterday, self.long_today)
        self._combine_position(self.short_yesterday, self.short_today)

    def get_value(self):
        return self.long_today.value + self.short_today.value + self.long_yesterday.value + self.short_yesterday.value

    def get_margin(self):
        return self.long_today.margin + self.long_yesterday.margin + self.short_today.margin + self.short_yesterday.margin

    def get_vol(self):
        return self.long_today.vol + self.short_today.vol + self.long_yesterday.vol + self.short_yesterday.vol

    def get_long_vol(self):
        return self.long_today.vol + self.long_yesterday.vol

    def get_short_vol(self):
        return self.short_today.vol + self.short_yesterday.vol

    def get_upnl(self):
        return self.long_today.upnl + self.long_yesterday.upnl + self.short_today.upnl + self.short_yesterday.upnl

    def print_position(self):
        return '今多:%s 今空:%s 昨多:%s 昨空:%s ' % (self.long_today, self.short_today, self.long_yesterday, self.short_yesterday)


    def _combine_position(self, p1, p2):
        p1.vol += p2.vol
        p1.cost += p2.cost
        p1.original_cost += p2.original_cost

        p1.upnl += p2.upnl
        p1.value = p1.price * p1.vol * p1.symbol.contract_size
        p1.margin = p1.value * p1.symbol.broker_margin * 0.01

        if p1.vol == 0:
            pass
        else:
            p1.avg_cost_per_unit = p1.cost/(p1.vol * p1.symbol.contract_size)
            p1.original_avg_cost_per_unit = p1.original_cost/(p1.vol * p1.symbol.contract_size)

        p2.clear_position()



if __name__ == '__main__':
    pass





