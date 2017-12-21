# -*- coding: utf-8 -*-

'''
author:       Jimmy
contact:      234390130@qq.com
file:         processEventEngine.py
time:         2017/8/25 上午10:06
description:  多进程异步事件驱动引擎

'''

__author__ = 'Jimmy'


from multiprocessing import Process, Queue


class EventEngine(object):
    # 初始化事件事件驱动引擎
    def __init__(self):
        #保存事件列表
        self.__eventQueue = Queue()
        #引擎开关
        self.__active = False
        #事件处理字典{'event1': [handler1,handler2] , 'event2':[handler3, ...,handler4]}
        self.__handlers = {}
        #保存事件处理进程池
        self.__processPool = []
        #事件引擎主进程
        self.__mainProcess = Process(target=self.__run)


    #执行事件循环
    def __run(self):
        while self.__active:
            #事件队列非空
            if not self.__eventQueue.empty():
                #获取队列中的事件 超时1秒
                event = self.__eventQueue.get(block=True ,timeout=1)
                #执行事件
                self.__process(event)
            else:
                # print('无任何事件')
                pass


    #执行事件
    def __process(self, event):
        if event.type in self.__handlers:
            for handler in self.__handlers[event.type]:
                #开一个进程去异步处理
                p = Process(target=handler, args=(event, ))
                #保存到进程池
                self.__processPool.append(p)
                p.start()


    #开启事件引擎
    def start(self):
        self.__active = True
        self.__mainProcess.start()


    #暂停事件引擎
    def stop(self):
        # 将事件管理器设为停止
        self.__active = False
        # 等待事件处理进程退出
        for p in self.__processPool:
            p.join()
        self.__mainProcess.join()


    #终止事件引擎
    def terminate(self):
        self.__active = False
        #终止所有事件处理进程
        for p in self.__processPool:
            p.terminate()
        self.__mainProcess.terminate()


    #注册事件
    def register(self, type, handler):
        """注册事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则创建
        try:
            handlerList = self.__handlers[type]
        except KeyError:
            handlerList = []
            self.__handlers[type] = handlerList

        # 若要注册的处理器不在该事件的处理器列表中，则注册该事件
        if handler not in handlerList:
            handlerList.append(handler)


    def unregister(self, type, handler):
        """注销事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则忽略该次注销请求
        try:
            handlerList = self.__handlers[type]

            # 如果该函数存在于列表中，则移除
            if handler in handlerList:
                handlerList.remove(handler)

            # 如果函数列表为空，则从引擎中移除该事件类型
            if not handlerList:
                del self.__handlers[type]
        except KeyError:
            pass


    def sendEvent(self, event):
        #发送事件 像队列里存入事件
        self.__eventQueue.put(event)


class Event(object):
    #事件对象
    def __init__(self, type =None):
        self.type = type
        self.dict = {}



#测试
if __name__ == '__main__':
    import time
    import threading
    import os
    EVENT_ARTICAL = "Event_Artical"

    # 事件源 公众号
    class PublicAccounts:
        def __init__(self, eventManager):
            self.__eventManager = eventManager

        def writeNewArtical(self):
            # 事件对象，写了新文章
            event = Event(EVENT_ARTICAL)
            event.dict["artical"] = u'如何写出更优雅的代码\n'
            # 发送事件
            self.__eventManager.sendEvent(event)
            print(u'公众号发送新文章 thread: %s pp: %s cp:%s\n' % (threading.current_thread().name, os.getppid(), os.getpid()))


    # 监听器 订阅者
    class ListenerTypeOne:
        def __init__(self, username):
            self.__username = username

        # 监听器的处理函数 读文章
        def ReadArtical(self, event):
            print(u'%s 收到新文章' % self.__username)
            print(u'%s 正在阅读新文章内容：%s thread: %s pp: %s cp:%s\n' % (self.__username, event.dict["artical"] ,threading.current_thread().name, os.getppid(), os.getpid()))


    class ListenerTypeTwo:
        def __init__(self, username):
            self.__username = username

        # 监听器的处理函数 读文章
        def ReadArtical(self, event):
            print(u'%s 收到新文章 睡3秒再看' % self.__username)
            time.sleep(3)
            print(u'%s 正在阅读新文章内容：%s thread: %s pp: %s cp:%s\n' % (self.__username, event.dict["artical"] ,threading.current_thread().name, os.getppid(), os.getpid()))


    def test():
        listner1 = ListenerTypeOne("thinkroom")  # 订阅者1
        listner2 = ListenerTypeTwo("steve")  # 订阅者2

        ee = EventEngine()

        # 绑定事件和监听器响应函数(新文章)
        ee.register(EVENT_ARTICAL, listner1.ReadArtical)
        ee.register(EVENT_ARTICAL, listner2.ReadArtical)
        for i in range(0, 20):
            listner3 = ListenerTypeOne("Jimmy")  # 订阅者X
            ee.register(EVENT_ARTICAL, listner3.ReadArtical)

        ee.start()

        #发送事件
        publicAcc = PublicAccounts(ee)
        publicAcc.writeNewArtical()


        # time.sleep(10)
        # ee.stop()

        # 再次发送事件
        # publicAcc = PublicAccounts(ee)
        # publicAcc.writeNewArtical()



        time.sleep(10)
        ee.terminate()

        # ee2 = EventEngine()
        #
        # # 绑定事件和监听器响应函数(新文章)
        # ee2.register(EVENT_ARTICAL, listner1.ReadArtical)
        # ee2.register(EVENT_ARTICAL, listner2.ReadArtical)
        # for i in range(0, 20):
        #     listner3 = ListenerTypeOne("Jimmy")  # 订阅者X
        #     ee2.register(EVENT_ARTICAL, listner3.ReadArtical)
        #
        # ee2.start()
        #
        # # 发送事件
        # publicAcc = PublicAccounts(ee2)
        # publicAcc.writeNewArtical()

    test()
