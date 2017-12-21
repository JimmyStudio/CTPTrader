# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         collectorStorage.py
time:         2017/9/25 下午3:27
description:  # tick收集过程中的数据存取

'''

__author__ = 'Jimmy'
from database import base as bs
from datetime import datetime as dt
from utils import tools as tl

# tick 插库
def insertTick(tick):
    db = bs.SharedDatabase.futuresDatabase
    # db = bs.SharedDatabase.testDatabase
    tk = bs.insertTime(tick)
    collection_name = tl.symbol_classify(tk['InstrumentID'])
    db[collection_name].insert(tk)


# 获取当日所有symbol
def getAllSymbols(trading_day):
    # db = bs.SharedDatabase.testDatabase
    db = bs.SharedDatabase.futuresDatabase
    result = db.symbols.find({'trading_day':trading_day},['InstrumentID'])
    universe = []
    while True:
        try:
            symbol = result.next()
            universe.append(symbol['InstrumentID'])
        except StopIteration:
            break
    return universe


# 插入当日所有可用合约信息
def insertAllSymbolOfTradingDay(lst):
    db = bs.SharedDatabase.futuresDatabase
    # db = bs.SharedDatabase.testDatabase
    if len(lst) > 0:
        # 去重 防止手动误操作出现重复
        db.symbols.remove({'trading_day':lst[0]['trading_day']})
        db.symbols.insert(lst)


def clearFutureData(day):
    lst = getAllSymbols(day)
    for symbol in lst:
        db = bs.SharedDatabase.futuresDatabase
        collection_name = tl.symbol_classify(symbol)
        print(collection_name)
        db[collection_name].remove({'TradingDay':day})


if __name__ == '__main__':
    clearFutureData(20171010)




