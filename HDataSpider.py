
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
import time

class DLFilings(unittest.TestCase):
    # 根据urllist.json从www.sec.gov下载财报数据
    # 首先执行下面命令，安装wkhtmltopdf工具：
    # brew install Caskroom/cask/wkhtmltopdf 
    
    def setUp(self):
        logFmt = '%(asctime)s %(lineno)04d %(levelname)-8s %(message)s'
        logging.basicConfig(level=logging.DEBUG, format=logFmt, datefmt='%H:%M',)

    def tcMain(self):
        pdfurlPath = 'urllist.json'
        pdfRoot = 'data'
        with open(pdfurlPath, 'r') as f:
            jData = json.loads(f.read())

        for item in jData:
            if len(item) == 0:
                continue
            name, url = item
            if not name.startswith('tencent'):
                continue

            extPos = url.rfind('.')
            extName = url[extPos :]
                
            localPath = os.path.join(pdfRoot, name) + extName

            with open(localPath, 'wb') as f:
                try:
                    f.write(urllib.request.urlopen(url).read())
                except:
                    logging.error('failed to download %s' % url)

            # 保存为pdf文件
            # pdfFullPath = os.path.join(pdfRoot, name) + '.pdf'
            # pdfkit.from_url(url, pdfFullPath)

class TSSample(unittest.TestCase):
    ''' 通过tushare获取每天信息 '''
    def tcMain(self):
        wd = ts.get_hist_data('hs300', start='2005-01-01')
        logging.info(wd)

class HDataSpider(object):
    def __init__(self, rootDir):
        self.rootDir = rootDir
        self.stockCodeListFilePath = os.path.join(self.rootDir, 'stockcodelist.json')
        self.hDataDir = os.path.join(self.rootDir, 'hdata')

    def Run(self):
        ''' 主逻辑 '''
        if not os.path.exists(self.rootDir):
            os.mkdir(self.rootDir)

        # 获取股票代码列表信息
        stockCodeList = self.GetStockCodeList()
        logging.debug('total stock code: %d' % (len(stockCodeList)))
        # return

        # 保存到文件
        saveSCLFile = False
        if saveSCLFile:
            with open(self.stockCodeListFilePath, 'w') as f:
                f.write(json.dumps(stockCodeList))

        # 下载股票历史数据
        if not os.path.exists(self.hDataDir):
            os.mkdir(self.hDataDir)

        for sci in stockCodeList:
            self.DownloadStockHData(sci, self.hDataDir, True)

    def GetStockCodeList(self):        
        stockCodeList = [   # 默认添加指数，这在列表里没有
            {'CODE':'0000300', 'SYMBOL':'000300', 'NAME':'沪深300'}, 
        ]
        return stockCodeList

    def DownloadStockHData(self, stockCodeInfo, hdataDir, notProcessIfHDataExists=False):
        pass

