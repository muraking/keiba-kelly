"""
楽天競馬 オッズ取得スクリプト
GitHub Actionsから呼び出され、オッズをindices.jsonに保存する
"""
import asyncio
import os
import json
import base64
import time
import requests
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

RAKUTEN_USER = os.environ.get("RAKUTEN_USER", "")
RAKUTEN_PASS = os.environ.get("RAKUTEN_PASS", "")
GH_TOKEN     = os.environ.get("GH_TOKEN", "")
GH_USER      = os.environ.get("GH_USER", "muraking")
GH_REPO      = os.environ.get("GH_REPO", "keiba-kelly")
GH_BRANCH    = os.environ.get("GH_BRANCH", "main")
GH_FILE      = os.environ.get("GH_FILE", "data/indices.json")
VENUE        = os.environ.get("VENUE", "")
RACE_NUM     = int(os.environ.get("RACE_NUM", "1"))
TODAY_JST    = os.environ.get("TODAY_JST", "")

JST = timezone(timedelta(hours=9))
TIMEOUT = 30000

VENUE_TO_CODE = {
    "帯広": "03", "帯広ば": "03", "門別": "04", "盛岡": "06", "水沢": "07",
    "浦和":   "08", "船橋": "09", "大井": "10", "川崎": "11",
    "金沢":   "12", "笠松": "13", "名古屋": "14", "園田": "17",
    "姫路":   "18", "高知": "31", "佐賀":  "32",
}

LOGIN_URL = "https://keiba.rakuten.co.jp/"
BET_URL   = "https://bet.keiba.rakuten.co.jp/bet/odds/"


def now_jst():
    return datetime.now(JST)


def get_today_jst():
    return now_jst().strftime("%Y-%m-%d")


def get_today():
    return now_jst().strftime("%Y%m%d")


