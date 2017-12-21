# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         sender.py
time:         2017/9/9 10:51
description:  

'''

__author__ = 'Jimmy'
from utils.environment import *

def ws_trade_connected(event):
    _push_to_client('trade_connected', event.dict)


def ws_trade_login(event):
    _push_to_client('trade_login', event.dict)


def ws_market_connected(event):
    _push_to_client('market_connected', event.dict)


def ws_market_login(event):
    _push_to_client('market_login', event.dict)


def ws_settlement_confirm(event):
    _push_to_client('settlement', event.dict)


def ws_on_tick(event):
    _push_to_client('tick', event.dict)


def ws_send_order(event):
    # 枚举转字符串
    direction = str(event.dict['direction']).split('.')[-1]
    event.dict['direction'] = direction
    price_type = str(event.dict['price_type']).split('.')[-1]
    event.dict['price_type'] = price_type
    stop_price = str(event.dict['stop_price']).split('.')[-1]
    event.dict['stop_price'] = stop_price
    contingent_condition = str(event.dict['contingent_condition']).split('.')[-1]
    event.dict['contingent_condition'] = contingent_condition

    _push_to_client('send_order', event.dict)


def ws_cancel_order(event):
    _push_to_client('cancel_order', event.dict)


def ws_on_order(event):
    _push_to_client('on_order',event.dict)


def ws_insert_order(event):
    _push_to_client('insert_order',event.dict)


def ws_insert_order_action(event):
    _push_to_client('insert_order_action',event.dict)


def ws_error_order_action(event):
    _push_to_client('error_order_action',event.dict)


def ws_trade(event):
    _push_to_client('trade',event.dict)


def ws_rsp_error(event):
    _push_to_client('rsp_error',event.dict)


def _push_to_client(key,value):
    clients = Environment.ws_clients
    for client in clients:
        client.write_message({key:value})