"""
@desc:内网穿透客户端主入口
@author:Zhao
@time: 2020/10/21 21:40
"""
#from src.main.InternalMain import InternalMain
#from src.main.Utils.IOUtils import *
from InternalMain import InternalMain
from Utils.IOUtils import *
import multiprocessing

if __name__ == '__main__':
    str = IOUtils.getConfigJson('config-c.json')
    for eachApp in str.keys():
        print(eachApp)
        appConfig = str.get(eachApp)
        p = multiprocessing.Process(target=InternalMain, args=(appConfig.get('remoteIP'), int(appConfig.get('commonPort')), int(appConfig.get('remotePort')), appConfig.get('localIP'), int(appConfig.get('localPort'))))
        p.start()