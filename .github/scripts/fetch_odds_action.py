"""
GitHub Actions上でSPAT4オッズを取得するスクリプト
- 保存済みCookieを使ってSPAT4にアクセス
- P122Sフレームから単勝・複勝オッズを取得
- GitHubのindices.jsonに保存
"""
import asyncio
from playwright.async_api import async_playwright
import json
import re
import requests
import base64
import os
from datetime import datetime, timezone, timedelta

# 環境変数から設定を取得
SPAT4_COOKIES_JSON = os.environ.get("SPAT4_COOKIES", "[]")
SPAT4_BASE_URL     = os.environ.get("SPAT4_BASE_URL", "https://www.spat4.jp")
GH_TOKEN           = os.environ.get("GH_TOKEN", "")
PLACE_ID           = os.environ.get("PLACE_ID", "")
RACE_NUM           = int(os.environ.get("RACE_NUM", "1"))
RACE_DATE          = os.environ.get("RACE_DATE", "")
TODAY_JST          = os.environ.get("TODAY_JST", "")

GH_USER   = "muraking"
GH_REPO   = "keiba-kelly"
GH_BRANCH = "main"
GH_FILE   = "data/indices.json"
TIMEOUT   = 60000

JST = timezone(timedelta(hours=9))

def parse_odds_from_lines(lines):
    result = {}
    for line in lines:
        parts = re.split(r'\s{2,}|\t', line)
        parts = [p.strip() for p in parts if p.strip()]
        nums_in_line = []
        tan_odds = None
        fuku_range = None
        for part in parts:
            p = part.replace(',', '')
            if re.match(r'^\d{1,2}$', p) and 1 <= int(p) <= 18:
                nums_in_line.append(int(p))
            elif re.match(r'^\d+\.\d+$', p):
                v = float(p)
                if 1.0 <= v < 999.9 and tan_odds is None:
                    tan_odds = v
            elif re.match(r'^\d+\.\d+-\d+\.?\d*$', p):
                fuku_range = p
        horse_num = nums_in_line[1] if len(nums_in_line) >= 2 else (nums_in_line[0] if nums_in_line else None)
        if not horse_num or (tan_odds is None and fuku_range is None):
            continue
        if horse_num not in result:
            entry = {}
            if tan_odds is not None:
                entry["tan"] = tan_odds
            if fuku_range is not None:
                fp = fuku_range.split("-")
                try:
                    entry["fuku_min"] = float(fp[0])
                    entry["fuku_max"] = float(fp[1]) if len(fp) > 1 else None
                except ValueError:
                    pass
            result[horse_num] = entry
    return result

def save_to_github(place_id, race_num, odds):
    api_url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/contents/{GH_FILE}"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    r = requests.get(api_url, headers=headers)
    if not r.ok:
        print(f"GitHub取得失敗: {r.status_code}")
        return False

    sha = r.json()["sha"]
    content = r.json()["content"].replace("\n", "")
    data = json.loads(base64.b64decode(content).decode())

    if "dates" not in data:
        data["dates"] = {}
    if TODAY_JST not in data["dates"]:
        data["dates"][TODAY_JST] = {}
    if "odds" not in data["dates"][TODAY_JST]:
        data["dates"][TODAY_JST]["odds"] = {}
    if place_id not in data["dates"][TODAY_JST]["odds"]:
        data["dates"][TODAY_JST]["odds"][place_id] = {}

    data["dates"][TODAY_JST]["odds"][place_id][str(race_num)] = odds
    data["dates"][TODAY_JST]["odds_updated"] = datetime.now(JST).isoformat()

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    encoded = base64.b64encode(json_str.encode()).decode()
    body = {
        "message": f"Update odds {TODAY_JST} {place_id} {race_num}R",
        "content": encoded,
        "branch": GH_BRANCH,
        "sha": sha
    }
    r = requests.put(api_url, headers=headers, json=body)
    return r.ok

async def main():
    print(f"オッズ取得: PLACE_ID={PLACE_ID} RACE_NUM={RACE_NUM} DATE={RACE_DATE}")

    cookies = json.loads(SPAT4_COOKIES_JSON)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        context.set_default_timeout(TIMEOUT)

        # Cookieを設定
        if cookies:
            await context.add_cookies(cookies)
            print(f"Cookie設定: {len(cookies)}件")

        page = await context.new_page()

        # オッズページへ直接アクセス
        url = f"{SPAT4_BASE_URL}/keiba/pc?HANDLERR=P120S&RACEDAYR={RACE_DATE}&PLACEIDR={PLACE_ID}&RACER={RACE_NUM}"
        print(f"アクセス: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
        except Exception as e:
            print(f"goto警告: {e}")
        await page.wait_for_timeout(5000)

        print(f"現在URL: {page.url}")

        # ログインページにリダイレクトされていたら再ログインが必要
        if "P001S" in page.url or "login" in page.url.lower():
            print("セッション切れ - spat4_save_session.pyを再実行してください")
            await browser.close()
            exit(1)

        # P122Sフレームを探す
        target_frame = None
        for frame in page.frames:
            if "P122S" in frame.url:
                target_frame = frame
                break

        if not target_frame:
            print("P122Sフレームが見つかりません")
            print(f"フレーム: {[f.url for f in page.frames]}")
            await browser.close()
            exit(1)

        text = await target_frame.evaluate("() => document.body ? document.body.innerText : ''")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        odds = parse_odds_from_lines(lines)

        if odds:
            print(f"取得成功: {len(odds)}頭")
            for n in sorted(odds.keys()):
                print(f"  {n}番: 単{odds[n].get('tan','?')}倍")
            if save_to_github(PLACE_ID, RACE_NUM, odds):
                print("GitHub保存成功")
            else:
                print("GitHub保存失敗")
        else:
            print("オッズ取得失敗（未発売の可能性）")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
