# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         httpHandler.py
time:         2017/9/9 上午10:45
description:

'''

__author__ = 'Jimmy'

import tornado.websocket
import tornado.web
import tornado.gen

from server.mainEngine import *
from utils.environment import *

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.set_header('Access-Control-Allow-Origin','*')
        self.write('首页')
        self.finish()


class StartEngineHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.set_header('Access-Control-Allow-Origin','*')

        me = MainEngine()
        Environment.main_engine = me
        me.start_up()

        self.write({'info':'success'})
        self.finish()