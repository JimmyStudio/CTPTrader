# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         eventType.py
time:         2017/8/28 下午1:05
description: 

'''

__author__ = 'Jimmy'


# 系统相关
EVENT_TIMER = 'eTimer'                  # 计时器事件，每隔1秒发送一次
EVENT_LOG = 'eLog'                      # 日志事件，全局通用

# 主动事件
EVENT_ORDER = 'eInsertOrder'                        # 发送报单
EVENT_ORDER_STORAGE = 'eInsertOrderStorage'         # 发送报单保持参数
EVENT_CANCEL = 'eCancel'                            # 发送撤单
EVENT_CANCEL_STORAGE = 'eCancelStorage'             # 保存发送撤单参数
# EVENT_QRY_POSITION = 'eQryPosition.'                       # 持仓回报事件 交易回报后查询持仓
# EVENT_QRY_ACCOUNT = 'eQryAccount.'                         # 账户回报事件 报单后查询账户

# 被动事件
EVENT_ON_TRADE_CONNECTED = 'eOnTradeConnected'                 # 连上交易服务器
EVENT_ON_TRADE_DISCONNECTED = 'eOnTradeDisConnected'           # 连上交易服务器失败
EVENT_ON_TRADE_LOGIN = 'eOnTradeLogin'                         # 登录交易服务器
EVENT_ON_MARKET_CONNECTED = 'eOnMarketConnected'               # 连上行情服务器
EVENT_ON_MARKET_DISCONNECTED = 'eOnMarketDisConnected'         # 未连上连上行情服务器

EVENT_ON_MARKET_LOGIN= 'eOnMarketLogin'                        # 登录行情服务器
EVENT_ON_SUBMARKETDATA= 'eOnSubMarketData'                     # 订阅行情成功

EVENT_ON_SETTLEMENT_CONFIRM= 'eOnSettlementInfoConfirm'        # 结算单确认

EVENT_ON_TICK = 'eOnTick.'                          # 收到Tick事件
EVENT_ON_BAR = 'eOnBar.'                            # 收到Bar事件
EVENT_ON_ORDER = 'eOnOrder'                         # 报单回报事件 OnRtnOrder
EVENT_ON_ORDER_CHANGE = 'eOnOrderChange'            # 报单回报事件 OnRtnOrder order成交或者撤销的事件

EVENT_ON_INPUT_ORDER = 'eOnInputOrder'              # 报单录入 OnRspOrderInsert OnErrRtnOrderInsert
EVENT_ON_INPUT_ORDER_ACTION = 'eOnInputOrderAction' # 输入报单操作 OnRspOrderAction
EVENT_ON_ORDER_ACTION = 'eOnOrderAction'            # 报单操作 OnErrRtnOrderAction
EVENT_ON_TRADE = 'eOnTrade'                         # 成交回报事件 OnRtnTrade
EVENT_ON_TRADE_LOG = 'eOnTradeLog'                  # 成交回报处理盈亏后插库
EVENT_ON_POSITION = 'eOnPosition.'                  # 持仓回报事件
EVENT_ON_ACCOUNT = 'eOnAccount.'                    # 账户回报事件

EVENT_CONTRACT = 'eContract.'           # 合约基础信息回报事件
EVENT_ERROR = 'eError.'                 # 错误回报事件

EVENT_UPDATE_CONTEXT = 'eUpdateContext'                 # 更新策略context
EVENT_BEFORE_TRADING = 'eBeforeTrading'                 # 交易开始之前
EVENT_FORCE_CLOSE = 'eForceClose'                       # 提前强制平仓型号
EVENT_TRADING_END = 'eTradingEnd'                       # 交易结束后



# 回测
EVENT_EXECUTE = 'eExecute' # 回测执行order
EVENT_PORTFOLIO = 'ePortfolio' # 回测更新账户持仓。。。


# ----------------------------------------------------------------------
def test():
    """检查是否存在内容重复的常量定义"""
    check_dict = {}

    global_dict = globals()

    for key, value in global_dict.items():
        if '__' not in key:  # 不检查python内置对象
            if value in check_dict:
                check_dict[value].append(key)
            else:
                check_dict[value] = [key]

    for key, value in check_dict.items():
        if len(value) > 1:
            print(u'存在重复的常量定义:' + str(key))
            for name in value:
                print(name)
            print('')

    print(u'测试完毕')


# 直接运行脚本可以进行测试
if __name__ == '__main__':
    test()