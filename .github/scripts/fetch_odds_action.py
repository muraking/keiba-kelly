"""
SPAT4 オッズ取得（GitHub Actions用）
expect_responseで内部APIを傍受する方式
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

async def get_odds(page, place_id, race_num, race_date):
    from urllib.parse import urlparse
    parsed = urlparse(page.url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"
    p120s_url = f"{base_domain}/keiba/pc?HANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}"
    print(f"オッズURL: {p120s_url}")

    # 全レスポンスを監視してAPIを探す
    all_responses = []

    async def on_response(response):
        try:
            body = await response.body()
            ct = response.headers.get('content-type', '')
            all_responses.append({
                'url': response.url,
                'status': response.status,
                'ct': ct,
                'size': len(body),
                'body': body
            })
        except:
            all_responses.append({'url': response.url, 'status': response.status, 'ct': '', 'size': 0, 'body': b''})

    page.on("response", on_response)

    try:
        await page.goto(p120s_url, wait_until="networkidle", timeout=TIMEOUT)
    except:
        await page.goto(p120s_url, wait_until="domcontentloaded", timeout=TIMEOUT)
    # WPScript.jsを解析してAPIのURLを探す
    for r in all_responses:
        if 'WPScript.js' in r['url'] and r['size'] > 10000:
            try:
                js = r['body'].decode('utf-8', errors='replace')
                print(f'WPScript.js size: {len(js)}')
                import re as _re
                paths = _re.findall(r'["\'](\/keiba\/[^"\'<>\s]{3,80})["\']', js)
                paths = list(set(p for p in paths if not any(p.endswith(x) for x in ['.js','.css','.png','.gif'])))
                print(f'パス候補({len(paths)}件):')
                for p in sorted(paths)[:30]: print(f"  {p}")
                ajax = _re.findall(r'url\s*:\s*["\']([^"\']{3,100})["\']', js)
                print(f'Ajax URL: {ajax[:10]}')
            except Exception as e:
                print(f"解析エラー: {e}")
            break
    # もっと長く待つ
    await page.wait_for_timeout(15000)
    print(f"追加待機後キャプチャ数: {len(all_responses)}")

    print(f"キャプチャ数: {len(all_responses)}")
    for r in all_responses:
        print(f"  [{r['status']}] {r['url'][:100]} ({r['ct'][:30]}) size={r['size']}")
        # JSONっぽければ中身も表示
        if 'json' in r['ct'] or r['url'].endswith('.json'):
            try:
                data = json.loads(r['body'])
                print(f"    JSON: {str(data)[:200]}")
            except:
                pass
        # HTMLでもオッズっぽい数字があれば表示
        elif r['size'] > 100 and r['size'] < 50000:
            try:
                for enc in ['utf-8', 'shift_jis', 'cp932']:
                    try:
                        text = r['body'].decode(enc)
                        if any(str(i) in text for i in range(1, 19)):
                            print(f"    内容: {text[:300]}")
                        break
                    except:
                        continue
            except:
                pass

    page.remove_listener("response", on_response)
    return {}

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
            "message": f"odds {place_id} {race_num}R",
            "content": base64.b64encode(json_str.encode()).decode(),
            "sha": sha, "branch": GH_BRANCH
        }
        r2 = req_lib.put(api_url, headers=headers, json=body)
        if r2.status_code in [200, 201]: return True
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
        print("API特定用デバッグ完了（オッズ未取得）")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())