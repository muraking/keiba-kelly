"""
SPAT4 オッズ取得（GitHub Actions用・ログイン方式）
"""
import asyncio, os, json, re, sys, requests as req_lib, base64
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright
from html.parser import HTMLParser

SPAT4_MEMBERNUM = os.environ.get("SPAT4_MEMBERNUM", "")
SPAT4_PASS      = os.environ.get("SPAT4_PASS", "")
GH_TOKEN        = os.environ.get("GH_TOKEN", "")
GH_USER   = "muraking"
GH_REPO   = "keiba-kelly"
GH_BRANCH = "main"
GH_FILE   = "data/indices.json"
PLACE_ID  = os.environ.get("PLACE_ID", "")
RACE_NUM  = int(os.environ.get("RACE_NUM", "1"))
RACE_DATE = os.environ.get("RACE_DATE", "")
TODAY_JST = os.environ.get("TODAY_JST", "")
LOGIN_URL = "https://www.spat4.jp/keiba/pc?C_SPHONE=off"
TIMEOUT   = 60000

def now_jst():
    return datetime.now(timezone(timedelta(hours=9)))

def extract_text(html_str):
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.texts = []
            self.skip = False
        def handle_starttag(self, tag, attrs):
            if tag in ['script','style','noscript']: self.skip = True
        def handle_endtag(self, tag):
            if tag in ['script','style','noscript']: self.skip = False
        def handle_data(self, data):
            if not self.skip and data.strip():
                self.texts.append(data.strip())
    p = Parser()
    p.feed(html_str)
    return "\n".join(p.texts)

async def login(page):
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(5000)
    await page.fill('input[name="MEMBERNUMR"]', SPAT4_MEMBERNUM)
    await page.fill('input[name="MEMBERIDR"]', SPAT4_PASS)
    print("入力完了")

    try:
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
            await page.evaluate("""
                () => {
                    for(const form of document.querySelectorAll('form')){
                        if(form.querySelector('[name="MEMBERNUMR"]')){
                            form.submit(); return;
                        }
                    }
                }
            """)
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"ナビゲーション: {e}")

    print(f"ログイン後URL: {page.url}")
    
    # セッションCookieを取得
    cookies = await page.context.cookies()
    print(f"Cookie数: {len(cookies)}")
    return cookies

async def get_odds_with_requests(p122s_url, cookies):
    """requestsライブラリでP122Sに直接アクセス"""
    session = req_lib.Session()
    for c in cookies:
        session.cookies.set(c['name'], c['value'], domain=c.get('domain',''))
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
        "Referer": p122s_url.replace("P122S", "P120S").split("&KINDINFOR")[0],
    }
    
    try:
        r = session.get(p122s_url, headers=headers, timeout=15)
        r.encoding = 'shift_jis'
        text = extract_text(r.text)
        print(f"requests内容: {text[:150]}")
        return parse_odds(text)
    except Exception as e:
        print(f"requestsエラー: {e}")
        return {}