class NE163Spider(HDataSpider):
    def __init__(self):
        HDataSpider.__init__(self, './financeData/finance163')

    ''' 抓取网易财经的股票信息 '''
    def getMarketRadar(self, page, count):
        url = 'http://quotes.money.163.com/hs/service/marketradar_ajax.php?page=%d&count=%d' % (page, count)
        logging.debug('querying : %s' % url)
        htmlText = urllib.request.urlopen(url).read().decode('gbk')
        jData = json.loads(htmlText)
        return jData

    def GetStockCodeList(self):
        ''' 获取股票代码的列表 '''
        count = 500
        jData = self.getMarketRadar(0, count)
        jList = jData['list']
        pageCount = jData['pagecount']
        for page in range(1, pageCount + 1):
            jData = self.getMarketRadar(page, count)
            count = jData['count']
            if count == 0:
                break
            jList.extend(jData['list'])
            
        stockCodeList = [   # 默认添加指数，这在列表里没有
            {'CODE':'0000300', 'SYMBOL':'000300', 'NAME':'沪深300'}, 
            {'CODE':'0000016', 'SYMBOL':'000016', 'NAME':'上证50'}, 
            {'CODE':'0000001', 'SYMBOL':'000001', 'NAME':'上证指数'}, 
            {'CODE':'0000002', 'SYMBOL':'000002', 'NAME':'A股指数'}, 
            {'CODE':'1399001', 'SYMBOL':'399001', 'NAME':'深证成指'}, 
            {'CODE':'1399002', 'SYMBOL':'399002', 'NAME':'深成指R'}, 
            {'CODE':'1399006', 'SYMBOL':'399006', 'NAME':'创业板指'}, 
            {'CODE':'1399102', 'SYMBOL':'399102', 'NAME':'创业板综'}, 
            {'CODE':'1399016', 'SYMBOL':'399106', 'NAME':'深证综指'}, 
        ]

        for i in jList:
            codeExists = False  # 列表里有大量的重复，把它们排除掉
            for sci in stockCodeList:
                if sci['CODE'] == i['CODE']:
                    codeExists = True
                    break
            if not codeExists:
                stockCodeList.append({'CODE':i['CODE'], 'SYMBOL':i['SYMBOL'], 'NAME':i['NAME']})

        return stockCodeList

    def GetStockHDataPathBySymbol(self, symbol):
        with open(self.stockCodeListFilePath, 'r') as f:
            jData = json.loads(f.read())
            for i in jData:
                if i['SYMBOL'] == symbol:
                    return '%s.txt' % os.path.join(self.hDataDir, i['CODE'])
        return None

    def DownloadStockHData(self, stockCodeInfo, hdataDir, notProcessIfHDataExists=False):
        ''' 下载个股的历史数据 '''
        code = stockCodeInfo['CODE']
        filePath = '%s.txt' % os.path.join(hdataDir, code)
        if notProcessIfHDataExists and os.path.exists(filePath): # 如果文件已存在就不再下载了
            logging.debug('%s exists escape.' % (filePath))
            return

        url = 'http://quotes.money.163.com/service/chddata.html?code=%s&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP' % (code)
        logging.debug('downloading %s: %s => %s' % (code, url, filePath))
        text = urllib.request.urlopen(url).read().decode('gbk').encode('utf-8')
        if len(text) < 500:
            logging.error('Failed to download %s: %s => %s' % (code, url, filePath))
            return

        with open(filePath, 'wb') as f:
            f.write(text)

class YahooSpider(HDataSpider):
    def __init__(self):
        HDataSpider.__init__(self, './financeData/yahoo')

    def GetStockCodeList(self):
        url = 'http://quote.eastmoney.com/usstocklist.html'
        htmlText = urllib.request.urlopen(url).read().decode('gbk')
        matchedItems = re.findall('<li><a target="_blank" href="(.+?)" title="(.+?)">(.+?)\((.+?)\)</a></li>', htmlText)
        stockCodeList = []
        for i in matchedItems:
            stockCodeList.append({'CODE':i[3], 'SYMBOL':i[3], 'NAME':i[1]})
        return stockCodeList

    def DownloadStockHData(self, stockCodeInfo, hdataDir, notProcessIfHDataExists=False):
        ''' 下载个股的历史数据 '''
        code = stockCodeInfo['CODE']
        filePath = '%s.txt' % os.path.join(hdataDir, code)
        if notProcessIfHDataExists and os.path.exists(filePath): # 如果文件已存在就不再下载了
            logging.debug('%s exists escape.' % (filePath))
            return

        url = 'https://finance.yahoo.com/quote/%s/history?period1=631123200&period2=%d&interval=1d&filter=history&frequency=1d' % (code, time.time())
        logging.debug('downloading %s: %s => %s' % (code, url, filePath))
        response = urllib.request.urlopen(url)
        if response.getcode() != 200:
            logging.error('Failed to download %s: %s => %s, return code=%d' % (code, url, filePath, response.getcode()))
            return
        text = response.read().decode('utf-8')
        
        startStr = '"HistoricalPriceStore":{"prices":'
        pos = text.find(startStr)
        if pos > 0:
            text = text[pos + len(startStr):]
        endStr = ',"isPending":'
        pos = text.find(endStr)
        text = text[:pos]

        if len(text) < 500:
            logging.error('Failed to download %s: %s => %s' % (code, url, filePath))
            return

        with open(filePath, 'wb') as f:
            f.write(text.encode('utf-8'))

