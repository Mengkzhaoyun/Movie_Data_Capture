# -*- coding: utf-8 -*-

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lxml import etree
from scrapinglib.javdb import Javdb
from scrapinglib.rule_loader import build_dmm_candidate_cids, resolve_dmm_hd_cover


SAMPLE_JAVDB_2026_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title> CAWB-012 【FANZA限定】美しき天才バレリーナ 清野咲 | JavDB 成人影片資料庫 </title>
</head>
<body>
  <div class="column-video-cover">
    <a href="/v/GZQMqq"><img src="https://c0.jdbstatic.com/covers/gz/GZQMqq.jpg" /></a>
  </div>
  <nav class="panel movie-panel-info">
    <div class="panel-block first-block">
      <strong>番號:</strong>
      <span class="value"><a href="/video_codes/CAWB">CAWB</a>-012</span>
    </div>
    <div class="panel-block">
      <strong>日期:</strong>
      <span class="value">2026-08-05</span>
    </div>
    <div class="panel-block">
      <strong>時長:</strong>
      <span class="value">120 分鍾</span>
    </div>
    <div class="panel-block">
      <strong>導演:</strong>
      <span class="value"><a href="/directors/nE6">イナバール</a></span>
    </div>
    <div class="panel-block">
      <strong>片商:</strong>
      <span class="value"><a href="/makers/rmZ">kawaii</a></span>
    </div>
    <div class="panel-block">
      <strong>評分:</strong>
      <span class="value"><span class="score-stars"></span> 4.56分, 由1668人評價</span>
    </div>
    <div class="panel-block">
      <strong>類別:</strong>
      <span class="value"><a href="/tags?c7=312">美少女電影</a>, <a href="/tags?c4=65">苗條</a></span>
    </div>
    <div class="panel-block">
      <strong>演員:</strong>
      <span class="value">
        <a class="actor-female" href="/actors/xvm6B">清野咲</a>,
        <a href="/actors/65x3M">野島誠</a>,
        <a href="/actors/NwRax">ピエール剣</a>
      </span>
    </div>
  </nav>
</body>
</html>
"""

SAMPLE_JAVDB_LEGACY_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title> IPZ-806  legacy test title | JavDB </title>
</head>
<body>
  <div class="column-video-cover">
    <img src="https://c0.jdbstatic.com/covers/ip/IPZ806.jpg" />
  </div>
  <nav class="panel movie-panel-info">
    <div class="panel-block">
      <strong>番號:</strong>
      <span class="value"><a href="/video_codes/IPZ">IPZ</a>-806</span>
    </div>
    <div class="panel-block">
      <strong>演員:</strong>
      <span class="value">
        <a href="/actors/a1">天海つばさ</a><strong class="symbol female">♀</strong>
        <a href="/actors/m1">森林原人</a><strong class="symbol male">♂</strong>
      </span>
    </div>
  </nav>
</body>
</html>
"""


class TestJavdbDeclarative(unittest.TestCase):
    def setUp(self):
        self.parser = Javdb()
        self.parser.init()
        self.parser.number = "CAWB-012"
        self.parser.detailurl = "https://javdb.com/v/GZQMqq"
        self.parser.morestoryline = False

    def test_2026_dom_extraction(self):
        tree = etree.fromstring(SAMPLE_JAVDB_2026_HTML, etree.HTMLParser())
        # Mock session to skip network on actor photo & test DMM cover upgrade
        mock_session = MagicMock()
        head_resp = MagicMock()
        head_resp.status_code = 200
        head_resp.url = "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/cawb00012/cawb00012pl.jpg"
        head_resp.headers = {"content-length": "778780"}
        mock_session.head.return_value = head_resp
        get_resp = MagicMock()
        get_resp.text = '<span class="avatar" style="background-image: url(https://c0.jdbstatic.com/avatars/xv/xvm6B.jpg)"></span>'
        mock_session.get.return_value = get_resp
        self.parser.session = mock_session

        data = json.loads(self.parser.dictformat(tree))
        self.assertEqual(data["number"], "CAWB-012")
        self.assertEqual(data["title"], "【FANZA限定】美しき天才バレリーナ 清野咲")
        self.assertEqual(data["actor"], ["清野咲"])
        self.assertEqual(data["runtime"], "120")
        self.assertEqual(data["studio"], "kawaii")
        self.assertEqual(data["director"], "イナバール")
        self.assertEqual(
            data["cover"],
            "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/cawb00012/cawb00012pl.jpg",
        )
        self.assertEqual(data["actor_photo"], {"清野咲": "https://c0.jdbstatic.com/avatars/xv/xvm6B.jpg"})

    def test_legacy_dom_fallback(self):
        self.parser.number = "IPZ-806"
        self.parser.session = None
        tree = etree.fromstring(SAMPLE_JAVDB_LEGACY_HTML, etree.HTMLParser())
        data = json.loads(self.parser.dictformat(tree))
        self.assertEqual(data["number"], "IPZ-806")
        self.assertEqual(data["actor"], ["天海つばさ"])
        self.assertEqual(data["cover"], "https://c0.jdbstatic.com/covers/ip/IPZ806.jpg")

    def test_field_fault_isolation_preserves_metadata(self):
        tree = etree.fromstring(SAMPLE_JAVDB_2026_HTML, etree.HTMLParser())
        self.parser.session = None

        def broken_actors(_tree):
            raise IndexError("simulated DOM drift in actor selector")

        self.parser.getActors = broken_actors
        data = json.loads(self.parser.dictformat(tree))
        self.assertEqual(data["number"], "CAWB-012")
        self.assertEqual(data["title"], "【FANZA限定】美しき天才バレリーナ 清野咲")
        self.assertEqual(data["actor"], [])
        self.assertEqual(data["cover"], "https://c0.jdbstatic.com/covers/gz/GZQMqq.jpg")

    def test_dmm_cover_fallback_on_404_or_now_printing(self):
        cids = build_dmm_candidate_cids("FNS-152")
        self.assertEqual(cids, ["fns00152", "1fns00152", "fns152"])

        mock_session = MagicMock()
        resp_404 = MagicMock()
        resp_404.status_code = 404
        resp_404.url = "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/fns00152/fns00152pl.jpg"
        resp_404.headers = {"content-length": "2732"}
        mock_session.head.return_value = resp_404

        cover = resolve_dmm_hd_cover(
            "FNS-152",
            mock_session,
            fallback_cover="https://c0.jdbstatic.com/covers/fn/FNS152.jpg",
        )
        self.assertEqual(cover, "https://c0.jdbstatic.com/covers/fn/FNS152.jpg")


if __name__ == "__main__":
    unittest.main()

