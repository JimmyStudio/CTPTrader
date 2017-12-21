# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         portfolio.py
time:         2017/10/31 下午2:49
description: 

'''

__author__ = 'Jimmy'
from trade.position import *


class Portfolio(object):
    def __init__(self, init_cash):
        self.init_cash = init_cash      # 初始资金
        self.frozen_cash = 0            # 冻结资金
        self.market_value = 0           # 市值 时刻变化
        self.static_total_value = init_cash     # 静态权益  每日结算时变化
        self.dynamic_total_value = init_cash    # 动态权益  时刻变化
        self.orders = {}                # 当前挂单
        self.positions = {}             # 仓位 {'rb1801': Position Object}
        self.upnl = 0
        self.daily_pnl = 0             # 当日平仓盈亏
        self.margin = 0                # 当前保证金
        self.daily_commission = 0      # 当日手续费
        self.total_commission = 0      # 总手续费
        self.deposite = 0
        self.withdraw = 0
        self.risk_ratio = 0.00
        self.symbol_infos = {}         # 订阅合约信息    {'rb1801':Symbol Object}
        self.last_prices = {}          # symbol 最新价 {'rb1801':1234.0}
        self.vol = 0                   # 总手数

    # 可用资金
    @property
    def avail_cash(self):
        return self.static_total_value + self.daily_pnl  - self.daily_commission - self.frozen_cash - self.margin


    def print_Portfolio(self):
        if self.positions:
            print('静: %.2f 动：%.2f, 冻结：%.2f, 可用：%.2f, 保证金：%.2f, 风险：%.4f, 日费：%.2f, 总费：%.2f, 日平：%.2f, 浮动：%.2f, 总手: %s' %(self.static_total_value,self.dynamic_total_value, self.frozen_cash, self.avail_cash,self.margin, self.risk_ratio,self.daily_commission,self.total_commission,self.daily_pnl,self.upnl,self.vol))
            for symbol, position in self.positions.items():
                print('仓位：%s' % position.print_position())
        else:
            print('静: %.2f 动：%.2f, 冻结：%.2f, 可用：%.2f, 保证金：%.2f, 风险：%.4f, 日费：%.2f, 总费：%.2f, 日平：%.2f, 浮动：%.2f, 总手: %s' %(self.static_total_value,self.dynamic_total_value, self.frozen_cash, self.avail_cash,self.margin, self.risk_ratio,self.daily_commission,self.total_commission,self.daily_pnl,self.upnl,self.vol))


    # def get_avail_cash(self):
    #     return self.static_total_value + self.daily_pnl  - self.daily_commission - self.frozen_cash - self.margin

    # 获取某个symbol 某个方向的总手数
    def get_vol(self, symbol, direction):
        if symbol in self.positions.keys():
            position = self.positions[symbol]
            if direction == LONG:
                return position.get_long_vol()
            else:
                return position.get_short_vol()

    # 获取当前挂单中的某个symbol的开平未成交单子的手数
    def get_vol_in_order(self, symbol, direction, offset=CLOSE):
        vol = 0
        for sys_id, order in self.orders.items():
            if order.symbol == symbol and order.direction == direction and order.offset == offset:
                vol += order.vol_left
        return vol

    # price_dict {'symbol':'rb1801','price':2231}
    def update_portfolio(self, price_dict):
        self.upnl = 0
        self.margin = 0
        self.market_value = 0
        self.vol = 0

        self.last_prices[price_dict['symbol']] = price_dict['price']

        for symbol, position in self.positions.items():
            # 更新 持仓value
            position.update_value(self.last_prices[symbol])
            # 统计浮动盈亏、保证金、市值、总手数
            self.upnl += position.get_upnl()
            self.margin += position.get_margin()
            self.market_value += position.get_value()
            self.vol += position.get_vol()

        self.dynamic_total_value = self.static_total_value + self.daily_pnl + self.upnl - self.daily_commission + self.deposite - self.withdraw
        self.risk_ratio = self.margin / self.dynamic_total_value
        self._check_risk_ratio()

        # self.print_Portfolio()

    def update_portfolio_with_settlement_infos(self, settlement_infos):
        self.upnl = 0
        self.margin = 0
        self.market_value = 0
        self.vol = 0

        for symbol, position in self.positions.items():
            # 更新 持仓value
            settlement_info = settlement_infos[symbol]
            self.last_prices[symbol] = settlement_info['pre_settlement_price']
            position.combine_position_dayend()
            # 按结算价 计算浮盈
            position.update_value(self.last_prices[symbol])
            self.upnl += position.get_upnl()
            # 将持仓成本价改为结算价 计算保证金，市值
            position.update_value_dayend(self.last_prices[symbol])
            self.margin += position.get_margin()
            self.market_value += position.get_value()
            self.vol += position.get_vol()


    # settlement_price_dict {'rb1801':{'pre_settlement_price':22323,'update_time':'20:22:22'}
    def update_portfolio_dayend(self, settlement_infos):
        self.update_portfolio_with_settlement_infos(settlement_infos)

        # 当日结存 = 上日结存 + 当日存取合计 + 平仓盈亏 + 浮动盈亏 - 当日手续费
        self.static_total_value = self.static_total_value + self.daily_pnl + self.upnl - self.daily_commission + self.deposite - self.withdraw
        self.dynamic_total_value = self.static_total_value
        # 可用资金 = 当日结存 - 保证金(按结算价计算)
        # self.avail_cash = self.static_total_value - self.margin
        self.risk_ratio = self.margin / self.static_total_value
        # 当日结存转为上日结存

        self.daily_pnl = 0 # 当日平仓盈亏置0
        self.upnl = 0 # 当日浮盈置为0
        self.total_commission += self.daily_commission # 手续费累加
        self.daily_commission = 0 # 当日手续费置0

        self._check_risk_ratio()

        self.print_Portfolio()


    # 根据order 变化冻结保证金
    def modify_portfolio_on_order_change(self, order):
        # 四种最终状态的order从context里删除
        if order.status == AT or order.status == CAN or order.status == PTNQ or order.status == NTNQ:
            del (self.orders[order.sys_id])
        else:
            # 开仓冻结保证金 平仓跟保证金无关
            if order.offset == OPEN:
                symbol_info = self.symbol_infos[order.symbol]
                # if symbol_info.opening_fee_by_value !=0:
                # 限价单按限价冻结保证金
                if order.price_type == LP:
                    order.margin = symbol_info.broker_margin * symbol_info.contract_size * order.vol_left * order.limit_price / 100
                # 市价单按最新价冻结保证金
                elif order.price_type == AP:
                    order.margin = symbol_info.broker_margin * symbol_info.contract_size * order.vol_left * \
                                   self.last_prices[order.symbol] / 100
                else:
                    raise ValueError('暂未考虑除LimitPrice/AnyPrice之外的报价类型')

            self.orders[order.sys_id] = order

        frozen_cash = 0
        for sys_id, order in self.orders.items():
            frozen_cash += order.margin
        self.frozen_cash = frozen_cash


    def modify_portfolio_on_trade(self, trade):
        symbol = trade.symbol
        symbol_obj = self.symbol_infos[trade.symbol]

        if trade.offset == OPEN:
            commission = symbol_obj.calculate_commission(OPEN, trade.vol, trade.price)
            self.daily_commission += commission
            trade.commission = commission

            if (trade.symbol in self.positions.keys()):
                position = self.positions[symbol]
                if trade.direction == LONG:
                    position.long_today.add_position(trade.vol, trade.price)
                else:
                    position.short_today.add_position(trade.vol, trade.price)
            else:
                new_position = Position(symbol_obj)
                if trade.direction == LONG:
                    new_position.long_today.init(trade.vol, trade.price)
                else:
                    new_position.short_today.init(trade.vol, trade.price)

                self.positions[trade.symbol] = new_position

        elif trade.offset == CLOSE_TODAY:
            self._close_today(symbol,symbol_obj,trade.direction, trade.vol, trade.price, trade)

        elif trade.offset == CLOSE_YESTERDAY:
            self._close_yesterday(symbol,symbol_obj,trade.direction, trade.vol, trade.price, trade)

        elif trade.offset == CLOSE:
            if symbol_obj.exch_code == 'SHFE':
                raise ValueError('只有大连郑州才有CLOSE')
            # 大连郑州先平今 再平昨
            position = self.positions[symbol]
            if trade.direction == LONG:
                long_today = position.long_today
                if long_today.vol >= trade.vol:
                    self._close_today(symbol,symbol_obj,LONG,trade.vol,trade.price, trade)
                else:
                    yesterday_vol = trade.vol - long_today.vol
                    self._close_today(symbol, symbol_obj, LONG, long_today.vol, trade.price, trade)
                    self._close_yesterday(symbol, symbol_obj, LONG, yesterday_vol, trade.price, trade)
            else:
                short_today = position.short_today
                if short_today.vol >= trade.vol:
                    self._close_today(symbol,symbol_obj,SHORT,trade.vol,trade.price, trade)
                else:
                    yesterday_vol = trade.vol - short_today.vol
                    self._close_today(symbol, symbol_obj, SHORT, short_today.vol, trade.price, trade)
                    self._close_yesterday(symbol, symbol_obj, SHORT, yesterday_vol, trade.price, trade)
        else:
            raise ValueError('暂未考虑除O/C/CT/CY之外的offset类型')


    def _close_today(self, symbol, symbol_obj, direction, vol, price, trade):
        if vol > 0:
            commission = symbol_obj.calculate_commission(CLOSE_TODAY, vol, price)
            self.daily_commission += commission
            trade.commission = commission

            position = self.positions[symbol]
            if direction == LONG:
                long_today = position.long_today
                if long_today.vol < vol:
                    raise ValueError('平今多仓位不足')
                pnl = (price - long_today.avg_cost_per_unit) * vol * symbol_obj.contract_size
                original_pnl = (price - long_today.original_avg_cost_per_unit) * vol * symbol_obj.contract_size

                free_margin = long_today.avg_cost_per_unit * vol * symbol_obj.contract_size * symbol_obj.broker_margin * 0.01
                self.margin -= free_margin
                print('%s平今多:%s手 平仓盈亏:%.2f 释放保证金：%.2f' % (symbol, vol, pnl, free_margin))
                trade.pnl = pnl
                trade.act_offset = CLOSE_TODAY
                trade.avg_cost_per_unit = long_today.avg_cost_per_unit
                trade.original_avg_cost_per_unit = long_today.original_avg_cost_per_unit
                trade.free_margin = free_margin
                trade.original_pnl = original_pnl

                self.daily_pnl += pnl
                long_today.close_position(vol)
            else:
                short_today = position.short_today
                if short_today.vol < vol:
                    raise ValueError('平今空仓位不足')
                pnl = (short_today.avg_cost_per_unit - price) * vol * symbol_obj.contract_size
                original_pnl = (short_today.original_avg_cost_per_unit - price) * vol * symbol_obj.contract_size

                free_margin = short_today.avg_cost_per_unit * vol * symbol_obj.contract_size * symbol_obj.broker_margin * 0.01
                self.margin -= free_margin
                print('%s平今空:%s手 平仓盈亏:%s 释放保证金：%s' % (symbol, vol, pnl, free_margin))
                trade.pnl = pnl
                trade.act_offset = CLOSE_TODAY
                trade.avg_cost_per_unit = short_today.avg_cost_per_unit
                trade.original_avg_cost_per_unit = short_today.original_avg_cost_per_unit
                trade.free_margin = free_margin
                trade.original_pnl = original_pnl

                self.daily_pnl += pnl
                short_today.close_position(vol)


    def _close_yesterday(self, symbol, symbol_obj, direction, vol, price, trade):
        if vol > 0:
            commission = symbol_obj.calculate_commission(CLOSE_YESTERDAY, vol, price)
            self.daily_commission += commission
            trade.commission = commission

            position = self.positions[symbol]
            if direction == LONG:
                long_yesterday = position.long_yesterday
                if long_yesterday.vol < vol:
                    raise ValueError('平昨多仓位不足')
                pnl = (price - long_yesterday.avg_cost_per_unit) * vol * symbol_obj.contract_size
                original_pnl = (price - long_yesterday.original_avg_cost_per_unit) * vol * symbol_obj.contract_size

                free_margin = long_yesterday.avg_cost_per_unit * vol * symbol_obj.contract_size * symbol_obj.broker_margin * 0.01
                self.margin -= free_margin
                print('%s平昨多:%s手 平仓盈亏:%s 释放保证金：%s' % (symbol, vol, pnl, free_margin))
                trade.pnl = pnl
                trade.act_offset = CLOSE_YESTERDAY
                trade.avg_cost_per_unit = long_yesterday.avg_cost_per_unit
                trade.original_avg_cost_per_unit = long_yesterday.original_avg_cost_per_unit
                trade.free_margin = free_margin
                trade.original_pnl = original_pnl

                self.daily_pnl += pnl
                long_yesterday.close_position(vol)
            else:
                short_yesterday = position.short_yesterday
                if short_yesterday.vol < vol:
                    raise ValueError('平昨空仓位不足')
                pnl = (short_yesterday.avg_cost_per_unit - price) * vol * symbol_obj.contract_size
                original_pnl = (short_yesterday.original_avg_cost_per_unit - price) * vol * symbol_obj.contract_size

                free_margin = short_yesterday.avg_cost_per_unit * vol * symbol_obj.contract_size * symbol_obj.broker_margin * 0.01
                self.margin -= free_margin
                print('%s平昨空:%s手 平仓盈亏:%s 释放保证金：%s' % (symbol, vol, pnl, free_margin))
                trade.pnl = pnl
                trade.act_offset = CLOSE_YESTERDAY
                trade.avg_cost_per_unit = short_yesterday.avg_cost_per_unit
                trade.original_avg_cost_per_unit = short_yesterday.original_avg_cost_per_unit
                trade.free_margin = free_margin
                trade.original_pnl = original_pnl

                self.daily_pnl += pnl
                short_yesterday.close_position(vol)

    def _check_risk_ratio(self):
        if self.risk_ratio > 1.25:
            print('账户风险度大于125%, 被强平')


    def __str__(self):
        return str(self.__dict__)
