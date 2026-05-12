"""
SPAT4 オッズ取得（GitHub Actions用）
network response監視でオッズAPIを直接取得
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
LOGIN_URL = "https://www.spat4.jp/keiba/pc?C_SPHONE=off"
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
    return page.url

async def get_odds(page, place_id, race_num, race_date):
    from urllib.parse import urlparse
    parsed = urlparse(page.url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"

    # レスポンスを監視してオッズAPIを探す
    captured_responses = []

    async def handle_response(response):
        url = response.url
        # オッズ関連のURLを記録
        if any(k in url for k in ['P122S', 'P125S', 'odds', 'tansho', 'tan', 'ODDS']):
            try:
                ct = response.headers.get('content-type', '')
                body = await response.body()
                captured_responses.append({
                    'url': url,
                    'status': response.status,
                    'content_type': ct,
                    'body': body
                })
                print(f"  捕捉: {url[:80]} ({response.status})")
            except:
                pass

    page.on("response", handle_response)

    url = f"{base_domain}/keiba/pc?HANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}"
    print(f"オッズURL: {url}")
    await page.goto(url, wait_until="networkidle", timeout=TIMEOUT)
    await page.wait_for_timeout(8000)
    print(f"現在URL: {page.url}")
    print(f"フレーム数: {len(page.frames)}")

    # P120SページからSHAIDを取得
    shaid = await page.evaluate("() => document.getElementById('SHAID')?.value || ''")
    print(f"SHAID: {shaid[:20] if shaid else 'なし'}")

    # P122Sフレームを確認（JS完了後のDOMを取得）
    # まず長めに待つ
    await page.wait_for_timeout(5000)
    for frame in page.frames:
        if 'P122S' in frame.url:
            print(f"P122Sフレーム: {frame.url[:80]}")
            # フレームのSHAIDも確認
            frame_shaid = await frame.evaluate("() => document.getElementById('SHAID')?.value || ''")
            print(f"フレームSHAID: {frame_shaid[:20] if frame_shaid else 'なし'}")
            frame_url_val = await frame.evaluate("() => document.getElementById('_v_url')?.value || ''")
            print(f"フレーム_v_url: {frame_url_val}")
            frame_text = await frame.evaluate("() => document.body ? document.body.innerText : ''")
            print(f"フレームDOM: {frame_text[:200]}")
            if 'ログイン' not in frame_text[:50] and 'エラー' not in frame_text[:50] and frame_text.strip():
                result = parse_odds(frame_text)
                if result:
                    print(f"フレームから{len(result)}頭取得成功")
                    return result

    # キャプチャした通信を確認
    print(f"捕捉レスポンス数: {len(captured_responses)}")
    for r in captured_responses:
        ct = r['content_type']
        body_str = ""
        if 'json' in ct:
            try:
                body_str = r['body'].decode('utf-8')
                print(f"JSON API: {r['url'][:80]}")
                print(f"  内容: {body_str[:200]}")
            except:
                pass
        elif 'html' in ct or 'text' in ct:
            try:
                for enc in ['utf-8', 'shift_jis', 'euc-jp']:
                    try:
                        body_str = r['body'].decode(enc)
                        break
                    except:
                        continue
                if body_str and 'ログイン' not in body_str[:50]:
                    print(f"HTML: {r['url'][:80]}")
                    print(f"  内容: {body_str[:150]}")
            except:
                pass

    # まずキャプチャしたP122Sレスポンスを優先的に処理
    for r in captured_responses:
        if 'P122S' in r['url']:
            raw = r['body']
            print(f"P122Sキャプチャbody長: {len(raw)}")
            print(f"先頭バイト: {raw[:50]}")
            try:
                text = raw.decode('utf-8', errors='replace')
                print(f"P122S全HTML:\n{text}")
            except Exception as e:
                print(f"デコード失敗: {e}")
            break

    # P122Sフレームから取得試行
    iframes = await page.evaluate(
        "() => Array.from(document.querySelectorAll('iframe,frame')).map(f=>f.src)"
    )
    p122s_url_orig = next((s for s in iframes if 'P122S' in s), None)
    if p122s_url_orig:
        # ログインドメインに統一
        p122s_url = re.sub(r'https://www\d*\.spat4\.jp', base_domain, p122s_url_orig)
        print(f"P122S URL: {p122s_url}")

        # page.gotoでP122Sに直接アクセス、networkidleまで待つ
        captured_responses.clear()
        await page.goto(p122s_url, wait_until="networkidle", timeout=TIMEOUT)
        await page.wait_for_timeout(3000)
        body = await page.evaluate("() => document.body ? document.body.innerText : ''")
        print(f"P122S内容: {body[:200]}")

        if 'ログイン' not in body[:50] and 'エラー' not in body[:50]:
            result = parse_odds(body)
            if result:
                return result

        # JS描画後のDOMをtableから取得
        body2 = await page.evaluate(
            "() => Array.from(document.querySelectorAll('tr, li')).map(r=>r.innerText).join('\\n')"
        )
        print(f"DOM取得: {body2[:200]}")
        result2 = parse_odds(body2)
        if result2:
            print(f"DOM取得から{len(result2)}頭")
            return result2

        # キャプチャしたP122Sレスポンスから試みる
        for r in captured_responses:
            if 'P122S' in r['url']:
                for enc in ['shift_jis', 'utf-8', 'euc-jp']:
                    try:
                        text = r['body'].decode(enc)
                        result = parse_odds(text)
                        if result:
                            print(f"キャプチャから{len(result)}頭取得")
                            return result
                    except:
                        continue

    # page.framesから試す
    target_frame = None
    for frame in page.frames:
        if 'P122S' in frame.url:
            target_frame = frame
            break

    if target_frame:
        frame_text = await target_frame.evaluate("() => document.body ? document.body.innerText : ''")
        print(f"フレーム内容: {frame_text[:100]}")
        if 'ログイン' not in frame_text[:50]:
            result = parse_odds(frame_text)
            if result:
                return result

    print("オッズ取得失敗")
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
        await login(page)
        odds = await get_odds(page, PLACE_ID, RACE_NUM, RACE_DATE)
        await browser.close()
    if not odds:
        sys.exit(1)
    print(f"{len(odds)}頭取得成功")
    save_to_github(PLACE_ID, RACE_NUM, odds, TODAY_JST)

if __name__ == "__main__":
    asyncio.run(main())