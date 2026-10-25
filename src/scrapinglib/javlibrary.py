# -*- coding: utf-8 -*-

import re
from urllib.parse import urljoin
from lxml import etree

from adc_function import load_cookies
from .httprequest import request_session
from .parser import Parser
from .rule_loader import (
    eval_all_xpaths,
    eval_first_xpath,
    load_source_rules,
    resolve_dmm_hd_cover,
)


class Javlibrary(Parser):
    source = 'javlibrary'

    expr_number = '//div[@id="video_id"]//td[@class="text"]/text()'
    expr_title = '//div[@id="video_title"]/h3/a/text()'
    expr_actor = '//div[@id="video_cast"]//span[@class="star"]/a/text()'
    expr_tags = '//div[@id="video_genres"]//span[@class="genre"]/a/text()'
    expr_cover = '//img[@id="video_jacket_img"]/@src'
    expr_release = '//div[@id="video_date"]//td[@class="text"]/text()'
    expr_studio = '//div[@id="video_maker"]//td[@class="text"]//a/text()'
    expr_runtime = '//div[@id="video_length"]//span[@class="text"]/text()'
    expr_userrating = '//div[@id="video_review"]//span[@class="score"]/text()'
    expr_director = '//div[@id="video_director"]//td[@class="text"]//a/text()'
    expr_extrafanart = '//div[@class="previewthumbs"]/img/@src'

    def extraInit(self):
        self.htmltree = None
        self.rules = load_source_rules(self.source)
        self.fields_rules = self.rules.get("fields", {})
        self.cookies = dict(self.rules.get("default_cookies") or {'over18': '18'})

    def _field_xpaths(self, key: str, fallback: list) -> list:
        configured = self.fields_rules.get(key)
        return configured if isinstance(configured, list) and configured else fallback

    def updateCore(self, core):
        if core and core.proxies:
            self.proxies = core.proxies
        if core and core.verify:
            self.verify = core.verify
        if core and core.morestoryline:
            self.morestoryline = True
        if core and core.specifiedSource == self.source:
            self.specifiedUrl = core.specifiedUrl
        self.cookies = dict(self.rules.get("default_cookies") or {'over18': '18'})
        cookies_dict, _ = load_cookies('javlibrary.json')
        if isinstance(cookies_dict, dict):
            self.cookies.update(cookies_dict)

    def _is_challenge(self, status_code: int, text: str) -> bool:
        if status_code in [403, 503]:
            return True
        keywords = self.rules.get("challenge_keywords") or ["Just a moment", "请稍候", "請稍候"]
        return any(kw in (text or "") for kw in keywords)

    def _fetch_page(self, url: str):
        """
        Fetch URL via curl_cffi first; if blocked by Cloudflare Turnstile,
        upgrade to DrissionPage browser session and directly reuse rendered HTML + final URL.
        """
        try:
            resp = self.session.get(url, allow_redirects=True)
            if not self._is_challenge(resp.status_code, resp.text):
                return str(resp.url), resp.text
        except Exception:
            resp = None

        from scrapinglib.cf_bypass import fetch_via_browser
        ok, final_url, html_text, new_cookies = fetch_via_browser(url, "javlibrary.json")
        if ok and html_text:
            if new_cookies:
                self.session.cookies.update(new_cookies)
            return final_url, html_text

        if resp is not None:
            return str(resp.url), resp.text
        return url, ""

    def search(self, number):
        self.number = number.upper()
        self.session = request_session(cookies=self.cookies, proxies=self.proxies, verify=self.verify)
        if self.specifiedUrl:
            self.detailurl = self.specifiedUrl
        else:
            self.detailurl = self.queryNumberUrl(self.number)
        if not self.detailurl:
            return 404
        if self.htmltree is None:
            final_url, html_text = self._fetch_page(self.detailurl)
            if not html_text:
                return 404
            self.detailurl = final_url
            self.htmltree = etree.fromstring(html_text, etree.HTMLParser())
        result = self.dictformat(self.htmltree)
        return result

    def queryNumberUrl(self, number: str):
        search_conf = self.rules.get("search", {})
        url_tpl = search_conf.get(
            "url_template", "https://www.javlibrary.com/cn/vl_searchbyid.php?keyword={number}"
        )
        queryUrl = url_tpl.format(number=number)
        final_url, html_text = self._fetch_page(queryUrl)
        if not html_text:
            return None

        detail_pattern = search_conf.get("detail_url_pattern", r'(/\?v=jav|/jav[a-zA-Z0-9]+\.html)')
        if re.search(detail_pattern, final_url):
            self.htmltree = etree.fromstring(html_text, etree.HTMLParser())
            return final_url

        queryTree = etree.fromstring(html_text, etree.HTMLParser())
        ids_xpath = search_conf.get("item_ids_xpath", '//div[@class="id"]/text()')
        urls_xpath = search_conf.get("item_urls_xpath", '//div[@class="id"]/../@href')
        numbers = [n.strip().upper() for n in queryTree.xpath(ids_xpath)]
        if number.upper() in numbers:
            urls = queryTree.xpath(urls_xpath)
            detailurl = urls[numbers.index(number.upper())]
            return urljoin("https://www.javlibrary.com/cn/", detailurl.lstrip('./'))
        return None

    def getNum(self, htmltree):
        return eval_first_xpath(htmltree, self._field_xpaths("number", [self.expr_number]))

    def getTitle(self, htmltree):
        title = eval_first_xpath(htmltree, self._field_xpaths("title", [self.expr_title]))
        num = self.getNum(htmltree)
        if num:
            title = title.replace(num, '').strip()
        return title

    def getCover(self, htmltree):
        url = eval_first_xpath(htmltree, self._field_xpaths("cover", [self.expr_cover]))
        if url and not url.startswith('http'):
            url = 'https:' + url
        cover_upgrade_conf = self.rules.get("cover_upgrade", {})
        if cover_upgrade_conf.get("strategy", "dmm_aws_2k_first") == "dmm_aws_2k_first":
            return resolve_dmm_hd_cover(
                self.number,
                self.session,
                fallback_cover=url,
                cover_upgrade_conf=cover_upgrade_conf,
            )
        return url

    def getRelease(self, htmltree):
        return eval_first_xpath(
            htmltree, self._field_xpaths("release", [self.expr_release])
        ).replace('/', '-')

    def getStudio(self, htmltree):
        return eval_first_xpath(htmltree, self._field_xpaths("studio", [self.expr_studio]))

    def getRuntime(self, htmltree):
        raw = eval_first_xpath(htmltree, self._field_xpaths("runtime", [self.expr_runtime]))
        m = re.search(r'\d+', raw)
        return m.group(0) if m else raw.strip()

    def getDirector(self, htmltree):
        return eval_first_xpath(htmltree, self._field_xpaths("director", [self.expr_director]))

    def getActors(self, htmltree):
        return eval_all_xpaths(htmltree, self._field_xpaths("actor", [self.expr_actor]))

    def getTags(self, htmltree):
        return eval_all_xpaths(htmltree, self._field_xpaths("tags", [self.expr_tags]))

    def getExtrafanart(self, htmltree):
        return eval_all_xpaths(htmltree, self._field_xpaths("extrafanart", [self.expr_extrafanart]))

    def getUserRating(self, htmltree):
        numstrs = eval_first_xpath(htmltree, self._field_xpaths("userrating", [self.expr_userrating]))
        nums = re.findall(r'[0-9.]+', numstrs)
        if nums:
            return float(nums[0])
        return ''

    def getOutline(self, htmltree):
        if self.morestoryline:
            from .storyline import getStoryline
            return getStoryline(self.number, self.getUncensored(htmltree),
                                proxies=self.proxies, verify=self.verify)
        return ''
