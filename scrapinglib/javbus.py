# -*- coding: utf-8 -*-

import re
import os
import secrets
import inspect
from lxml import etree
from urllib.parse import urljoin
from .parser import Parser
import config
import json

class Javbus(Parser):
    
    source = 'javbus'

    expr_number = '/html/head/meta[@name="keywords"]/@content'
    expr_title = '/html/head/title/text()'
    expr_studio = '//span[contains(text(),"製作商:")]/../a/text()'
    expr_studio2 = '//span[contains(text(),"メーカー:")]/../a/text()'
    expr_director = '//span[contains(text(),"導演:")]/../a/text()'
    expr_directorJa = '//span[contains(text(),"監督:")]/../a/text()'
    expr_series = '//span[contains(text(),"系列:")]/../a/text()'
    expr_series2 = '//span[contains(text(),"シリーズ:")]/../a/text()'
    expr_label = '//span[contains(text(),"系列:")]/../a/text()'
    expr_cover = '//a[@class="bigImage"]/@href'
    expr_release = '/html/body/div[5]/div[1]/div[2]/p[2]/text()'
    expr_runtime = '/html/body/div[5]/div[1]/div[2]/p[3]/text()'
    expr_actor = '//div[@class="star-name"]/a'
    expr_actorphoto = '//div[@class="star-name"]/../a/img'
    expr_extrafanart = '//div[@id="sample-waterfall"]/a/@href'
    expr_tags = '/html/head/meta[@name="keywords"]/@content'
    expr_uncensored = '//*[@id="navbar"]/ul[1]/li[@class="active"]/a[contains(@href,"uncensored")]'

    def search(self, number):
        self.number = number
        # self.cookies =  {
        #                   "PHPSESSID": "ft1m9a7m2pfo7nsh69btoji7i2",
        #                   "existmag": "mag",
        #                   "4fJN_2132_seccodecSh2oo8l": "64452.4665bcf5ff29823728",
        #                   "4fJN_2132_smile": "4D1",
        #                   "4fJN_2132_nofavfid": "1",
        #                   "starinfo": "glyphicon glyphicon-minus",
        #                   "4fJN_2132_home_diymode": "1",
        #                   "4fJN_2132_seccodecSAYVsJEGdC5": "18240.10bbf65d56b3c8b595",
        #                   "4fJN_2132_lastcheckfeed": "317940|1713092807",
        #                   "4fJN_2132_auth": "17f4LcLJg8xIvGnPvE5BIMc5JvthMM4v0RLW+17WY9/FElE/62J/mhdSi3gaxP3Z1PXrCnYslsXl1UEQ5yT2ImlV3Ixw",
        #                   "bus_auth": "f540feU6dN+NcEGzSrvyvRxz4f2wNCwGF7ztkqZblMYEiP4sonFpMDqJBU8Mc6lb",
        #                   "4fJN_2132_st_t": "317940|1713229300|8ffceecdfa47420070a12e8fd206d0c4",
        #                   "4fJN_2132_lip": "154.17.26.64|1713490537",
        #                   "4fJN_2132_ulastactivity": "9490U9+vfVA/mr/DbkhqjgYSY2SG0EGbwWi2Cu/OBx8bhHMsY3tj",
        #                   "4fJN_2132_st_p": "317940|1714033023|d196cede7118716994ad498a8bfdc538",
        #                   "4fJN_2132_viewid": "tid_136378"
        # }

        try:
            if self.specifiedUrl:
                self.detailurl = self.specifiedUrl
                htmltree = self.getHtmlTree(self.detailurl)
                result = self.dictformat(htmltree)
                return result
            try:
                newnumber = number
                if number == "DV-1649" :
                    newnumber = "DV-1649_2014-07-25"
                if number == "DV-1195" :
                    newnumber = "DV-1195_2010-10-08"
                if number == "BKD-003" :
                    newnumber = "BKD-003_2009-09-05"
                self.detailurl = 'https://www.javbus.com/' + newnumber
                self.htmlcode = self.getHtml(self.detailurl)
            except:
                mirror_url = "https://www." + secrets.choice([
                    'buscdn.art',
                    ]) + "/"
                self.detailurl = mirror_url + number
                self.htmlcode = self.getHtml(self.detailurl)
            if self.htmlcode == 404:
                return 404
            htmltree = etree.fromstring(self.htmlcode,etree.HTMLParser())
            self.extraheader = {"Referer": self.detailurl}
            result = self.dictformat(htmltree)
            return result
        except:
            self.searchUncensored(number)

    def dictformat(self, htmltree):
        try:
            dic = {
                'number': self.getNum(htmltree),
                'title': self.getTitle(htmltree),
                'studio': self.getStudio(htmltree),
                'release': self.getRelease(htmltree),
                'year': self.getYear(htmltree),
                'outline': self.getOutline(htmltree),
                'runtime': self.getRuntime(htmltree),
                'director': self.getDirector(htmltree),
                'actor': self.getActors(htmltree),
                'actor_photo': self.getActorPhoto(htmltree),
                'cover': self.getCover(htmltree),
                'cover_small': self.getSmallCover(htmltree),
                'extrafanart': self.getExtrafanart(htmltree),
                'trailer': self.getTrailer(htmltree),
                'tag': self.getTags(htmltree),
                'label': self.getLabel(htmltree),
                'series': self.getSeries(htmltree),
                'userrating': self.getUserRating(htmltree),
                'uservotes': self.getUserVotes(htmltree),
                'uncensored': self.getUncensored(htmltree),
                'website': self.detailurl,
                'source': self.source,
                'imagecut': self.getImagecut(htmltree),
                'headers': self.extraheader,
            }
            dic = self.extradict(dic)
        except Exception as e:
            if config.getInstance().debug():
                print(e)
            dic = {"title": ""}
        js = json.dumps(dic, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return js

    def searchUncensored(self, number):
        """ 二次搜索无码
        """
        self.imagecut = 0
        self.uncensored = True

        w_number = number.replace('.', '-')
        if self.specifiedUrl:
            self.detailurl = self.specifiedUrl
        else:
            self.detailurl = 'https://www.javbus.red/' + w_number
        self.htmlcode = self.getHtml(self.detailurl)
        if self.htmlcode == 404:
            return 404
        htmltree = etree.fromstring(self.htmlcode, etree.HTMLParser())
        result = self.dictformat(htmltree)
        return result

    def getNum(self, htmltree):
        return super().getNum(htmltree).split(',')[0]

    def getTitle(self, htmltree):
        title = super().getTitle(htmltree)
        title = str(re.findall('^.+?\s+(.*) - JavBus$', title)[0]).strip()
        return title

    def getStudio(self, htmltree):
        if self.uncensored:
            return self.getTreeElement(htmltree, self.expr_studio2)
        else:
            return self.getTreeElement(htmltree, self.expr_studio)

    def getCover(self, htmltree):
        return urljoin("https://www.javbus.com", super().getCover(htmltree)) 

    def getRuntime(self, htmltree):
        return super().getRuntime(htmltree).strip(" ['']分鐘")

    def getActors(self, htmltree):
        actors = super().getActors(htmltree)
        b=[]
        for i in actors:
            b.append(i.attrib['title'])
        return b
    
    def getActorPhoto(self, htmltree):
        actors = self.getTreeAll(htmltree, self.expr_actorphoto)
        d = {}
        for i in actors:
            p = i.attrib['src']
            if "nowprinting.gif" in p:
                continue
            t = i.attrib['title']
            d[t] = urljoin("https://www.javbus.com", p)
        return d

    def getDirector(self, htmltree):
        if self.uncensored:
            return self.getTreeElement(htmltree, self.expr_directorJa)
        else:
            return self.getTreeElement(htmltree, self.expr_director)

    def getSeries(self, htmltree):
        if self.uncensored:
            return self.getTreeElement(htmltree, self.expr_series2)
        else:
            return self.getTreeElement(htmltree, self.expr_series)

    def getTags(self, htmltree):
        tags = self.getTreeElement(htmltree, self.expr_tags).split(',')
        return tags[2:]

    def getOutline(self, htmltree):
        if self.morestoryline:
            if any(caller for caller in inspect.stack() if os.path.basename(caller.filename) == 'airav.py'):
                return ''   # 从airav.py过来的调用不计算outline直接返回，避免重复抓取数据拖慢处理速度
            from .storyline import getStoryline
            return getStoryline(self.number , uncensored = self.uncensored,
                                proxies=self.proxies, verify=self.verify)
        return ''
