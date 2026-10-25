# -*- coding: utf-8 -*-

import json
import re
from lxml import etree

import config
from .httprequest import request_session
from .javbus import Javbus
from .parser import Parser
from .rule_loader import (
    eval_all_xpaths,
    eval_first_xpath,
    load_source_rules,
    resolve_dmm_hd_cover,
)


class Airav(Parser):
    source = 'airav'

    expr_title = '/html/head/title/text()'
    expr_number = '/html/head/title/text()'
    expr_studio = '//a[contains(@href,"?video_factory=")]/text()'
    expr_release = '//li[contains(text(),"發片日期")]/text()'
    expr_outline = "string(//div[@class='d-flex videoDataBlock']/div[@class='synopsis']/p)"
    expr_actor = '//ul[@class="videoAvstarList"]/li/a[starts-with(@href,"/idol/")]/text()'
    expr_cover = '//img[contains(@src,"/storage/big_pic/")]/@src'
    expr_tags = '//div[@class="tagBtnMargin"]/a/text()'
    expr_extrafanart = '//div[@class="mobileImgThumbnail"]/a/@href'

    def extraInit(self):
        self.specifiedSource = None
        self.addtion_Javbus = True
        self.javbus = {"title": ""}
        self.rules = load_source_rules(self.source)
        self.fields_rules = self.rules.get("fields", {})
        self.session = None

    def _field_xpaths(self, key: str, fallback: list) -> list:
        configured = self.fields_rules.get(key)
        return configured if isinstance(configured, list) and configured else fallback

    def _try_fetch_airav_api(self) -> dict:
        endpoints = self.rules.get("api_endpoints") or [
            "https://www.airav.wiki/api/video/barcode/{number}?lng=zh-CN"
        ]
        for tpl in endpoints:
            url = tpl.format(number=self.number.upper())
            try:
                req = self.session.get(url, timeout=6, verify=self.verify)
                if req.status_code == 200 and req.text.strip().startswith("{"):
                    payload = json.loads(req.text)
                    res = payload.get("result")
                    if isinstance(res, dict) and res.get("name"):
                        self.detailurl = url
                        return res
            except Exception:
                continue
        return {}

    def search(self, number):
        self.number = number
        if self.specifiedUrl:
            self.detailurl = self.specifiedUrl
        else:
            self.detailurl = "https://www.airav.wiki/api/video/barcode/" + self.number.upper() + "?lng=zh-CN"

        if self.addtion_Javbus:
            try:
                engine = Javbus()
                javbusinfo = engine.scrape(self.number, self)
                if javbusinfo == 404 or not isinstance(javbusinfo, str):
                    self.javbus = {"title": ""}
                else:
                    self.javbus = json.loads(javbusinfo)
            except Exception:
                self.javbus = {"title": ""}

        self.session = request_session(cookies=self.cookies, proxies=self.proxies, verify=self.verify)
        api_result = self._try_fetch_airav_api()
        if api_result:
            return self.dictformat(api_result)

        # 若 AirAV 源站 (airav.wiki 521 / 域名拦截) 不可用，且 addtion_Javbus 已成功获取元数据，则平滑降级返回
        if self.addtion_Javbus and isinstance(self.javbus, dict) and self.javbus.get("title"):
            fallback_dic = dict(self.javbus)
            fallback_dic["source"] = self.source
            cover_upgrade_conf = self.rules.get("cover_upgrade", {})
            if cover_upgrade_conf.get("strategy", "dmm_aws_2k_first") == "dmm_aws_2k_first":
                fallback_dic["cover"] = resolve_dmm_hd_cover(
                    self.number,
                    self.session,
                    fallback_cover=fallback_dic.get("cover", ""),
                    cover_upgrade_conf=cover_upgrade_conf,
                )
            return json.dumps(fallback_dic, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

        return json.dumps({"title": ""}, ensure_ascii=False)

    def getNum(self, htmltree):
        if isinstance(htmltree, dict):
            res = htmltree.get("barcode", "")
            if res:
                return res
        if self.addtion_Javbus:
            result = self.javbus.get('number')
            if isinstance(result, str) and len(result):
                return result
        number = eval_first_xpath(htmltree, self._field_xpaths("number", [self.expr_number]))
        m = re.findall(r'^\[(.*?)]', number)
        return str(m[0]) if m else number

    def getTitle(self, htmltree):
        if isinstance(htmltree, dict):
            res = htmltree.get("name", "")
            if res:
                return res
        title = eval_first_xpath(htmltree, self._field_xpaths("title", [self.expr_title]))
        m = re.findall(r'](.*?)- AIRAV', title)
        return str(m[0]).strip() if m else title.strip()

    def getStudio(self, htmltree):
        if self.addtion_Javbus:
            result = self.javbus.get('studio')
            if isinstance(result, str) and len(result):
                return result
        if isinstance(htmltree, dict):
            factories = htmltree.get("factories") or []
            if factories and isinstance(factories[0], dict):
                return factories[0].get("name", "")
            return ""
        return eval_first_xpath(htmltree, self._field_xpaths("studio", [self.expr_studio]))

    def getRelease(self, htmltree):
        if self.addtion_Javbus:
            result = self.javbus.get('release')
            if isinstance(result, str) and len(result):
                return result
        if isinstance(htmltree, dict):
            return str(htmltree.get("publish_date", "")).strip()
        try:
            raw = eval_first_xpath(htmltree, self._field_xpaths("release", [self.expr_release]))
            return re.search(r'\d{4}-\d{2}-\d{2}', raw).group()
        except Exception:
            return ''

    def getYear(self, htmltree):
        if self.addtion_Javbus:
            result = self.javbus.get('year')
            if isinstance(result, str) and len(result):
                return result
        release = self.getRelease(htmltree)
        m = re.findall(r'\d{4}', release)
        return str(m[0]) if m else ''

    def getOutline(self, htmltree):
        if isinstance(htmltree, dict):
            return htmltree.get("description") or ""
        return eval_first_xpath(htmltree, self._field_xpaths("outline", [self.expr_outline]))

    def getRuntime(self, htmltree):
        if self.addtion_Javbus:
            result = self.javbus.get('runtime')
            if isinstance(result, str) and len(result):
                return result
        return ''

    def getDirector(self, htmltree):
        if self.addtion_Javbus:
            result = self.javbus.get('director')
            if isinstance(result, str) and len(result):
                return result
        return ''

    def getActors(self, htmltree):
        if isinstance(htmltree, dict):
            a = htmltree.get("actors") or []
            return [i["name"] for i in a if isinstance(i, dict) and i.get("name")]
        actors = eval_all_xpaths(htmltree, self._field_xpaths("actor", [self.expr_actor]))
        if actors:
            return actors
        if self.addtion_Javbus:
            result = self.javbus.get('actor')
            if isinstance(result, list) and len(result):
                return result
        return []

    def getCover(self, htmltree):
        raw_cover = ""
        if self.addtion_Javbus:
            result = self.javbus.get('cover')
            if isinstance(result, str) and len(result):
                raw_cover = result
        if not raw_cover:
            if isinstance(htmltree, dict):
                raw_cover = htmltree.get("img_url") or ""
            else:
                raw_cover = eval_first_xpath(htmltree, self._field_xpaths("cover", [self.expr_cover]))

        cover_upgrade_conf = self.rules.get("cover_upgrade", {})
        if cover_upgrade_conf.get("strategy", "dmm_aws_2k_first") == "dmm_aws_2k_first":
            return resolve_dmm_hd_cover(
                self.number,
                self.session,
                fallback_cover=raw_cover,
                cover_upgrade_conf=cover_upgrade_conf,
            )
        return raw_cover

    def getSeries(self, htmltree):
        if self.addtion_Javbus:
            result = self.javbus.get('series')
            if isinstance(result, str) and len(result):
                return result
        return ''

    def getExtrafanart(self, htmltree):
        if isinstance(htmltree, dict):
            return htmltree.get("images") or []
        if self.addtion_Javbus and self.javbus.get("extrafanart"):
            return self.javbus.get("extrafanart")
        return eval_all_xpaths(htmltree, self._field_xpaths("extrafanart", [self.expr_extrafanart]))

    def getTags(self, htmltree):
        if isinstance(htmltree, dict):
            tag = htmltree.get("tags") or []
            return [i["name"] for i in tag if isinstance(i, dict) and i.get("name")]
        return eval_all_xpaths(htmltree, self._field_xpaths("tags", [self.expr_tags]))
