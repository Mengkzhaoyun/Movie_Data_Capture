import os
import json
import logging
from pathlib import Path
import time
import traceback
import config

def auto_bypass_cloudflare(target_url, cookie_filename="javdb.json"):
    """
    Spawns a headless browser to solve Cloudflare Turnstile automated challenge
    and saves the extracted cookies.
    """
    try:
        from DrissionPage import ChromiumPage, ChromiumOptions
    except ImportError:
        print("[-] DrissionPage is not installed. Cloudflare auto-bypass is disabled.")
        return False

    print(f"[*] Starting Cloudflare Auto-Bypass for {target_url}...")
    co = ChromiumOptions()
    
    # Apply proxy if configured
    proxy_conf = config.getInstance().proxy()
    if proxy_conf.enable and proxy_conf.address:
        co.set_proxy(f"{proxy_conf.proxytype}://{proxy_conf.address}")
        
    # Start headless
    co.headless(True)
    # Anti-detection args
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--incognito')
    
    page = None
    success = False
    try:
        page = ChromiumPage(co)
        page.get(target_url)
        
        # Wait for challenge to resolve
        for i in range(25):
            title = page.title
            print(f"[*] CF Bypass waiting [{i}s] Title: {title}")
            if "Just a moment" not in title and "请稍候" not in title and len(title) > 0:
                print(f"[+] Successfully bypassed Cloudflare for {target_url}!")
                
                # Extract and save cookies
                cookies_list = []
                try:
                    cookies_list = page.cookies(as_dict=False)
                except Exception:
                    cookies_list = page.cookies()
                    
                if cookies_list:
                    # convert to EditThisCookie format supported by load_cookies
                    cookie_dicts = []
                    for c in cookies_list:
                        if isinstance(c, dict):
                            cookie_dicts.append(c)
                            
                    if len(cookie_dicts) > 0:
                        save_path = Path.cwd() / cookie_filename
                        with open(save_path, 'w', encoding='utf-8') as f:
                            json.dump(cookie_dicts, f, indent=4)
                        print(f"[+] Saved retrieved cookies to {save_path.absolute()}")
                        success = True
                break
            time.sleep(1)
            
    except Exception as e:
        print(f"[-] Auto-bypass failed: {e}")
        if config.getInstance().debug():
            traceback.print_exc()
    finally:
        if page:
            try:
                page.quit()
            except:
                pass
                
    return success
