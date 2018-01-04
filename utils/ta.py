# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         ta.py
time:         2017/9/12 上午10:53
description: 

'''

__author__ = 'Jimmy'
import numpy as np
from utils.objects import *
from trade.order import *
from datetime import datetime as dt
import datetime as dtm
from database import base as bs
from utils import tools as tl
import pymongo

class KDJ(object):
    def __init__(self, cyclenum= 13,a =1/3, b=1/3):
        self.a = a
        self.b = b
        self.cyclenum = cyclenum
        self.barlow = []
        self.barhigh = []

    def compute(self,bar,k1,d1):
        self.barlow.append(bar.low)
        self.barhigh.append(bar.high)
        # print(self.barlow)
        # print(self.barhigh)
        bar_len = len(self.barlow)
        if bar_len < self.cyclenum:
            return None
        else:
            high = max(self.barhigh)
            low = min(self.barlow)
            close = bar.close
            if high != low:
                rsv = 100 * (close - low)/(high - low)
            else:
                rsv = 50
            k2 = (1 - self.a) * k1 + self.a * rsv
            d2 = (1 - self.b) * d1 + self.b * k2
            j2 = 3*k2 - 2*d2
            kdjout = KDJOut(k1=k1,d1=d1,k2=k2,d2=d2,j2=j2)
            del self.barhigh[0]
            del self.barlow[0]
            return kdjout

# 计算移动均线
class MA(object):
    def __init__(self, cycle=75):
        self.cycle = cycle
        self.prices = []

    def compute(self, bar):
        bar_len = len(self.prices)
        if bar_len < self.cycle -1:
            self.prices.append(bar.close)
            return None
        else:
            self.prices.append(bar.close)
            arr = np.array(self.prices)
            ma = arr.mean()
            del self.prices[0]
            return ma


#计算unit N
class ATR(object):
    def __init__(self, account, cycle=20, dpp=10, coe=0.2):
        self.account = account
        self.bar = None
        self.cycle = cycle
        self.dpp = dpp
        self.n = 0
        self.count = 0
        self.coe = coe


    def compute(self, bar):
        if self.count == 0:
            self.bar = bar
            self.count += 1
            return AtrR(0,0)
        else:
            arr = np.array([bar.high - bar.low,bar.high - self.bar.close, self.bar.close - bar.low])
            tr = arr.max()

            if self.count < self.cycle + 1:
                self.n = (self.n * self.count + tr) / (self.count + 1)
            else:
                self.n = (self.n * (self.cycle -1) + tr) / self.cycle

            dv = self.n * self.dpp
            unit = int((0.01 * self.coe *self.account)/dv)
            self.bar = bar
            self.count += 1
            out = AtrR(unit,self.n)

            return out

# 计算n日突破信号
class BreakLimit(object):
    def __init__(self, cycle = 20):
        self.cycle = cycle
        self.highs = []
        self.lows = []


    def compute(self, bar):
        high_len = len(self.highs)
        if high_len < self.cycle:
            self._update(bar)
            return None
        elif high_len == self.cycle:
            arr_high = np.array(self.highs)
            arr_low = np.array(self.lows)
            max = arr_high.max()
            min = arr_low.min()
            del self.highs[0]
            del self.lows[0]
            self._update(bar)

            print('时间:%s BreakLimit=>max - min : %d - %d' % (dt.now(), max, min))

            if bar.close > max:
                return BlR(direction=LONG,price=max)
            elif bar.close < min:
                return BlR(direction=SHORT,price=min)
            else:
                return None

    def _update(self, bar):
        self.highs.append(bar.high)
        self.lows.append(bar.low)


# 计算n日突破信号
class StopLimit(object):
    def __init__(self, cycle = 10):
        self.cycle = cycle
        self.highs = []
        self.lows = []


    def compute(self, bar):
        high_len = len(self.highs)
        if high_len < self.cycle:
            self._update(bar)
            return None
        elif high_len == self.cycle:
            arr_high = np.array(self.highs)
            arr_low = np.array(self.lows)
            max = arr_high.max()
            min = arr_low.min()
            del self.highs[0]
            del self.lows[0]
            self._update(bar)

            print('时间:%s StopLimit=>max - min : %d - %d' % (dt.now(), max, min))

            if bar.close > max :
                # print('空单止盈')
                return 'SELL_STOP'
            elif bar.close < min:
                # print('多单止盈')
                return 'BUY_STOP'
            else:
                return None

    def _update(self, bar):
        self.highs.append(bar.high)
        self.lows.append(bar.low)

# 计算boll线上中下轨
class Boll(object):
    def __init__(self, cycle = 26, k=2):
        self._cycle = cycle
        self._k = k
        self._close_prices=[]


    def compute(self, bar):
        bar_length = len(self._close_prices)
        if bar_length < self._cycle - 1:
            self._close_prices.append(bar.close)
            return None
        else:
            # 计算n-1个bar的close均值 即中轨
            # temp1 = np.array(self._close_prices)
            # mb = temp1.mean()

            self._close_prices.append(bar.close)
            temp2 = np.array(self._close_prices)
            # n个bar的标准差
            md = temp2.std()
            mb = temp2.mean()

            up = mb + self._k * md  # 上轨 = 中轨 + k * n个bar标准差
            dn = mb - self._k * md  # 下轨 = 中轨 - k * n个bar标准差
            bollout = BollOut(up, mb, dn, md)
            del self._close_prices[0]
            return bollout

# tick 转 bar  支持 任意秒 xS  or 任意分钟 xM 任意小时x H
class TickConver(object):
    def __init__(self, symbol, data_frequency = '30S'):
        self.symbol = symbol
        self.__option = self._compute_bar_option(data_frequency) # 3S, 4M , 1H
        self.bar_period = self.__option['period'] # x
        self.bar_type = self.__option['type']  # S M H
        self.periods = self._periods_by_night_close_time(symbol)
        self.bar_step = self._set_bar_step()
        self.tables = self._generate_tables()
        self.current_table = self.tables[0]
        self.tick_prices = []
        self.begin_time = ''
        self.vol_begin = 0

    def tick_to_bar(self, tick):
        tick_timestamp = self._time_to_int(tick['UpdateTime'])
        if self._check_tick(tick_timestamp,tick):
            if self.begin_time == '':
                self.begin_time = tick['UpdateTime']

            if self.current_table.begin_sec < self.current_table.end_sec:
                if self.current_table.begin_sec <= tick_timestamp < self.current_table.end_sec:
                    self.tick_prices.append(tick['LastPrice'])
                    return None
                else:
                    bar = None
                    if len(self.tick_prices) > 0:
                        self.tick_prices.append(tick['LastPrice'])
                        vol = int(tick['Volume']) - self.vol_begin
                        bar = Bar(self.symbol, self.tick_prices[0], self.tick_prices[-1], max(self.tick_prices),
                                  min(self.tick_prices),
                                  trading_day=tick['TradingDay'], begin_time=self.begin_time,
                                  end_time=tick['UpdateTime'], vol=vol, tick_counter=len(self.tick_prices))
                        self.tick_prices = []
                        self.begin_time = ''
                        self.vol_begin = 0
                    for table in self.tables:
                        if table.begin_sec < table.end_sec:
                            if table.begin_sec <= tick_timestamp < table.end_sec:
                                self.current_table = table
                                self.begin_time = tick['UpdateTime']
                                self.vol_begin = int(tick['Volume'])
                                self.tick_prices.append(tick['LastPrice'])
                        else:
                            if table.begin_sec <= tick_timestamp < 86400:
                                self.current_table = table
                                self.begin_time = tick['UpdateTime']
                                self.vol_begin = int(tick['Volume'])
                                self.tick_prices.append(tick['LastPrice'])

                            elif 0 <= tick_timestamp < table.end_sec:
                                self.current_table = table
                                self.begin_time = tick['UpdateTime']
                                self.vol_begin = int(tick['Volume'])
                                self.tick_prices.append(tick['LastPrice'])
                    if bar:
                        return bar
            else:
                if self.current_table.begin_sec <= tick_timestamp < 86400:
                    self.tick_prices.append(tick['LastPrice'])
                    return None
                elif 0 <= tick_timestamp < self.current_table.end_sec:
                    self.tick_prices.append(tick['LastPrice'])
                    return None
                else:
                    bar = None
                    if len(self.tick_prices) > 0:
                        self.tick_prices.append(tick['LastPrice'])
                        vol = int(tick['Volume']) - self.vol_begin
                        bar = Bar(self.symbol, self.tick_prices[0], self.tick_prices[-1], max(self.tick_prices),
                                  min(self.tick_prices),
                                  trading_day=tick['TradingDay'], begin_time=self.begin_time,
                                  end_time=tick['UpdateTime'], vol=vol, tick_counter=len(self.tick_prices))
                        self.tick_prices = []
                        self.begin_time = ''
                        self.vol_begin = 0
                    for table in self.tables:
                        if table.begin_sec < table.end_sec:
                            if table.begin_sec <= tick_timestamp < table.end_sec:
                                self.current_table = table
                                self.begin_time = tick['UpdateTime']
                                self.vol_begin = int(tick['Volume'])
                                self.tick_prices.append(tick['LastPrice'])
                        else:
                            if table.begin_sec <= tick_timestamp < 86400:
                                self.current_table = table
                                self.begin_time = tick['UpdateTime']
                                self.vol_begin = int(tick['Volume'])
                                self.tick_prices.append(tick['LastPrice'])

                            elif 0 <= tick_timestamp < table.end_sec:
                                self.current_table = table
                                self.begin_time = tick['UpdateTime']
                                self.vol_begin = int(tick['Volume'])
                                self.tick_prices.append(tick['LastPrice'])
                    if bar:
                        return bar

    def _compute_bar_option(self, data_frequency):
        if data_frequency == '' or data_frequency == '1T':
            raise ValueError('data_frequency can not be \'%s\' !!!' % data_frequency)
        period = int(''.join(list(filter(str.isdigit, data_frequency))))
        type = data_frequency[-1]
        return {'period': period, 'type': type}

    def _set_bar_step(self):
        if self.bar_type == 'M':
            return self.bar_period * 60
        elif self.bar_type == 'H':
            return self.bar_period * 3600
        else:
            return self.bar_period

    # 获取开盘收盘时间
    def _periods_by_night_close_time(self, symbol):
        db = bs.SharedDatabase.futuresDatabase
        symbol_code = tl.symbol_to_code(symbol)
        result = db.future_info.find({'instrument_code':symbol_code})
        try:
            res = result.next()
            nct= res['night_close_hour'] * 3600 + res['night_close_minute'] * 60
            self._night_close_time = nct
            if res['night_close_hour'] < 3:
                return [Region(75600,86400),Region(0, nct),Region(32400, 36900),Region(37800, 41400),Region(48600, 54000)]
            else:
                return [Region(75600,nct),Region(32400, 36900),Region(37800, 41400),Region(48600, 54000)]
        except StopIteration:
            return None

    def _generate_tables(self):
        tables = []
        left_sep = 0
        for period in self.periods:
            begin = period.begin_sec
            if left_sep != 0:
                temp_end = tables[-1]
                begin = period.begin_sec + self.bar_step - left_sep
                reg = Region(temp_end.end_sec, begin)
                tables.append(reg)

            end = period.end_sec
            sep = begin

            while sep + self.bar_step < end:
                temp = sep + self.bar_step
                reg = Region(sep, temp)
                sep = temp
                tables.append(reg)
            temp_end = tables[-1]
            left_sep = end - temp_end.end_sec

        if left_sep != 0:
            temp_end = tables[-1]
            reg = Region(temp_end.end_sec, 54000)
            tables.append(reg)
        return tables

    def _check_tick(self, tick_timestamp,tick):
        flag = True

        # 11:30:00 ~ 13:30:00  15:00:00 ~ 21:00:00
        if 41400 < tick_timestamp < 48600 or 54000 < tick_timestamp < 75600:
            print('时间: %s ta不计入bar的tick 11:30:00 ~ 13:30:00  15:00:00 ~ 21:00:00 %s ' % (dt.now(), tick))
            flag = False

        # 收盘时间 < 3:00
        if self._night_close_time < 10800:
            # 2:30:00 ~ 9:00:00
            if self._night_close_time < tick_timestamp < 32400:
                print('时间: %s ta不计入bar的tick 2:30:00 ~ 9:00:00 %s ' % (dt.now(), tick))
                flag = False
        else:
            # 23:00:00 ~ 24:00:00
            if self._night_close_time < tick_timestamp < 86400:
                print('时间: %s ta不计入bar的tick 23:00:00 ~ 24:00:00 %s ' % (dt.now(), tick))
                flag = False
            # 00:00:00 ~ 9:00:00
            elif 0 < tick_timestamp < 32400:
                print('时间: %s ta不计入bar的tick %s 00:00:00 ~ 9:00:00 ' % (dt.now(), tick))
                flag = False
        return flag

    def _time_to_int(self, tm):
        temp = tm.split(':')
        return int(temp[0]) * 3600 + int(temp[1]) * 60 + int(temp[2])


#     def tick_to_bar(self, tick):
#         # tick updatatime 合法
#         if self._check_tick(tick) :
#             # tick数量类型bar
#             if self._bar_type == 'T':
#                 if self._bar_period == 1:
#                     return tick
#                 else:
#                     bar_length = len(self._tick_prices)
#                     if bar_length == 0:
#                         self._vol_begin = int(tick['Volume'])
#
#                     if bar_length < self._bar_period:
#                         self._tick_prices.append(tick['LastPrice'])
#                         self._ticks.append(tick)
#                         self._begin_time = tick['UpdateTime']
#                         return None
#                     elif bar_length == self._bar_period:
#                         # 由于tick是快照,下一个bar的第一个tick计算到上一个bar中,保证bar连续
#                         self._tick_prices.append(tick['LastPrice'])
#                         self._ticks.append(tick)
#                         vol = int(tick['Volume']) - self._vol_begin
#                         arr = np.array(self._tick_prices)
#                         bar = Bar(self.symbol, self._tick_prices[0], self._tick_prices[-1], arr.max(), arr.min(),
#                                   trading_day=tick['TradingDay'], begin_time=self._begin_time,
#                                   end_time=tick['UpdateTime'], vol=vol, tick_counter=bar_length + 1,ticks=self._ticks)
#                         self._tick_prices = []
#                         self._ticks = []
#                         self._tick_prices.append(tick['LastPrice'])
#                         self._ticks.append(tick)
#
#                         return bar


if __name__ == '__main__':

    ct = TickConver('al1802', '1H')
    print(ct.bar_step)
    for tb in ct.tables:
        print(tb)

    db = pymongo.MongoClient(host='192.168.1.10', port=27017).futures
    # res = db.al_price.find({'InstrumentID': 'al1802','TradingDay':20180104,'insert_date':'2018-01-03'},['InstrumentID', 'UpdateTime','TradingDay','LastPrice','Volume'])
    # while True:
    #     try:
    #         bar = ct.tick_to_bar(next(res))
    #         if bar:
    #             print(bar)
    #     except StopIteration:
    #         break

    res = db.al_price.find({'InstrumentID': 'al1802', 'TradingDay': 20180104, 'insert_date': '2018-01-04'},
                           ['InstrumentID', 'UpdateTime', 'TradingDay', 'LastPrice', 'Volume'])
    while True:
        try:
            bar = ct.tick_to_bar(next(res))
            if bar:
                print(bar)
        except StopIteration:
            break




