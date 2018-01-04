# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         symbol.py
time:         2017/10/31 下午4:08
description: 

'''

__author__ = 'Jimmy'
from database import tradeStorage as ts
from trade.order import *

# {
#     'night_close_time': '23: 30: 00',
#     'night_close_hour': 23,
#     'night_close_minute': 30,
#     'exch_code': 'CZCE',  # DCE # SHFE
#     'instrument_name': '郑煤',
#     'instrument_code': 'zc',
#     'tick_size': 0.2,
#     'contract_size': 100,
#     'exch_margin': 8.0,
#     'broker_margin': 14.0,
#     'opening_fee_by_value': 0.0,
#     'opening_fee_by_num': 5.0,
#     'closing_fee_by_value': 0.0,
#     'closing_fee_by_num': 5.0,
#     'closing_today_fee_by_value': 0.0,
#     'closing_today_fee_by_num': 9.0
# }

class Symbol(object):
    def __init__(self, symbol):
        # 从futures.future_info获取symbol信息
        info = ts.get_future_info(symbol)
        del info['_id']
        del info['trade_date']
        self.__dict__.update(info)


    def calculate_commission(self, offset, vol, price):
        if offset == OPEN:
            if self.opening_fee_by_value != 0:
                return self.opening_fee_by_value * vol * price * self.contract_size
            else:
                return self.opening_fee_by_num * vol
        elif offset == CLOSE_TODAY:
            if self.closing_today_fee_by_value != 0:
                return self.closing_today_fee_by_value * vol * price * self.contract_size
            else:
                return self.closing_today_fee_by_num * vol
        elif offset == CLOSE_YESTERDAY:
            if self.closing_fee_by_value != 0:
                return self.closing_fee_by_value * vol * price * self.contract_size
            else:
                return self.closing_fee_by_value * vol

    # True 先平今 False 先平昨
    def compare_close_fee(self):
        close_today_fee = self.calculate_commission(CLOSE_TODAY, 1, 1)
        close_yesterday_fee = self.calculate_commission(CLOSE_YESTERDAY, 1, 1)
        if close_today_fee <= close_yesterday_fee:
            return True
        else:
            return False


    def __str__(self):
        return str(self.__dict__)


if __name__ == '__main__':
    sym = Symbol('IH1801')
    print(sym)
    # print(sym.calculate_commission(CLOSE,3,6010))
    # print(sym.calculate_commission(CLOSE_TODAY,5,6015))
    # al = Symbol('al1801')
    # print(al.calculate_commission(OPEN,2,15415))
    # print(al.calculate_commission(CLOSE_TODAY,2,15400))