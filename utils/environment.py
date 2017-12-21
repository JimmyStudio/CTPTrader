# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         environment.py
time:         2017/8/31 上午9:54
description:  全局静态变量

'''



__author__ = 'Jimmy'


class Environment(object):
    ws_clients = []
    main_engine = None
    strategy_engines = {}

    # {
    #     'id1':engine1,
    #     'id2':engine2,
    # }


