"""
@desc: 内网穿透客户端
@author: Zhao
@time: 2020/10/21 19:35
"""
import select
import socket
from threading import Thread


class MappingClient:
    def __init__(self, fromIP, fromPort, Ptype, remoteIP, remotePort):
        # 远程VPS的IP地址
        self.remoteIP = remoteIP
        # 远程VPS数据监听端口
        self.remotePort = remotePort
        # 源IP
        self.fromIP = fromIP
        # 源端口
        self.fromPort = fromPort
        # clientA：连接内网APP的套接字
        self.clientA = None
        # clientB:连接VPS的套接字
        self.clientB = None
        # select监听的可读列表
        self.readableList = []
        # 协议类型
        self.Ptype = Ptype

    # 连接内网APP
    def connectClientA(self):
        if not self.clientA:
            self.clientA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 可以使TCP通信的信息包保持连续性。这些信息包可以在没有信息传输的时候，使通信的双方确定连接是保持的
            self.clientA.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.clientA.connect((self.fromIP, self.fromPort))
            print('ClientA connected!')
            # 将ClientA添加进监听可读列表
            self.readableList.append(self.clientA)

    # 连接VPS
    def connectClientB(self):
        if not self.clientB:
            self.clientB = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.clientB.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.clientB.connect((self.remoteIP, self.remotePort))
            print('ClientB connected!')
            # 将ClientB添加进监听可读列表
            self.readableList.append(self.clientB)

    # 关闭ClientA
    def closeClientA(self):
        # 先将ClientA从监听列表中移除再关闭，否则会有异常，ClientB同理
        if self.clientA in self.readableList:
            self.readableList.remove(self.clientA)
        self.clientA.shutdown(2)
        self.clientA = None
        print('ClientA closed!')

    def closeClientB(self):
        if self.clientB in self.readableList:
            self.readableList.remove(self.clientB)
        self.clientB.shutdown(2)
        self.clientB = None
        print('ClientB closed!')

    # 端口映射
    def TCPMapping(self):
        # 连接内网APP和外网VPS
        self.connectClientA()
        self.connectClientB()
        while True:
            # 使用select监听
            rs, ws, es = select.select(self.readableList, [], [])
            for each in rs:
                # 如果可读对象为ClientA，将可读的数据转发到ClientB，若遇到异常、无数据则关闭连接
                if each == self.clientA:
                    try:
                        tdataA = each.recv(1024)
                        self.clientB.send(tdataA)
                    except ConnectionResetError as e:
                        print(e)
                        self.closeClientA()
                        return
                    if not tdataA:
                        if self.clientA is not None:
                            self.closeClientA()
                            self.closeClientB()
                            return
                # 如果当前可读对象为ClientB，将读取的数据转发给ClientA，若遇到异常、无数据则关闭连接
                elif each == self.clientB:
                    try:
                        tdataB = each.recv(1024)
                        self.clientA.send(tdataB)
                    except ConnectionResetError as e:
                        self.closeClientB()
                        return
                    if tdataB == bytes('NODATA', encoding='utf-8'):
                        self.closeClientA()
                        self.closeClientB()
                        return
                    if not tdataB:
                        self.closeClientA()
                        self.closeClientB()
                        return


# 主方法
def InternalMain(remoteIP, commonPort, remotePort, localIP, localPort):
    # remoteIP:远程VPS的IP地址
    # commonPort:心跳检测端口
    # remotePort:远程VPS数据监听端口
    # localIP:本地IP
    # localPort:本地端口
    # clientC与远程VPS做心跳
    clientC = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientC.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    clientC.connect((remoteIP, commonPort))
    r1 = [clientC]
    # 监听
    while True:
        rs, ws, es = select.select(r1, [], [])
        for each in rs:
            if each == clientC:
                tdataC = each.recv(1024)
                if not tdataC:
                    r1.remove(clientC)
                    clientC.close()
                    clientC.connect((remoteIP, commonPort))
                    r1 = [clientC]
                    break
                # 若远程VPS接收到用户访问请求，则激活一个线程用于处理
                if tdataC == bytes('ACTIVATE', encoding='utf-8'):
                    print(tdataC.decode('utf-8'))
                    foo = MappingClient(localIP, localPort, 'tcp', remoteIP, remotePort)
                    t = Thread(target=foo.TCPMapping)
                    t.setDaemon(True)
                    t.start()
                # 心跳检测
                elif tdataC == bytes('IAMALIVE', encoding='utf-8'):
                    b = bytes('OK', encoding='utf-8')
                    clientC.send(b)