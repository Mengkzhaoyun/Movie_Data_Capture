import json
import socket
import time
import traceback
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import config


def _is_proxy_reachable(address: str, timeout: float = 0.5) -> bool:
    if not address or ":" not in address:
        return False
    host, port_str = address.rsplit(":", 1)
    try:
        port = int(port_str)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def _is_challenge_title(title: str, target_url: str) -> bool:
    if not title or not title.strip():
        return True
    t = title.strip()
    lower_t = t.lower()
    challenge_markers = [
        "just a moment",
        "请稍候",
        "請稍候",
        "attention required",
        "cloudflare",
        "security check",
    ]
    if any(m in lower_t for m in challenge_markers):
        return True
    # Chromium initially sets page.title to the bare hostname/URL before <title> is parsed
    host = urlparse(target_url).hostname or ""
    if host and lower_t == host.lower():
        return True
    if lower_t.startswith("http://") or lower_t.startswith("https://"):
        return True
    return False


def fetch_via_browser(
    target_url: str,
    cookie_filename: str = "javdb.json",
    max_wait_seconds: int = 25,
) -> Tuple[bool, str, str, Dict[str, str]]:
    """
    Use DrissionPage to solve Cloudflare Turnstile challenge (including auto-clicking
    the Turnstile widget when rendered), save cookies, and return:
        (success, final_url, html_text, cookies_dict)
    """
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except ImportError:
        print("[-] DrissionPage is not installed. Cloudflare auto-bypass is disabled.")
        return False, target_url, "", {}

    print(f"[*] Starting Cloudflare Browser Fetch for {target_url}...")
    co = ChromiumOptions()

    # Apply proxy only if configured and actually reachable
    proxy_conf = config.getInstance().proxy()
    if proxy_conf.enable and proxy_conf.address and _is_proxy_reachable(proxy_conf.address):
        ptype = "socks5" if proxy_conf.proxytype == "socks5h" else proxy_conf.proxytype
        if ptype in ("http", "https"):
            co.set_proxy(f"{ptype}://{proxy_conf.address}")

    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--disable-blink-features=AutomationControlled")

    page = None
    success = False
    final_url = target_url
    html_text = ""
    cookies_dict: Dict[str, str] = {}

    try:
        page = ChromiumPage(co)
        page.get(target_url)

        for i in range(max_wait_seconds):
            title = page.title or ""
            print(f"[*] CF Bypass waiting [{i}s] Title: {title}")
            if not _is_challenge_title(title, target_url):
                print(f"[+] Successfully bypassed Cloudflare for {target_url}!")
                final_url = page.url or target_url
                html_text = page.html or ""
                success = True

                # Extract and save cookies
                cookies_list = []
                try:
                    cookies_list = page.cookies(as_dict=False)
                except Exception:
                    cookies_list = page.cookies()

                if isinstance(cookies_list, dict):
                    cookies_dict = {str(k): str(v) for k, v in cookies_list.items()}
                elif isinstance(cookies_list, list):
                    cookie_dicts = []
                    for c in cookies_list:
                        if isinstance(c, dict):
                            cookie_dicts.append(c)
                            if "name" in c and "value" in c:
                                cookies_dict[str(c["name"])] = str(c["value"])
                    if cookie_dicts and cookie_filename:
                        save_path = Path.cwd() / cookie_filename
                        with open(save_path, "w", encoding="utf-8") as f:
                            json.dump(cookie_dicts, f, indent=4)
                        print(f"[+] Saved retrieved cookies to {save_path.absolute()}")
                break

            # Attempt to click Turnstile checkbox if rendered
            try:
                inp = page.ele("@name=cf-turnstile-response", timeout=0.4)
                if inp:
                    parent = inp.parent()
                    if parent and parent.rect.size[1] > 20:
                        parent.click.at(30, 25)
            except Exception:
                pass

            time.sleep(1)

    except Exception as e:
        print(f"[-] Auto-bypass failed: {e}")
        if config.getInstance().debug():
            traceback.print_exc()
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass

    return success, final_url, html_text, cookies_dict


def auto_bypass_cloudflare(target_url: str, cookie_filename: str = "javdb.json") -> bool:
    """
    Backward-compatible wrapper around fetch_via_browser.
    """
    ok, _, _, _ = fetch_via_browser(target_url, cookie_filename=cookie_filename)
    return ok
