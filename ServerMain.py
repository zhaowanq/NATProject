"""
@desc:内网穿透服务器主入口
@author:Zhao
@time:2020/10/20 19:23
"""
import multiprocessing

#from src.main.Utils.IOUtils import *
#from src.main.ExternalMain import *
from Utils.IOUtils import *
from ExternalMain import *


if __name__ ==  '__main__':
    str = IOUtils.getConfigJson('config-s.json')
    for eachApp in str.keys():  # 读取str字典中的每一个键
        print(eachApp)
        appconfig = str.get(eachApp)    # 根据键取出对应键的值
        p = multiprocessing.Process(target=ExternalMain, args=(int(appconfig.get('toPort')), int(appconfig.get('commonPort')), int(appconfig.get('remotePort'))))
        p.start()

