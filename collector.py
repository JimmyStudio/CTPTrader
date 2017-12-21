# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         collector.py
time:         2017/9/25 上午11:28
description: 

'''

__author__ = 'Jimmy'
from utils.objects import *
from engine.eventEngine import *
from trade.api import *
from engine.eventType import *
from database import collectorStorage as cs
from collector.handleTick import *
from utils import tools as tl
from datetime import datetime as dt
import time as tm
from database import tradeStorage as ts
import gc as gc


class Collector(object):
    def __init__(self):
        self.context = Context()
        self.context.collector_flag = True
        self.context.strategy_id = 'Collector'
        self.context.strategy_name = '数据收集器'

        self.context.user_id = '00305188'
        self.context.password = 'Jinmi123'
        self.context.broker_id = '6000'
        self.context.trade_front = 'tcp://101.231.162.58:41205'
        self.context.market_front = 'tcp://101.231.162.58:41213'

        self.reboot_flag = False  # false表示已暂停， ture表示已开启



    def start_up(self):
        reboot_thread = Thread(target=self._auto_reboot)
        reboot_thread.start()


    def _login(self, schedule_reboot_flag, trading_day):

        # 交易日
        self.context.trading_day = trading_day

        self._engine = EventEngine()
        self._engine.register(EVENT_ON_TICK, self._handle_tick)
        self._engine.register(EVENT_LOG, ts.insertLog) # log

        self._engine.start()


        self._md = MApi(self._engine, self.context)
        self._td = TApi(self._engine, self.context)
        self._td.login()

        # while True:
        #     if self.context.settlementInfo_confirm_flag and self.context.finish_qry_instrument_flag:
        #         self.context.universe = cs.getAllSymbols(trading_day)
        #         self._md.login()
        #         break

        if schedule_reboot_flag == 'new':
            # 新交易日
            # 1.先确认结算单
            # 2.查询合约信息并入库
            while True:
                if self.context.settlementInfo_confirm_flag and self.context.finish_qry_instrument_flag:
                    self.context.universe = cs.getAllSymbols(trading_day)
                    self._md.login()
                    break

        elif schedule_reboot_flag == 'start':
            # 日内节点启动
            self.context.universe = cs.getAllSymbols(trading_day)
            self._md.login()



    def _logout(self):
        self._engine.stop()
        self._md.logout()
        self._td.logout()
        # 回收内存
        del self._engine
        del self._md
        del self._td
        gc.collect()



    def _auto_reboot(self):
        while True:
            schedule_reboot_flag = tl.schedule_reboot()
            # print(schedule_reboot_flag.trading_day)
            if schedule_reboot_flag is not None:
                if schedule_reboot_flag.flag == 'start' and self.reboot_flag == False:
                    self.reboot_flag = True
                    print('时间: %s ===日内节点启动===' % dt.now())
                    self._login(schedule_reboot_flag.flag, schedule_reboot_flag.trading_day)

                    event = Event(EVENT_LOG)
                    event.dict = {
                            'message': '日内启动',
                            'type': 'log',
                            'engine': 'collector'
                    }
                    event.sync_flag = False
                    self._engine.sendEvent(event)

                    # 晚上8:40 新的一个交易日
                elif schedule_reboot_flag.flag == 'new' and self.reboot_flag == False:
                    self.reboot_flag = True
                    self.context.finish_qry_instrument_flag = False  # 新交易日重新查询持仓
                    self.context.settlementInfo_confirm_flag = False  # 新交易日重新确认结算单
                    print('时间: %s ===新交易日启动===' % dt.now())


                    self._login(schedule_reboot_flag.flag, schedule_reboot_flag.trading_day)

                    event = Event(EVENT_LOG)
                    event.dict = {
                            'message': '新交易日启动',
                            'type': 'log',
                            'engine': 'collector'
                    }
                    event.sync_flag = False
                    self._engine.sendEvent(event)

                elif schedule_reboot_flag.flag == 'stop' and self.reboot_flag == True:
                    self.reboot_flag = False
                    print('时间: %s ===停止===' % dt.now())
                    event = Event(EVENT_LOG)
                    event.dict = {
                            'message': '停止',
                            'type': 'log',
                            'engine': 'collector'
                    }
                    event.sync_flag = False
                    self._engine.sendEvent(event)

                    # 每次stop处理已保存tick的数据
                    if schedule_reboot_flag.status == 'process':

                        print('时间: %s ===交易日结束处理数据===' % dt.now())
                        event = Event(EVENT_LOG)
                        event.dict = {
                                'message': '交易日结束处理数据',
                                'type': 'log',
                                'engine': 'collector'
                        }
                        event.sync_flag = False
                        self._engine.sendEvent(event)

                    self._logout()


            tm.sleep(120)



    def _handle_tick(self, event):
        tick = event.dict
        # 入库  tick数据有可能残缺  原因不明
        # if tick['TradingDay'] != '':
        tick['TradingDay'] = int(tick['TradingDay'])
        cs.insertTick(tick)





if __name__ == '__main__':
    c = Collector()
    print('时间: %s ===Collector启动===' % datetime.now())
    c.start_up()