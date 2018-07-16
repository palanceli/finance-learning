
# -*- coding:utf-8 -*-

import logging
import os
import unittest
import json
import bs4
import urllib
import urllib.request
import tushare as ts
import re
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import strpdate2num
import numpy as np

class RTDataSpider(object):
    def __init__(self):
        # 前三个字段是public interface，抓取结果会更新到rtData
        self.rtData = [
        {'name':'搜狗', 'symbol':'SOGO', 'rtData':0.0},
        {'name':'小米', 'symbol':'01810.HK', 'rtData':0.0}
        ]

    def Run(self):
        return self.rtData

class QQRTDataSplider(RTDataSpider):
    def __init__(self):
        RTData.__init__(self)
        self.rtData = [
        {'name':'搜狗',           'symbol':'SOGO',        'rtData':0.0, 'requestid':'usSOGO'},
        {'name':'小米',           'symbol':'01810.HK',    'rtData':0.0, 'requestid':'r_hk01810'},
        {'name':'标普500',        'symbol':'SPY',         'rtData':0.0, 'requestid':'usSPY'},
        {'name':'纳斯达克100',     'symbol':'QQQ',         'rtData':0.0, 'requestid':'usQQQ'},
        {'name':'沪深300',        'symbol':'000300',      'rtData':0.0, 'requestid':'sh000300'},
        {'name':'博时沪深',        'symbol':'050002',      'rtData':0.0, 'requestid':'s_jj050002'},
        ]

    def Run(self):
        urlstr = 'http://sqt.gtimg.cn/utf8/q='
        urlparamstr = ''
        for item in rtData:
            if len(urlparamstr) > 0:
                urlparamstr += ','
            urlparamstr += item['requestid']
        urlstr += urlparamstr
        responseStr = urllib.request.urlopen(urlstr).read().decode('utf-8')

        self.parseResponse(responseStr)
        return self.rtData

    def parseResponse(self, responseStr):
        items = responseStr.split(';')
        for i in items:
            i = i.strip()
            if len(i) == 0:
                continue
            # logging.debug(i)
            responseID, v = i.split('=')
            lastestPrice = float(v.split('~')[3])
            self.updateRTData(responseID, lastestPrice)

    def requestID2responsID(self, requestID):
        return 'v_' + requestID

    def updateRTData(self, responseID, lastestPrice):
        for k, v in self.qlist.items():
            requestID = v['requestid']
            if responseID == self.requestID2responsID(requestID):
                v['rtData'] = lastestPrice
                return v

class StockHelper(unittest.TestCase):
    def tcShowRT(self):
        csvPath = 'rtdata.csv'
        rtfs = QQRTFinanceSplider()
        rtData = rtfs.Run()

        csvstr = '代号,名称,最新价格\n'
        for item in rtData:
            symbol = v['symbol']
            name = v['name']
            lastestPrice = v['rtData']
            csvstr += '"%s","%s",%.4f\n' % (symbol, name, lastestPrice)

        with open(csvPath, 'w') as f:
            f.write(csvstr)

if __name__ == '__main__':
    logFmt = '%(asctime)s %(lineno)04d %(levelname)-8s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=logFmt, datefmt='%H:%M',)
    unittest.main()
    # cmd: python -m main Main.case1
