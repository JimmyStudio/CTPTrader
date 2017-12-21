# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         server.py
time:         2017/8/28 下午12:49
description: 

'''

__author__ = 'Jimmy'

import tornado
from tornado.options import define, options
from tornado import httpserver
from server.handlers import wsHandler as ws_handler
from server.handlers import httpHandler as http_handler

define('port', default=8080, help= 'run on the given port', type=int)

if __name__ == '__main__':
    print('start server at: localhost: %s' % options.port)

    tornado.options.parse_command_line()
    app = tornado.web.Application(
        handlers=[
            (r'/ws', ws_handler.wsHandler),
            (r'/start/engine',http_handler.StartEngineHandler)
        ]
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