async def login(page):
    print("ログイン中...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)

    await page.click('text=マイページログイン')
    await page.wait_for_timeout(2000)

    el = await page.wait_for_selector('input[type="text"]', timeout=5000)
    await el.click()
    await el.fill('')
    await el.type(RAKUTEN_USER, delay=50)
    await page.wait_for_timeout(500)
    try:
        btn = await page.wait_for_selector('button:has-text("次へ")', timeout=3000)
        await btn.click()
    except:
        await page.keyboard.press('Enter')
    await page.wait_for_timeout(3000)

    el = await page.wait_for_selector('input[type="password"]', timeout=5000)
    await el.click()
    await el.fill('')
    await el.type(RAKUTEN_PASS, delay=50)
    await page.wait_for_timeout(500)
    try:
        btn = await page.wait_for_selector('button:has-text("次へ")', timeout=3000)
        await btn.click()
    except:
        await page.keyboard.press('Enter')
    await page.wait_for_timeout(4000)
    print(f"ログイン完了: {page.url}")


async def fetch_odds(page, venue, race_num, today):
    code = VENUE_TO_CODE.get(venue)
    if not code:
        raise ValueError(f"未対応の会場: {venue}")

    race_id = f"{today}{code}{str(race_num).zfill(8)}"
    url = f"{BET_URL}RACEID/{race_id}"
    print(f"レースページ: {url}")

    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(3000)

    # ページ確認
    text = await page.evaluate("() => document.body.innerText")
    print(f"ページ内容（先頭200文字）: {text[:200]}")
    await page.screenshot(path="rakuten_odds_debug.png")

    # 会場タブクリック（text=セレクターで直接クリック）
    try:
        await page.click(f'text={venue}', timeout=3000)
        await page.wait_for_timeout(2000)
        print(f"会場タブクリック: {venue}")
    except:
        # フォールバック: JSで全要素を検索
        clicked = await page.evaluate(f"""
            () => {{
                for (const el of document.querySelectorAll('*')) {{
                    if (el.children.length === 0 && el.innerText && el.innerText.trim() === '{venue}') {{
                        el.click();
                        return el.tagName;
                    }}
                }}
                return false;
            }}
        """)
        print(f"JS会場クリック: {clicked}" if clicked else f"会場タブ見つからず: {venue}")
        await page.wait_for_timeout(2000)

    # レース番号クリック
    try:
        await page.click(f'text={race_num}R', timeout=3000)
        await page.wait_for_timeout(2000)
        print(f"レース番号クリック: {race_num}R")
    except:
        print(f"レース番号クリック失敗: {race_num}R")

    # テーブル全体をデバッグダンプ
    debug_info = await page.evaluate("""
        () => {
            const tables = document.querySelectorAll('table');
            return Array.from(tables).slice(0, 3).map((t, ti) => {
                const rows = t.querySelectorAll('tr');
                return {
                    ti,
                    rows: Array.from(rows).slice(0, 15).map((r, ri) => {
                        const cs = r.querySelectorAll('td');
                        return {ri, cells: Array.from(cs).map(c => c.innerText.trim().substring(0, 10))};
                    }).filter(r => r.cells.length > 0)
                };
            });
        }
    """)
    for t in debug_info:
        print(f"  [テーブル{t['ti']}]")
        for r in t['rows']:
            print(f"    行{r['ri']}: {r['cells']}")

    # テーブルからオッズ取得
    # 楽天競馬テーブル構造: 列0=枠番, 列1=馬番, 列2=馬名, 列3=騎手, 列4=単勝, 列5=複勝
    result = await page.evaluate("""
        () => {
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                const tableResult = {};
                let found = false;
                for (const row of rows) {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 4) continue;
                    // 楽天競馬テーブル: 列0=枠番, 列1=馬番, 列2=馬名, 列3=騎手, 列4=単勝, 列5=複勝
                    const numText = cells[1]?.innerText?.trim();
                    if (!/^[0-9]{1,2}$/.test(numText)) continue;
                    if (cells.length < 5) continue;
                    const num = parseInt(numText);
                    const tan = parseFloat(cells[4]?.innerText?.trim());
                    if (isNaN(tan) || tan < 1.0) continue;
                    found = true;
                    const entry = { tan: tan };
                    const fukuText = cells[fukuIdx]?.innerText?.trim() || '';
                    if (fukuText.includes('-')) {
                        const parts = fukuText.split('-');
                        const fmin = parseFloat(parts[0]);
                        const fmax = parseFloat(parts[1]);
                        if (!isNaN(fmin) && fmin > 0) {
                            entry.fuku_min = fmin;
                            entry.fuku_max = isNaN(fmax) ? null : fmax;
                        }
                    }
                    tableResult[num] = entry;
                }
                if (found) return tableResult;
            }
            return {};
        }
    """)

    odds_map = {int(k): v for k, v in result.items()}
    if odds_map:
        print(f"✅ オッズ取得: {len(odds_map)}頭")
        for num, o in sorted(odds_map.items()):
            fuku = f" 複{o.get('fuku_min','?')}-{o.get('fuku_max','?')}" if 'fuku_min' in o else ""
            print(f"  {num}番: 単{o['tan']}{fuku}")
    else:
        print("⚠️ オッズ取得失敗")
    return odds_map


def save_to_github(venue, race_num, odds, today_jst):
    api_url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/contents/{GH_FILE}"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    for attempt in range(3):
        try:
            r = requests.get(api_url, headers=headers)
            if not r.ok:
                print(f"GitHub取得失敗: {r.status_code}")
                return False

            sha = r.json()["sha"]
            content = r.json()["content"].replace("\n", "")
            data = json.loads(base64.b64decode(content).decode())

            if "dates" not in data:
                data["dates"] = {}
            if today_jst not in data["dates"]:
                data["dates"][today_jst] = {}
            if "odds" not in data["dates"][today_jst]:
                data["dates"][today_jst]["odds"] = {}

            # 楽天場コードをキーに保存
            code = VENUE_TO_CODE.get(venue, venue)
            if code not in data["dates"][today_jst]["odds"]:
                data["dates"][today_jst]["odds"][code] = {}

            data["dates"][today_jst]["odds"][code][str(race_num)] = odds
            data["dates"][today_jst]["odds_updated"] = now_jst().isoformat()

            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            body = {
                "message": f"rakuten odds {venue} {race_num}R {now_jst().strftime('%H:%M')}",
                "content": base64.b64encode(json_str.encode()).decode(),
                "sha": sha,
                "branch": GH_BRANCH
            }
            r2 = requests.put(api_url, headers=headers, json=body)
            if r2.status_code in [200, 201]:
                print(f"✅ GitHub保存成功")
                return True
            if r2.status_code == 409:
                print(f"SHA競合 リトライ {attempt+1}/3...")
                time.sleep(3)
                continue
            print(f"保存失敗: {r2.status_code}")
            return False
        except Exception as e:
            print(f"エラー: {e}")
            return False
    return False


async def main():
    if not VENUE:
        print("❌ VENUE が設定されていません")
        raise SystemExit(1)

    today     = get_today()
    today_jst = TODAY_JST or get_today_jst()

    print(f"=== 楽天競馬オッズ取得 ===")
    print(f"会場: {VENUE} {RACE_NUM}R / 日付: {today_jst}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox']
        )
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)

        await login(page)
        odds = await fetch_odds(page, VENUE, RACE_NUM, today)
        await browser.close()

    if not odds:
        print("❌ オッズ取得失敗")
        raise SystemExit(1)

    save_to_github(VENUE, RACE_NUM, odds, today_jst)
    print("✅ 完了")


if __name__ == "__main__":
    asyncio.run(main())
