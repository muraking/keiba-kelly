"""
IPAT SP版 中央競馬オッズ自動取得スクリプト
"""
import asyncio
import json
import requests
import base64
import re
import os
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

# ===== 設定 =====
IPAT_ID   = os.environ.get("IPAT_ID", "ここに加入者番号を入力")
IPAT_PIN  = os.environ.get("IPAT_PIN", "ここに暗証番号を入力")
IPAT_PARS = os.environ.get("IPAT_PARS", "ここにP-ARS番号を入力")

GH_TOKEN  = os.environ.get("GH_TOKEN", "ここにGitHubトークンを入力")
GH_USER   = "muraking"
GH_REPO   = "keiba-kelly"
GH_BRANCH = "main"
GH_FILE   = "data/indices.json"

LOGIN_URL = "https://www.ipat.jra.go.jp/sp/"
TIMEOUT   = 30000
# =================

def now_jst():
    return datetime.now(timezone(timedelta(hours=9)))

def get_today_jst():
    return now_jst().strftime("%Y-%m-%d")

async def login(page):
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)
    await page.fill('#userid', IPAT_ID)
    await page.fill('#password', IPAT_PIN)
    await page.fill('#pars', IPAT_PARS)
    await page.evaluate("ToSPMenu()")
    await page.wait_for_timeout(3000)

async def get_course_list(page):
    """開催会場一覧を取得、URLも返す"""
    await page.click('text=オッズ投票')
    await page.wait_for_timeout(2000)
    course_list_url = page.url
    text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    courses = []
    for line in lines:
        # 「東京(土)」「京都(日)」などのパターン（GIなど特別レース名を除外）
        if re.match(r'^.+\([土日]\)$', line):
            courses.append(line)
    return courses, course_list_url

async def get_race_list(page, course_name):
    """レース一覧を取得"""
    # 会場リンクが表示されるまで待つ
    await page.wait_for_selector(f'text={course_name}', timeout=TIMEOUT)
    await page.click(f'text={course_name}')
    await page.wait_for_timeout(2000)
    text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    races = []
    for line in lines:
        m = re.match(r'^(\d+)R$', line)
        if m:
            races.append(int(m.group(1)))
    return races

async def get_tan_odds(page, race_num):
    """単勝オッズを取得"""
    # レースをクリック
    await page.click(f'text={race_num}R')
    await page.wait_for_timeout(1500)
    # 式別から選択
    await page.click('text=式別から選択')
    await page.wait_for_timeout(1500)
    # 単勝
    await page.click('text=単勝')
    await page.wait_for_timeout(2000)

    text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # パース: 馬番・馬名・オッズの3行セット
    result = {}
    i = 0
    while i < len(lines):
        # 馬番（1〜18の整数）
        if re.match(r'^\d{1,2}$', lines[i]) and 1 <= int(lines[i]) <= 18:
            num = int(lines[i])
            if i + 2 < len(lines):
                name = lines[i + 1]
                odds_str = lines[i + 2]
                # オッズ（小数または整数）
                if re.match(r'^\d+\.?\d*$', odds_str):
                    odds_val = float(odds_str)
                    if odds_val > 0:
                        result[num] = {"tan": odds_val, "name": name}
                    i += 3
                    continue
        i += 1

    return result

async def get_fuku_odds(page):
    """複勝オッズを取得（単勝ページから式別に戻って複勝選択）"""
    try:
        # 式別選択画面へ戻る
        back_links = await page.query_selector_all('a')
        clicked = False
        for link in back_links:
            text = (await link.inner_text()).strip()
            if '式別選択' in text and '戻' in text:
                await link.click()
                clicked = True
                await page.wait_for_timeout(1500)
                break
        if not clicked:
            return {}
        await page.click('text=複勝')
        await page.wait_for_timeout(2000)
    except Exception as e:
        return {}

    text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    result = {}
    i = 0
    while i < len(lines):
        if re.match(r'^\d{1,2}$', lines[i]) and 1 <= int(lines[i]) <= 18:
            num = int(lines[i])
            if i + 2 < len(lines):
                # 複勝は「下限〜上限」形式または単一値
                name = lines[i + 1]
                odds_str = lines[i + 2]
                m = re.match(r'^(\d+\.?\d*)〜(\d+\.?\d*)$', odds_str)
                if m:
                    fmin = float(m.group(1))
                    fmax = float(m.group(2))
                    if fmin > 0:
                        result[num] = {"fuku_min": fmin, "fuku_max": fmax}
                    i += 3
                    continue
                elif re.match(r'^\d+\.?\d*$', odds_str):
                    fval = float(odds_str)
                    if fval > 0:
                        result[num] = {"fuku_min": fval}
                    i += 3
                    continue
        i += 1
    return result

def save_to_github(all_odds, today_jst):
    """GitHubに保存"""
    api_url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/contents/{GH_FILE}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    r = requests.get(api_url, headers=headers)
    if not r.ok:
        print(f"  GitHub取得失敗: {r.status_code}")
        return False

    sha = r.json()["sha"]
    content = r.json()["content"].replace("\n", "")
    data = json.loads(base64.b64decode(content).decode())

    if "dates" not in data: data["dates"] = {}
    if today_jst not in data["dates"]: data["dates"][today_jst] = {}
    if "jra_odds" not in data["dates"][today_jst]: data["dates"][today_jst]["jra_odds"] = {}

    data["dates"][today_jst]["jra_odds"].update(all_odds)
    data["dates"][today_jst]["jra_odds_updated"] = now_jst().isoformat()

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    body = {
        "message": f"JRA odds {now_jst().strftime('%H:%M')}",
        "content": base64.b64encode(json_str.encode()).decode(),
        "sha": sha,
        "branch": GH_BRANCH
    }
    r2 = requests.put(api_url, headers=headers, json=body)
    if r2.status_code in [200, 201]:
        print("  GitHub保存成功")
        return True
    print(f"  GitHub保存失敗: {r2.status_code}")
    return False

async def main():
    today_jst = get_today_jst()
    print(f"=== IPAT SP版 JRAオッズ取得 ({today_jst}) ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)

        await login(page)
        print("ログイン完了")

        # 会場一覧を取得
        courses, course_list_url = await get_course_list(page)
        print(f"開催会場: {courses}")

        all_odds = {}

        for course in courses:
            print(f"\n{course}:")
            all_odds[course] = {}

            # 会場ごとに再ログイン → オッズ投票 → 会場選択
            await login(page)
            await page.click('text=オッズ投票')
            await page.wait_for_timeout(2000)

            # レース一覧を取得
            races = await get_race_list(page, course)
            print(f"  レース数: {len(races)}")

            # レース一覧URLを保存
            race_list_url = page.url

            for race_num in races:
                print(f"  {race_num}R 取得中...", end=' ', flush=True)

                # レース一覧に戻る
                await page.goto(race_list_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                await page.wait_for_timeout(1000)

                # 単勝取得
                tan = await get_tan_odds(page, race_num)
                # 複勝取得
                fuku = await get_fuku_odds(page)

                # マージ
                merged = {}
                for num, info in tan.items():
                    merged[num] = {"tan": info["tan"]}
                for num, info in fuku.items():
                    if num not in merged: merged[num] = {}
                    merged[num].update(info)

                if merged:
                    all_odds[course][race_num] = merged
                    print(f"{len(merged)}頭 OK")
                else:
                    print("失敗")

        # GitHub保存
        print("\nGitHubに保存中...")
        save_to_github(all_odds, today_jst)

        await browser.close()
        print("完了")

if __name__ == "__main__":
    asyncio.run(main())
