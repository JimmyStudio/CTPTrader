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



# tick 转 bar  支持 任意Tick xT or任意秒 xS  or 任意分钟 xM
# x 需要能整除60, 否则有BUG
# x分钟的bar 如果第一个x分钟内只有一个tick则交易量为当前tick的量
# 目前不考虑股指国债...
# 任意 x hour 有BUG -- 20171103
class TickConver(object):
    def __init__(self, symbol, data_frequency = '30T'):
        self.symbol = symbol
        self._tick_prices = []
        self._begin_time = ''
        self._trading_day = ''
        self._vol_begin = 0
        self._vol_update = 0
        self.__option = self._compute_bar_option(data_frequency)
        self._bar_period = self.__option['period']
        self._bar_type = self.__option['type']
        self._night_close_time = self._get_night_close_time(symbol)
        self._bar_step = self._set_bar_step()
        self._ticks = []



    def tick_to_bar(self, tick):
        # tick updatatime 合法
        if self._check_tick(tick) :
            # tick数量类型bar
            if self._bar_type == 'T':
                if self._bar_period == 1:
                    return tick
                else:
                    bar_length = len(self._tick_prices)
                    if bar_length == 0:
                        self._vol_begin = int(tick['Volume'])

                    if bar_length < self._bar_period:
                        self._tick_prices.append(tick['LastPrice'])
                        self._ticks.append(tick)
                        self._begin_time = tick['UpdateTime']
                        return None
                    elif bar_length == self._bar_period:
                        # 由于tick是快照,下一个bar的第一个tick计算到上一个bar中,保证bar连续
                        self._tick_prices.append(tick['LastPrice'])
                        self._ticks.append(tick)
                        vol = int(tick['Volume']) - self._vol_begin
                        arr = np.array(self._tick_prices)
                        bar = Bar(self.symbol, self._tick_prices[0], self._tick_prices[-1], arr.max(), arr.min(),
                                  trading_day=tick['TradingDay'], begin_time=self._begin_time,
                                  end_time=tick['UpdateTime'], vol=vol, tick_counter=bar_length + 1,ticks=self._ticks)
                        self._tick_prices = []
                        self._ticks = []
                        self._tick_prices.append(tick['LastPrice'])
                        self._ticks.append(tick)

                        return bar
            # 时间间隔类 bar
            elif self._bar_type == 'M' or self._bar_type == 'S' or self._bar_type == 'H':
                bar_length = len(self._tick_prices)
                if bar_length == 0:
                    self._init_first_tick_of_bar(tick)
                    return None
                else:
                    time_space = self._compute_time_space()
                    if self._compute_time_delta(self._trading_day, tick['UpdateTime'],
                                                self._begin_time) >= self._bar_period * self._bar_step + time_space:
                        # 由于tick是快照,下一个bar的第一个tick计算到上一个bar中,保证bar连续
                        self._tick_prices.append(tick['LastPrice'])
                        self._ticks.append(tick)
                        self._vol_update = int(tick['Volume'])

                        vol = abs(self._vol_update - self._vol_begin)
                        arr = np.array(self._tick_prices)
                        bar = Bar(self.symbol, self._tick_prices[0], self._tick_prices[-1], arr.max(), arr.min(),
                                  trading_day=tick['TradingDay'], begin_time=self._begin_time,
                                  end_time=tick['UpdateTime'], vol=vol, tick_counter=len(self._tick_prices),ticks=self._ticks)
                        self._tick_prices = []
                        self._ticks = []
                        self._init_first_tick_of_bar(tick)
                        return bar
                    else:
                        self._tick_prices.append(tick['LastPrice'])
                        self._ticks.append(tick)
                        self._vol_update = int(tick['Volume'])
                        return None
            else:
                print('Unexcept bar type')
                return None
        else:
            return None


    def _init_first_tick_of_bar(self, tick):
        self._tick_prices.append(tick['LastPrice'])
        self._ticks.append(tick)
        self._trading_day = tick['TradingDay']
        self._begin_time = tick['UpdateTime']
        self._vol_begin = int(tick['Volume'])

    # 计算时间差  跨00:00:00的时间差计算需加1天后计算
    def _compute_time_delta(self, trading_day, update_time, compare_time):
        ut_year = ct_year = int(trading_day[0:4])
        ut_month = ct_month = int(trading_day[4:6])
        ut_day = ct_day = int(trading_day[6:8])

        uts = update_time.split(':')
        cts = compare_time.split(':')

        ut = dt(ut_year, ut_month, ut_day, int(uts[0]), int(uts[1]), int(uts[2]))

        # begin_time 秒位置为0参与计算 防止出现9:23:06 - 9:20:06 但实际应为 9:23:06-9:20:00
        ct = 0
        if self._bar_type == 'M':
            extra_min = int(cts[1]) % self._bar_period
            reset_min = int(cts[1]) - extra_min
            ct = dt(ct_year, ct_month, ct_day, int(cts[0]), reset_min, 0)
        # tick以秒为单位则按秒间隔重置tick开始时间
        elif self._bar_type == 'S':
            extra_sec = int(cts[2]) % self._bar_period
            reset_sec = int(cts[2]) - extra_sec
            ct = dt(ct_year, ct_month, ct_day, int(cts[0]), int(cts[1]), reset_sec)

        elif self._bar_type == 'H':
            # extra_hour = int(cts[0]) % self._bar_period
            # reset_hour = int(cts[0]) - extra_hour
            ct = dt(ct_year, ct_month, ct_day, int(cts[0]), 0, 0)

        if int(uts[0]) < 3:
            ut = ut + dtm.timedelta(days=1)
        if int(cts[0]) < 3:
            ct = ct + dtm.timedelta(days=1)
        return (ut - ct).seconds

    # 计算bar类型  1.按Tick数量组成bar  2.按时间周期组成bar
    def _compute_bar_option(self, data_frequency):
        if data_frequency == '' or data_frequency == '1T':
            raise ValueError('data_frequency can not be \'%s\' !!!' % data_frequency)
        period = int(''.join(list(filter(str.isdigit, data_frequency))))
        type = data_frequency[-1]
        return {'period': period, 'type': type}

    def _set_bar_step(self):
        if self._bar_type == 'M':
            return 60
        elif self._bar_type == 'H':
            return 3600
        else:
            return 1

    # 计算交易节点间隔 按秒计算
    def _compute_time_space(self):
        # print(self._night_close_time)
        if self._bar_period == 1 or self._night_close_time == None:
            return 0
        else:
            temp = self._begin_time.split(':')
            beg_timestamp = int(temp[0]) * 3600 + int(temp[1]) * self._bar_step + int(temp[2])
            end_timestamp = beg_timestamp + self._bar_period * self._bar_step

            if beg_timestamp <= self._night_close_time < end_timestamp:
                if self._night_close_time < 10800:
                    return 32400 - self._night_close_time
                else:
                    return 86400 -self._night_close_time + 32400

            elif beg_timestamp <= 36900 < end_timestamp:
                return 900
            elif beg_timestamp <= 41400 < end_timestamp:
                return 7200
            else:
                return 0

    # 检查tick是否有效  => 是否在时间范围内 比如8：59：59, 15:00:01 ,23:30:01...均为不合法tick 不计入bar
    def _check_tick(self, tick):
        tick_timestamp = self._time_to_int(tick['UpdateTime'])
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


    # 获取夜盘收盘时间
    def _get_night_close_time(self, symbol):
        db = bs.SharedDatabase.futuresDatabase
        symbol_code = tl.symbol_to_code(symbol)
        result = db.future_info.find({'instrument_code':symbol_code})
        try:
            res = result.next()
            night_close_time = res['night_close_time']
            temp = night_close_time.split(':')
            return int(temp[0]) * 3600 + int(temp[1]) * 60 + int(temp[2])
        except StopIteration:
            return None


    def _time_to_int(self, tm):
        temp = tm.split(':')
        return int(temp[0]) * 3600 + int(temp[1]) * 60 + int(temp[2])


