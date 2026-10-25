# -*- coding: utf-8 -*-

import inspect
import json
import os
import re
import secrets
from urllib.parse import urljoin
from lxml import etree

import config
from .httprequest import request_session
from .parser import Parser
from .rule_loader import (
    eval_all_xpaths,
    eval_first_xpath,
    load_source_rules,
    resolve_dmm_hd_cover,
)


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

    def extraInit(self):
        self.rules = load_source_rules(self.source)
        self.fields_rules = self.rules.get("fields", {})
        default_cookies = self.rules.get("default_cookies") or {"existmag": "all", "dv": "1"}
        self.cookies = dict(default_cookies)
        self.session = None

    def _field_xpaths(self, key: str, fallback: list) -> list:
        configured = self.fields_rules.get(key)
        return configured if isinstance(configured, list) and configured else fallback

    def search(self, number):
        self.number = number
        if not self.cookies:
            self.cookies = {"existmag": "all", "dv": "1"}
        else:
            self.cookies.setdefault("existmag", "all")
            self.cookies.setdefault("dv", "1")
        self.session = request_session(cookies=self.cookies, proxies=self.proxies, verify=self.verify)

        try:
            if self.specifiedUrl:
                self.detailurl = self.specifiedUrl
                htmltree = self.getHtmlTree(self.detailurl)
                if htmltree == 404:
                    return 404
                self.extraheader = {"Referer": self.detailurl}
                return self.dictformat(htmltree)

            newnumber = number
            if number == "DV-1649":
                newnumber = "DV-1649_2014-07-25"
            elif number == "DV-1195":
                newnumber = "DV-1195_2010-10-08"
            elif number == "BKD-003":
                newnumber = "BKD-003_2009-09-05"

            mirrors = self.rules.get("mirrors") or ["https://www.javbus.com", "https://www.buscdn.art"]
            self.htmlcode = 404
            for base_url in mirrors:
                try:
                    self.detailurl = f"{base_url.rstrip('/')}/{newnumber}"
                    self.htmlcode = self.getHtml(self.detailurl)
                    if self.htmlcode != 404 and self.htmlcode:
                        break
                except Exception:
                    continue

            if self.htmlcode == 404 or not self.htmlcode:
                return self.searchUncensored(number)

            htmltree = etree.fromstring(self.htmlcode, etree.HTMLParser())
            self.extraheader = {"Referer": self.detailurl}
            result = self.dictformat(htmltree)
            parsed = json.loads(result)
            if not parsed.get("title"):
                return self.searchUncensored(number)
            return result
        except Exception:
            return self.searchUncensored(number)

    def extradict(self, dic: dict):
        dic['headers'] = self.extraheader
        return dic

    def searchUncensored(self, number):
        """ 二次搜索无码
        """
        self.imagecut = 0
        self.uncensored = True

        w_number = number.replace('.', '-')
        if self.specifiedUrl:
            self.detailurl = self.specifiedUrl
        else:
            uncensored_base = self.rules.get("uncensored_mirror", "https://www.javbus.red").rstrip('/')
            self.detailurl = f"{uncensored_base}/{w_number}"
        try:
            self.htmlcode = self.getHtml(self.detailurl)
        except Exception:
            return 404
        if self.htmlcode == 404 or not self.htmlcode:
            return 404
        htmltree = etree.fromstring(self.htmlcode, etree.HTMLParser())
        self.extraheader = {"Referer": self.detailurl}
        return self.dictformat(htmltree)

    def getNum(self, htmltree):
        raw = eval_first_xpath(htmltree, self._field_xpaths("number", [self.expr_number]))
        num = raw.split(',')[0].strip()
        if not num:
            raise ValueError("Empty number on JavBus page")
        return num

    def getTitle(self, htmltree):
        title = eval_first_xpath(htmltree, self._field_xpaths("title", [self.expr_title]))
        matches = re.findall(r'^.+?\s+(.*) - JavBus$', title)
        if not matches:
            raise ValueError(f"Unexpected JavBus title format: {title}")
        return str(matches[0]).strip()

    def getStudio(self, htmltree):
        if self.uncensored:
            return eval_first_xpath(
                htmltree, self._field_xpaths("studio_uncensored", [self.expr_studio2, self.expr_studio])
            )
        return eval_first_xpath(
            htmltree, self._field_xpaths("studio", [self.expr_studio, self.expr_studio2])
        )

    def getCover(self, htmltree):
        rel = eval_first_xpath(htmltree, self._field_xpaths("cover", [self.expr_cover]))
        raw_cover = urljoin("https://www.javbus.com", rel) if rel else ""
        cover_upgrade_conf = self.rules.get("cover_upgrade", {})
        if cover_upgrade_conf.get("strategy", "dmm_aws_2k_first") == "dmm_aws_2k_first":
            return resolve_dmm_hd_cover(
                self.number,
                self.session,
                fallback_cover=raw_cover,
                cover_upgrade_conf=cover_upgrade_conf,
            )
        return raw_cover

    def getRelease(self, htmltree):
        raw = eval_first_xpath(htmltree, self._field_xpaths("release", [self.expr_release]))
        m = re.search(r'\d{4}-\d{2}-\d{2}', raw)
        return m.group(0) if m else raw.strip().replace('/', '-')

    def getRuntime(self, htmltree):
        raw = eval_first_xpath(htmltree, self._field_xpaths("runtime", [self.expr_runtime]))
        m = re.search(r'\d+', raw)
        return m.group(0) if m else raw.strip(" ['']分鐘")

    def getActors(self, htmltree):
        actors = eval_all_xpaths(
            htmltree, self._field_xpaths("actor_nodes", [self.expr_actor]), deduplicate=False
        )
        b = []
        for i in actors:
            if hasattr(i, "attrib") and "title" in i.attrib:
                b.append(i.attrib['title'])
            elif isinstance(i, str) and i.strip():
                b.append(i.strip())
        return b

    def getActorPhoto(self, htmltree):
        actors = eval_all_xpaths(
            htmltree, self._field_xpaths("actorphoto_nodes", [self.expr_actorphoto]), deduplicate=False
        )
        d = {}
        for i in actors:
            if not hasattr(i, "attrib"):
                continue
            p = i.attrib.get('src', '')
            if not p or "nowprinting.gif" in p:
                continue
            t = i.attrib.get('title', '')
            if t:
                d[t] = urljoin("https://www.javbus.com", p)
        return d

    def getDirector(self, htmltree):
        if self.uncensored:
            return eval_first_xpath(
                htmltree, self._field_xpaths("director_uncensored", [self.expr_directorJa, self.expr_director])
            )
        return eval_first_xpath(
            htmltree, self._field_xpaths("director", [self.expr_director, self.expr_directorJa])
        )

    def getSeries(self, htmltree):
        if self.uncensored:
            return eval_first_xpath(
                htmltree, self._field_xpaths("series_uncensored", [self.expr_series2, self.expr_series])
            )
        return eval_first_xpath(
            htmltree, self._field_xpaths("series", [self.expr_series, self.expr_series2])
        )

    def getLabel(self, htmltree):
        return eval_first_xpath(htmltree, self._field_xpaths("label", [self.expr_label]))

    def getExtrafanart(self, htmltree):
        return eval_all_xpaths(htmltree, self._field_xpaths("extrafanart", [self.expr_extrafanart]))

    def getTags(self, htmltree):
        keywords = eval_first_xpath(htmltree, [self.expr_tags])
        if keywords and ',' in keywords:
            tags = [t.strip() for t in keywords.split(',') if t.strip()]
            return tags[2:]
        return eval_all_xpaths(htmltree, self._field_xpaths("tags", [self.expr_tags]))

    def getOutline(self, htmltree):
        if self.morestoryline:
            if any(caller for caller in inspect.stack() if os.path.basename(caller.filename) == 'airav.py'):
                return ''   # 从airav.py过来的调用不计算outline直接返回，避免重复抓取数据拖慢处理速度
            from .storyline import getStoryline
            return getStoryline(self.number, uncensored=self.uncensored,
                                proxies=self.proxies, verify=self.verify)
        return ''
