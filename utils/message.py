# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         message.py
time:         2017/12/18 下午3:23
description: 

'''

import requests as rq

__author__ = 'Jimmy'


def send(msg, mobile='13381597676‬'):
    url = 'http://222.73.117.158/msg/HttpBatchSendSM'
    r = rq.post(url=url, data={
        'needstatus': True,
        'account': 'nanniu',
        'pswd': 'Nansy38Bkk',
        'mobile': mobile,
        'msg': msg})
