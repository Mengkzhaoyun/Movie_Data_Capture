# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import getTreeAll, getTreeElement

_RULE_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_rules_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "scrapinglib" / "rules"
        if base.exists():
            return base
    return Path(__file__).resolve().parent / "rules"


def load_source_rules(source: str) -> Dict[str, Any]:
    """Load declarative YAML/JSON rules for a given scraping source."""
    if source in _RULE_CACHE:
        return _RULE_CACHE[source]

    rules_dir = _get_rules_dir()
    yaml_path = rules_dir / f"{source}.yaml"
    json_path = rules_dir / f"{source}.json"

    data: Dict[str, Any] = {}
    if yaml_path.exists():
        try:
            import yaml  # type: ignore
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            pass

    if not data and json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    _RULE_CACHE[source] = data
    return data


def eval_first_xpath(tree, xpaths: List[str], index: int = 0) -> str:
    """Evaluate a list of fallback XPaths and return the first non-empty string."""
    if tree is None or not xpaths:
        return ""
    for expr in xpaths:
        if not expr:
            continue
        try:
            val = getTreeElement(tree, expr, index)
            if isinstance(val, str) and val.strip():
                return val.strip()
        except Exception:
            continue
    return ""


def eval_all_xpaths(tree, xpaths: List[str], deduplicate: bool = True) -> List[Any]:
    """Evaluate a list of XPaths and combine results."""
    if tree is None or not xpaths:
        return []
    combined: List[Any] = []
    for expr in xpaths:
        if not expr:
            continue
        try:
            items = getTreeAll(tree, expr)
            for item in items:
                if isinstance(item, str):
                    cleaned = item.strip()
                    if cleaned and cleaned != ",":
                        if not deduplicate or cleaned not in combined:
                            combined.append(cleaned)
                elif item is not None:
                    if not deduplicate or item not in combined:
                        combined.append(item)
        except Exception:
            continue
    return combined


def build_dmm_candidate_cids(number: str) -> List[str]:
    """Convert standard movie number (e.g. CAWB-012, FNS-152) to candidate DMM CIDs."""
    if not number:
        return []
    m = re.match(r"^([a-zA-Z]{2,6})-(\d{2,5})$", number.strip())
    if not m:
        return []
    prefix = m.group(1).lower()
    digits = m.group(2)
    padded = digits.zfill(5)
    cids = [
        f"{prefix}{padded}",
        f"1{prefix}{padded}",
        f"{prefix}{digits}",
    ]
    # Deduplicate while preserving order
    seen = set()
    result = []
    for cid in cids:
        if cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def resolve_dmm_hd_cover(
    number: str,
    session,
    fallback_cover: str = "",
    cover_upgrade_conf: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Probe DMM official AWS 2K/HD watermark-free cover first;
    fall back to the source's own cover (e.g. JavDB) if unavailable.
    """
    cids = build_dmm_candidate_cids(number)
    if not cids or session is None:
        return fallback_cover

    conf = cover_upgrade_conf or {}
    templates = conf.get("dmm_templates") or [
        "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{cid}/{cid}pl.jpg",
        "https://pics.dmm.co.jp/mono/movie/adult/{cid}/{cid}pl.jpg",
    ]
    min_size = int(conf.get("min_content_length", 20000))

    for cid in cids:
        for tpl in templates:
            url = tpl.format(cid=cid)
            try:
                resp = session.head(url, allow_redirects=True, timeout=5)
                final_url = str(getattr(resp, "url", url))
                if resp.status_code != 200 or "now_printing" in final_url or "noimage" in final_url:
                    continue
                content_len = int(resp.headers.get("content-length") or resp.headers.get("Content-Length") or 0)
                if content_len >= min_size:
                    return url
                if content_len == 0:
                    # Fallback range/get check if server omitted Content-Length on HEAD
                    g_resp = session.get(url, allow_redirects=True, timeout=6)
                    if (
                        g_resp.status_code == 200
                        and "now_printing" not in str(getattr(g_resp, "url", url))
                        and len(g_resp.content) >= min_size
                    ):
                        return url
            except Exception:
                continue

    return fallback_cover

