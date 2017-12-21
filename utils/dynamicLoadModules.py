# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         hhh.py
time:         2017/8/28 上午10:45
description:  动态加载策略

'''

__author__ = 'Jimmy'


import os
import os.path

from utils.objects import *


def loadStrategys(rootDir):
    list_dirs = os.walk(rootDir)
    package = rootDir.split('/')[-1]
    modules = []
    for dirName, subdirList, fileList in list_dirs:
        for f in fileList:
            file_name = f
            if file_name[0:9] == "strategy_" and file_name[-3:] == ".py":
                asname = file_name[0:-3]
                exe_str = "from " + package + " import " + asname + " as "+ asname
                exe_str_dic = {asname:exe_str}
                modules.append(exe_str_dic)
                # exec(exe_str, globals())
    return modules


if __name__ == '__main__':
    modules = loadStrategys('../strategys')
    print(modules)
    for m in modules:
        c = Context()
        eval(m).initialize(c)
        eval(m).handleData(c, 'tick')








