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


_DMM_PREFIX_INDEX: Optional[Dict[str, Dict[str, Any]]] = None


def _get_dmm_prefix_index() -> Dict[str, Dict[str, Any]]:
    """Build and cache an O(1) lookup table from label prefix (e.g. 'ABF', 'ABP', 'FNS') to DMM maker rules."""
    global _DMM_PREFIX_INDEX
    if _DMM_PREFIX_INDEX is not None:
        return _DMM_PREFIX_INDEX

    makers_data = load_source_rules("dmm_makers")
    index: Dict[str, Dict[str, Any]] = {}
    groups = makers_data.get("groups", {})
    for group_name, group_conf in groups.items():
        maker_prefix = str(group_conf.get("maker_prefix", ""))
        cid_suffix = str(group_conf.get("cid_suffix", ""))
        channels = group_conf.get("channels") or ["digital_padded", "mono_raw", "mono_padded"]
        for p in group_conf.get("prefixes", []):
            key = str(p).strip().upper()
            if key:
                index[key] = {
                    "group": group_name,
                    "maker_prefix": maker_prefix,
                    "cid_suffix": cid_suffix,
                    "channels": list(channels),
                }
    _DMM_PREFIX_INDEX = index
    return index


def extract_dmm_cid_from_url(url_or_text: str) -> str:
    """Extract official DMM CID from a DMM preview video or image URL if present."""
    if not url_or_text:
        return ""
    m = re.search(r"dmm\.co\.jp/litevideo/freepv/[^/]+/[^/]+/([a-z0-9_]+)/", url_or_text, re.I)
    if m:
        return m.group(1).lower()
    m2 = re.search(
        r"dmm\.co\.jp/(?:pics_dig/)?(?:digital/video|digital/amateur|mono/movie/adult)/([a-z0-9_]+)/",
        url_or_text,
        re.I,
    )
    if m2:
        return m2.group(1).lower()
    return ""


