# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         objects.py
time:         2017/8/30 下午2:44
description: 

'''

__author__ = 'Jimmy'


class Context(object):
    def __init__(self):

        # 策略相关
        self.universe = []
        self.strategy_id = ''
        self.strategy_name = ''
        self.bar_frequency = '30S'
        self.init_cash = 0  # 初始资金

        # 日内策略需配置 交易日结束前几分钟清仓...***会删除该策略的context***
        self.force_close_minutes = {} # {'rb1801':5, 'SB801': 5, 'al1801':0 }

        # 分别保存策略订阅的合约的自定义中间变量
        # self.variables = {}  # {'rb1801': Variable Object}

        # handle_tick/bar
        self.receive_tick_flag = True  # 是否接收tick
        self.receive_bar_flag = True    # 是否接收bar

        # 账户信息
        self.user_id = '008105'
        self.password = '1'
        self.broker_id = '9999'
        # 电信
        self.market_front = 'tcp://180.168.146.187:10010'
        self.trade_front = 'tcp://180.168.146.187:10000'
        # 移动
        # self.market_front = 'tcp://218.202.237.33 :10012'
        # self.trade_front = 'tcp://218.202.237.33 :10002'

        # self.user_id = '00305188'
        # self.password = 'Jinmi123'
        # self.broker_id = '6000'
        # self.trade_front = 'tcp://101.231.162.58:41205'
        # self.market_front = 'tcp://101.231.162.58:41213'

        self.user_product_info = 'Jinmi'


        # *****private******
        self.collector_flag = False
        self.settlementInfo_confirm_flag = False  # 结算单确认完成
        self.finish_qry_instrument_flag = False  # 完成合约查询
        # {
        #     'OrderSysID': Order(),
        # }
        # 保存当前下的单 orderStatusType：AllTraded全部成交，Canceled取消时删除
        self.orders = {}
        self.trading_day = '' # 当前交易日,由mainEngine获得
        self.tick_convers = {} # {'rb1801':TickConver Object}
        # {
        #     'rb1801': {'pre_settlement_price': 1234, 'update_time': '19:30:22'},
        # }
        self.settlement_infos={}    # 登录后获得的第一个tick是结算tick或者无效tick, 不进行插库
        self.symbol_infos = {}      # 订阅合约信息 {'rb1801':symbol object}
        self.portfolio = None


    def check_context(self):
        if self.strategy_id == '':
            raise ValueError('必须设置策略id')

        if self.strategy_name == '':
            raise ValueError('必须设置策略name')

        if len(self.universe) < 1:
            raise ValueError('至少订阅一个合约!!!')

        if self.init_cash < 1:
            raise ValueError('初始资金需 > 0')

        if self.bar_frequency == '' or self.bar_frequency == '1T':
            raise ValueError('bar_frequency can not be \'%s\' !!!' % self.bar_frequency)

        if self.force_close_minutes:
            for symbol in self.universe:
                if symbol in self.force_close_minutes.keys():
                    if not isinstance(self.force_close_minutes[symbol], int):
                        raise ValueError('force_close_minutes value 需为 int 类型')
                else:
                    self.force_close_minutes[symbol] = 0
        else:
            for symbol in self.universe:
                self.force_close_minutes[symbol] = 0

#
# class Variable(object):
#     def __init__(self):
#         pass



class Tick(object):
    def __init__(self, symbol='', last_price=0.0, trading_day='', time='', millsec='', vol='', turnover=0.0,open_interest='',bid_price1=0.0,bid_vol1=0,ask_pric1=0.0,ask_vol1=0):
        self.symbol = symbol
        self.last_price = last_price
        self.trading_day = trading_day
        self.time = time
        self.millsec = millsec
        self.vol = vol                      # 成交量
        self.turnover = turnover            # 成交金额
        self.open_interest = open_interest  # 总持仓量  空单+多单
        self.bid_price1= bid_price1
        self.bid_vol1 = bid_vol1
        self.ask_price1 = ask_pric1
        self.ask_vol1 = ask_vol1

    def __str__(self):
        return str(self.__dict__)

class Bar(object):
    def __init__(self,symbol,op,cl,high,low,trading_day='',begin_time='',end_time='',vol=0, tick_counter=0,ticks=''):
        self.symbol = symbol
        self.open = op
        self.close = cl
        self.high = high
        self.low = low
        self.trading_day = trading_day
        self.begin_time = begin_time
        self.end_time = end_time
        self.vol = vol
        self.tick_counter = tick_counter
        self.ticks = ticks


    def __str__(self):
        return 'symbol:%s, open: %.2f, close: %.2f, high: %.2f, low: %.2f, vol:%d, tick_counter:%d trading_day:%s, begin_time:%s, end_time:%s' %(self.symbol,self.open, self.close, self.high, self.low, self.vol, self.tick_counter,self.trading_day,self.begin_time,self.end_time)


# atr 计算结果
class AtrR(object):
    def __init__(self, unit, n):
        self.unit = unit
        self.n = n

    def __str__(self):
        return 'unit: %d, n: %.2f' %(self.unit, self.n)


# 均线突破结果
class BlR(object):
    def __init__(self, direction, price):
        self.direction = direction
        self.price = price

    def __str__(self):
        return 'direction: %d, price: %.2f' %(self.direction, self.price)

# 布林线计算结果
class BollOut(object):
    def __init__(self, top, mid, bot, std):
        self.top = top
        self.mid = mid
        self.bot = bot
        self.std = std


    def __str__(self):
        return 'Boll: top %.2f, mid: %.2f, bot: %.2f std: %.2f' %(self.top, self.mid, self.bot, self.std)


class RebootInfo(object):
    def __init__(self, flag, status, trading_day, force_close_infos=''):
        self.flag = flag # 开始 start 新交易日 new 清理未成交订单 clear
        self.status = status # 数据收集状态 collect 收集中，process 收盘处理
        self.trading_day = trading_day # 交易日， 晚上9点启动 从数据库取下一个交易日 collector需要用
        self.force_close_infos = force_close_infos

    def __str__(self):
        return 'flag: %s, status: %s, trading_day: %s end_ids: %s' % (self.flag, self.status, self.trading_day, self.force_close_infos)


class KDJOut(object):
    def __init__(self, k1, d1, k2,d2,j2):
        self.k1 = k1
        self.k2 = k2
        self.d1 = d1
        self.d2 = d2
        self.j2 = j2

    def __str__(self):
        return 'KDJ: k1 %.2f, d1: %.2f, k2: %.2f, d2: %.2f, j1: %.2f' %(self.k1, self.d1, self.k2, self.d2, self.j2)


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


if __name__ == '__main__':
    # dict = {
    #         'rb1801':{
    #                 'flag':False, # 是否已经收到
    #                 'info':{} # tick dictionary
    #              }
    #         }
    dict = {}
    dict['rb1801']= {'flag':False}
    dict['rb1801']['flag'] = True

    print(dict)
    dict['rb1801']= {'flag':False,
                     'info':{'ss':22,'fdsf':'2e2'}
                     }

    print(dict['rb1801']['info']['ss'])

