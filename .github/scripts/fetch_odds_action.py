"""
SPAT4 オッズ取得スクリプト（GitHub Actions用・ログイン方式）
"""
import asyncio
import os
import json
import re
import sys
import requests
import base64
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

SPAT4_MEMBERNUM = os.environ.get("SPAT4_MEMBERNUM", "")
SPAT4_PASS      = os.environ.get("SPAT4_PASS", "")
GH_TOKEN        = os.environ.get("GH_TOKEN", "")
GH_USER         = "muraking"
GH_REPO         = "keiba-kelly"
GH_BRANCH       = "main"
GH_FILE         = "data/indices.json"

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

    # ページ内容とinputを確認
    text = await page.evaluate("() => document.body ? document.body.innerText : ''")
    print(f"ページ内容: {text[:200]}")

    all_inputs = await page.evaluate("""
        () => Array.from(document.querySelectorAll('input')).map(i => ({
            name: i.name, type: i.type, id: i.id,
            visible: i.offsetParent !== null, value: i.value.substring(0,10)
        }))
    """)
    print(f"inputs: {all_inputs[:15]}")

    # 可視のtext/password inputに入力
    visible_text = [i for i in all_inputs if i['visible'] and i['type'] in ['text', 'tel', 'number', '']]
    visible_pass = [i for i in all_inputs if i['visible'] and i['type'] == 'password']

    print(f"visible text inputs: {visible_text}")
    print(f"visible password inputs: {visible_pass}")

    filled = 0
    # 加入者番号
    if visible_text:
        sel = f'input[name="{visible_text[0]["name"]}"]' if visible_text[0]["name"] else f'input[type="{visible_text[0]["type"]}"]'
        try:
            await page.fill(sel, SPAT4_MEMBERNUM)
            print(f"加入者番号入力OK: {sel}")
            filled += 1
        except Exception as e:
            print(f"加入者番号エラー: {e}")

    # パスワード
    if visible_pass:
        sel = f'input[name="{visible_pass[0]["name"]}"]' if visible_pass[0]["name"] else 'input[type="password"]'
        try:
            await page.fill(sel, SPAT4_PASS)
            print(f"パスワード入力OK: {sel}")
            filled += 1
        except Exception as e:
            print(f"パスワードエラー: {e}")

    if filled >= 2:
        # ログインボタンを探す
        login_clicked = False
        for selector in ['input[type="submit"]', 'button[type="submit"]', 'button', 'a']:
            try:
                els = await page.query_selector_all(selector)
                for el in els:
                    t = await el.inner_text() if hasattr(el, 'inner_text') else ''
                    v = await el.get_attribute('value') or ''
                    if 'ログイン' in t or 'ログイン' in v or selector == 'input[type="submit"]':
                        if await el.is_visible():
                            await el.click()
                            login_clicked = True
                            print(f"ログインボタンクリック: {selector}")
                            break
            except: pass
            if login_clicked: break

        if not login_clicked:
            await page.evaluate("document.querySelector('form') && document.querySelector('form').submit()")
            print("フォームJS submit")

        await page.wait_for_timeout(5000)
        print(f"ログイン後URL: {page.url}")
        return True

    print(f"ログイン失敗 (filled={filled})")
    return False

async def get_odds(page, place_id, race_num, race_date):
    url = f"https://www.spat4.jp/keiba/pc?HANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}"
    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(3000)

    p122s_frame = None
    for attempt in range(5):
        frames = page.frames
        for frame in frames:
            if 'P122S' in frame.url or 'p122s' in frame.url.lower():
                p122s_frame = frame
                break
        if p122s_frame:
            break
        print(f"  フレーム待機中... ({attempt+1}/5)")
        await page.wait_for_timeout(3000)

    if not p122s_frame:
        print(f"  P122Sフレームなし frames={[f.url[:60] for f in page.frames]}")
        text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        return parse_odds(text)

    text = await p122s_frame.evaluate("() => document.body ? document.body.innerText : ''")
    return parse_odds(text)

def parse_odds(text):
    result = {}
    for line in text.split('\n'):
        line = line.strip()
        parts = re.split(r'\s{2,}|\t', line)
        parts = [p.strip() for p in parts if p.strip()]
        nums, tan, fuku = [], None, None
        for p in parts:
            p = p.replace(',', '')
            if re.match(r'^\d{1,2}$', p) and 1 <= int(p) <= 18:
                nums.append(int(p))
            elif re.match(r'^\d+\.\d+$', p):
                v = float(p)
                if 1.0 <= v < 9999.9 and tan is None:
                    tan = v
            elif re.match(r'^\d+\.?\d*-\d+\.?\d*$', p):
                fuku = p
            elif re.match(r'^\d{3,}$', p):
                v = float(p)
                if 1.0 <= v < 9999 and tan is None:
                    tan = v
        num = nums[1] if len(nums) >= 2 else (nums[0] if nums else None)
        if not num or (tan is None and fuku is None):
            continue
        if num not in result:
            e = {}
            if tan: e["tan"] = tan
            if fuku:
                fp = fuku.split("-")
                try:
                    fmin = float(fp[0])
                    fmax = float(fp[1]) if len(fp) > 1 else None
                    if fmin > 0:
                        e["fuku_min"] = fmin
                        if fmax: e["fuku_max"] = fmax
                except: pass
            result[num] = e
    return result

def save_to_github(place_id, race_num, odds, today_jst):
    api_url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/contents/{GH_FILE}"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    for attempt in range(3):
        r = requests.get(api_url, headers=headers)
        if not r.ok:
            print(f"GitHub取得失敗: {r.status_code}")
            return False
        sha = r.json()["sha"]
        content = r.json()["content"].replace("\n", "")
        data = json.loads(base64.b64decode(content).decode())
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
        r2 = requests.put(api_url, headers=headers, json=body)
        if r2.status_code in [200, 201]:
            print("GitHub保存成功")
            return True
        if r2.status_code == 409:
            print(f"SHA競合 → リトライ ({attempt+1}/3)")
            continue
        print(f"GitHub保存失敗: {r2.status_code}")
        return False
    return False

async def main():
    print(f"オッズ取得: PLACE_ID={PLACE_ID} RACE_NUM={RACE_NUM} DATE={RACE_DATE}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)

        ok = await login(page)
        if not ok:
            await browser.close()
            sys.exit(1)

        odds = await get_odds(page, PLACE_ID, RACE_NUM, RACE_DATE)
        await browser.close()

    if not odds:
        print("オッズ取得失敗")
        sys.exit(1)

    print(f"{len(odds)}頭取得成功")
    save_to_github(PLACE_ID, RACE_NUM, odds, TODAY_JST)

if __name__ == "__main__":
    asyncio.run(main())