if __name__ == '__main__':
    ma = MA(cycle=2)
    for i in range(10):
        bar = Bar(symbol='rb1801',op=i+2,cl=i,high=i+5,low=i-5)
        print(ma.compute(bar))


    # tick1 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '02:22:05',
    #     'LastPrice': 22,
    #     'Volume':33
    # }
    #
    # tick2 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '02:23:07',
    #     'LastPrice': 26,
    #     'Volume': 333
    #
    # }
    #
    # tick3 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '02:24:00',
    #     'LastPrice': 23,
    #     'Volume': 432
    # }
    #
    # tick4 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '02:24:12',
    #     'LastPrice': 20,
    #     'Volume': 455
    # }
    #
    # tick5 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '02:27:00',
    #     'LastPrice': 21,
    #     'Volume': 467
    # }
    #
    # tick6 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '02:28:15',
    #     'LastPrice': 88,
    #     'Volume': 487
    # }
    #
    # tick7 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '09:00:01',
    #     'LastPrice': 11,
    #     'Volume': 490
    # }
    #
    # tick8 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '09:04:01',
    #     'LastPrice': 11,
    #     'Volume': 490
    # }
    #
    # tick9 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '09:05:00',
    #     'LastPrice': 11,
    #     'Volume': 490
    # }
    #
    # tick10 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '10:14:02',
    #     'LastPrice': 1,
    #     'Volume': 490
    # }
    #
    # tick11 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '10:15:06',
    #     'LastPrice': 17,
    #     'Volume': 540
    # }
    #
    # tick12 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '10:30:02',
    #     'LastPrice': 170,
    #     'Volume': 540
    # }
    #
    # tick13 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '10:31:02',
    #     'LastPrice': 17,
    #     'Volume': 560
    # }
    #
    # tick14 = {
    #     'TradingDay': '20170927',
    #     'UpdateTime': '10:32:02',
    #     'LastPrice': 17,
    #     'Volume': 560
    # }
    #
    #
    # ct = TickConver('ag1801','3M')
    # print(ct.tick_to_bar(tick1))
    # print(ct.tick_to_bar(tick2))
    # print(ct.tick_to_bar(tick3))
    # print(ct.tick_to_bar(tick4))
    # print(ct.tick_to_bar(tick5))
    # print(ct.tick_to_bar(tick6))
    # print(ct.tick_to_bar(tick7))
    # print(ct.tick_to_bar(tick8))
    # print(ct.tick_to_bar(tick9))
    # print(ct.tick_to_bar(tick10))
    # print(ct.tick_to_bar(tick11))
    # print(ct.tick_to_bar(tick12))
    # print(ct.tick_to_bar(tick13))
    # print(ct.tick_to_bar(tick14))



