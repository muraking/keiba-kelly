"""
SPAT4 オッズ取得（GitHub Actions用）
C900J/C901J 内部APIをexpect_responseで傍受する方式
"""
import asyncio, os, json, re, sys, base64
import requests as req_lib
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

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
LOGIN_URL = "https://www.spat4.jp/keiba/sp"
TIMEOUT   = 60000

def now_jst():
    return datetime.now(timezone(timedelta(hours=9)))

async def login(page):
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(5000)
    await page.fill('input[name="MEMBERNUMR"]', SPAT4_MEMBERNUM)
    await page.fill('input[name="MEMBERIDR"]', SPAT4_PASS)
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
        await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"ログイン遷移: {e}")
    print(f"ログイン後URL: {page.url}")

async def get_odds(page, place_id, race_num, race_date):
    from urllib.parse import urlparse
    parsed = urlparse(page.url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"
    p120s_url = f"{base_domain}/keiba/pc?HANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}"
    print(f"オッズURL: {p120s_url}")

    # 全レスポンスを保存してWPScript.jsを詳細解析
    captured_odds = {}
    wpscript_body = None

    async def on_response(response):
        nonlocal wpscript_body
        url = response.url
        if 'WPScript.js' in url and wpscript_body is None:
            try:
                wpscript_body = await response.body()
            except: pass
        if 'C900J' in url or 'C901J' in url:
            try:
                body = await response.body()
                ct = response.headers.get('content-type', '')
                print(f"内部API捕捉: {url[:100]} ({ct}) size={len(body)}")
                # デコード試行
                for enc in ['utf-8', 'shift_jis', 'cp932']:
                    try:
                        text = body.decode(enc)
                        print(f"  内容({enc}): {text[:300]}")
                        # オッズデータを解析
                        odds = parse_api_response(text)
                        if odds:
                            captured_odds.update(odds)
                        break
                    except:
                        continue
            except Exception as e:
                print(f"  キャプチャエラー: {e}")

    page.on("response", on_response)

    # P120Sページを開く（C900J/C901JのAjaxが発火する）
    try:
        await page.goto(p120s_url, wait_until="networkidle", timeout=TIMEOUT)
    except:
        await page.goto(p120s_url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(8000)

    print(f"現在URL: {page.url}")
    print(f"捕捉オッズ: {len(captured_odds)}頭")

    # WPScript.jsの詳細解析
    if wpscript_body:
        try:
            js = wpscript_body.decode('utf-8', errors='replace')
            print(f"WPScript.js size: {len(js)}")
            # P122S関連のコードを探す
            import re as _re
            # P122S周辺のコードを抽出
            p122s_matches = [m.start() for m in _re.finditer(r'P122S|C900|C901|tanOdds|getOdds|ODDS|tansho|fukusho', js, _re.IGNORECASE)]
            print(f"オッズ関連キーワード位置: {p122s_matches[:10]}")
            for pos in p122s_matches[:5]:
                print(f"  [{pos}]: {repr(js[max(0,pos-50):pos+100])}")
            # HANDLERR= パターンを全て抽出
            handlers = _re.findall(r'HANDLERR=([A-Z0-9]+)', js)
            print(f"HANDLERR一覧: {list(set(handlers))}")
        except Exception as e:
            print(f"WPScript解析エラー: {e}")
    else:
        print("WPScript.js未取得")

    if captured_odds:
        return captured_odds

    # C900JをrequestsでCookieを引き継いで直接呼び出す
    print("C900J直接呼び出し...")
    from urllib.parse import urlparse
    parsed2 = urlparse(page.url)
    base2 = f"{parsed2.scheme}://{parsed2.netloc}"

    cookies = await page.context.cookies()
    session = req_lib.Session()
    for c in cookies:
        session.cookies.set(c['name'], c['value'], domain=c.get('domain',''))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"{base2}/keiba/pc?HANDLERR=P122S&BEFOREHANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}&KINDINFOR=1",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
    }

    # C900J: 単勝複勝オッズ取得API
    c900j_url = f"{base2}/keiba/pc?HANDLERR=C900J&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}&KINDINFOR=1"
    print(f"C900J: {c900j_url}")
    try:
        r = session.get(c900j_url, headers=headers, timeout=15)
        print(f"C900J status: {r.status_code}")
        for enc in ['utf-8', 'shift_jis', 'cp932']:
            try:
                text = r.content.decode(enc)
                print(f"C900J内容({enc}): {text[:300]}")
                odds = parse_api_response(text)
                if odds:
                    print(f"C900Jから{len(odds)}頭取得")
                    return odds
                break
            except: continue
    except Exception as e:
        print(f"C900Jエラー: {e}")

    # C901J: 更新データ取得API
    c901j_url = f"{base2}/keiba/pc?HANDLERR=C901J&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}&KINDINFOR=1"
    print(f"C901J: {c901j_url}")
    try:
        r = session.get(c901j_url, headers=headers, timeout=15)
        print(f"C901J status: {r.status_code}")
        for enc in ['utf-8', 'shift_jis', 'cp932']:
            try:
                text = r.content.decode(enc)
                print(f"C901J内容({enc}): {text[:300]}")
                odds = parse_api_response(text)
                if odds:
                    print(f"C901Jから{len(odds)}頭取得")
                    return odds
                break
            except: continue
    except Exception as e:
        print(f"C901Jエラー: {e}")

    # フォールバック: P122Sフレームから取得
    print("フォールバック: P122Sフレームから取得...")
    for frame in page.frames:
        if 'P122S' in frame.url:
            try:
                text = await frame.evaluate("() => document.body ? document.body.innerText : ''")
                if 'ログイン' not in text[:50] and text.strip():
                    odds = parse_odds_text(text)
                    if odds:
                        print(f"P122Sフレームから{len(odds)}頭取得")
                        return odds
            except:
                pass

    return {}

def parse_api_response(text):
    """C900J/C901JのAPIレスポンスからオッズを解析"""
    odds = {}
    # JSON形式の場合
    try:
        data = json.loads(text)
        print(f"  JSONデータ: {str(data)[:200]}")
        # オッズデータを探す
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list) and len(v) >= 2:
                    # [オッズ, 時刻, 人気, 馬番] 形式の可能性
                    try:
                        if len(v) >= 4:
                            horse_str = str(v[3])
                            nums = [int(horse_str[i:i+2]) for i in range(0, len(horse_str), 2)]
                            if nums and 1 <= nums[0] <= 18:
                                tan = float(v[0]) if v[0] else None
                                if tan and tan > 1.0:
                                    odds[nums[0]] = {"tan": tan}
                    except:
                        pass
        return odds
    except:
        pass

    # テキスト形式の場合はparse_odds_textを使用
    return parse_odds_text(text)

def parse_odds_text(text):
    """テキスト形式のオッズを解析"""
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
        if r2.status_code == 409: continue
    return False

async def main():
    print(f"オッズ取得: PLACE_ID={PLACE_ID} RACE_NUM={RACE_NUM} DATE={RACE_DATE}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844},
            is_mobile=True,
        )
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)
        await login(page)
        odds = await get_odds(page, PLACE_ID, RACE_NUM, RACE_DATE)
        await browser.close()
    if not odds:
        print("オッズ取得失敗")
        sys.exit(1)
    print(f"{len(odds)}頭取得成功")
    save_to_github(PLACE_ID, RACE_NUM, odds, TODAY_JST)

if __name__ == "__main__":
    asyncio.run(main())