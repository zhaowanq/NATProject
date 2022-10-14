"""
@desc:内网穿透服务器端
@author: Zhao
@time:created on 2020/10/18 16:45
"""

import select
import socket
import time
from threading import Thread


# 内网穿透服务器端子线程类


class MappingSubServer:
    def __init__(self, connA, connB, serverB):
        # serverA的连接对象
        self.connA = connA
        # serverB的连接对象
        self.connB = connB
        # 监听可读列表、可写列表、错误列表
        self.readableList = [connA, connB]
        self.writableList = []
        self.errorList = []
        # serverB实体
        self.serverB = serverB

    # 关闭连接
    def closeConnection(self):
        b = bytes('NODATA', encoding='utf-8')  # 把字符串转换为字节串
        self.connA.send(b)
        self.readableList.remove(self.connB)
        self.readableList.remove(self.connA)
        self.connB.close()
        self.connA.close()

    # 端口转发
    # ServerB:centos7 ServerA:win7
    def TCPForwarding(self):
        while True:
            rs, ws, es = select.select(self.readableList, self.writableList, self.errorList)
            for each in rs:
                # 如果当前是connA，则接收数据转发给connB，传输结束关闭连接返回，遇错返回
                if each == self.connA:
                    try:
                        tdataA = each.recv(1024)
                        self.connB.send(tdataA)
                        # print(tdataA)
                        if not tdataA:
                            self.closeConnection()
                            return
                    except BlockingIOError as e:
                        print(e)
                        return
                    except ConnectionAbortedError as e:
                        print(e)
                        return
                # 如果当前是connB，则接收数据转发给connA，传输结束关闭连接返回，遇错返回
                elif each == self.connB:
                    try:
                        tdataB = each.recv(1024)
                        self.connA.send(tdataB)
                        if not tdataB:
                            self.closeConnection()
                            return
                    except ConnectionAbortedError as e:
                        print(e)
                        return
                    except ConnectionResetError as e:
                        print(e)
                        return


# 内网穿透服务器端
class MappingServer:
    def __init__(self, toPort, commonPort, remotePort):
        # remotePort：本台机器开放哪个端口供内网服务器连接 8000
        self.remotePort = remotePort
        # commonPort:心跳检测端口 7000
        self.commonPort = commonPort
        # toPort:外部用户访问端口   9000
        self.toPort = toPort
        # self.serverA
        # self.serverB
        # self.serverC
        self.serverA = None
        self.serverB = None
        self.serverC = None
        # connC实例，需要每个对象维护一个，用于心跳检测,用来为ClientC服务
        self.connC = None
        # 判断connC是否挂掉
        self.isAlive = False
        self.readableList = []
        self.writableList = []
        self.errorList = []

    def initServerA(self):
        self.serverA = None
        self.serverA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverA.bind(('', self.remotePort))
        self.serverA.listen(5)
        self.serverA.setblocking(1)

    def initServerB(self):
        self.serverB = None
        self.serverB = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 当服务器进程终止后，立刻释放其绑定的端口
        self.serverB.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverB.bind(('', self.toPort))
        self.serverB.listen(5)
        self.serverB.setblocking(1)
        self.readableList.append(self.serverB)

    def initServerC(self):
        self.serverC = None
        self.serverC = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverC.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverC.bind(('', self.commonPort))
        self.serverC.listen(5)
        self.serverC.setblocking(1)

    def TCPForwarding(self):
        self.initServerA()
        self.initServerB()
        while True:
            rs, ws, es = select.select(self.readableList, self.writableList, self.errorList)
            for each in rs:
                if each == self.serverB:
                    # 如果connC挂掉，不做任何事情，等待连接恢复
                    if not self.isAlive:
                        continue
                    try:
                        # 如果有外部请求，激活数据管道，每个请求一个线程
                        connB, addB = self.serverB.accept()
                        print('Server B IP : %s:%d' % addB)
                        b = bytes('ACTIVATE', encoding='utf-8')
                        self.connC.send(b)
                        connA, addA = self.serverA.accept()
                        print('ServerA IP : %s:%d' % addA)
                        mss = MappingSubServer(connA, connB, self.serverB)
                        t = Thread(target=mss.TCPForwarding)
                        t.setDaemon(True)
                        t.start()
                    except BlockingIOError as e:
                        print(e)
                        continue

    # 心跳检测，若挂掉等待连接恢复，每秒发送一次心跳
    def heartbeat(self):
        while True:
            if not self.isAlive:
                self.initServerC()
                self.connC, addC = self.serverC.accept()
                print('ServerC IP : %s:%d' % addC)
                self.isAlive = True
            b = bytes('IAMALIVE', encoding='utf-8')
            try:
                self.connC.send(b)
                tdataC = self.connC.recv(1024)
                if not tdataC:
                    self.connC.close()
                    self.connC = None
                    self.isAlive = False
            except:
                print('ServerC已断开，等待重新连接...')
                self.isAlive = False
            time.sleep(1)


# 主方法
def ExternalMain(toPort, commonPort, remotePort):
    f = MappingServer(toPort, commonPort, remotePort)
    t = Thread(target=f.heartbeat)
    # 主线程结束时，结束子线程
    t.setDaemon(True)
    t.start()
    f.TCPForwarding()