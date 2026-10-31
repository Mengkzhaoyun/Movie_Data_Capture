# -*- coding: utf-8 -*-

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lxml import etree
from scrapinglib.airav import Airav
from scrapinglib.javbus import Javbus
from scrapinglib.javdb import Javdb
from scrapinglib.javlibrary import Javlibrary
from scrapinglib.rule_loader import (
    build_dmm_candidate_cids,
    build_dmm_cover_urls,
    extract_dmm_cid_from_url,
    resolve_dmm_hd_cover,
)


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

SAMPLE_JAVBUS_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta name="keywords" content="CAWB-012,kawaii,美少女,苗條,單體作品" />
  <title>CAWB-012 【重大発表】美しき天才バレリーナ 清野咲 - JavBus</title>
</head>
<body>
  <a class="bigImage" href="/pics/cover/cfuk_b.jpg"></a>
  <div class="col-md-3 info">
    <p><span class="header">識別碼:</span> <span>CAWB-012</span></p>
    <p><span class="header">發行日期:</span> 2026-07-31</p>
    <p><span class="header">長度:</span> 125分鐘</p>
    <p><span class="header">導演:</span> <a href="/director/1">イナバール</a></p>
    <p><span class="header">製作商:</span> <a href="/studio/1">kawaii</a></p>
  </div>
  <div class="star-box">
    <a href="/star/1"><img src="/pics/actress/1_a.jpg" title="清野咲" /></a>
    <div class="star-name"><a href="/star/1" title="清野咲">清野咲</a></div>
  </div>
</body>
</html>
"""

SAMPLE_JAVLIBRARY_TBODY_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div id="video_title"><h3><a href="/cn/javme3qe5i.html">CAWB-012 【重大発表】美しき天才バレリーナ 清野咲</a></h3></div>
  <img id="video_jacket_img" src="//pics.dmm.co.jp/mono/movie/adult/cawb012/cawb012pl.jpg" />
  <div id="video_id"><table><tbody><tr><td class="header">識別碼:</td><td class="text">CAWB-012</td></tr></tbody></table></div>
  <div id="video_date"><table><tbody><tr><td class="header">發行日期:</td><td class="text">2026-08-05</td></tr></tbody></table></div>
  <div id="video_length"><table><tbody><tr><td class="header">長度:</td><td><span class="text">120</span> 分钟</td></tr></tbody></table></div>
  <div id="video_director"><table><tbody><tr><td class="header">導演:</td><td class="text"><span class="director"><a href="vl_director.php?d=1">イナバール</a></span></td></tr></tbody></table></div>
  <div id="video_maker"><table><tbody><tr><td class="header">發行商:</td><td class="text"><span class="maker"><a href="vl_maker.php?m=1">kawaii</a></span></td></tr></tbody></table></div>
  <div id="video_genres"><table><tbody><tr><td class="header">類別:</td><td class="text"><span class="genre"><a href="vl_genre.php?g=1">美少女</a></span></td></tr></tbody></table></div>
  <div id="video_cast"><table><tbody><tr><td class="header">演員:</td><td class="text"><span class="cast"><span class="star"><a href="vl_star.php?s=1">清野咲</a></span></span></td></tr></tbody></table></div>
</body>
</html>
"""


