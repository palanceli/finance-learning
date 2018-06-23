
# -*- coding:utf-8 -*-

import logging
import os
import unittest
import pdfkit
import json
import bs4
import urllib
import urllib.request

class Main(unittest.TestCase):
    def setUp(self):
        logFmt = '%(asctime)s %(lineno)04d %(levelname)-8s %(message)s'
        logging.basicConfig(level=logging.DEBUG, format=logFmt, datefmt='%H:%M',)

    def case1(self, imgName, img):
        option = webdriver.ChromeOptions()

class DLFilings(unittest.TestCase):
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


if __name__ == '__main__':
    logFmt = '%(asctime)s %(lineno)04d %(levelname)-8s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=logFmt, datefmt='%H:%M',)
    unittest.main()
    # cmd: python -m main Main.case1
