# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         base.py
time:         2017/9/25 下午3:29
description:  

'''

__author__ = 'Jimmy'
import pymongo
from utils import tools as tl
import datetime as dt


# host_ip = '192.168.1.10'
host_ip = '127.0.0.1'

class SharedDatabase(object):
    tradeDatabase = pymongo.MongoClient(host=host_ip, port=27017).trade
    futuresDatabase = pymongo.MongoClient(host=host_ip, port=27017).futures
    # testDatabase = pymongo.MongoClient(host=host_ip, port=27017).test


# 插入时间
def insertTime(dict):
    date = tl.getTime()
    dict['insert_date'] = date[0]
    dict['insert_time'] = date[1]
    dict['insert_msec'] = date[2]
    return dict

def getTradingDay():
    today = dt.date.today()
    yesterday = today - dt.timedelta(days=1)
    # trade_date 日期为整数: 20170926
    td = _get_trading_day(int(''.join(str(today).split('-'))))
    yd = _get_trading_day(int(''.join(str(yesterday).split('-'))))

    return {
        'today':td,
        'yesterday':yd
    }


def _get_trading_day(day):
    db = SharedDatabase.futuresDatabase
    result = db.trade_date.find({'cur_trade_date': day})
    try:
        res = result.next()
        return res
    except StopIteration:
        return ''


def copy_db(collection_name):
    db1 = pymongo.MongoClient(host='116.226.243.99', port=27017).futures
    db2 = SharedDatabase.futuresDatabase
    result = db1[collection_name].find()
    while True:
        try:
            res = result.next()
            db2[collection_name].insert(res)
        except StopIteration:
            break

def insert_trade_date(lst):
    db = SharedDatabase.futuresDatabase
    db.trade_date.insert(lst)

# 查询数据收集器日志
def check_collector(date):
    db = pymongo.MongoClient(host='192.168.1.10', port=27017).trade
    res = db.log.find({'type':'log', 'engine':'collector', 'insert_date':date})
    while True:
        try:
            print(res.next())
        except StopIteration:
            break
    res = db.rb_price.find({'InstrumentID':'rb1805','TradingDay':20171221},['InstrumentID', 'UpdateTime','TradingDay','LastPrice','insert_date','insert_time']).sort([('insert_time', -1)]).limit(1)
    print(next(res))

# 清除某个账户某个策略的log
def clear_log(user_id, strategy_id=''):
    db = SharedDatabase.tradeDatabase
    if strategy_id:
        db.log.remove({'user_id': user_id, 'strategy_id': strategy_id})
        db.trade.remove({'user_id': user_id, 'strategy_id': strategy_id})
        db.send_order.remove({'user_id': user_id, 'strategy_id': strategy_id})
        db.cancel_order.remove({'user_id': user_id, 'strategy_id': strategy_id})
        db.order.remove({'InvestorID': user_id, 'strategy_id': strategy_id})
        db.order_action.remove({'InvestorID': user_id, 'strategy_id': strategy_id})
        db.contexts.remove({'user_id': user_id, 'strategy_id': strategy_id})
    else:
        db.log.remove({'user_id': user_id})
        db.trade.remove({'user_id': user_id})
        db.send_order.remove({'user_id': user_id})
        db.cancel_order.remove({'user_id': user_id})
        db.order.remove({'InvestorID': user_id})
        db.order_action.remove({'InvestorID': user_id})
        db.contexts.remove({'user_id': user_id})

def check_trade(user_id, strategy_id):
    db = SharedDatabase.tradeDatabase
    result = db.trade.find({'user_id':user_id, 'strategy_id':strategy_id})
    pnl = 0
    or_pnl = 0
    while True:
        try:
            res = result.next()
            print(res)
            pnl += res['pnl']
            or_pnl += res['original_pnl']
        except StopIteration:
            break
    print(pnl)
    print(or_pnl)


def check_log(insert_date):
    db = pymongo.MongoClient(host='192.168.1.10', port=27017).trade
    res = db.log.find({'type': 'log', 'insert_date': insert_date})
    while True:
        try:
            print(res.next())
        except StopIteration:
            break


if __name__ == '__main__':
    pass










