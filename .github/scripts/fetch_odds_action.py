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
            await page.evaluate(
                "() => { for(const f of document.querySelectorAll('form')){ if(f.querySelector('[name=MEMBERNUMR]')){f.submit();return;} } }"
            )
        await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"ログイン遷移: {e}")
    # ログイン後のURLがwww1/www2/www3のサブドメインになっているか確認
    # なっていない場合はP001Sに明示的に移動
    if 'www1' not in page.url and 'www2' not in page.url and 'www3' not in page.url:
        # P001Sに遷移してサブドメインを確定させる
        try:
            await page.wait_for_url('**/keiba/pc?HANDLERR=P001S*', timeout=10000)
        except:
            pass
    print(f"ログイン後URL: {page.url}")


async def get_odds(page, place_id, race_num, race_date):
    from urllib.parse import urlparse, urljoin
    parsed = urlparse(page.url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"
    if parsed.netloc == 'www.spat4.jp':
        base_domain = "https://www2.spat4.jp"

    p120s_url = f"{base_domain}/keiba/pc?HANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}"
    print(f"P120S: {p120s_url}")

    # レスポンス監視
    captured_odds = {}
    wpscript_body = None

    async def on_response(response):
        nonlocal wpscript_body
        url = response.url
        if 'WPScript.js' in url and wpscript_body is None:
            try: wpscript_body = await response.body()
            except: pass

    page.on("response", on_response)

    # P120Sを読み込む（networkidleまで待つ）
    try:
        await page.goto(p120s_url, wait_until="networkidle", timeout=TIMEOUT)
    except:
        await page.goto(p120s_url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(5000)
    print(f"現在URL: {page.url}")

    # ★ P120SのHTMLからiframe srcを動的取得
    iframe_srcs = await page.evaluate("""
        () => Array.from(document.querySelectorAll('iframe,frame')).map(f => ({
            src: f.src,
            name: f.name || '',
            id: f.id || ''
        }))
    """)
    print(f"iframes: {[(f['name'], f['src'][-60:]) for f in iframe_srcs]}")

    # P122S相当のフレームsrcを特定（LEFT nameまたはP122S含む）
    odds_src = None
    for f in iframe_srcs:
        if 'P122S' in f['src'] or f['name'] == 'LEFT':
            odds_src = f['src']
            break

    if not odds_src:
        print("オッズiframeが見つかりません")
        page.remove_listener("response", on_response)
        return {}

    # srcが相対URLの場合は絶対URLに変換
    if odds_src.startswith('/'):
        odds_src = base_domain + odds_src

    print(f"オッズフレームsrc: {odds_src}")

    # page.framesから対応するフレームを探す
    target_frame = None
    for attempt in range(8):
        for frame in page.frames:
            # URLが一致するフレームを探す（パラメータ部分で比較）
            if 'P122S' in frame.url or (odds_src and frame.url.split('?')[0] == odds_src.split('?')[0]):
                target_frame = frame
                break
        if target_frame:
            print(f"フレーム発見: attempt={attempt+1} url={target_frame.url[-60:]}")
            break
        await page.wait_for_timeout(2000)

    if target_frame:
        try:
            await target_frame.wait_for_load_state("domcontentloaded", timeout=10000)
        except: pass
        await page.wait_for_timeout(2000)

        text = await target_frame.evaluate("() => document.body ? document.body.innerText : ''")
        v_url = await target_frame.evaluate("() => document.getElementById('_v_url')?.value || ''")
        print(f"フレーム_v_url: {v_url}")
        print(f"フレーム内容: {text[:100]}")

        if v_url != '/pc/err' and 'ログイン' not in text[:50]:
            odds = parse_odds_text(text)
            if odds:
                print(f"フレームから{len(odds)}頭取得成功")
                page.remove_listener("response", on_response)
                return odds

    # フォールバック: requestsでCookieを引き継いでodds_srcに直接アクセス
    print("requestsでodds_src直接アクセス...")
    cookies = await page.context.cookies()
    import requests as req_lib2
    session = req_lib2.Session()
    for c in cookies:
        session.cookies.set(c['name'], c['value'], domain=c.get('domain', ''))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": p120s_url,
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    try:
        r = session.get(odds_src, headers=headers, timeout=15)
        for enc in ['shift_jis', 'cp932', 'utf-8']:
            try:
                text2 = r.content.decode(enc)
                print(f"requests内容({enc}): {text2[:100]}")
                if 'ログイン' not in text2[:50] and 'エラー' not in text2[:50]:
                    odds2 = parse_odds_text(text2)
                    if odds2:
                        print(f"requestsから{len(odds2)}頭取得成功")
                        page.remove_listener("response", on_response)
                        return odds2
                break
            except: continue
    except Exception as e:
        print(f"requestsエラー: {e}")

    page.remove_listener("response", on_response)
    return {}




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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
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