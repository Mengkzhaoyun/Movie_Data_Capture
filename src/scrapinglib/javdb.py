# -*- coding: utf-8 -*-

import re
from urllib.parse import urljoin
from lxml import etree
import config
from .httprequest import request_session
from .parser import Parser
from .rule_loader import (
    eval_all_xpaths,
    eval_first_xpath,
    extract_dmm_cid_from_url,
    load_source_rules,
    resolve_dmm_hd_cover,
)


class Javdb(Parser):
    source = 'javdb'

    expr_number = '//strong[contains(text(),"番號")]/../span/text()'
    expr_number2 = '//strong[contains(text(),"番號")]/../span/a/text()'
    expr_title = "/html/head/title/text()"
    expr_title_no = '//*[contains(@class,"movie-list")]/div/a/div[contains(@class, "video-title")]/text()'
    expr_runtime = '//strong[contains(text(),"時長")]/../span/text()'
    expr_runtime2 = '//strong[contains(text(),"時長")]/../span/a/text()'
    expr_uncensored = '//strong[contains(text(),"類別")]/../span/a[contains(@href,"/tags/uncensored?") or contains(@href,"/tags/western?")]'
    expr_actor = '//span[@class="value"]/a[contains(@href,"/actors/")]/text()'
    expr_actor2 = '//span[@class="value"]/a[contains(@href,"/actors/")]/../strong/@class'
    expr_release = '//strong[contains(text(),"日期")]/../span/text()'
    expr_release_no = '//*[contains(@class,"movie-list")]/div/a/div[contains(@class, "meta")]/text()'
    expr_studio = '//strong[contains(text(),"片商")]/../span/a/text()'
    expr_studio2 = '//strong[contains(text(),"賣家:")]/../span/a/text()'
    expr_director = '//strong[contains(text(),"導演")]/../span/text()'
    expr_director2 = '//strong[contains(text(),"導演")]/../span/a/text()'
    expr_cover = "//div[contains(@class, 'column-video-cover')]/a/img/@src"
    expr_cover2 = "//div[contains(@class, 'column-video-cover')]/img/@src"
    expr_cover_no = '//*[contains(@class,"movie-list")]/div/a/div[contains(@class, "cover")]/img/@src'
    expr_trailer = '//span[contains(text(),"預告片")]/../../video/source/@src'
    expr_extrafanart = "//article[@class='message video-panel']/div[@class='message-body']/div[@class='tile-images preview-images']/a[contains(@href,'/samples/')]/@href"
    expr_tags = '//strong[contains(text(),"類別")]/../span/a/text()'
    expr_tags2 = '//strong[contains(text(),"類別")]/../span/text()'
    expr_series = '//strong[contains(text(),"系列")]/../span/text()'
    expr_series2 = '//strong[contains(text(),"系列")]/../span/a/text()'
    expr_label = '//strong[contains(text(),"系列")]/../span/text()'
    expr_label2 = '//strong[contains(text(),"系列")]/../span/a/text()'
    expr_userrating = '//span[@class="score-stars"]/../text()'
    expr_uservotes = '//span[@class="score-stars"]/../text()'
    expr_actorphoto = '//strong[contains(text(),"演員:")]/../span/a[starts-with(@href,"/actors/")]'

    def extraInit(self):
        self.fixstudio = False
        self.noauth = False
        self.dbsite = 'javdb'
        self.rules = load_source_rules(self.source)
        self.fields_rules = self.rules.get("fields", {})

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
        # special
        if core and core.dbcookies:
            self.cookies = core.dbcookies
        else:
            self.cookies = {'over18': '1', 'theme': 'auto', 'locale': 'zh'}
        if core and core.dbsite:
            self.dbsite = core.dbsite
        else:
            self.dbsite = 'javdb'

    def _is_challenge_response(self, resp) -> bool:
        if resp.status_code in [403, 503]:
            return True
        keywords = self.rules.get("challenge_keywords") or ["Just a moment", "请稍候"]
        return any(kw in resp.text for kw in keywords)

    def _fetch_with_cf_fallback(self, url: str):
        resp = self.session.get(url)
        if self._is_challenge_response(resp):
            from scrapinglib.cf_bypass import auto_bypass_cloudflare
            base_url = f"https://{self.dbsite}.com/"
            if auto_bypass_cloudflare(base_url, "javdb.json"):
                from adc_function import load_cookies
                new_cookies, _ = load_cookies("javdb.json")
                if new_cookies:
                    self.session.cookies.update(new_cookies)
                    resp = self.session.get(url)
        return resp

    def search(self, number: str):
        self.number = number
        self.session = request_session(cookies=self.cookies, proxies=self.proxies, verify=self.verify)
        if self.specifiedUrl:
            self.detailurl = self.specifiedUrl
        else:
            self.detailurl = self.queryNumberUrl(number)
        resp = self._fetch_with_cf_fallback(self.detailurl)
        self.deatilpage = resp.text
        auth_keywords = self.rules.get("auth_wall_keywords") or [
            '此內容需要登入才能查看或操作',
            '需要VIP權限才能訪問此內容',
        ]
        if any(kw in self.deatilpage for kw in auth_keywords):
            self.noauth = True
            self.imagecut = 0
            result = self.dictformat(self.querytree)
        else:
            htmltree = etree.fromstring(self.deatilpage, etree.HTMLParser())
            result = self.dictformat(htmltree)
        return result

    def queryNumberUrl(self, number):
        search_conf = self.rules.get("search", {})
        url_tpl = search_conf.get("url_template", "https://{site}.com/search?q={number}&f=all")
        javdb_url = url_tpl.format(site=self.dbsite, number=number)
        try:
            resp = self._fetch_with_cf_fallback(javdb_url)
            self.querytree = etree.fromstring(resp.text, etree.HTMLParser())

            urls_xpath = search_conf.get("item_urls_xpath", '//*[contains(@class,"movie-list")]/div/a/@href')
            ids_xpath = search_conf.get(
                "item_ids_xpath",
                '//*[contains(@class,"movie-list")]/div/a/div[contains(@class, "video-title")]/strong/text()',
            )

            urls = self.getTreeAll(self.querytree, urls_xpath)
            if not urls:
                print(f'[!] {self.number}: No search results found in javdb')
                raise Exception(f'[!] {self.number}: No search results found in javdb')

            # 欧美影片的特殊处理
            if re.search(r'[a-zA-Z]+\.\d{2}\.\d{2}\.\d{2}', number):
                print(f'[+] {self.number}: Western video detected')
                correct_url = urls[0]
            else:
                ids = self.getTreeAll(self.querytree, ids_xpath)
                print(f'[+] {self.number}: Found {len(ids)} results: {ids}')

                try:
                    self.queryid = ids.index(number)
                    correct_url = urls[self.queryid]
                except ValueError:
                    if not ids:
                        print(f'[!] {self.number}: No IDs found in search results')
                        raise ValueError("No IDs found in javdb search results")

                    if ids[0].upper() != number.upper():
                        print(f'[!] {self.number}: Expected {number}, but found {ids[0]}')
                        raise ValueError(f"number not found in javdb (found: {ids[0]})")

                    self.queryid = 0
                    correct_url = urls[0]
                except IndexError as e:
                    print(f'[!] {self.number}: Index error - urls:{len(urls)}, ids:{len(ids)}')
                    raise IndexError(f"Index mismatch: urls({len(urls)}), ids({len(ids)})") from e

            return urljoin(resp.url, correct_url)

        except Exception as e:
            print(f'[!] {self.number}: Error in queryNumberUrl: {str(e)}')
            print(f'[!] Response status: {resp.status_code if "resp" in locals() else "N/A"}')
            print(f'[!] Response URL: {resp.url if "resp" in locals() else "N/A"}')
            raise

    def getNum(self, htmltree):
        if self.noauth:
            return self.number
        # 番号被分割开，需要合并后才是完整番号
        part1 = eval_first_xpath(htmltree, self._field_xpaths("number_suffix", [self.expr_number]))
        part2 = eval_first_xpath(htmltree, self._field_xpaths("number_prefix", [self.expr_number2]))
        dp_number = part2 + part1
        # NOTE 检测匹配与更新 self.number
        if dp_number.upper() != self.number.upper():
            raise Exception(f'[!] {self.number}: find [{dp_number}] in javdb, not match')
        self.number = dp_number
        return self.number

    def getTitle(self, htmltree):
        if self.noauth:
            return eval_first_xpath(htmltree, self._field_xpaths("title_noauth", [self.expr_title_no]), self.queryid)
        browser_title = eval_first_xpath(htmltree, self._field_xpaths("title", [self.expr_title]))
        title = browser_title[:browser_title.find(' | JavDB')].strip()
        return title.replace(self.number, '').strip()

    def getCover(self, htmltree):
        if self.noauth:
            raw_cover = eval_first_xpath(
                htmltree, self._field_xpaths("cover_noauth", [self.expr_cover_no]), self.queryid
            )
        else:
            raw_cover = eval_first_xpath(
                htmltree, self._field_xpaths("cover", [self.expr_cover, self.expr_cover2])
            )

        # 方案 1：优先基于内置片商元数据规则与预告片 CID 定位 DMM 官方无水印原图，失败则回退 JavDB 封面
        cover_upgrade_conf = self.rules.get("cover_upgrade", {})
        if cover_upgrade_conf.get("strategy", "dmm_aws_2k_first") == "dmm_aws_2k_first":
            hint_cid = ""
            if not self.noauth:
                hint_cid = extract_dmm_cid_from_url(self.getTrailer(htmltree))
            upgraded = resolve_dmm_hd_cover(
                self.number,
                getattr(self, "session", None),
                fallback_cover=raw_cover,
                cover_upgrade_conf=cover_upgrade_conf,
                hint_cid=hint_cid,
            )
            if upgraded and upgraded != raw_cover and config.getInstance().debug():
                print(f"[+] {self.number}: Upgraded JavDB cover to DMM 2K watermark-free cover: {upgraded}")
            return upgraded
        return raw_cover

    def getRelease(self, htmltree):
        if self.noauth:
            return eval_first_xpath(
                htmltree, self._field_xpaths("release_noauth", [self.expr_release_no]), self.queryid
            )
        return eval_first_xpath(htmltree, self._field_xpaths("release", [self.expr_release])).replace('/', '-')

    def getRuntime(self, htmltree):
        raw = eval_first_xpath(
            htmltree, self._field_xpaths("runtime", [self.expr_runtime, self.expr_runtime2])
        )
        m = re.search(r'\d+', raw)
        return m.group(0) if m else raw.rstrip('mi').strip()

    def getStudio(self, htmltree):
        return eval_first_xpath(
            htmltree, self._field_xpaths("studio", [self.expr_studio, self.expr_studio2])
        )

    def getDirector(self, htmltree):
        return eval_first_xpath(
            htmltree, self._field_xpaths("director", [self.expr_director, self.expr_director2])
        )

    def getSeries(self, htmltree):
        results = eval_all_xpaths(
            htmltree, self._field_xpaths("series", [self.expr_series, self.expr_series2])
        )
        result = ''.join(results)
        if not result and self.fixstudio:
            result = self.getStudio(htmltree)
        return result

    def getLabel(self, htmltree):
        results = eval_all_xpaths(
            htmltree, self._field_xpaths("label", [self.expr_label, self.expr_label2])
        )
        result = ''.join(results)
        if not result and self.fixstudio:
            result = self.getStudio(htmltree)
        return result

    def getActors(self, htmltree):
        try:
            actor_gender = config.getInstance().actor_gender()
        except Exception:
            actor_gender = 'female'

        if actor_gender not in ['female', 'male', 'both', 'all']:
            actor_gender = 'female'

        # 优先使用声明式规则提取（兼容 2026 新版 a.actor-female 与旧版 strong.symbol）
        if actor_gender == 'female':
            r = eval_all_xpaths(
                htmltree,
                self._field_xpaths(
                    "actor_female",
                    [
                        '//span[@class="value"]/a[contains(@href,"/actors/") and contains(@class,"actor-female")]/text()',
                        '//span[@class="value"]/strong[@class="symbol female"]/preceding-sibling::a[1]/text()',
                    ],
                ),
            )
            # 若页面未标记性别 class，则回退全部演员避免漏提
            if not r:
                r = eval_all_xpaths(htmltree, self._field_xpaths("actor_all", [self.expr_actor]))
        elif actor_gender == 'male':
            r = eval_all_xpaths(
                htmltree,
                self._field_xpaths(
                    "actor_male",
                    [
                        '//span[@class="value"]/a[contains(@href,"/actors/") and (contains(@class,"actor-male") or not(@class))]/text()',
                        '//span[@class="value"]/strong[@class="symbol male"]/preceding-sibling::a[1]/text()',
                    ],
                ),
            )
        else:
            r = eval_all_xpaths(htmltree, self._field_xpaths("actor_all", [self.expr_actor]))

        if re.match(r'FC2-[\d]+', self.number, re.A) and not r:
            r = '素人'
            self.fixstudio = True
        return r

    def getOutline(self, htmltree):
        if self.morestoryline:
            from .storyline import getStoryline
            return getStoryline(
                self.number,
                self.getUncensored(htmltree),
                proxies=self.proxies,
                verify=self.verify,
            )
        return ''

    def getTrailer(self, htmltree):
        video = eval_first_xpath(htmltree, self._field_xpaths("trailer", [self.expr_trailer]))
        if video:
            if 'https:' not in video:
                video_url = 'https:' + video
            else:
                video_url = video
        else:
            video_url = ''
        return video_url

    def getExtrafanart(self, htmltree):
        return eval_all_xpaths(htmltree, self._field_xpaths("extrafanart", [self.expr_extrafanart]))

    def getTags(self, htmltree):
        return eval_all_xpaths(htmltree, self._field_xpaths("tags", [self.expr_tags, self.expr_tags2]))

    def getUserRating(self, htmltree):
        try:
            numstrs = eval_first_xpath(htmltree, self._field_xpaths("userrating", [self.expr_userrating]))
            nums = re.findall('[0-9.]+', numstrs)
            return float(nums[0])
        except Exception:
            return ''

    def getUserVotes(self, htmltree):
        try:
            result = eval_first_xpath(htmltree, self._field_xpaths("uservotes", [self.expr_uservotes]))
            v = re.findall('[0-9.]+', result)
            return int(v[1])
        except Exception:
            return ''

    def getaphoto(self, url, session):
        html_page = session.get(url).text
        img_url = re.findall(r'<span class\=\"avatar\" style\=\"background\-image\: url\((.*?)\)', html_page)
        return img_url[0] if img_url else ''

    def getActorPhoto(self, htmltree):
        actorall = eval_all_xpaths(
            htmltree, self._field_xpaths("actor_nodes", [self.expr_actorphoto]), deduplicate=False
        )
        if not actorall:
            return {}
        actors = self.getActors(htmltree)
        actor_photo = {}
        for i in actorall:
            if not hasattr(i, 'attrib') or 'href' not in i.attrib:
                continue
            x = re.findall(r'/actors/(.*)', i.attrib['href'], re.A)
            if not len(x) or not len(x[0]) or i.text not in actors:
                continue
            try:
                pic_url = self.getaphoto(urljoin(f'https://{self.dbsite}.com', i.attrib['href']), self.session)
                if len(pic_url):
                    actor_photo[i.text] = pic_url
            except Exception:
                pass
        return actor_photo
