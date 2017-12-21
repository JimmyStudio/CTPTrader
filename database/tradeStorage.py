# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         tradeStorage.py
time:         2017/9/4 下午3:18
description:  交易过程中的数据入库存取

'''

__author__ = 'Jimmy'


import pymongo
from libs.ctp.ctp_struct import *
from bson import json_util as jsonb
from database import base as bs
import pickle as pkl
from utils import tools as tl



# 报单回报 OnRtnOrder
def insertRtnOrder(event):
    db = bs.SharedDatabase.tradeDatabase
    dict = getStrategyInfo(event.dict)
    db.order.insert(dict)


# 报单操作 OnErrRtnOrderAction
def insertErrRtnOrderAction(event):
    db = bs.SharedDatabase.tradeDatabase
    dict = getStrategyInfo(event.dict)
    db.order_action.insert(dict)


# 输入报单操作 OnRspOrderAction
def insertRspOrderAction(event):
    db = bs.SharedDatabase.tradeDatabase
    dict = getStrategyInfo(event.dict)
    db.input_order_action.insert(dict)


# 报单录入 OnRspOrderInsert OnErrRtnOrderInsert
def insertRspOrderInsert(event):
    db = bs.SharedDatabase.tradeDatabase
    dict = getStrategyInfo(event.dict)
    db.input_order.insert(dict)


# 交易回报 OnRtnTrade
def insertRtnTrade(event):
    db = bs.SharedDatabase.tradeDatabase
    trade = event.dict.__dict__
    dict = getStrategyInfo(trade)
    db.trade.insert(dict)

# 请求错误
def insertRspError(event):
    db = bs.SharedDatabase.tradeDatabase
    dict = getStrategyInfo(event.dict)
    db.error_info.insert(dict)
    # db.CThostFtdcRspInfoField.insert(event.dict)


# 保存下单参数
def insertSendOrderArgs(event):
    db = bs.SharedDatabase.tradeDatabase
    event.dict = bs.insertTime(event.dict)
    db.send_order.insert(event.dict)

# 保存撤单参数
def insertCancelOrderArgs(event):
    db = bs.SharedDatabase.tradeDatabase
    event.dict = bs.insertTime(event.dict)
    db.cancel_order.insert(event.dict)



# 更新持仓
def updatePosition(event):
    db = bs.SharedDatabase.tradeDatabase
    dict = bs.insertTime(event.dict)
    if db.position.find({'user_id': dict['user_id'],'broker_id':dict['broker_id'],'trading_day':dict['trading_day']}).count() > 0:
        db.position.update({'user_id': dict['user_id'],'broker_id':dict['broker_id'],'trading_day':dict['trading_day']},{"$set": dict})
    else:
        db.position.insert(dict)


# 更新账户
def updateAccount(event):
    db = bs.SharedDatabase.tradeDatabase
    dict = bs.insertTime(event.dict)
    if db.account.find({'AccountID': dict['AccountID'],'BrokerID':dict['BrokerID'],'TradingDay':dict['TradingDay']}).count() > 0:
        db.account.update({'AccountID': dict['AccountID'],'BrokerID':dict['BrokerID'],'TradingDay':dict['TradingDay']},{"$set": dict})
    else:
        db.account.insert(dict)

# 插入连接、登录、结算日志
def insertLog(event):
    db = bs.SharedDatabase.tradeDatabase
    dict = bs.insertTime(event.dict)
    db.log.insert(dict)

# 获取策略id、name 暂时弃用 2017.09.26
def getStrategyInfo(dict):
    db = bs.SharedDatabase.tradeDatabase
    dict = bs.insertTime(dict)
    # result = list(db.send_order.find({'order_ref':int(dict['OrderRef']),'user_id':dict['InvestorID'],'broker_id':dict['BrokerID']}))
    # if len(result) > 0:
    #     result = result[0]
    #     dict['strategy_name'] = result['strategy_name']
    #     dict['strategy_id'] = result['strategy_id']
    # else:
    #     dict['strategy_name'] = '未知'
    #     dict['strategy_id'] = '未知'
    return dict

# 获取最大报单编号
def getMaxOrderRef(userid, brokerid):
    db = bs.SharedDatabase.tradeDatabase
    result = db.send_order.find({'user_id':userid,'broker_id':brokerid}).sort([('order_ref', -1)]).limit(1)
    try:
        res = result.next()
        return int(res['order_ref'])
    except StopIteration:
        return 0


# 获取最大撤单编号
def getMaxOrderActionRef(userid, brokerid):
    db = bs.SharedDatabase.tradeDatabase
    result = db.cancel_order.find({'InvestorID':userid,'BrokerID':brokerid}).sort([('order_action_ref', -1)]).limit(1)
    try:
        res = result.next()
        return int(res['order_action_ref'])
    except StopIteration:
        return 0


# 保存context
def updateContext(event):
    db = bs.SharedDatabase.tradeDatabase
    ctxs = event.dict
    # contexts 永远只保存正在运行的策略的context
    if len(ctxs) != 0:
        for ctx in ctxs:
            # 如果是日内清仓的 clear = True 删除context
            # 否则更新context
            # if ctx['clear']:
            #     db.contexts.remove({'user_id': ctx['user_id'], 'broker_id': ctx['broker_id'], 'strategy_id':ctx['strategy_id'], 'strategy_name':ctx['strategy_name']})
            # else:
            ctx = bs.insertTime(ctx)
            if db.contexts.find(
                    {'user_id': ctx['user_id'], 'broker_id': ctx['broker_id'], 'strategy_id': ctx['strategy_id'],
                     'strategy_name': ctx['strategy_name']}).count() > 0:
                db.contexts.update(
                    {'user_id': ctx['user_id'], 'broker_id': ctx['broker_id'], 'strategy_id': ctx['strategy_id'],
                     'strategy_name': ctx['strategy_name']}, {"$set": ctx})
            else:
                db.contexts.insert(ctx)


# 获取context
def getConext(userid, brokerid, strategy_id, strategy_name):
    db = bs.SharedDatabase.tradeDatabase
    result = db.contexts.find({'user_id': userid, 'broker_id': brokerid, 'strategy_id':strategy_id, 'strategy_name':strategy_name}).limit(1)
    try:
        res = result.next()['context']
        ctx = pkl.loads(res)
        return ctx
    except StopIteration:
        return None



# 获取合约属性future_info
def get_future_info(symbol):
    db = bs.SharedDatabase.futuresDatabase
    instrument_code = tl.symbol_to_code(symbol)
    result = db.future_info.find({'instrument_code': instrument_code})
    try:
        res = result.next()
        return res
    except StopIteration:
        return None

def adjust_context():
    db = bs.SharedDatabase.tradeDatabase
    result = db.contexts.find(
        {'user_id': '00305188', 'broker_id': '6000', 'strategy_id': 'boll_00305188', 'strategy_name': '布林策略'}).limit(1)
    res = result.next()['context']
    ctx = pkl.loads(res)

    ctx.portfolio.static_total_value = 101126
    ctx.portfolio.daily_pnl = 28.6
    ctx.portfolio.daily_commission = 28.6

    serialize_ctx = pkl.dumps(ctx)
    dict = {
        'context': serialize_ctx,
        'user_id': ctx.user_id,
        'broker_id': ctx.broker_id,
        'strategy_id': ctx.strategy_id,
        'strategy_name': ctx.strategy_name,
    }
    print(dict)

    ctxs = [dict]
    if len(ctxs) != 0:
        for ctx in ctxs:
            # 如果是日内清仓的 clear = True 删除context
            # 否则更新context
            # if ctx['clear']:
            #     db.contexts.remove({'user_id': ctx['user_id'], 'broker_id': ctx['broker_id'], 'strategy_id':ctx['strategy_id'], 'strategy_name':ctx['strategy_name']})
            # else:
            ctx = bs.insertTime(ctx)
            if db.contexts.find(
                    {'user_id': ctx['user_id'], 'broker_id': ctx['broker_id'], 'strategy_id': ctx['strategy_id'],
                     'strategy_name': ctx['strategy_name']}).count() > 0:
                db.contexts.update(
                    {'user_id': ctx['user_id'], 'broker_id': ctx['broker_id'], 'strategy_id': ctx['strategy_id'],
                     'strategy_name': ctx['strategy_name']}, {"$set": ctx})
            else:
                db.contexts.insert(ctx)



if __name__ == '__main__':
    adjust_context()