def build_dmm_candidate_cids(number: str, hint_cid: str = "") -> List[str]:
    """
    Convert standard movie number (e.g. CAWB-012, FNS-152, ABP-933, ABF-125, T28-605, IBW-874)
    to deterministic DMM CIDs using the built-in studio prefix metadata registry.
    """
    cids: List[str] = []
    if hint_cid and hint_cid.strip():
        cids.append(hint_cid.strip().lower())

    if not number:
        return cids
    m = re.match(r"^([a-zA-Z][a-zA-Z0-9]{1,6})-(\d{2,5})$", number.strip())
    if not m:
        return cids

    prefix_upper = m.group(1).upper()
    prefix = m.group(1).lower()
    digits = m.group(2)
    padded = digits.zfill(5)

    prefix_index = _get_dmm_prefix_index()
    rule = prefix_index.get(prefix_upper)

    if rule is not None:
        mp = rule["maker_prefix"]
        sfx = rule.get("cid_suffix", "")
        for ch in rule["channels"]:
            if ch in ("digital_padded", "digital_legacy_padded", "mono_padded"):
                cids.append(f"{mp}{prefix}{padded}{sfx}")
            elif ch in ("mono_raw", "amateur_raw"):
                cids.append(f"{mp}{prefix}{digits}{sfx}")
    else:
        makers_data = load_source_rules("dmm_makers")
        fallback_mps = makers_data.get("fallback_maker_prefixes") or ["", "1", "118"]
        for mp in fallback_mps:
            cids.append(f"{mp}{prefix}{padded}")
        for mp in fallback_mps:
            cids.append(f"{mp}{prefix}{digits}")

    # Deduplicate while preserving deterministic priority order
    seen = set()
    result = []
    for cid in cids:
        if cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def build_dmm_cover_urls(
    number: str,
    cover_upgrade_conf: Optional[Dict[str, Any]] = None,
    hint_cid: str = "",
) -> List[str]:
    """
    Build ordered DMM cover URLs directly from studio metadata rules so that
    known prefixes (e.g. S1 '', SOD/Faleno '1', Prestige '118' digital vs DVD mono)
    hit the exact endpoint on the first request without blind polling.
    """
    conf = cover_upgrade_conf or {}
    makers_data = load_source_rules("dmm_makers")
    tpl_map = makers_data.get("templates") or {}
    digital_tpl = tpl_map.get(
        "digital", "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{cid}/{cid}pl.jpg"
    )
    digital_legacy_tpl = tpl_map.get(
        "digital_legacy", "https://pics.dmm.co.jp/digital/video/{cid}/{cid}pl.jpg"
    )
    mono_tpl = tpl_map.get(
        "mono", "https://pics.dmm.co.jp/mono/movie/adult/{cid}/{cid}pl.jpg"
    )
    amateur_tpl = tpl_map.get(
        "amateur", "https://awsimgsrc.dmm.co.jp/pics_dig/digital/amateur/{cid}/{cid}jp.jpg"
    )
    custom_templates = conf.get("dmm_templates")

    urls: List[str] = []

    def _add_url(u: str) -> None:
        if u and u not in urls:
            urls.append(u)

    if hint_cid and hint_cid.strip():
        hcid = hint_cid.strip().lower()
        _add_url(digital_tpl.format(cid=hcid))
        _add_url(digital_legacy_tpl.format(cid=hcid))
        _add_url(mono_tpl.format(cid=hcid))
        _add_url(amateur_tpl.format(cid=hcid))

    if not number:
        return urls

    m = re.match(r"^([a-zA-Z][a-zA-Z0-9]{1,6})-(\d{2,5})$", number.strip())
    if not m:
        return urls

    prefix_upper = m.group(1).upper()
    prefix = m.group(1).lower()
    digits = m.group(2)
    padded = digits.zfill(5)

    prefix_index = _get_dmm_prefix_index()
    rule = prefix_index.get(prefix_upper)

    if rule is not None:
        mp = rule["maker_prefix"]
        sfx = rule.get("cid_suffix", "")
        cid_padded = f"{mp}{prefix}{padded}{sfx}"
        cid_raw = f"{mp}{prefix}{digits}{sfx}"
        for ch in rule["channels"]:
            if ch == "digital_padded":
                _add_url(digital_tpl.format(cid=cid_padded))
            elif ch == "digital_legacy_padded":
                _add_url(digital_legacy_tpl.format(cid=cid_padded))
            elif ch == "mono_raw":
                _add_url(mono_tpl.format(cid=cid_raw))
            elif ch == "mono_padded":
                _add_url(mono_tpl.format(cid=cid_padded))
            elif ch == "amateur_raw":
                _add_url(amateur_tpl.format(cid=cid_raw))
        # Secondary safety net: if studio switched between prefixed and unprefixed DMM channel
        if mp or sfx:
            _add_url(digital_tpl.format(cid=f"{prefix}{padded}"))
            _add_url(mono_tpl.format(cid=f"{prefix}{digits}"))
    else:
        cids = build_dmm_candidate_cids(number, hint_cid=hint_cid)
        templates = custom_templates or [digital_tpl, digital_legacy_tpl, mono_tpl]
        for cid in cids:
            for tpl in templates:
                _add_url(tpl.format(cid=cid))
        _add_url(amateur_tpl.format(cid=f"{prefix}{digits}"))

    return urls


def resolve_dmm_hd_cover(
    number: str,
    session,
    fallback_cover: str = "",
    cover_upgrade_conf: Optional[Dict[str, Any]] = None,
    hint_cid: str = "",
) -> str:
    """
    Probe DMM official AWS 2K/HD or Mono watermark-free cover using deterministic
    studio prefix metadata rules first; fall back to the source's own cover if unavailable.
    """
    if session is None:
        return fallback_cover

    candidate_urls = build_dmm_cover_urls(
        number, cover_upgrade_conf=cover_upgrade_conf, hint_cid=hint_cid
    )
    if not candidate_urls:
        return fallback_cover

    conf = cover_upgrade_conf or {}
    min_size = int(conf.get("min_content_length", 20000))

    for url in candidate_urls:
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

