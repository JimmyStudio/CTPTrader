# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         tools.py
time:         2017/9/7 下午5:16
description: 

'''

__author__ = 'Jimmy'
from datetime import datetime as dt
from database import base as bs
from utils.objects import *
import logging as log
from trade.symbol import *
import os


def getTime():
    date = str(dt.now()).split(' ')
    t = date[-1].split('.')
    return [date[0], t[0], t[-1]]

# BUG 周一凌晨3点会触发保存context命令
def schedule_reboot(strategies=None):
    '''
    :param trade_end_delta: 停止交易前几分钟（按15:00为截止交易时间）
    :return: 
    '''
    trading_day = bs.getTradingDay()
    # 如果今天不是交易日, 但是昨天是交易日 处理交易日跨到非交易日时凌晨收盘问题
    if trading_day['today'] == '' :
        if trading_day['yesterday'] != '':
            now = dt.now()
            time_now = now.hour * 60 + now.minute

            # 日内策略提前平仓判断
            if strategies:
                force_close_infos = []
                for strategy_id, strategy_dict in strategies.items():
                    force_close_minutes = strategy_dict['force_close_minutes']
                    force_close_flags = strategy_dict['force_close_flags']
                    symbol_infos = strategy_dict['symbols']
                    for symbol in force_close_minutes:
                        # 如果该symbol 没有发生过日内平仓
                        if not force_close_flags[symbol]:
                            # 提前平仓时间差
                            fcm = force_close_minutes[symbol]
                            if fcm > 0:
                                # check 当前时间是否在强平范围内
                                # 如果是夜盘
                                symbol_info = symbol_infos[symbol]
                                if symbol_info.night_close_hour < 3:
                                    close_time = symbol_info.night_close_hour * 60 + symbol_info.night_close_minute
                                    stop_time = close_time - fcm
                                    if stop_time <= time_now and time_now <= close_time:
                                        force_close_infos.append({strategy_id: symbol})
                # 如果有需要日内平仓的策略
                if len(force_close_infos) > 0:
                    return RebootInfo('force_close', 'collect', trading_day['yesterday']['next_trade_date'],
                                      force_close_infos=force_close_infos)

            if 152 < time_now and time_now <= 157:
                # 2:30 ~ 2:35 凌晨结束保存未成交订单
                return RebootInfo('save', 'collect', trading_day['yesterday']['next_trade_date'])
            elif 157 < time_now and time_now <= 160:
                # 2:35 ~ 2:40 凌晨结束
                return RebootInfo('stop', 'collect', trading_day['yesterday']['next_trade_date'])
            else:
                return None
        else:
            return None

    # 如果当天是交易日 所有时间段均处理
    else :
        now = dt.now()
        time_now = now.hour * 60 + now.minute
        # 8:40~11:50 13:10 ~ 15:35 20:40~23:59 0:00 ~3:00

        # 日内策略提前平仓判断
        if strategies :
            force_close_infos = []
            for strategy_id, strategy_dict in strategies.items():
                force_close_minutes = strategy_dict['force_close_minutes']
                force_close_flags = strategy_dict['force_close_flags']
                symbol_infos = strategy_dict['symbols']
                for symbol in force_close_minutes:
                    # 如果该symbol 没有发生过日内平仓
                    if not force_close_flags[symbol]:
                        #提前平仓时间差
                        fcm = force_close_minutes[symbol]
                        if fcm > 0 :
                            # check 当前时间是否在强平范围内
                            # 如果是夜盘
                            symbol_info = symbol_infos[symbol]
                            if symbol_info.night_close_hour != 99:
                                close_time = symbol_info.night_close_hour * 60 + symbol_info.night_close_minute
                                stop_time = close_time - fcm
                                if stop_time <= time_now and time_now <= close_time:
                                    force_close_infos.append({strategy_id: symbol})

                            # 如果是下午3点前
                            stop_time = 900 - fcm
                            if stop_time <= time_now and time_now <= 900:
                                force_close_infos.append({strategy_id:symbol})
            # 如果有需要日内平仓的策略
            if len(force_close_infos) > 0:
                return RebootInfo('force_close', 'collect', trading_day['today']['cur_trade_date'],force_close_infos=force_close_infos)

        if 525 <= time_now and time_now < 540:
            # 8:45 ~ 8:55 开启
            return RebootInfo('start','collect',trading_day['today']['cur_trade_date'])

        elif 700 <= time_now and time_now <= 705:
            # 11:40 ~11:45 保存未成交订单
            return RebootInfo('save', 'collect', trading_day['today']['cur_trade_date'])
        elif 710 <= time_now and time_now <= 715:
            # 11：50 ~ 11：55 午间停止
            return RebootInfo('stop', 'collect', trading_day['today']['cur_trade_date'])

        elif 795 <= time_now and time_now <= 805:
            # 13:15 ~ 13:25 下午开启
            return RebootInfo('start','collect', trading_day['today']['cur_trade_date'])

        elif 915 <= time_now and time_now <= 920:
            # 15：15 ~ 15：20 当日结束 触发trading_end事件
            return RebootInfo('trading_end','collect', trading_day['today']['cur_trade_date'])

        elif 925 <= time_now and time_now <= 930:
            # 15：25 ~ 15：30 当日结束 清理未成交订单 保存context
            return RebootInfo('clear','collect', trading_day['today']['cur_trade_date'])

        elif 935 <= time_now and time_now <= 940:
            # 15:35 ~ 15:40 当日结束
            return RebootInfo('stop','process', trading_day['today']['cur_trade_date'])

        elif 1245 <= time_now and time_now < 1255:
            # 20:45 ~ 20:55 启动新的交易日
            return RebootInfo('new','collect', trading_day['today']['next_trade_date'])
        #
        elif 1255 <= time_now and time_now < 1260:
            # 20:55 ~ 21:00 启动新的交易日之前触发before_trading方法
            return RebootInfo('before_trading','collect', trading_day['today']['next_trade_date'])

        elif 152 < time_now and time_now <= 157:
            # 2:30 ~ 2:35 凌晨结束保存未成交订单
            return RebootInfo('save','collect', trading_day['today']['cur_trade_date'])
        elif 157 < time_now and time_now <= 160:
            # 2:35 ~ 2:40 凌晨结束
            return RebootInfo('stop','collect', trading_day['today']['cur_trade_date'])

        else:
            return None


# 'rb1801' -> 'rb_price'
def symbol_classify(symbol):
    f = filter(str.isalpha, symbol)
    symbol_class = ''.join(list(f)).lower() # 表名统一转小写
    return symbol_class+'_price'


# 'rb1801' -> 'rb'
def symbol_to_code(symbol):
    f = filter(str.isalpha, symbol)
    symbol_class = ''.join(list(f)).lower()  # 表名统一转小写
    return symbol_class


# tick updatetime 与系统时间 ±5分钟 才就行插库, 否则舍弃
def tick_filter(tick):
    update_times = tick['UpdateTime'].split(':')
    now = dt.now()
    date = str(now).split(' ')
    dates = date[0].split('-')
    update_time_dt = dt(int(dates[0]), int(dates[1]), int(dates[2]), int(update_times[0]), int(update_times[1]), int(update_times[2]))
    gap = (update_time_dt-now).seconds/60
    if gap >=0 and gap <= 5:
        return True
    elif gap >= 1435 and gap <= 1440:
        return True
    else:
        print('时间: %s tool不计入bar的tick %s ' % (dt.now(), tick))
        return False


# 配置logging
def config_logging():
    log.basicConfig(level=log.INFO,
                        format='%(asctime)s %(filename)s[line:%(lineno)d][%(thread)d][%(threadName)s]%(levelname)-8s=> %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename='server.log',
                        filemode='a')

    #################################################################################################
    # 定义一个StreamHandler，将INFO级别或更高的日志信息打印到标准错误，并将其添加到当前的日志处理对象#
    console = log.StreamHandler()
    console.setLevel(log.INFO)
    formatter = log.Formatter(fmt='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)-8s=> %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    console.setFormatter(formatter)
    log.getLogger('').addHandler(console)


def get_path():
    rootdir = os.getcwd()
    print('rootdir = ' + rootdir)
    for (dirpath, dirnames, filenames) in os.walk(rootdir):
        for dirname in dirnames:
            print('dirname = ' + dirname)
        for filename in filenames:
            # 下面的打印结果类似为：D:\pythonDirDemo\path1\path1-1\path1-1.1.txt
            print(os.path.join(dirpath, filename))
        print('------------------one circle end-------------------')


if __name__ == '__main__':
    dict = {
        'boll':{
                'force_close_minutes': {'ag1801':80},  # 日内平仓时间差
                'force_close_flags': {'ag1801':False},  # 日内平仓标志
                'symbols':{'ag1801':Symbol('ag1801')} # symbol info
            }
    }
    print(schedule_reboot(dict))
