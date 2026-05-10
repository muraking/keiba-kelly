"""
IPAT SP版 1レース分のオッズ取得（GitHub Actions用）
選択中のレースだけ高速取得
"""
import asyncio
import os
import json
import re
import requests
import base64
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

IPAT_ID   = os.environ.get("IPAT_ID", "")
IPAT_PIN  = os.environ.get("IPAT_PIN", "")
IPAT_PARS = os.environ.get("IPAT_PARS", "")
GH_TOKEN  = os.environ.get("GH_TOKEN", "")
GH_USER   = "muraking"
GH_REPO   = "keiba-kelly"
GH_BRANCH = "main"
GH_FILE   = "data/indices.json"

VENUE     = os.environ.get("VENUE", "")      # 例: 東京
RACE_NUM  = int(os.environ.get("RACE_NUM", "1"))
TODAY_JST = os.environ.get("TODAY_JST", "")

LOGIN_URL = "https://www.ipat.jra.go.jp/sp/"
TIMEOUT   = 30000

def now_jst():
    return datetime.now(timezone(timedelta(hours=9)))

async def login(page):
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)
    await page.fill('#userid', IPAT_ID)
    await page.fill('#password', IPAT_PIN)
    await page.fill('#pars', IPAT_PARS)
    await page.evaluate("ToSPMenu()")
    await page.wait_for_timeout(3000)
    print(f"ログイン完了: {page.url}")

async def get_odds_one_race(page, venue, race_num):
    """指定会場・レースの単勝・複勝オッズを取得"""
    # オッズ投票
    await page.click('text=オッズ投票')
    await page.wait_for_timeout(2000)

    # 会場クリック
    links = await page.query_selector_all('a')
    for link in links:
        t = (await link.inner_text()).strip()
        if venue in t and ('土' in t or '日' in t):
            await link.tap()
            await page.wait_for_timeout(2000)
            break

    # レースクリック
    race_list_url = page.url
    race_btns = await page.query_selector_all('a')
    for btn in race_btns:
        t = (await btn.inner_text()).strip()
        if t == f'{race_num}R' or t.startswith(f'{race_num}R'):
            await btn.tap()
            await page.wait_for_timeout(2000)
            break

    # 式別から選択 → 単勝
    await page.click('text=式別から選択')
    await page.wait_for_timeout(1500)
    await page.click('text=単勝')
    await page.wait_for_timeout(2000)

    # オッズ取得
    text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    result = {}
    i = 0
    while i < len(lines):
        if re.match(r'^\d{1,2}$', lines[i]) and 1 <= int(lines[i]) <= 18:
            num = int(lines[i])
            if i + 2 < len(lines):
                odds_str = lines[i + 2]
                if re.match(r'^\d+\.?\d*$', odds_str):
                    result[num] = {"tan": float(odds_str)}
                    i += 3
                    continue
        i += 1

    # 複勝取得
    try:
        back_links = await page.query_selector_all('a')
        for link in back_links:
            t = (await link.inner_text()).strip()
            if '式別選択' in t and '戻' in t:
                await link.click()
                await page.wait_for_timeout(1500)
                break
        await page.click('text=複勝')
        await page.wait_for_timeout(2000)
        text2 = await page.evaluate("() => document.body.innerText")
        lines2 = [l.strip() for l in text2.split('\n') if l.strip()]
        i = 0
        while i < len(lines2):
            if re.match(r'^\d{1,2}$', lines2[i]) and 1 <= int(lines2[i]) <= 18:
                num = int(lines2[i])
                if i + 2 < len(lines2):
                    odds_str = lines2[i + 2]
                    m = re.match(r'^(\d+\.?\d*)〜(\d+\.?\d*)$', odds_str)
                    if m:
                        if num not in result: result[num] = {}
                        result[num]['fuku_min'] = float(m.group(1))
                        result[num]['fuku_max'] = float(m.group(2))
                        i += 3
                        continue
            i += 1
    except:
        pass

    return result

def save_to_github(venue, race_num, odds, today_jst):
    """GitHubのjra_oddsに保存"""
    api_url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/contents/{GH_FILE}"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    for attempt in range(3):
        r = requests.get(api_url, headers=headers)
        if not r.ok: return False
        sha = r.json()["sha"]
        content = r.json()["content"].replace("\n", "")
        data = json.loads(base64.b64decode(content).decode())
        if "dates" not in data: data["dates"] = {}
        if today_jst not in data["dates"]: data["dates"][today_jst] = {}
        if "jra_odds" not in data["dates"][today_jst]: data["dates"][today_jst]["jra_odds"] = {}
        jra_odds = data["dates"][today_jst]["jra_odds"]
        # 会場キーを探す
        course_key = None
        for k in jra_odds:
            if venue in k:
                course_key = k
                break
        if not course_key:
            from datetime import date
            wd = date.today().weekday()
            day_str = "土" if wd == 5 else "日"
            course_key = f"{venue}({day_str})"
            jra_odds[course_key] = {}
        jra_odds[course_key][race_num] = odds
        data["dates"][today_jst]["jra_odds_updated"] = now_jst().isoformat()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        body = {
            "message": f"JRA odds {venue} {race_num}R {now_jst().strftime('%H:%M')}",
            "content": base64.b64encode(json_str.encode()).decode(),
            "sha": sha, "branch": GH_BRANCH
        }
        r2 = requests.put(api_url, headers=headers, json=body)
        if r2.status_code in [200, 201]:
            print(f"GitHub保存成功: {course_key} {race_num}R {len(odds)}頭")
            return True
        if r2.status_code == 409:
            continue
    return False

async def main():
    print(f"=== IPAT 1レース取得 {VENUE} {RACE_NUM}R ({TODAY_JST}) ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)
        await login(page)
        odds = await get_odds_one_race(page, VENUE, RACE_NUM)
        await browser.close()

    if not odds:
        print("オッズ取得失敗")
        return
    print(f"{len(odds)}頭取得成功")
    save_to_github(VENUE, RACE_NUM, odds, TODAY_JST)

if __name__ == "__main__":
    asyncio.run(main())
