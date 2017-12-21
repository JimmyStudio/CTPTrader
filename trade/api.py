# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         api.py
time:         2017/8/28 下午2:03
description: 

'''

__author__ = 'Jimmy'

import threading
from copy import deepcopy

import numpy as np
import pandas as pd

from database.tradeStorage import *
from engine.eventEngine import *
from engine.eventType import *
from libs.ctp.quote import Quote
from libs.ctp.trade import Trade
from server.handlers.sender import *
from utils.objects import *
from datetime import datetime
from database import collectorStorage as cs
from utils import ta as ta
import time as tm
from trade.order import *
from utils import tools as tl


class MApi:
    '''
    行情API的封装后所有数据自动推送到事件驱动引擎中，由其负责推送到各个监听该事件的回调函数上
    '''
    def __init__(self, eventEngine, context):
        self._eventEngine = eventEngine
        self._context = context

        # Quote继承CTP的CThostFtdcMdApi
        self._quote = Quote()
        # 请求编号
        self._reqid = 0
        # 默认用户名密码
        self._userid = self._context.user_id
        self._password = self._context.password
        self._brokerid = self._context.broker_id

        #注册事件
        self._eventEngine.register(EVENT_ON_TICK, ws_on_tick)                           # 收到tick

        self._eventEngine.register(EVENT_ON_MARKET_CONNECTED, ws_market_connected)      # 行情服务连接上 ws推送
        self._eventEngine.register(EVENT_ON_MARKET_CONNECTED, insertLog)                # 行情服务连接上 保存日志

        self._eventEngine.register(EVENT_ON_MARKET_DISCONNECTED, insertLog)             # 行情服务连接失败 保存日志

        self._eventEngine.register(EVENT_ON_MARKET_LOGIN, ws_market_login)              # 行情服务登录  ws 推送
        self._eventEngine.register(EVENT_ON_MARKET_LOGIN, insertLog)                    # 行情服务登录  保存日志

        self._eventEngine.register(EVENT_ON_SUBMARKETDATA, insertLog)                   # 订阅行情成功


    def login(self):
        userMApi = self._quote.CreateApi()
        userSApi = self._quote.CreateSpi()
        self._quote.RegisterSpi(userSApi)
        # 连接行情服务器回调
        self._quote.OnFrontConnected = self.onFrontConnected
        self._quote.OnFrontDisconnected = self.onFrontDisconnected
        # 登录回调
        self._quote.OnRspUserLogin = self.onRspUserLogin
        # 订阅行情
        self._quote.OnRspSubMarketData = self.OnRspSubMarketData
        # 订阅数据
        self._quote.OnRtnDepthMarketData = self.onRtnDepthMarketData

        self._quote.RegCB()
        self._quote.RegisterFront(self._context.market_front)
        self._quote.Init()

    def logout(self):
        self._quote.Release()


    def onFrontConnected(self):
        print('时间:%s 行情服务器连接成功' % datetime.now())

        event = Event(EVENT_ON_MARKET_CONNECTED)
        event.dict = {
            'message':'行情服务器连接成功',
            'type':'success',
            'user_id':self._userid,
            'borker_id':self._brokerid,
            'strategy_id': self._context.strategy_id,
            'strategy_name': self._context.strategy_name
        }
        event.sync_flag = False
        self._eventEngine.sendEvent(event)

        # 登录
        self._quote.ReqUserLogin(BrokerID=self._brokerid, UserID=self._userid,UserProductInfo=self._context.user_product_info)


    def onFrontDisconnected(self, nReason):
        print('时间:%s 行情服务器连接失败, 原因：%d' % (datetime.now(), nReason))

        event = Event(EVENT_ON_MARKET_DISCONNECTED)
        event.dict ={
                'message': '行情服务器连接失败',
                'type': 'failure',
                'data':nReason,
                'user_id': self._userid,
                'borker_id': self._brokerid,
                'strategy_id': self._context.strategy_id,
                'strategy_name': self._context.strategy_name
            }
        event.sync_flag = False
        self._eventEngine.sendEvent(event)


    def onRspUserLogin(self, loginField, rspInfo, reqid, isLast):
        if rspInfo.ErrorID == 0:
            print('时间:%s 行情服务器登录成功' % datetime.now())

            event = Event(EVENT_ON_MARKET_LOGIN)
            event.dict = {
                    'message': '行情服务器登录成功',
                    'type': 'success',
                    'data': loginField.__dict__,
                    'user_id': self._userid,
                    'borker_id': self._brokerid,
                    'strategy_id': self._context.strategy_id,
                    'strategy_name': self._context.strategy_name
                }
            event.sync_flag = False
            self._eventEngine.sendEvent(event)

            universe = self._context.universe
            for symbol in universe:
                self.subscribe(symbol)
        else:
            print('时间:%s 行情服务器登录失败[%d]' %(datetime.now(), self._reqid))

            event = Event(EVENT_ON_MARKET_LOGIN)
            event.dict ={
                    'message': '行情服务器登录失败',
                    'type': 'failure',
                    'data': rspInfo.__dict__,
                    'user_id': self._userid,
                    'borker_id': self._brokerid,
                    'strategy_id':self._context.strategy_id,
                    'strategy_name':self._context.strategy_name
                }
            event.sync_flag = False
            self._eventEngine.sendEvent(event)

            self._reqid += 1
            self._quote.ReqUserLogin(BrokerID=self._brokerid, UserID=self._userid, UserProductInfo=self._context.user_product_info)

        # print('Rsp行情登录回报：[data] : %s [rsqinfo] : %s [isLast] : %s'% (loginField, rspInfo, isLast))


    def OnRspSubMarketData(self, data, info, n, last):

        event = Event(EVENT_ON_SUBMARKETDATA)

        if info.ErrorID == 0:
            # print('时间:%s ==Rsp订阅行情合约成功==' % datetime.now())

            event.dict ={
                    'message': '订阅行情合约成功',
                    'type': 'success',
                    'data': data.__dict__,
                    'user_id': self._userid,
                    'borker_id': self._brokerid,
                    'strategy_id': self._context.strategy_id,
                    'strategy_name': self._context.strategy_name
                }

        else:
            event.dict ={
                    'message': '订阅行情合约失败',
                    'type': 'failure',
                    'data': info.__dict__,
                    'user_id': self._userid,
                    'borker_id': self._brokerid,
                    'strategy_id': self._context.strategy_id,
                    'strategy_name': self._context.strategy_name
                }

        event.sync_flag = False
        self._eventEngine.sendEvent(event)


    def onRtnDepthMarketData(self, data):
        """行情推送"""
        # print('Rtn订阅行情合约推送: %s' %data)
        # tick数据有可能残缺  原因不明
        if data.__dict__['TradingDay'] != '':
            symbol = data.__dict__['InstrumentID']
            if not self._context.collector_flag:
                # 量 转 手均为0的tick是开盘的集合竞价tick 包含了结算价和开盘价(开盘价按集合竞价在不断变化）
                if data.__dict__['Volume'] == 0 and data.__dict__['Turnover'] == 0:
                    self._context.settlement_infos[symbol] = {'pre_settlement_price': data.__dict__['PreSettlementPrice'],'update_time':data.__dict__['UpdateTime']}

            # tick updatetime 与系统时间 ±5分钟 才就行插库, 否则舍弃
            if tl.tick_filter(data.__dict__):
                # 如果是数据收集器 始终发送tick 事件
                if self._context.collector_flag:
                    event = Event(EVENT_ON_TICK)
                    event.dict = data.__dict__
                    event.sync_flag = False
                    self._eventEngine.sendEvent(event)
                else:
                    # 如果策略接收tick则发送tick事件
                    if self._context.receive_tick_flag:
                        event = Event(EVENT_ON_TICK)
                        event.dict = data.__dict__
                        event.sync_flag = False
                        self._eventEngine.sendEvent(event)
                    # 如果策略接收bar 则发送bar 事件
                    if self._context.receive_bar_flag:
                        # 按 合约名 获取对应的 tick_conver
                        tick_conver = self._context.tick_convers[symbol]
                        bar = tick_conver.tick_to_bar(data.__dict__)
                        # bar = self._context.tick_conver.tick_to_bar(data.__dict__)
                        if bar is not None:
                            event = Event(EVENT_ON_BAR)
                            event.dict = bar
                            event.sync_flag = False
                            self._eventEngine.sendEvent(event)

    #----------------------------------------------------
    # 行情主动函数
    #----------------------------------------------------
    def subscribe(self, instrumentid):
        """订阅合约"""
        self._quote.SubscribeMarketData(pInstrumentID=instrumentid)

    def unSubscribe(self, instrumentid):
        """退订合约"""
        self._quote.UnSubscribeMarketData(pInstrumentID=instrumentid)


class TApi:
    '''
    封装交易服务器Api
    '''
    def __init__(self, eventEngine, context):
        self._eventEngine = eventEngine
        self._context = context
        self._trade = Trade()
        self._lock = threading.Lock()

        self.positions = [] # 查持仓
        self._instruments = [] # 查合约信息

        # 默认用户名密码
        self._userid = self._context.user_id
        self._password = self._context.password
        self._brokerid = self._context.broker_id

        # 请求编号
        self._reqid = 0
        # 报单编号，由api负责管理
        self._orderRef = getMaxOrderRef(self._userid,self._brokerid)
        # 前置id FrontID
        self._frontID = 0
        # 会话id
        self._sessionID = 0
        # ReqOrderAction 报单操作ref
        self._order_action_ref = getMaxOrderActionRef(self._userid,self._brokerid)


        # 注册交易handler
        # 主动
        self._eventEngine.register(EVENT_ORDER, self.sendOrder)                 # 下单
        self._eventEngine.register(EVENT_ORDER_STORAGE, insertSendOrderArgs)    # 保存下单参数
        self._eventEngine.register(EVENT_ORDER_STORAGE, ws_send_order)          # 推送下单参数
        self._eventEngine.register(EVENT_CANCEL, self.cancelOrder)              # 撤单
        self._eventEngine.register(EVENT_CANCEL_STORAGE, insertCancelOrderArgs) # 保存撤单参数
        self._eventEngine.register(EVENT_CANCEL_STORAGE, ws_cancel_order)       # 推送撤单参数

        # 每隔1秒查询持仓/账户
        # self._eventEngine.registerSwicthHandlers([self.getPosition,self.getAccount])      # 推送撤单参数


        # 被动
        self._eventEngine.register(EVENT_ON_TRADE_CONNECTED, ws_market_connected)       # 交易服务器连接上 ws推送
        self._eventEngine.register(EVENT_ON_TRADE_CONNECTED, insertLog)                 # 交易服务器连接上 log

        self._eventEngine.register(EVENT_ON_TRADE_DISCONNECTED, insertLog)              # 交易服务器连接上失败 log

        self._eventEngine.register(EVENT_ON_TRADE_LOGIN, ws_market_login)               # 交易服务器登录  ws
        self._eventEngine.register(EVENT_ON_TRADE_LOGIN, insertLog)                     # 交易服务器登录 log

        self._eventEngine.register(EVENT_ON_SETTLEMENT_CONFIRM, ws_settlement_confirm)  # 结算单确认完成 ws
        self._eventEngine.register(EVENT_ON_SETTLEMENT_CONFIRM, insertLog)              # 结算单确认完成 log

        self._eventEngine.register(EVENT_ON_ORDER, insertRtnOrder)                      # 报单回报
        self._eventEngine.register(EVENT_ON_ORDER, ws_on_order)                         # 报单回报
        # self._eventEngine.register(EVENT_ON_ORDER, self.getAccount)                     # 报单回报后查询账户资金

        self._eventEngine.register(EVENT_ON_INPUT_ORDER, insertRspOrderInsert)          # 报单录入
        self._eventEngine.register(EVENT_ON_INPUT_ORDER, ws_insert_order)               # 报单录入

        self._eventEngine.register(EVENT_ON_INPUT_ORDER_ACTION, insertRspOrderAction)   # 输入报单
        self._eventEngine.register(EVENT_ON_INPUT_ORDER_ACTION, ws_insert_order_action) # 输入报单

        self._eventEngine.register(EVENT_ON_ORDER_ACTION, insertErrRtnOrderAction)      # 报单操作
        self._eventEngine.register(EVENT_ON_ORDER_ACTION, ws_error_order_action)        # 报单操作

        # self._eventEngine.register(EVENT_ON_TRADE, insertRtnTrade)                      # 交易回报
        self._eventEngine.register(EVENT_ON_TRADE, ws_trade)                            # 交易回报
        # self._eventEngine.register(EVENT_ON_TRADE, self.getPosition)                    # 交易回报后查询持仓

        # 错误
        self._eventEngine.register(EVENT_ERROR, insertRspError)                         # 请求错误
        self._eventEngine.register(EVENT_ERROR, ws_rsp_error)                           # 请求错误

        # 更新账户&持仓
        self._eventEngine.register(EVENT_ON_ACCOUNT, updateAccount)                      # 更新账户
        self._eventEngine.register(EVENT_ON_POSITION, updatePosition)                    # 更新持仓





    def login(self):
        userTApi = self._trade.CreateApi()
        userSApi = self._trade.CreateSpi()
        self._trade.RegisterSpi(userSApi)
        # 连接交易服务器回调
        self._trade.OnFrontConnected = self.onFrontConnected
        self._trade.OnFrontDisconnected = self.onFrontDisconnected
        # 登录回调
        self._trade.OnRspUserLogin = self.onRspUserLogin
        #
        self._trade.OnRtnInstrumentStatus = self.onRtnInstrumentStatus
        # 结算单确认
        self._trade.OnRspSettlementInfoConfirm = self.onRspSettlementInfoConfirm
        # 查询全部交易合约
        self._trade.OnRspQryInstrument = self.onRspQryInstrument
        # tick截面数据
        self._trade.OnRspQryDepthMarketData = self.onRspQryDepthMarketData
        # 查询持仓
        self._trade.OnRspQryInvestorPosition = self.onRspQryInvestorPosition
        # 查询账户
        self._trade.OnRspQryTradingAccount = self.onRspQryTradingAccount
        # 报单录入
        self._trade.OnRspOrderInsert = self.onRspOrderInsert
        # 报单状态变化
        self._trade.OnRspOrderAction = self.onRspOrderAction
        # 报单状态改变
        self._trade.OnRtnOrder = self.onRtnOrder
        # 报单发生成交
        self._trade.OnRtnTrade = self.onRtnTrade
        # 报单录入错误
        self._trade.OnErrRtnOrderInsert = self.onErrRtnOrderInsert
        # 报价操作错误回报。由交易托管系统主动通知客户端，该方法会被调用。
        self._trade.OnErrRtnOrderAction = self.onErrRtnOrderAction
        # 请求错误
        self._trade.OnRspError = self.onRspError
        # 查询报单
        self._trade.OnRspQryOrder = self.onRspQryOrder


        self._trade.RegCB()
        self._trade.RegisterFront(self._context.trade_front)
        self._trade.SubscribePublicTopic(nResumeType=2)  # 只传送登录后公有流的内容
        self._trade.SubscribePrivateTopic(nResumeType=2)  # 只传送登录后私有流的内容
        self._trade.Init()

    def logout(self):
        self._trade.Release()


    def onFrontConnected(self):
        print('时间:%s 交易服务器连接成功' % datetime.now())

        event = Event(EVENT_ON_TRADE_CONNECTED)
        event.dict = {
                'message': '交易服务器连接成功',
                'type': 'success',
                'user_id': self._userid,
                'borker_id': self._brokerid,
                'strategy_id': self._context.strategy_id,
                'strategy_name': self._context.strategy_name
            }
        event.sync_flag = False
        self._eventEngine.sendEvent(event)

        self._reqid += 1
        self._trade.ReqUserLogin(BrokerID=self._brokerid, UserID=self._userid, Password=self._password,UserProductInfo=self._context.user_product_info)

    def onFrontDisconnected(self, nReason):
        print('时间:%s 交易服务器连接失败, 原因：%d' % (datetime.now(), nReason))

        event = Event(EVENT_ON_TRADE_DISCONNECTED)
        event.dict = {
                'message': '交易服务器连接失败',
                'type': 'failure',
                'data': nReason,
                'user_id': self._userid,
                'borker_id': self._brokerid,
                'strategy_id': self._context.strategy_id,
                'strategy_name': self._context.strategy_name
            }
        event.sync_flag = False
        self._eventEngine.sendEvent(event)

    def onRspUserLogin(self, loginField, rspInfo, reqid, isLast):
        """登陆回报"""
        if rspInfo.ErrorID == 0:
            print('时间:%s 交易服务器登陆成功' % datetime.now())

            event = Event(EVENT_ON_TRADE_LOGIN)
            event.dict ={
                    'message': '交易服务器登陆成功',
                    'type': 'success',
                    'data': loginField.__dict__,
                    'user_id': self._userid,
                    'borker_id': self._brokerid,
                    'strategy_id': self._context.strategy_id,
                    'strategy_name': self._context.strategy_name
                }
            event.sync_flag = False
            self._eventEngine.sendEvent(event)

            self._frontID = loginField.FrontID
            self._sessionID = loginField.SessionID

            # 如果需要确认结算单
            if self._context.settlementInfo_confirm_flag == False:
                self._reqid += 1
                self._trade.ReqSettlementInfoConfirm(BrokerID=self._brokerid, InvestorID=self._userid)  # 对账单确认
                # self.getOrder()
        else:
            print('时间:%s 交易服务器登录失败 %d' %(datetime.now(), self._reqid))

            event = Event(EVENT_ON_TRADE_LOGIN)
            event.dict = {
                    'message': '交易服务器登录失败',
                    'type': 'failure',
                    'data': rspInfo.__dict__,
                    'user_id': self._userid,
                    'borker_id': self._brokerid,
                    'strategy_id': self._context.strategy_id,
                    'strategy_name': self._context.strategy_name
                }
            event.sync_flag = False
            self._eventEngine.sendEvent(event)

            self._reqid += 1
            self._trade.ReqUserLogin(BrokerID=self._brokerid, UserID=self._userid, Password=self._password)

        # print('Rsp交易登录回报：[data]=%s [rsqinfo] = %s [reqid] = %s [isLast] = %s'% (loginField, rspInfo, reqid,isLast))


    def onRtnInstrumentStatus(self, data):
        pass
        # print('Rtn合约状态：%s '% data.__dict__) # 交易所关闭前会返回数据


    def onRspSettlementInfoConfirm(self, settlementInfoConfirmField, rspInfo, reqid, isLast):
        if rspInfo.ErrorID == 0:
            print('时间:%s Rsp结算单确认完成：%s' % (datetime.now(), settlementInfoConfirmField.__dict__))
            # 结算确认后开始查询合约资料 或者 登录行情服务器
            self._context.settlementInfo_confirm_flag = True

            event = Event(EVENT_ON_SETTLEMENT_CONFIRM)
            event.dict ={
                    'message': '结算单确认成功',
                    'type': 'success',
                    'data': settlementInfoConfirmField.__dict__,
                    'user_id': self._userid,
                    'borker_id': self._brokerid,
                    'strategy_id': self._context.strategy_id,
                    'strategy_name': self._context.strategy_name
                }
            event.sync_flag = False
            self._eventEngine.sendEvent(event)

            # 如果是数据收集器，就查询全部合约资料
            if self._context.collector_flag :
                self.getInstrument()

            # 查询资金
            self.getAccount('')

        else:
            # print('时间:%s Rsp结算单确认错误 %s' % (datetime.now(), rspInfo.__dict__))

            event = Event(EVENT_ON_SETTLEMENT_CONFIRM)
            event.dict ={
                    'message': '结算单确认失败',
                    'type': 'failure',
                    'data': rspInfo.__dict__,
                    'user_id': self._userid,
                    'borker_id': self._brokerid,
                    'strategy_id': self._context.strategy_id,
                    'strategy_name': self._context.strategy_name
                }
            event.sync_flag = False
            self._eventEngine.sendEvent(event)

            self._reqid += 1
            self._trade.ReqSettlementInfoConfirm(BrokerID=self._brokerid, InvestorID=self._userid)  # 对账单确认


    def onRspQryInstrument(self, data, error, n, islast):
        """
        合约查询回报
        """
        if error.ErrorID == 0:
            # print(data.InstrumentID)
            # print(data.ProductClass)
            # print(data.CombinationType)
            # 只保存独立的期货合约
            if data.ProductClass == b'1' and data.CombinationType == b'0':
                # print('时间:%s RspQry查询所有合约成功: %s' %(datetime.now(), data.__dict__))
                dict = deepcopy(data.__dict__)
                dict['trading_day'] = self._context.trading_day
                self._instruments.append(dict)
            if islast == True:
                # print('时间:%s ---查询所有合约完毕---' % datetime.now())
                cs.insertAllSymbolOfTradingDay(self._instruments)
                self._context.finish_qry_instrument_flag = True
                self._instruments = []
                # print('时间:%s ---所有合约插库完毕---' % datetime.now())


    def onRspQryDepthMarketData(self, data, error, n, last):
        # tick数据回报
        pass
        # print('RspQry交易tick数据: [%s] [%s]'% (data.__dict__, error))


    def onRspQryInvestorPosition(self, data, error, n, last):
        """持仓查询回报"""
        # print('RspQry查询持仓回报: [%s] [%s] [%s]'% (data.__dict__, error,last))
        if error.ErrorID == 0:
            if last == True:
                self.positions.append(data.__dict__)
                dict = {
                    'broker_id': self._brokerid,
                    'user_id': self._userid,
                    'position': self.positions,
                    'trading_day':self._context.trading_day
                }
                event = Event(EVENT_ON_POSITION)
                event.dict = dict
                event.sync_flag = False
                self._eventEngine.sendEvent(event)
                self.positions = []
            else:
                self.positions.append(data.__dict__)


    # ----------------------------------------------------------------------
    def onRspQryTradingAccount(self, data, error, n, last):
        """资金账户查询回报"""
        # if error.ErrorID == 0:
        # print('RspQry查询账户资金回报: [%s] [%s]'% (data.__dict__, error))
        if error.ErrorID == 0:
            event = Event(EVENT_ON_ACCOUNT)
            dict = deepcopy(data.__dict__)
            dict['trading_day'] = self._context.trading_day
            event.dict = dict
            event.sync_flag = False
            self._eventEngine.sendEvent(event)
            # 查询资金后查询持仓
            self.getPosition('')


    def onRtnTrade(self, data):
        """
        成交回报。
        当发生成交时交易托管系统会通知客户端，该方法会被调用。 
        """
        # print('时间:%s Rtn成交回报: 买卖:%s 开平:%s 价:%s 量:%s orderRef:%s orderSysID:%s' %(datetime.now(), data.__dict__['Direction'], data.__dict__['OffsetFlag'], data.__dict__['Price'], data.__dict__['Volume'], data.__dict__['OrderRef'], data.__dict__['OrderSysID']))

        # onTrade的data.TradingRole 可能为空格b' '  => space
        trade = TradeInfo(symbol=data.getInstrumentID(),
                          direction=data.getDirection().name,
                          offset=data.getOffsetFlag().name,
                          vol=data.getVolume(),
                          price=data.getPrice(),
                          user_id=data.getUserID(),
                          broker_id=data.getBrokerID(),
                          sys_id=data.getOrderSysID(),
                          strategy_id=self._context.strategy_id,
                          strategy_name=self._context.strategy_id,
                          exchange_id=data.getExchangeID(),
                          trade_id=data.getTradeID(),
                          trade_date=data.getTradeDate(),
                          trade_time=data.getTradeTime(),
                          trading_day=int(data.getTradingDay()),
                          )
        event = Event(EVENT_ON_TRADE)
        event.dict = trade
        event.sync_flag = False
        self._eventEngine.sendEvent(event)

    def onRtnOrder(self, data):
        """
        报单回报.
        当客户端进行报单录入、报单操作及其它原因(如部分成交)导致报单状态发生变化时，交易托管系统会主动通知客户端，该方法会被调用。
        """
        # 更新最大报单编号
        # newref = data.OrderRef
        # self.__orderRef = max(self._orderRef, int(newref))

        # print('时间:%s Rtn报单回报: 买卖:%s 开平:%s 价:%s 量:%s orderRef:%s orderSysID:%s' %(datetime.now(), data.__dict__['Direction'], data.__dict__['CombOffsetFlag'], data.__dict__['LimitPrice'], data.__dict__['VolumeTotalOriginal'], data.__dict__['OrderRef'], data.__dict__['OrderSysID']))

        dict = deepcopy(data.__dict__)
        dict['strategy_id'] = self._context.strategy_id
        dict['strategy_name'] = self._context.strategy_name

        # EnumOrderStatusType
        # {
        #   AllTraded = 48, // 全部成交。                                                         --->最终状态
        #   PartTradedQueueing = 49, // 部分成交，且还在队列中。说明，部分成交，部分在等待成交。
        #   PartTradedNotQueueing = 50, // 部分成交，不在队列中，说明：部成部撤。                    --->最终状态。
        #   NoTradeQueueing = 51, // 未成交，在交易队列中。说明：报单在市场中，但没有成交
        #   NoTradeNotQueueing = 52, // 没有交易且不在队列中，说明：报单被CTP拒绝。                   --->最终状态
        #   Canceled = 53, // 报单被取消                                                          --->最终状态
        #   Unknown = 97, // 未知。说明：报单已经被CTP接收，但还没发往交易所。
        #   NotTouched = 98, // 预埋单未触发
        #   Touched = 99, // 预埋单已触发
        # }

        # 更新环境中的挂单
        if data.__dict__['OrderSysID'] is not '':

            order = Order(symbol=data.__dict__['InstrumentID'],
                          direction=data.__dict__['Direction'],
                          offset=data.__dict__['CombOffsetFlag'],
                          vol_total_original=data.__dict__['VolumeTotalOriginal'],
                          vol_left=data.__dict__['VolumeTotal'],
                          vol_traded=data.__dict__['VolumeTraded'],
                          price_type=data.__dict__['OrderPriceType'],
                          limit_price=data.__dict__['LimitPrice'],
                          stop_price=data.__dict__['StopPrice'],
                          contingent_condition=data.__dict__['ContingentCondition'],
                          user_id=data.__dict__['UserID'],
                          broker_id=data.__dict__['BrokerID'],
                          sys_id=data.__dict__['OrderSysID'],
                          status=data.__dict__['OrderStatus'],
                          strategy_id=dict['strategy_id'],
                          strategy_name=dict['strategy_name'],
                          order_ref=data.__dict__['OrderRef'],
                          front_id=data.__dict__['FrontID'],
                          session_id=data.__dict__['SessionID'],
                          exchange_id=data.__dict__['ExchangeID'],
                          msg=data.__dict__['StatusMsg']
                          )

            # if data.__dict__['OrderStatus'] == 'AllTraded' or data.__dict__['OrderStatus'] == 'Canceled' or data.__dict__['OrderStatus'] == 'PartTradedNotQueueing' or data.__dict__['OrderStatus'] == 'NoTradeNotQueueing':
            #     del (self._context.orders[data.__dict__['OrderSysID']])
            # else:
            #     self._context.orders[data.__dict__['OrderSysID']] = order

            event = Event(EVENT_ON_ORDER_CHANGE)
            event.dict = order
            event.sync_flag = False
            self._eventEngine.sendEvent(event)



            # for k,v in self._context.orders.items():
            #     print('时间:%s Rtn当前挂单: 买卖:%s 开平:%s 价:%s 量:%s orderRef:%s orderSysID:%s' %(datetime.now(), v['Direction'], v['CombOffsetFlag'],v['LimitPrice'],v['VolumeTotalOriginal'],v['OrderRef'],v['OrderSysID']))


        event = Event(EVENT_ON_ORDER)
        event.dict = dict
        event.sync_flag = False
        self._eventEngine.sendEvent(event)

    def onRspOrderInsert(self, data, error, n, last):
        """
        报单录入应答。
        当客户端发出过报单录入指令后，交易托管系统返回响应时， 该方法会被调用。
        """
        # print('时间:%s Rsp报单录入回报: 买卖:%s 开平:%s 价:%s 量:%s orderRef:%s' %(datetime.now(), data.__dict__['Direction'], data.__dict__['CombOffsetFlag'], data.__dict__['LimitPrice'], data.__dict__['VolumeTotalOriginal'], data.__dict__['OrderRef']))
        # print(data)
        if error.ErrorID == 0:
            event = Event(EVENT_ON_INPUT_ORDER)
            dict = deepcopy(data.__dict__)
            dict['strategy_id'] = self._context.strategy_id,
            dict['strategy_name'] = self._context.strategy_name
            event.dict = dict
            event.sync_flag = False
            self._eventEngine.sendEvent(event)



    def onRspOrderAction(self, data, error, n, last):
        """
        报单操作应答。
        报单操作包括报单的撤销、报单的挂起、报单的激活、报单 的修改。当客户端发出过报单操作指令后，交易托管系统返回响应时，该方法会 被调用。 
        """
        # print('时间:%s Rsp报单操作/报单状态改变: 价:%s 量:%s orderRef:%s orderSysID:%s' %(datetime.now(), data.__dict__['LimitPrice'], data.__dict__['VolumeChange'], data.__dict__['OrderRef'], data.__dict__['OrderSysID']))
        if error.ErrorID == 0:
            event = Event(EVENT_ON_INPUT_ORDER_ACTION)
            dict = deepcopy(data.__dict__)
            dict['strategy_id'] = self._context.strategy_id,
            dict['strategy_name'] = self._context.strategy_name
            event.dict = dict
            event.sync_flag = False
            self._eventEngine.sendEvent(event)


    def onErrRtnOrderInsert(self, data, error):
        """
        报单录入错误回报。由交易托管系统主动通知客户端，该方法会被调用
        """
        # print('时间:%s Rtn报单录入错误回报: 买卖:%s 开平:%s 价:%s 量:%s orderRef:%s' %(datetime.now(), data.__dict__['Direction'], data.__dict__['CombOffsetFlag'], data.__dict__['LimitPrice'], data.__dict__['VolumeTotalOriginal'], data.__dict__['OrderRef']))
        # print(data)
        if error.ErrorID == 0:
            event = Event(EVENT_ON_INPUT_ORDER)
            dict = deepcopy(data.__dict__)
            dict['strategy_id'] = self._context.strategy_id,
            dict['strategy_name'] = self._context.strategy_name
            event.dict = dict
            event.sync_flag = False
            self._eventEngine.sendEvent(event)


    def onErrRtnOrderAction(self, data, error):
        '''
        报价操作错误回报。
        由交易托管系统主动通知客户端，该方法会被调用。
        '''
        # print('时间:%s Rtn报价操作错误回报: %s' % (datetime.now(), data.__dict__))

        event = Event(EVENT_ON_ORDER_ACTION)
        dict = deepcopy(data.__dict__)
        dict['strategy_id'] = self._context.strategy_id,
        dict['strategy_name'] = self._context.strategy_name
        event.dict = dict
        event.sync_flag = False
        self._eventEngine.sendEvent(event)


    def onRspError(self, error, n, last):
        """
        针对用户请求的出错通知。
        """
        # print('时间:%s Rsp行情请求出错: %s' % (datetime.now(), error.__dict__))

        event = Event(EVENT_ERROR)
        dict = deepcopy(error.__dict__)
        dict['strategy_id'] = self._context.strategy_id,
        dict['strategy_name'] = self._context.strategy_name
        event.dict = dict
        event.sync_flag = False
        self._eventEngine.sendEvent(event)

    def onRspQryOrder(self, data, error, n, last):
        """
        查询Order。
        """
        pass
        # print('时间:%s RspQry查询挂单: %s' %(datetime.now(), data.__dict__))
        # event = Event(EVENT_ERROR)
        # dict = deepcopy(error.__dict__)
        # event.dict = dict
        # event.sync_flag = False
        # self._eventEngine.sendEvent(event)

    #----------------------------------------------------
    # 交易主动函数
    #----------------------------------------------------
    def getInstrument(self):
        """查询全部合约信息"""
        self._reqid += 1
        self._trade.ReqQryInstrument()

    def reqQryDepthMarketData(self, InstrumentID, ExchangeID):
        # 查询合约截面数据
        self._reqid += 1
        self._trade.ReqQryDepthMarketData(InstrumentID=InstrumentID, ExchangeID=ExchangeID)

    # 查询报单
    def getOrder(self):
        self._reqid += 1
        self._trade.ReqQryOrder(BrokerID=self._brokerid, InvestorID = self._userid)


    def getAccount(self, event):
        """查询账户"""
        self._lock.acquire()
        self._reqid += 1
        self._lock.release()
        self._trade.ReqQryTradingAccount(self._brokerid, self._userid)

    def getPosition(self, event):
        """查询持仓"""
        self._lock.acquire()
        self._reqid += 1
        self._lock.release()
        self._trade.ReqQryInvestorPosition(BrokerID=self._brokerid, InvestorID=self._userid)

    def sendOrder(self, event):
        self._lock.acquire()
        self._reqid += 1
        self._orderRef += 1
        self._lock.release()

        order = event.dict
        instrumentid = order.symbol
        vol = order.vol_total_original
        limit_price = order.limit_price
        direction = order.direction_original
        offset = order.offset_original
        priceType = order.price_type_original
        stop_price = order.stop_price
        contingent_condition = order.contingent_condition_original

        # 加入_reqid、_orderRef
        dict = deepcopy(order.__dict__)
        dict['reqid'] = self._reqid
        dict['order_ref'] = self._orderRef
        del dict['offset_original']
        del dict['direction_original']
        del dict['price_type_original']
        del dict['contingent_condition_original']
        _event  = Event(EVENT_ORDER_STORAGE)
        _event.dict = dict
        _event.sync_flag = False
        self._eventEngine.sendEvent(_event)

        # print('时间:%s Req发送报单: 买卖:%s 开平:%s 价:%s 量:%s orderRef:%s' %(datetime.now(), event.dict['direction'], event.dict['offset'], event.dict['limit_price'], event.dict['vol'], event.dict['order_ref']))

        self._trade.ReqOrderInsert(BrokerID=self._brokerid,
                                    InvestorID=self._userid,
                                    InstrumentID=instrumentid,
                                    LimitPrice=limit_price,
                                    OrderRef='{0:>12}'.format(self._orderRef),
                                    UserID=self._userid,
                                    OrderPriceType=priceType,
                                    Direction=direction,
                                    CombOffsetFlag=offset,
                                    CombHedgeFlag=HedgeFlagType.Speculation.__char__(),
                                    VolumeTotalOriginal=vol,
                                    TimeCondition=TimeConditionType.GFD,
                                    VolumeCondition=VolumeConditionType.AV,
                                    MinVolume=1,
                                    ForceCloseReason=ForceCloseReasonType.NotForceClose,
                                    ContingentCondition=contingent_condition,
                                    StopPrice=stop_price)
        return self._orderRef

    def cancelOrder(self, event):
        """撤单"""
        order = event.dict
        self._lock.acquire()
        self._reqid = self._reqid + 1
        self._order_action_ref += 1
        self._lock.release()

        dict = deepcopy(order.__dict__)
        dict['reqid'] = self._reqid
        dict['order_action_ref'] = self._order_action_ref
        del dict['offset_original']
        del dict['direction_original']
        del dict['price_type_original']
        del dict['contingent_condition_original']
        _event = Event(EVENT_CANCEL_STORAGE)
        _event.dict = dict
        _event.sync_flag = False
        self._eventEngine.sendEvent(_event)

        # print('时间:%s Req发送撤单: 买卖:%s 开平:%s 价:%s 量:%s OrderSysID:%s' %(datetime.now(), event.dict['Direction'], event.dict['CombOffsetFlag'], event.dict['LimitPrice'], event.dict['VolumeTotalOriginal'], order['OrderSysID']))

        self._trade.ReqOrderAction(BrokerID=self._brokerid,
                                   OrderActionRef= self._order_action_ref,
                              InvestorID=self._userid,
                              OrderRef=order.order_ref,
                              FrontID=int(order.front_id),
                              SessionID=int(order.session_id),
                              OrderSysID=order.sys_id,
                              ActionFlag=ActionFlagType.Delete,
                              ExchangeID=order.exchange_id,
                              InstrumentID=order.symbol)



