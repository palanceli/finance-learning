
# -*- coding:utf-8 -*-

import logging
import os
import unittest
import pdfkit
import json
import bs4
import urllib
import urllib.request
import tushare as ts
import re
import datetime

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

class FinanceSpider(object):
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
        pass

    def DownloadStockHData(self, stockCodeInfo, hdataDir, notProcessIfHDataExists=False):
        pass


class NE163Spider(FinanceSpider):
    def __init__(self):
        FinanceSpider.__init__(self, './finance163')

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

    def ParseHData(self, path):
        hdata = {}
        minDate = None
        maxDate = None
        with open(path, 'r') as f:
            cLine = 0
            for line in f:
                cLine += 1
                if cLine == 1:
                    continue
                items = line.split(',')
                dt = items[0]
                tclose = float(items[3])
                topen = float(items[6])
                if minDate == None:
                    minDate = dt
                elif dt < minDate:
                    minDate = dt

                if maxDate == None:
                    maxDate = dt
                elif dt > maxDate:
                    maxDate = dt

                hdata[dt] = {'DATE': dt, 'TCLOSE':tclose, 'TOPEN':topen}
            hdata['minDate'] = minDate
            hdata['maxDate'] = maxDate
        return hdata

class FinanceStrategy(object):
    def addMonths(self, dt, months):
        ''' 取months个月后的1号 '''
        month = dt.month - 1 + months
        year = dt.year + int(month / 12)
        month = month % 12 + 1
        return datetime.datetime(year, month, 1)

    def getUpRoundDate(self, dt, hdata):
        hmaxDate = hdata['maxDate']
        while dt.strftime('%Y-%m-%d') not in hdata:
            dt = dt + datetime.timedelta(days=1)
            if dt.strftime('%Y-%m-%d') > hmaxDate:
                logging.error('Failed to get UP Round date. dt=%s maxdate=%s' % (dt.strftime('%Y-%m-%d'), hmaxDate))
                return None
        return dt

    def getHData(self, start, end, intervalMonths, hdata):
        hminDate = hdata['minDate']
        hmaxDate = hdata['maxDate']
        while start.strftime('%Y-%m-%d') < hminDate:
            start = start + datetime.timedelta(days=1)
        start = self.getUpRoundDate(start, hdata)

        retHData = []

        if start is None:
            return retHData

        while end.strftime('%Y-%m-%d') > hmaxDate:
            end = end - datetime.timedelta(days=1)
        end = self.getUpRoundDate(end, hdata)


        dt = start
        while dt < end:
            hdItem = hdata[dt.strftime('%Y-%m-%d')]
            retHData.append(hdItem)
            dt = self.addMonths(dt, 1)
            dt = self.getUpRoundDate(dt, hdata)
            if dt is None:
                break

        return retHData

    def ProcDingtou(self, stockSymbol, start, end):
        ''' 对于股票stockSymbol，从start到end，每个月固定定投，计算到end时的损益率 '''
        fs = NE163Spider()
        hdataFilePath = fs.GetStockHDataPathBySymbol(stockSymbol)
        fullHData = fs.ParseHData(hdataFilePath)

        hdata = self.getHData(start, end, 1, fullHData)
        for i in hdata:
            logging.debug(i)

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

class StockHelper(unittest.TestCase):
    def tcGetCnHData(self):
        ''' 获取中国A股的历史数据 '''
        fs = NE163Spider()
        fs.Run()

    def tcAnalyze(self):
        fs = FinanceStrategy()
        msg = ''
        start = datetime.datetime(2016, 1, 1)
        end = datetime.datetime(2018, 7, 1)
        result = fs.ProcDingtou('000300', start, end)
        msg += '[%s, %s] ' % (result['start'], result['end'])
        msg += '总投入: %.2f，总产出: %.2f，总收益率: %.2f%%，' % (result['cInput'], result['cOutput'], result['deltaRate'])
        msg += '年复合收益率: %.2f%%' % (result['compoundDeltaRate'])
        msg += '\n'
        logging.info(msg)

if __name__ == '__main__':
    logFmt = '%(asctime)s %(lineno)04d %(levelname)-8s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=logFmt, datefmt='%H:%M',)
    unittest.main()
    # cmd: python -m main Main.case1
