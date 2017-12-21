# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         order.py
time:         2017/10/31 下午2:59
description: 

'''

__author__ = 'Jimmy'
from libs.ctp.ctp_struct import *


LONG = 'long'     # 多 => buy
SHORT = 'short'   # 空 => sell

# 目前仅考虑
# 0-开 通用
# 大连郑州-1-平
# 上海-3-平今 ；4-平昨
OPEN = 'Open'                           # 0 开
CLOSE = 'Close'                         # 1 平
FORECE_CLOSE = 'ForceClose'             # 2
CLOSE_TODAY = 'CloseToday'              # 3 平今
CLOSE_YESTERDAY = 'CloseYesterday'      # 4 平昨
FORECE_OFF = 'ForceOff'                 # 5
LOCAL_FORCE_CLOSE = 'LocalForceClose'   # 6

# order状态
AT = 'AllTraded'                #   AllTraded = 48, // 全部成交。                                                         --->最终状态
PTQ = 'PartTradedQueueing'      #   PartTradedQueueing = 49, // 部分成交，且还在队列中。说明，部分成交，部分在等待成交。
PTNQ = 'PartTradedNotQueueing'  #   PartTradedNotQueueing = 50, // 部分成交，不在队列中，说明：部成部撤。                    --->最终状态。
NTQ = 'NoTradeQueueing'         #   NoTradeQueueing = 51, // 未成交，在交易队列中。说明：报单在市场中，但没有成交
NTNQ = 'NoTradeNotQueueing'     #   NoTradeNotQueueing = 52, // 没有交易且不在队列中，说明：报单被CTP拒绝。                   --->最终状态
CAN = 'Canceled'                #   Canceled = 53, // 报单被取消                                                          --->最终状态
UK = 'Unknown'                  #   Unknown = 97, // 未知。说明：报单已经被CTP接收，但还没发往交易所。
NT = 'NotTouched'               #   NotTouched = 98, // 预埋单未触发
TOU = 'Touched'                 #   Touched = 99, // 预埋单已触发

# 价格类型
LP = 'LimitPrice'
AP = 'AnyPrice'

# 报单触发类型
IMM = 'Immediately'

# order函数参数  => OnOrder ->data.__dict__['key']
# price_type : OrderPriceTypeType.LimitPrice => 'LimitPrice'
# contingent_condition : ContingentConditionType.Immediately => 'Immediately'

class Order(object):
    def __init__(self,
                 symbol='',
                 direction='',
                 offset='',
                 vol_total_original=0,
                 vol_left=0,
                 vol_traded=0,
                 price_type='' ,
                 limit_price=0.0,
                 stop_price=0.0,
                 contingent_condition='',
                 user_id='',
                 broker_id='',
                 strategy_id='',
                 strategy_name='',
                 sys_id='',
                 status='',
                 order_ref='',
                 front_id='',
                 session_id='',
                 exchange_id='',
                 msg='',
                 margin=0.0
                 ):
        self.symbol = symbol
        self.direction = self._conver_to_str(direction) # direction => Long/short
        self.offset = self._conver_offset(offset) # 0,1,2... => open/close
        self.offset_original = offset
        self.price_type = self._conver_to_str(price_type) # OrderPriceTypeType.LimitPrice => Any/Limit
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.contingent_condition = self._conver_to_str(contingent_condition) # 挂单方式 默认立即挂单 ContingentConditionType.Immediately => 'Immediately'
        self.vol_total_original = vol_total_original # 下单总数
        self.user_id = user_id
        self.broker_id = broker_id
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name

        # 交易所OnOrder加入如下属性
        self.msg = msg  # 报单状态信息
        self.vol_left = vol_left  # 剩余数量
        self.vol_traded = vol_traded # 成交数量
        self.sys_id = sys_id  # 交易orderid
        self.status = status  # order状态
        self.order_ref = order_ref # 报单引用编号
        self.front_id = front_id # 前置编号
        self.session_id = session_id # 会话编号
        self.exchange_id = exchange_id # 交易所代码

        # portfolio加入 冻结保证金
        self.margin = margin


        # ctp sell close => 平多  buy close => 平空
        self._conver_direction(self.direction, self.offset)
        # direction/offset/price_type/contingent_condition 转为ctp接口的原始类型已供ctp调用
        self._decode_order()



    def _decode_order(self):
        # direction
        if self.direction == LONG:
            if self.offset == OPEN:
                self.direction_original = DirectionType.Buy
            else:
                self.direction_original = DirectionType.Sell
        else:
            if self.offset == OPEN:
                self.direction_original = DirectionType.Sell
            else:
                self.direction_original = DirectionType.Buy

        # offset
        if self.offset == OPEN:
            self.offset_original = OffsetFlagType.Open.__char__()
        elif self.offset == CLOSE:
            self.offset_original = OffsetFlagType.Close.__char__()
        elif self.offset == FORECE_CLOSE:
            self.offset_original = OffsetFlagType.ForceClose.__char__()
            print('暂未考虑除O/C/CT/CY之外的offset类型 %s' % self.offset)
        elif self.offset == CLOSE_TODAY:
            self.offset_original = OffsetFlagType.CloseToday.__char__()
        elif self.offset == CLOSE_YESTERDAY:
            self.offset_original = OffsetFlagType.CloseYesterday.__char__()
        elif self.offset == FORECE_OFF:
            self.offset_original = OffsetFlagType.ForceOff.__char__()
            print('暂未考虑除O/C/CT/CY之外的offset类型 %s' % self.offset)
        else:
            self.offset_original = OffsetFlagType.LocalForceClose.__char__()
            print('暂未考虑除O/C/CT/CY之外的offset类型 %s' % self.offset)

        # price_type
        if self.price_type == LP:
            self.price_type_original = OrderPriceTypeType.LimitPrice
        elif self.price_type == AP:
            self.price_type_original = OrderPriceTypeType.AnyPrice
        else:
            print('暂未考虑除LimitPrice/AnyPrice之外的报价类型：%s' % self.price_type)

        # contingent_condition
        if self.contingent_condition == IMM:
            self.contingent_condition_original = ContingentConditionType.Immediately
        else:
            print('暂未考虑除Immediately之外的触发类型：%s' % self.contingent_condition)


    def _conver_direction(self, direction, offset):
        if direction == 'Buy':
            if offset == OPEN:
                self.direction = LONG
            else:
                self.direction = SHORT
        elif direction == 'Sell':
            if offset == OPEN:
                self.direction = SHORT
            else:
                self.direction = LONG


    def _conver_offset(self, offset):
        if offset == OffsetFlagType.Open.__char__(): # 0
            return OPEN
        elif offset == OffsetFlagType.Close.__char__() : # 1
            return CLOSE
        elif offset == OffsetFlagType.ForceClose.__char__(): # 2
            return FORECE_CLOSE
        elif offset == OffsetFlagType.CloseToday.__char__(): # 3
            return CLOSE_TODAY
        elif offset == OffsetFlagType.CloseYesterday.__char__(): # 4
            return CLOSE_YESTERDAY
        elif offset == OffsetFlagType.ForceOff.__char__(): # 5
            return FORECE_OFF
        elif offset == OffsetFlagType.LocalForceClose.__char__():
            return LOCAL_FORCE_CLOSE
        else:
            return offset


    def _conver_to_str(self, prama):
        lst = str(prama).split('.')
        if len(lst) > 1:
            return lst[1]
        else:
            return prama


    def __str__(self):
        return str(self.__dict__)


class TradeInfo(object):
    def __init__(self,
                 symbol='',
                 direction='',
                 offset='',
                 vol = 0,
                 price = 0,
                 user_id = '',
                 broker_id='',
                 exchange_id = '',
                 trade_id = '',
                 sys_id='',
                 trade_date='',
                 trade_time='',
                 trading_day = '',
                 strategy_id='',
                 strategy_name='',
                 pnl =0,
                 original_pnl = 0,
                 original_avg_cost_per_unit = 0,
                 commission = 0,
                 avg_cost_per_unit = 0,
                 act_offset='',
                 free_margin = 0
                 ):
        self.symbol = symbol
        self.direction = direction
        self.offset = offset
        self.vol = vol
        self.price = price
        self.user_id = user_id
        self.broker_id = broker_id
        self.exchange_id = exchange_id
        self.trade_id = trade_id
        self.sys_id = sys_id
        self.trade_date = trade_date
        self.trade_time = trade_time
        self.trading_day = trading_day
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        # 处理持仓时加入下列属性
        self.commission = commission # 手续费
        self.pnl = pnl # 平仓盈亏参与结算
        self.original_pnl = original_pnl # 不参与结算
        self.avg_cost_per_unit = avg_cost_per_unit # 持仓成本
        self.original_avg_cost_per_unit = original_avg_cost_per_unit # 不参与结算的持仓成本
        self.act_offset = act_offset # 实际平今平昨
        self.free_margin = free_margin # 释放保证金



        self._conver_direction(self.direction, self.offset)


    def _conver_direction(self, direction, offset):
        if direction == 'Buy':
            if offset == OPEN:
                self.direction = LONG
            else:
                self.direction = SHORT
        elif direction == 'Sell':
            if offset == OPEN:
                self.direction = SHORT
            else:
                self.direction = LONG


    def __str__(self):
        return str(self.__dict__)

if __name__ == '__main__':
    # order = Order(direction=DirectionType.Buy,offset=OffsetFlagType.Open.__char__(),price_type=OrderPriceTypeType.AnyPrice,contingent_condition=ContingentConditionType.Immediately)
    order2 = Order(direction=SHORT,offset=CLOSE,price_type='AnyPrice',contingent_condition='Immediately')
    # order3 = Order(direction='Buy',offset=CLOSE,price_type=AP,contingent_condition=IMM)
    # print(order)
    print(order2)
    # print(order3)