class HDataParser(object):
    def __init__(self, path, symbol):
        self.path = path
        self.hdata = self.parseHData()
        self.symbol = symbol

    def GetStockSymbol(self):
        return self.symbol

    def addMonths(self, dt, months):
        ''' 取months个月后的1号 '''
        month = dt.month - 1 + months
        year = dt.year + int(month / 12)
        month = month % 12 + 1
        return datetime.datetime(year, month, 1)

    def doParseHDataByCol(self, dateCol, closeCol):
        hdata = {}
        minDate = None
        maxDate = None
        with open(self.path, 'r') as f:
            cLine = 0
            for line in f:
                cLine += 1
                if cLine == 1:
                    continue
                items = line.split(',')
                dt = items[dateCol]
                tclose = float(items[closeCol])
                if minDate == None:
                    minDate = dt
                elif dt < minDate:
                    minDate = dt

                if maxDate == None:
                    maxDate = dt
                elif dt > maxDate:
                    maxDate = dt

                hdata[dt] = {'DATE': dt, 'TCLOSE':tclose}
            hdata['minDate'] = minDate
            hdata['maxDate'] = maxDate
        return hdata

    def parseHData(self):
        hdata = {'2018-01-01': {'DATE': '2018-01-01', 'TCLOSE':0.0, 'TOPEN':0.1},
            'maxDate':'2018-01-01',
            'minDate':'2018-01-01'
        }
        return hdata

    def getUpRoundDate(self, dt):
        ''' 向上取圆整：在self.hdata中找到距离dt最近的日期 '''
        hmaxDate = self.hdata['maxDate']
        while dt.strftime('%Y-%m-%d') not in self.hdata:
            dt = dt + datetime.timedelta(days=1)
            if dt.strftime('%Y-%m-%d') > hmaxDate:
                return None
        return dt

    def ExtraceData(self, start, end, intervalMonths):
        ''' 从start 到end，每隔intervalMonths个月抽取一条数据 '''
        hminDate = self.hdata['minDate']
        hmaxDate = self.hdata['maxDate']
        start = self.getUpRoundDate(start)

        retHData = []

        if start is None:
            return retHData

        if end.strftime('%Y-%m-%d') > hmaxDate:
            end = datetime.datetime.strptime(hmaxDate, '%Y-%m-%d')
        end = self.getUpRoundDate(end)

        dt = start
        while dt < end:
            hdItem = self.hdata[dt.strftime('%Y-%m-%d')]
            retHData.append(hdItem)
            dt = self.addMonths(dt, 1)
            dt = self.getUpRoundDate(dt)
            if dt is None:
                break

        return retHData

    def doGetDtAndTCloseAsFloat(self, dtCol, tcloseCol):
        myGetDate = lambda astr:mdates.strpdate2num("%Y-%m-%d")(astr.decode())
        dt, tclose = np.loadtxt(self.path, delimiter=',', unpack=True, converters={0:myGetDate}, 
            skiprows=1, usecols=(dtCol, tcloseCol))
        return dt, tclose

class HDParser163(HDataParser):
    def __init__(self, symbol):
        fs = NE163Spider()
        hdataFilePath = fs.GetStockHDataPathBySymbol(symbol)
        HDataParser.__init__(self, hdataFilePath, symbol)

    def parseHData(self):
        return self.doParseHDataByCol(0, 3)

    def GetDtAndTCloseAsFloat(self):
        return self.doGetDtAndTCloseAsFloat(0, 3)

class HDParserYahoo(HDataParser):
    def __init__(self, symbol):
        path = './financeData/financeYahoo/hdata/%s.csv' % symbol
        HDataParser.__init__(self, path, symbol)

    def parseHData(self):
        return self.doParseHDataByCol(0, 5)

    def GetDtAndTCloseAsFloat(self):
        return self.doGetDtAndTCloseAsFloat(0, 5)

