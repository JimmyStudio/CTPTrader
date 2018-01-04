# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         test.py
time:         2017/9/26 下午5:50
description: 

'''

__author__ = 'Jimmy'
from database import base as bs
from utils import tools as tl
from datetime import datetime as dt
from utils.objects import *
import pymongo


class Region(object):
    def __init__(self, begin_sec, end_sec):
        self.begin_sec = begin_sec
        self.end_sec = end_sec

    def string_to_sec(self, str):
        strs = str.split(':')
        return int(strs[0]) * 3600 + int(strs[1]) * 60 + int(strs[2])

    def sec_to_string(self, sec):
        m_l = sec % 3600
        hour = (sec - m_l)/3600
        sec = m_l % 60
        min = (m_l - sec) / 60
        return '%s:%s:%s' % (str(int(hour)).zfill(2), str(int(min)).zfill(2), str(int(sec)).zfill(2))

    def __str__(self):
        return '%s ~ %s' %(self.sec_to_string(self.begin_sec),self.sec_to_string(self.end_sec))


class TickConver(object):
    def __init__(self, symbol, data_frequency = '30T'):
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



if __name__ == '__main__':

    ct = TickConver('al1802', '1H')
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

    # res = db.rb_price.find({'InstrumentID': 'rb1805', 'TradingDay': 20180104, 'insert_date': '2018-01-04'},
    #                        ['InstrumentID', 'UpdateTime', 'TradingDay', 'LastPrice', 'Volume'])
    # i= 0
    # while True:
    #     try:
    #         bar = ct.tick_to_bar(next(res))
    #         if bar:
    #             print(bar)
    #     except StopIteration:
    #         break



