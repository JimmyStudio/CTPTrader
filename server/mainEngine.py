# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         mainEngine.py
time:         2017/9/19 23:07
description:  

'''

__author__ = 'Jimmy'

from strategies.boll2.boll_2 import *
from utils import tools as tl
from database import tradeStorage as ts
import pickle as pkl
from datetime import datetime
import time as tm


class MainEngine(EventEngine):

    def __init__(self):
        super(MainEngine,self).__init__()
        self.strategies = {}

        # flag的作用在于只调用一次
        self.reboot_flag = False # false表示已暂停， ture表示已开启
        self.update_context_flag = False # false表示未保存  ture表示正在保存
        self.trading_end_flag = False # false表示未保存  ture表示正在保存
        self.before_trading_flag = False # false表示未保存  ture表示正在保存

        self.register(EVENT_UPDATE_CONTEXT, ts.updateContext) # 注册context更新事件

        self.register(EVENT_LOG, ts.insertLog) # log


    # 通过类名实例化并启动一个策略
    def add_strategy(self, strategy_class):
        # 实例化一个 strategy 放入 self.strategies中 等待_auto_reboot操作
        strategy = eval(strategy_class)()
        force_close_flags = {}
        for symbol in strategy.context.force_close_minutes:
            force_close_flags[symbol] = False
        self.strategies[strategy.context.strategy_id] = {
            'strategy': strategy,
            'suspend': True,  # 新加入的策略设置为暂停状态
            'class': strategy_class,
            'id': strategy.context.strategy_id,
            'force_close_minutes': strategy.context.force_close_minutes, # 日内平仓时间差
            'force_close_flags': force_close_flags, # 日内平仓标志
            'symbols':strategy.context.symbol_infos # symbol info
        }


    def stop_strategy(self, strategy_id):
        if strategy_id in self.strategies.keys():
            self.strategies[strategy_id]['strategy'].stop()
            del self.strategies[strategy_id]


    def start_up(self):
        self.start()

        event = Event(EVENT_LOG)
        event.dict ={
                'message': 'mainEngine启动',
                'type': 'log',
                'engine': 'main'
            }
        event.sync_flag = False
        self.sendEvent(event)

        reboot_thread = Thread(target=self._auto_reboot)
        reboot_thread.start()


    def shut_down(self):
        for id, strategy in self.strategies.items():
            strategy['strategy'].stop()
        self.strategies = {}
        self.stop()


    # 定时重启策略
    def _auto_reboot(self):
        while True:
            # 策略字典不为空
            if self.strategies:

                schedule_reboot_flag = tl.schedule_reboot(self.strategies)

                if schedule_reboot_flag is not None :
                    if schedule_reboot_flag.flag == 'start' and self.reboot_flag == False:
                        self.reboot_flag = True
                        # 重置update_context_flag
                        self.update_context_flag = False
                        print('时间: %s ===启动===' % datetime.now())
                        dict_info ={
                                'message': '日内启动',
                                'type': 'log',
                                'engine': 'main'
                            }
                        self._send_event(EVENT_LOG, dict_info)

                        self._reboot_strategys(schedule_reboot_flag.trading_day)

                        # 晚上8:45 新的一个交易日
                    elif schedule_reboot_flag.flag == 'new' and self.reboot_flag == False:
                        self.reboot_flag = True
                        self.trading_end_flag = False    # 新交易日重置 trading_end_flag
                        self.before_trading_flag = False # 新交易日重置 before_trading_flag
                        self.update_context_flag = False
                        print('时间: %s ===新交易日启动===' % datetime.now())
                        dict_info = {
                                'message': '新交易日启动',
                                'type': 'log',
                                'engine':'main'
                            }
                        self._send_event(EVENT_LOG, dict_info)

                        self._reboot_strategys(schedule_reboot_flag.trading_day)
                    elif schedule_reboot_flag.flag == 'stop' and self.reboot_flag == True:
                        self.reboot_flag = False
                        print('时间: %s ===停止===' % datetime.now())
                        dict_info ={
                                'message': '停止',
                                'type': 'log',
                                'engine': 'main'
                            }
                        self._send_event(EVENT_LOG, dict_info)

                        self._suspend_strategys()

                    elif schedule_reboot_flag.flag == 'save' and self.update_context_flag == False:
                        self.update_context_flag = True
                        print('时间: %s ===更新context===' % datetime.now())
                        ctxs = self._handle_context(False, schedule_reboot_flag.trading_day)
                        self._send_event(EVENT_UPDATE_CONTEXT, ctxs)

                        dict_info ={
                                'message': '更新context',
                                'type': 'log',
                                'engine': 'main'
                            }
                        self._send_event(EVENT_LOG, dict_info)

                    elif schedule_reboot_flag.flag == 'before_trading' and self.before_trading_flag == False:
                        self.before_trading_flag = True
                        print('时间: %s ===交易日开盘前,发送before_trading事件===' % datetime.now())
                        self._emit_events(EVENT_BEFORE_TRADING,'交易日开盘前,发送before_trading事件件')

                    elif schedule_reboot_flag.flag == 'trading_end' and self.trading_end_flag == False:
                        self.trading_end_flag = True
                        print('时间: %s ===交易日结束,发送trading_end事件===' % datetime.now())
                        self._emit_events(EVENT_TRADING_END,'交易日结束,发送trading_end事件')

                    elif schedule_reboot_flag.flag == 'clear' and self.update_context_flag == False:
                        self.update_context_flag = True

                        self.end_trading_flag = False # 重置截止交易flag
                        print('时间: %s ===交易日结束清除未成交挂单/重置结算单确认信息===' % datetime.now())

                        ctxs = self._handle_context(True, schedule_reboot_flag.trading_day)
                        self._send_event(EVENT_UPDATE_CONTEXT, ctxs)

                        dict_info ={
                                'message': '交易日结束清除未成交挂单/重置结算单确认信息',
                                'type': 'log',
                                'engine': 'main'
                        }
                        self._send_event(EVENT_LOG, dict_info)

                    elif schedule_reboot_flag.flag == 'force_close':
                        force_close_infos = schedule_reboot_flag.force_close_infos
                        for force_close_info in force_close_infos: # [{'boll':'rb1801'},{'boll':'m1801'}]
                            for strategy_id, symbol in force_close_info.items(): # {'boll':'rb1801'}
                                strategy_dict = self.strategies[strategy_id]
                                force_close_flags = strategy_dict['force_close_flags']
                                # 如果对应symbol没有发生过强平
                                if not force_close_flags[symbol]:
                                    force_close_flags[symbol] = True # 修改flag
                                    # 针对该策略下发对应symbol的强平事件
                                    strategy_engine = Environment.strategy_engines[strategy_id]
                                    event = Event(EVENT_FORCE_CLOSE)
                                    event.dict = symbol
                                    event.sync_flag = False
                                    strategy_engine.sendEvent(event)

                                    ctx = strategy_dict['strategy'].context
                                    dict_info = {
                                        'message': '%s交易结束前提前强制清盘' % symbol,
                                        'type': 'log',
                                        'strategy_id': strategy_id,
                                        'strategy_name': ctx.strategy_name,
                                        'user_id': ctx.user_id,
                                        'broker_id': ctx.broker_id,
                                        'engine': 'main'

                                    }
                                    self._send_event(EVENT_LOG, dict_info)

                tm.sleep(1)




    # 重启所有策略
    def _reboot_strategys(self, trading_day):
        for id, strategy in self.strategies.items():
            strategy_class = strategy['class']
            # 子线程启动一个策略engine  通过类名重新实例化
            strategy = eval(strategy_class)()

            strategy_thread = Thread(target=strategy.run)
            strategy_thread.start()

            # 重置context的trading_day
            strategy.context.trading_day = trading_day

            force_close_flags = {}
            for symbol in strategy.context.force_close_minutes:
                force_close_flags[symbol] = False

            self.strategies[strategy.context.strategy_id] = {
                'strategy': strategy,
                'suspend': False,
                'class': strategy_class,
                'id': strategy.context.strategy_id,
                'force_close_minutes': strategy.context.force_close_minutes,  # 日内平仓时间差
                'force_close_flags': force_close_flags,  # 日内平仓标志
                'symbols':strategy.context.symbol_infos # symbol info
            }


    # 暂停所有策略
    def _suspend_strategys(self):
        for id, strategy in self.strategies.items():
            if strategy['suspend'] == False:  # 如果不是暂停状态 则终止
                strategy['strategy'].stop()
                strategy['suspend'] = True

    # 给所有策略下发各类事件
    def _emit_events(self, event_type, log_info):
        for strategy_id, strategy_dict in self.strategies.items():
            # 将EVENT_TRADING_END事件通过各个策略的引擎下发
            if strategy_id in Environment.strategy_engines.keys():
                strategy_engine = Environment.strategy_engines[strategy_id]
                event = Event(event_type)
                event.sync_flag = False
                strategy_engine.sendEvent(event)

                ctx = strategy_dict['strategy'].context
                dict_info = {
                        'message': log_info,
                        'type': 'log',
                        'strategy_id': strategy_id,
                        'strategy_name': ctx.strategy_name,
                        'user_id': ctx.user_id,
                        'broker_id': ctx.broker_id,
                        'engine': 'main'

                    }
                self._send_event(EVENT_LOG, dict_info)

    # 发送自己接收的事件
    def _send_event(self, event_type, dict_info):
        event = Event(event_type)
        event.dict = dict_info
        event.sync_flag = False
        self.sendEvent(event)

    # 获取context
    def _handle_context(self, clear_unfilled_order_flag, trading_day):
        contexts = []

        for id, strategy in self.strategies.items():
            # 没有经历过日内平仓的策略需要保存 context
            # 日内平仓的策略删除 context
            # if not strategy['end_trading_flag']:
            ctx = strategy['strategy'].context
            # 更新context.trading_day 废弃？
            # ctx.trading_day = trading_day
            # 一个交易日结束 清空挂单，将确认结算单flag置为false
            if clear_unfilled_order_flag:
                ctx.orders = {}
                ctx.settlementInfo_confirm_flag = False
            # 序列化 context
            serialize_ctx = pkl.dumps(ctx)
            dict = {
                'context': serialize_ctx,
                'user_id': ctx.user_id,
                'broker_id': ctx.broker_id,
                'strategy_id': ctx.strategy_id,
                'strategy_name': ctx.strategy_name,
                # 'clear': strategy['force_close_flag']  # true 表示经历过日内平仓，清空对应的context
            }
            contexts.append(dict)

        return contexts



if __name__ == '__main__':
    me = MainEngine()
    me.start_up()
    print('时间: %s ===MainEngine启动===' % datetime.now())
    me.add_strategy('BollStrategy_2')