class Dingtou(object):
    def invest(self, hdataParser, start, end):
        ''' 对于股票stockSymbol，从start到end，每个月固定定投，计算到end时的损益率 '''
        hdata = hdataParser.ExtraceData(start, end, 1)

        tcloseOnEnd = hdata[-1]['TCLOSE']
        cInput = 0.0
        cOutput = 0.0
        for hItem in hdata:
            tclose = hItem['TCLOSE']
            hItem['INPUT'] = 1.0
            cInput += hItem['INPUT']
            hItem['OUTPUT'] = 1.0 * tcloseOnEnd / tclose
            cOutput += hItem['OUTPUT']

        deltaRate = (cOutput - cInput) * 100.0 / cInput
        nYear = (end - start).days / 365.0
        compoundDeltaRate = (pow(cOutput / cInput, 1/nYear) - 1) * 100.0

        return {'start':hdata[0]['DATE'], 'end':hdata[-1]['DATE'], 'cInput':cInput, 'cOutput':cOutput, 'deltaRate':deltaRate, 'compoundDeltaRate':compoundDeltaRate}

    def Group2Now(self, hdataParser, startYear):
        ''' 以[startYear, 2017)中的每年为起点，求到今天定投hdataParser的收益率 '''
        nowYear = 2018
        for i in range(startYear, nowYear):
            msg = ''
            start = datetime.datetime(i, 1, 1)
            end = datetime.datetime.today()
            result = self.invest(hdataParser, start, end)
            msg += '[%s, %s] ' % (result['start'], result['end'])
            msg += '总投入: %-8.2f 总产出: %-8.2f 总收益率: %6.2f%%   ' % (result['cInput'], result['cOutput'], result['deltaRate'])
            msg += '年复合收益率: %6.2f%%' % (result['compoundDeltaRate'])
            logging.info(msg)

    def GroupToYear(self, hdataParser, startYear, nYear):
        ''' 以[startYear, nowYear - nYear)中的每年为起点，求nYear年定投hdataParser的收益率 '''
        for i in range(startYear, 2019 - nYear):
            msg = ''
            start = datetime.datetime(i, 1, 1)
            end = datetime.datetime(i + nYear, 1, 1)
            result = self.invest(hdataParser, start, end)
            msg += '[%s, %s] ' % (result['start'], result['end'])
            msg += '总投入: %-8.2f 总产出: %-8.2f 总收益率: %6.2f%%   ' % (result['cInput'], result['cOutput'], result['deltaRate'])
            msg += '年复合收益率: %6.2f%%' % (result['compoundDeltaRate'])
            logging.info(msg)

    def investAndStand(self, hdataParser, investStart, investEnd, standEnd):
        ''' 对于股票stockSymbol，从investStart到investEnd，每个月固定定投，之后不再投入，计算到standEnd时的损益率 '''
        hdata = hdataParser.ExtraceData(investStart, investEnd, 1)
        standEnd = hdataParser.getUpRoundDate(standEnd)
        if standEnd == None:
            standEnd = datetime.datetime.strptime(hdataParser.hdata['maxDate'], '%Y-%m-%d')

        tcloseOnEnd = hdata[standEnd.strftime('%Y-%m-%d')]['TCLOSE']
        cInput = 0.0
        cOutput = 0.0
        for hItem in hdata:
            tclose = hItem['TCLOSE']
            hItem['INPUT'] = 1.0
            cInput += hItem['INPUT']
            hItem['OUTPUT'] = 1.0 * tcloseOnEnd / tclose
            cOutput += hItem['OUTPUT']

        deltaRate = (cOutput - cInput) * 100.0 / cInput
        nYear = (end - start).days / 365.0
        compoundDeltaRate = (pow(cOutput / cInput, 1/nYear) - 1) * 100.0

        return {'start':hdata[0]['DATE'], 'end':hdata[-1]['DATE'], 'cInput':cInput, 'cOutput':cOutput, 'deltaRate':deltaRate, 'compoundDeltaRate':compoundDeltaRate}


    def GroupInvestAndStand(self, hdataParser, startYear, nInvestYear, nStandYear):
        ''' 以[startYear, nowYear - nYear)中的每年为起点，求nYear年定投hdataParser，之后nStandYear不再投入的收益率 '''
        
        for i in range(startYear, 2019 - nInvestYear - nStandYear):
            msg = ''
            investStart = datetime.datetime(i, 1, 1)
            investEnd = datetime.datetime(i + nInvestYear, 1, 1)
            standEnd = datetime.datetime(i + nInvestYear + nStandYear)
            result = self.invest(hdataParser, investStart, investEnd, standEnd)
            msg += '[%s, %s] ' % (result['start'], result['end'])
            msg += '总投入: %-8.2f 总产出: %-8.2f 总收益率: %6.2f%%   ' % (result['cInput'], result['cOutput'], result['deltaRate'])
            msg += '年复合收益率: %6.2f%%' % (result['compoundDeltaRate'])
            logging.info(msg)

class FinanceFigure(object):
    def ShowFigure(self, hdataParser):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1) # nRows, nCols, nFig 将画布分割成 nRows × nCols，本图像画在从左到右从上到下的第nFig块
        fig.suptitle(hdataParser.GetStockSymbol(), fontsize=14, fontweight='bold')
        ax.set_xlabel('Time')
        ax.set_ylabel('TClose')
        dt, tclose = hdataParser.GetDtAndTCloseAsFloat()

        ax.plot(dt, tclose)

        # ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=range(1, 32), interval=15))
        # ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        for label in ax.xaxis.get_ticklabels():
            label.set_rotation(45)

        plt.show()

