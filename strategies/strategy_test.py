# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         strategy_test.py
time:         2017/8/28 上午11:43
description: 

'''

__author__ = 'Jimmy'

from trade.tradeStrategy import *
from datetime import datetime as dt


class test_strategy(TradeStrategy):

    def initialize(self):
        self.context.universe = ['rb1801']
        self.context.strategy_id = '000001'
        self.context.strategy_name = '测试'
        self.context.data_frequency = '30S'
        self.context.init_cash = 100000

        self.flag = True

    def handle_data(self, data):
        print('时间: %s => %s' % (datetime.now(), data))

        # if self.flag:
        #     self.flag = False
        #     print('==================================')
        #     print('==========策略触发限价交易==========')
        #     self.order(self.context.universe[0], LONG, OPEN, 1)


if __name__ == '__main__':
    t = test_strategy()
    symbol_obj = t.context.symbol_infos['rb1801']
    p = Position(symbol_obj)
    p.long_yesterday.vol = 2
    p.long_yesterday.avg_cost_per_unit = 3222
    t.context.portfolio.positions['rb1801'] = p
    t.context.portfolio.print_Portfolio()

    t.order('rb1801',LONG,CLOSE,2,3333)
    # t.run()