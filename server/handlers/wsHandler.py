# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         wsHandler.py
time:         2017/9/9 上午10:45
description:

'''

__author__ = 'Jimmy'

import tornado.websocket
import tornado.web
import tornado.gen
from utils.environment import *

class wsHandler(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        # print(origin)
        return True


    def open(self, *args, **kwargs):
        # 每个连接的客户端保存进入静态变量
        Environment.ws_clients.append(self)
        print('websocket_open')


    def on_message(self, message):
        print('on_message')


    def on_close(self):
        print('on_close')

