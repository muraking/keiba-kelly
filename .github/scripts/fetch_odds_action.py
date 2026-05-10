"""
SPAT4 オッズ取得スクリプト（GitHub Actions用・ログイン方式）
Cookieを使わずに毎回ログインするため、毎日のCookie更新が不要
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
    """SPAT4にログイン"""
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(3000)

    # ログインフォームを探す
    try:
        # ログインフォームの入力欄を確認
        await page.wait_for_selector('input', timeout=10000)
        inputs = await page.query_selector_all('input')
        visible_inputs = []
        for inp in inputs:
            if await inp.is_visible():
                type_ = await inp.get_attribute('type') or 'text'
                if type_ not in ['hidden', 'submit', 'button']:
                    visible_inputs.append(inp)
        
        print(f"visible inputs: {len(visible_inputs)}")
        if len(visible_inputs) >= 2:
            await visible_inputs[0].fill(SPAT4_MEMBERNUM)
            await visible_inputs[1].fill(SPAT4_PASS)
            await page.click('input[type="submit"]')
            await page.wait_for_timeout(5000)
            print(f"ログイン完了: {page.url}")
            return True
        else:
            print("ログインフォームが見つかりません")
            return False
    except Exception as e:
        print(f"ログインエラー: {e}")
        return False

async def get_odds(page, place_id, race_num, race_date):
    """P122Sフレームからオッズを取得"""
    url = f"https://www.spat4.jp/keiba/pc?HANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}"
    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(3000)

    # P122Sフレームを待機
    p122s_frame = None
    for attempt in range(5):
        frames = page.frames
        for frame in frames:
            if 'P122S' in frame.url or 'p122s' in frame.url.lower():
                p122s_frame = frame
                break
        if p122s_frame:
            break
        print(f"  フレーム待機中... ({attempt+1}/5) frames={[f.url[:60] for f in frames]}")
        await page.wait_for_timeout(3000)

    if not p122s_frame:
        # フレームが見つからない場合はメインページから取得を試みる
        print("  P122Sフレームなし → メインページから取得試行")
        text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        return parse_odds_from_text(text)

    text = await p122s_frame.evaluate("() => document.body ? document.body.innerText : ''")
    return parse_odds_from_text(text)

def parse_odds_from_text(text):
    """テキストから単勝・複勝オッズをパース"""
    result = {}
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        parts = re.split(r'\s{2,}|\t', line)
        parts = [p.strip() for p in parts if p.strip()]
        nums = []
        tan_odds = None
        fuku_range = None
        for part in parts:
            p = part.replace(',', '')
            if re.match(r'^\d{1,2}$', p) and 1 <= int(p) <= 18:
                nums.append(int(p))
            elif re.match(r'^\d+\.\d+$', p):
                v = float(p)
                if 1.0 <= v < 9999.9 and tan_odds is None:
                    tan_odds = v
            elif re.match(r'^\d+\.?\d*-\d+\.?\d*$', p):
                fuku_range = p
            elif re.match(r'^\d{3,}$', p):
                v = float(p)
                if 1.0 <= v < 9999 and tan_odds is None:
                    tan_odds = v
        horse_num = nums[1] if len(nums) >= 2 else (nums[0] if nums else None)
        if not horse_num or (tan_odds is None and fuku_range is None):
            continue
        if horse_num not in result:
            entry = {}
            if tan_odds is not None:
                entry["tan"] = tan_odds
            if fuku_range is not None:
                fp = fuku_range.split("-")
                try:
                    fmin = float(fp[0])
                    fmax = float(fp[1]) if len(fp) > 1 else None
                    if fmin > 0:
                        entry["fuku_min"] = fmin
                        if fmax: entry["fuku_max"] = fmax
                except: pass
            result[horse_num] = entry
    return result

def save_to_github(place_id, race_num, odds, today_jst):
    """GitHubにオッズを保存"""
    api_url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/contents/{GH_FILE}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
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
            "sha": sha,
            "branch": GH_BRANCH
        }
        r2 = requests.put(api_url, headers=headers, json=body)
        if r2.status_code in [200, 201]:
            print(f"GitHub保存成功")
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

        # ログイン
        ok = await login(page)
        if not ok:
            await browser.close()
            sys.exit(1)

        # オッズ取得
        odds = await get_odds(page, PLACE_ID, RACE_NUM, RACE_DATE)
        await browser.close()

    if not odds:
        print("オッズ取得失敗")
        sys.exit(1)

    print(f"{len(odds)}頭のオッズ取得成功")

    # GitHub保存
    save_to_github(PLACE_ID, RACE_NUM, odds, TODAY_JST)

if __name__ == "__main__":
    asyncio.run(main())