class TestDeclarativeScrapers(unittest.TestCase):
    def setUp(self):
        self.parser = Javdb()
        self.parser.init()
        self.parser.number = "CAWB-012"
        self.parser.detailurl = "https://javdb.com/v/GZQMqq"
        self.parser.morestoryline = False

    def test_javdb_2026_dom_extraction(self):
        tree = etree.fromstring(SAMPLE_JAVDB_2026_HTML, etree.HTMLParser())
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

    def test_javdb_legacy_dom_fallback(self):
        self.parser.number = "IPZ-806"
        self.parser.session = None
        tree = etree.fromstring(SAMPLE_JAVDB_LEGACY_HTML, etree.HTMLParser())
        data = json.loads(self.parser.dictformat(tree))
        self.assertEqual(data["number"], "IPZ-806")
        self.assertEqual(data["actor"], ["天海つばさ"])
        self.assertEqual(data["cover"], "https://c0.jdbstatic.com/covers/ip/IPZ806.jpg")

    def test_javbus_declarative_extraction(self):
        bus = Javbus()
        bus.init()
        bus.number = "CAWB-012"
        bus.detailurl = "https://www.javbus.com/CAWB-012"
        bus.extraheader = {"Referer": bus.detailurl}
        bus.session = None
        tree = etree.fromstring(SAMPLE_JAVBUS_HTML, etree.HTMLParser())
        data = json.loads(bus.dictformat(tree))
        self.assertEqual(bus.cookies.get("dv"), "1")
        self.assertEqual(data["number"], "CAWB-012")
        self.assertEqual(data["title"], "【重大発表】美しき天才バレリーナ 清野咲")
        self.assertEqual(data["release"], "2026-07-31")
        self.assertEqual(data["runtime"], "125")
        self.assertEqual(data["studio"], "kawaii")
        self.assertEqual(data["actor"], ["清野咲"])
        self.assertEqual(data["cover"], "https://www.javbus.com/pics/cover/cfuk_b.jpg")

    def test_javlibrary_tbody_resilient_extraction(self):
        lib = Javlibrary()
        lib.init()
        lib.number = "CAWB-012"
        lib.detailurl = "https://www.javlibrary.com/cn/javme3qe5i.html"
        lib.session = None
        tree = etree.fromstring(SAMPLE_JAVLIBRARY_TBODY_HTML, etree.HTMLParser())
        data = json.loads(lib.dictformat(tree))
        self.assertEqual(data["number"], "CAWB-012")
        self.assertEqual(data["title"], "【重大発表】美しき天才バレリーナ 清野咲")
        self.assertEqual(data["release"], "2026-08-05")
        self.assertEqual(data["runtime"], "120")
        self.assertEqual(data["studio"], "kawaii")
        self.assertEqual(data["director"], "イナバール")
        self.assertEqual(data["actor"], ["清野咲"])
        self.assertEqual(data["tag"], ["美少女"])
        self.assertEqual(data["cover"], "https://pics.dmm.co.jp/mono/movie/adult/cawb012/cawb012pl.jpg")

    def test_airav_api_and_javbus_fallback(self):
        air = Airav()
        air.init()
        air.number = "CAWB-012"
        air.detailurl = "https://www.airav.wiki/api/video/barcode/CAWB-012?lng=zh-CN"
        air.javbus = {
            "number": "CAWB-012",
            "studio": "kawaii",
            "release": "2026-07-31",
            "year": "2026",
            "runtime": "125",
            "director": "イナバール",
            "cover": "https://www.javbus.com/pics/cover/cfuk_b.jpg",
        }
        api_payload = {
            "barcode": "CAWB-012",
            "name": "芭蕾舞天才美少女中出解禁 清野咲",
            "description": "这是中文剧情简介",
            "actors": [{"name": "清野咲"}],
            "tags": [{"name": "中出"}, {"name": "美少女"}],
            "images": ["https://example.com/1.jpg"],
        }
        data = json.loads(air.dictformat(api_payload))
        self.assertEqual(data["number"], "CAWB-012")
        self.assertEqual(data["title"], "芭蕾舞天才美少女中出解禁 清野咲")
        self.assertEqual(data["outline"], "这是中文剧情简介")
        self.assertEqual(data["actor"], ["清野咲"])
        self.assertEqual(data["studio"], "kawaii")

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
        # Known maker_1 studio (Faleno FNS -> 1fns00152 directly, no wasted unprefixed probe)
        cids_fns = build_dmm_candidate_cids("FNS-152")
        self.assertEqual(cids_fns, ["1fns00152", "1fns152"])

        # Known prestige_118 digital + mono studio (ABP -> 118abp00933, 118abp933)
        cids_abp = build_dmm_candidate_cids("ABP-933")
        self.assertEqual(cids_abp, ["118abp00933", "118abp933"])

        # Known prestige_118_mono_only studio (ABF/ABW -> mono 118abf125 first)
        urls_abf = build_dmm_cover_urls("ABF-125")
        self.assertEqual(
            urls_abf[0],
            "https://pics.dmm.co.jp/mono/movie/adult/118abf125/118abf125pl.jpg",
        )

        # Regression tests for Hunter (HUNTB), Planet Plus (AMBI), ROYAL (ROYD), TMA (T28), I.B.WORKS (IBW), Amateur (ANKK)
        self.assertEqual(
            build_dmm_cover_urls("HUNTB-382")[0],
            "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/huntb00382/huntb00382pl.jpg",
        )
        self.assertEqual(
            build_dmm_cover_urls("AMBI-186")[0],
            "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/h_237ambi00186/h_237ambi00186pl.jpg",
        )
        for royd_num, royd_cid in [("ROYD-199", "royd00199"), ("ROYD-271", "royd00271"), ("ROYD-294", "royd00294")]:
            self.assertEqual(
                build_dmm_cover_urls(royd_num)[0],
                f"https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{royd_cid}/{royd_cid}pl.jpg",
            )
        self.assertEqual(
            build_dmm_cover_urls("T28-605")[0],
            "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/55t2800605/55t2800605pl.jpg",
        )
        self.assertEqual(
            build_dmm_cover_urls("IBW-874")[0],
            "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/504ibw00874z/504ibw00874zpl.jpg",
        )
        self.assertEqual(
            build_dmm_cover_urls("ANKK-098")[0],
            "https://awsimgsrc.dmm.co.jp/pics_dig/digital/amateur/ankk098/ankk098jp.jpg",
        )

        # Extract CID from DMM trailer URL
        self.assertEqual(
            extract_dmm_cid_from_url("//cc3001.dmm.co.jp/litevideo/freepv/1/118/118abp00933/118abp00933_dmb_w.mp4"),
            "118abp00933",
        )

        mock_session = MagicMock()
        resp_404 = MagicMock()
        resp_404.status_code = 404
        resp_404.url = "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/1fns00152/1fns00152pl.jpg"
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