async def get_odds(page, place_id, race_num, race_date, cookies):
    from urllib.parse import urlparse
    parsed = urlparse(page.url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"
    url = f"{base_domain}/keiba/pc?HANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}"
    print(f"オッズURL: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(8000)
    print(f"現在URL: {page.url}")

    # セッション確認
    text = await page.evaluate("() => document.body ? document.body.innerText : ''")
    if 'ログイン' in text[:80] or 'エラー' in text[:80]:
        print(f"セッション切れ: {text[:80]}")
        return {}

    # iframeのsrcからP122S URLを取得
    iframes = await page.evaluate(
        "() => Array.from(document.querySelectorAll('iframe,frame')).map(f=>f.src)"
    )
    p122s_url_orig = next((s for s in iframes if 'P122S' in s), None)
    # ログイン後のドメインにP122S URLを書き換え（ロードバランサー対策）
    if p122s_url_orig:
        import re as _re
        p122s_url = _re.sub(r'https://www\d*\.spat4\.jp', base_domain, p122s_url_orig)
    else:
        p122s_url = None
    print(f"P122S URL: {p122s_url}")

    if not p122s_url:
        print("P122S iframeなし")
        return parse_odds(text)

    # 方法1: page.gotoでP122Sに直接アクセス（成功実績あり）
    print(f"P122S直接アクセス: {p122s_url}")
    await page.goto(p122s_url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(3000)
    body = await page.evaluate("() => document.body ? document.body.innerText : ''")
    print(f"P122S内容: {body[:80]}")
    if 'ログイン' not in body[:50] and 'エラー' not in body[:50]:
        result = parse_odds(body)
        if result:
            print(f"{len(result)}頭取得成功")
            return result

    # 方法2: page.framesから試す（P120Sに戻ってから）
    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(5000)
    target_frame = None
    for attempt in range(5):
        for frame in page.frames:
            if 'P122S' in frame.url:
                target_frame = frame
                break
        if target_frame:
            break
        await page.wait_for_timeout(3000)

    if target_frame:
        frame_text = await target_frame.evaluate("() => document.body ? document.body.innerText : ''")
        print(f"フレーム内容: {frame_text[:80]}")
        if 'ログイン' not in frame_text[:50] and 'エラー' not in frame_text[:50]:
            result = parse_odds(frame_text)
            if result:
                return result

    # 方法3: requestsで直接取得
    print("requestsでP122S取得...")
    result2 = await get_odds_with_requests(p122s_url, cookies)
    if result2:
        return result2

    return {}

def parse_odds(text):
    result = {}
    for line in text.split('\n'):
        parts = re.split(r'\s{2,}|\t', line.strip())
        parts = [p.strip().replace(',','') for p in parts if p.strip()]
        nums, tan, fuku = [], None, None
        for p in parts:
            if re.match(r'^\d{1,2}$', p) and 1 <= int(p) <= 18:
                nums.append(int(p))
            elif re.match(r'^\d+\.\d+$', p):
                v = float(p)
                if 1.0 <= v < 9999.9 and tan is None: tan = v
            elif re.match(r'^\d+\.?\d*-\d+\.?\d*$', p):
                fuku = p
            elif re.match(r'^\d{3,}$', p):
                v = float(p)
                if 1.0 <= v < 9999 and tan is None: tan = v
        num = nums[1] if len(nums) >= 2 else (nums[0] if nums else None)
        if not num or (tan is None and fuku is None): continue
        if num not in result:
            e = {}
            if tan: e["tan"] = tan
            if fuku:
                fp = fuku.split("-")
                try:
                    fmin = float(fp[0])
                    if fmin > 0:
                        e["fuku_min"] = fmin
                        if len(fp) > 1: e["fuku_max"] = float(fp[1])
                except: pass
            result[num] = e
    return result

def save_to_github(place_id, race_num, odds, today_jst):
    api_url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/contents/{GH_FILE}"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    for attempt in range(3):
        r = req_lib.get(api_url, headers=headers)
        if not r.ok: return False
        sha = r.json()["sha"]
        data = json.loads(base64.b64decode(r.json()["content"].replace("\n","")).decode())
        if "dates" not in data: data["dates"] = {}
        if today_jst not in data["dates"]: data["dates"][today_jst] = {}
        if "odds" not in data["dates"][today_jst]: data["dates"][today_jst]["odds"] = {}
        if place_id not in data["dates"][today_jst]["odds"]:
            data["dates"][today_jst]["odds"][place_id] = {}
        data["dates"][today_jst]["odds"][place_id][race_num] = odds
        data["dates"][today_jst]["odds_updated"] = now_jst().isoformat()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        body = {
            "message": f"odds {place_id} {race_num}R {now_jst().strftime('%H:%M')}",
            "content": base64.b64encode(json_str.encode()).decode(),
            "sha": sha, "branch": GH_BRANCH
        }
        r2 = req_lib.put(api_url, headers=headers, json=body)
        if r2.status_code in [200, 201]:
            print("GitHub保存成功")
            return True
        if r2.status_code == 409:
            continue
    return False

async def main():
    print(f"オッズ取得: PLACE_ID={PLACE_ID} RACE_NUM={RACE_NUM} DATE={RACE_DATE}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        cookies = await login(page)
        odds = await get_odds(page, PLACE_ID, RACE_NUM, RACE_DATE, cookies)
        await browser.close()
    if not odds:
        print("オッズ取得失敗")
        sys.exit(1)
    print(f"{len(odds)}頭取得成功")
    save_to_github(PLACE_ID, RACE_NUM, odds, TODAY_JST)

if __name__ == "__main__":
    asyncio.run(main())