class StockHelper(unittest.TestCase):
    def tcTest(self):
        hDataSpider = YahooSpider()
        hDataSpider.Run()

    def tcGetCnHData(self):
        ''' 获取中国A股的历史数据 '''
        fs = NE163Spider()
        fs.Run()

    def tcQQQDingtou2Now(self):
        ''' 以[1993, 2017)中的每年为起点，求到今天定投纳斯达克100的收益率 '''
        hdataParser = HDParserYahoo('QQQ')
        dingtou = Dingtou()
        dingtou.Group2Now(hdataParser, 1999)

    def tcQQQDingtou2(self):
        ''' 以[1993, 2016)中的每年为起点，求2年定投投纳斯达克100的收益率 '''
        hdataParser = HDParserYahoo('QQQ')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 1999, 2)

    def tcQQQDingtou3(self):
        ''' 以[1993, 2016)中的每年为起点，求3年定投投纳斯达克100的收益率 '''
        hdataParser = HDParserYahoo('QQQ')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 1999, 3)


    def tcQQQDingtou5(self):
        ''' 以[1993, 2014)中的每年为起点，求5年定投纳斯达克100的收益率 '''
        hdataParser = HDParserYahoo('QQQ')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 1999, 5)

    def tcQQQDingtou10(self):
        ''' 以[1993, 2009)中的每年为起点，求10年定投纳斯达克100的收益率 '''
        hdataParser = HDParserYahoo('QQQ')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 1999, 10)

    def tcSPYDingtou2Now(self):
        ''' 以[1993, 2017)中的每年为起点，求到今天定投标普500的收益率 '''
        hdataParser = HDParserYahoo('SPY')
        dingtou = Dingtou()
        dingtou.Group2Now(hdataParser, 1993)

    def tcSPYDingtou3(self):
        ''' 以[1993, 2016)中的每年为起点，求3年定投标普500的收益率 '''
        hdataParser = HDParserYahoo('SPY')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 1993, 3)

    def tcSPYDingtou2(self):
        ''' 以[1993, 2016)中的每年为起点，求2年定投标普500的收益率 '''
        hdataParser = HDParserYahoo('SPY')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 1993, 2)


    def tcSPYDingtou5(self):
        ''' 以[1993, 2014)中的每年为起点，求5年定投标普500的收益率 '''
        hdataParser = HDParserYahoo('SPY')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 1993, 5)

    def tcSPYDingtou10(self):
        ''' 以[1993, 2009)中的每年为起点，求10年定投标普500的收益率 '''
        hdataParser = HDParserYahoo('SPY')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 1993, 10)

    def tcHS300Dingtou2Now(self):
        ''' 以[2002, 2017)中的每年为起点，求到今天定投沪深300的收益率 '''
        hdataParser = HDParser163('000300')
        dingtou = Dingtou()
        dingtou.Group2Now(hdataParser, 2002)

    def tcHS300Dingtou3(self):
        ''' 以[2002, 2016)中的每年为起点，求3年定投沪深300的收益率 '''
        hdataParser = HDParser163('000300')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 2002, 3)

    def tcHS300Dingtou2(self):
        ''' 以[2002, 2016)中的每年为起点，求2年定投沪深300的收益率 '''
        hdataParser = HDParser163('000300')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 2002, 2)

    def tcHS300Dingtou5(self):
        ''' 以[2002, 2014)中的每年为起点，求5年定投沪深300的收益率 '''
        hdataParser = HDParser163('000300')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 2002, 5)

    def tcHS300Dingtou10(self):
        ''' 以[2002, 2009)中的每年为起点，求10年定投沪深300的收益率 '''
        hdataParser = HDParser163('000300')
        dingtou = Dingtou()
        dingtou.GroupToYear(hdataParser, 2002, 10)

    def tcShowHS300(self):
        hdataParser = HDParser163('000300')
        ff = FinanceFigure()
        ff.ShowFigure(hdataParser)

    def tcShowQQQ(self):
        hdataParser = HDParserYahoo('QQQ')
        ff = FinanceFigure()
        ff.ShowFigure(hdataParser)
        
    def tcShowSPY(self):
        hdataParser = HDParserYahoo('SPY')
        ff = FinanceFigure()
        ff.ShowFigure(hdataParser)

if __name__ == '__main__':
    logFmt = '%(asctime)s %(lineno)04d %(levelname)-8s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=logFmt, datefmt='%H:%M',)
    unittest.main()
    # cmd: python -m main Main.case1
