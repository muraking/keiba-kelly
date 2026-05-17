"""
楽天競馬 自動購入スクリプト（単勝）
"""
import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

RAKUTEN_USER = os.environ.get("RAKUTEN_USER", "")
RAKUTEN_PASS = os.environ.get("RAKUTEN_PASS", "")

COURSE_NAME  = os.environ.get("COURSE_NAME", "")
RACE_NUM     = int(os.environ.get("RACE_NUM", "1"))
BETS         = json.loads(os.environ.get("BETS", "[]"))
DRY_RUN      = os.environ.get("DRY_RUN", "1") == "1"
TODAY        = os.environ.get("TODAY", "")  # YYYYMMDD形式

TIMEOUT = 30000

# 楽天競馬 場コード
VENUE_TO_CODE = {
    "帯広": "03", "帯広ば": "03",
    "門別":   "04",
    "盛岡":   "06",
    "水沢":   "07",
    "浦和":   "08",
    "船橋":   "09",
    "大井":   "10",
    "川崎":   "11",
    "金沢":   "12",
    "笠松":   "13",
    "名古屋": "14",
    "園田":   "17",
    "姫路":   "18",
    "高知":   "31",
    "佐賀":   "32",
}

LOGIN_URL = "https://keiba.rakuten.co.jp/"
BET_URL   = "https://bet.keiba.rakuten.co.jp/bet/odds/"


def get_today():
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST).strftime("%Y%m%d")


def build_race_id(venue, race_num, today):
    """RACEID形式: YYYYMMDD + 場コード2桁 + 00000001～12"""
    code = VENUE_TO_CODE.get(venue)
    if not code:
        raise ValueError(f"未対応の会場: {venue}")
    return f"{today}{code}{str(race_num).zfill(8)}"


async def login(page):
    print("ログイン中...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)

    # スクリーンショットでページ確認
    await page.screenshot(path="rakuten_login_top.png")
    text = await page.evaluate("() => document.body.innerText")
    print(f"トップページ内容（先頭200文字）: {text[:200]}")

    # マイページログインボタンをクリック
    try:
        await page.click('text=マイページログイン')
    except:
        await page.click('a:has-text("ログイン")')
    await page.wait_for_timeout(2000)
    await page.screenshot(path="rakuten_login_1.png")
    print(f"ログイン画面URL: {page.url}")

    # ユーザーID入力 → Enterキーで次へ（Reactページ対応）
    for selector in ['input[type="text"]', 'input[type="email"]', 'input[name="u"]']:
        try:
            el = await page.wait_for_selector(selector, timeout=5000)
            await el.click()
            await el.fill('')
            await el.type(RAKUTEN_USER, delay=50)
            print(f"  ユーザーID入力OK: {selector}")
            break
        except:
            continue

    await page.wait_for_timeout(500)

    # 次へボタン → click()とEnterの両方を試す
    try:
        btn = await page.wait_for_selector('button:has-text("次へ")', timeout=3000)
        await btn.click()
        print("  次へボタン click() OK")
    except:
        await page.keyboard.press('Enter')
        print("  次へボタン Enter OK")

    await page.wait_for_timeout(3000)
    await page.screenshot(path="rakuten_login_2.png")
    print(f"パスワード画面URL: {page.url}")

    # パスワード画面に遷移したか確認
    pw_text = await page.evaluate("() => document.body.innerText")
    print(f"パスワード画面内容（先頭100文字）: {pw_text[:100]}")

    # パスワード入力
    for selector in ['input[type="password"]', 'input[name="p"]']:
        try:
            el = await page.wait_for_selector(selector, timeout=5000)
            await el.click()
            await el.fill('')
            await el.type(RAKUTEN_PASS, delay=50)
            print(f"  パスワード入力OK: {selector}")
            break
        except:
            continue

    await page.wait_for_timeout(500)

    # ログインボタン
    try:
        btn = await page.wait_for_selector('button:has-text("次へ")', timeout=3000)
        await btn.click()
        print("  ログインボタン click() OK")
    except:
        await page.keyboard.press('Enter')
        print("  ログインボタン Enter OK")

    await page.wait_for_timeout(4000)
    await page.screenshot(path="rakuten_login_3.png")

    print(f"ログイン完了: {page.url}")

    # ログイン確認
    text = await page.evaluate("() => document.body.innerText")
    if "ログアウト" in text or "マイページ" in text:
        print("✅ ログイン成功")
    else:
        print("⚠️ ログイン状態が確認できません")
        await page.screenshot(path="rakuten_login_check.png")


async def get_balance(page):
    """購入限度額を取得"""
    try:
        # 投票画面に移動して残高確認
        await page.goto(BET_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
        await page.wait_for_timeout(2000)
        text = await page.evaluate("() => document.body.innerText")
        m = re.search(r'購入限度額\s*([\d,]+)', text)
        if m:
            v = int(m.group(1).replace(',', ''))
            print(f"✅ 購入限度額: ¥{v:,}")
            return v
        print("⚠️ 購入限度額取得失敗 → デフォルト¥10,000")
        return 10000
    except Exception as e:
        print(f"⚠️ 残高取得エラー: {e}")
        return 10000


async def navigate_to_race(page, venue, race_num, today):
    """レースページに直接アクセス"""
    race_id = build_race_id(venue, race_num, today)
    url = f"{BET_URL}RACEID/{race_id}"
    print(f"レースページ: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(3000)

    # 会場タブが表示されている場合は対象会場をクリック
    try:
        venue_tab = await page.query_selector(f'a:has-text("{venue}"), li:has-text("{venue}")')
        if venue_tab:
            await venue_tab.click()
            await page.wait_for_timeout(2000)
            print(f"  会場タブクリック: {venue}")
    except Exception as e:
        print(f"  会場タブスキップ: {e}")

    # レース番号クリック（完全一致でJSクリック）
    js = f"""() => {{
        const els = document.querySelectorAll('a, td, li, span');
        for (const el of els) {{
            if (el.innerText?.trim() === '{race_num}R') {{
                el.click();
                return true;
            }}
        }}
        return false;
    }}"""
    clicked = await page.evaluate(js)
    if clicked:
        await page.wait_for_timeout(2000)
        print(f"  レース番号クリック: {race_num}R")
    else:
        print(f"  レース番号クリック失敗: {race_num}R")

    text = await page.evaluate("() => document.body.innerText")

    if "単勝" in text or "複勝" in text:
        print(f"✅ レースページ表示OK: {venue} {race_num}R")
        return True
    else:
        print("⚠️ レースページが正しく表示されていません")
        await page.screenshot(path="rakuten_race_check.png")
        return False


async def fetch_odds(page):
    """現在ページの単勝・複勝オッズを取得
    テーブル1の構造: 列0=馬番, 列1=馬名(link), 列2=騎手, 列3=単勝オッズ(link), 列4=複勝オッズ(link), 列5=人気
    戻り値: {馬番: {"tan": 単勝オッズ, "fuku_min": 複勝最小, "fuku_max": 複勝最大}}
    """
    odds_map = {}
    try:
        result = await page.evaluate("""
            () => {
                const tables = document.querySelectorAll('table');
                for (const table of tables) {
                    const rows = table.querySelectorAll('tr');
                    let isHorseTable = false;
                    const tableResult = {};

                    for (const row of rows) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length < 4) continue;

                        const numText = cells[0]?.innerText?.trim();
                        if (!/^\d{1,2}$/.test(numText)) continue;

                        const num = parseInt(numText);
                        const tanText = cells[3]?.innerText?.trim();
                        const fukuText = cells[4]?.innerText?.trim();

                        const tan = parseFloat(tanText);
                        if (isNaN(tan) || tan < 1.0) continue;

                        isHorseTable = true;
                        const entry = { tan: tan };

                        // 複勝オッズ（例: "1.2-2.2"）
                        if (fukuText && fukuText.includes('-')) {
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

                    if (isHorseTable) return tableResult;
                }
                return {};
            }
        """)

        for num_str, entry in result.items():
            odds_map[int(num_str)] = entry

        if odds_map:
            print(f"  オッズ取得: {len(odds_map)}頭")
            for num, o in sorted(odds_map.items()):
                fuku = f" 複{o.get('fuku_min','?')}-{o.get('fuku_max','?')}" if 'fuku_min' in o else ""
                print(f"    {num}番: 単{o['tan']}{fuku}")
        else:
            print("  ⚠️ オッズ取得失敗")

    except Exception as e:
        print(f"オッズ取得エラー: {e}")
    return odds_map


async def add_to_cart(page, bets):
    """単勝オッズをクリックして馬券カゴに追加"""
    print("馬券カゴに追加中...")

    for bet in bets:
        num = bet['num']
        print(f"  {num}番を選択...")
        try:
            # 列構造自動判定:
            # 枠番+馬番: 列0=枠番, 列1=馬番, 列4=単勝, 列5=複勝 (高知・佐賀・帯広)
            # 枠番のみ: 行番号を馬番として使用, 列3=単勝 (盛岡・金沢)
            clicked = await page.evaluate(f"""
                () => {{
                    const tables = document.querySelectorAll('table');
                    let horseCount = 0;
                    for (const table of tables) {{
                        const rows = table.querySelectorAll('tr');
                        horseCount = 0;
                        for (const row of rows) {{
                            const cells = row.querySelectorAll('td');
                            if (cells.length < 4) continue;
                            const col0 = cells[0]?.innerText?.trim();
                            const col1 = cells[1]?.innerText?.trim();
                            const col0IsNum = /^[0-9]{{1,2}}$/.test(col0);
                            const col1IsNum = /^[0-9]{{1,2}}$/.test(col1);
                            if (!col0IsNum) continue;
                            let tanIdx, numText;
                            if (col1IsNum) {{
                                // 枠番+馬番構造
                                numText = col1; tanIdx = 4;
                            }} else {{
                                // 枠番のみ構造 → 行番号を馬番に
                                horseCount++;
                                numText = String(horseCount); tanIdx = 3;
                            }}
                            if (numText === '{num}') {{
                                // 単勝オッズセル（tanIdx）のaタグをクリック
                                const a = cells[tanIdx]?.querySelector('a');
                                if (a) {{
                                    a.click();
                                    return 'a_click:' + cells[tanIdx].innerText.trim();
                                }}
                                cells[tanIdx]?.click();
                                return 'cell_click';
                            }}
                        }}
                    }}
                    return false;
                }}
            """)
            print(f"    {num}番: {clicked}")
            await page.wait_for_timeout(1500)

        except Exception as e:
            print(f"    {num}番 エラー: {e}")

    await page.wait_for_timeout(1000)

    # カゴ追加確認（件数表示）
    cart_count = await page.evaluate(r"""
        () => {
            const text = document.body.innerText;
            const m = text.match(/件数[：:]?\s*(\d+)/);
            return m ? m[1] : '不明';
        }
    """)
    print(f"カゴ件数: {cart_count}")


async def input_amounts(page, bets):
    """各馬の金額を入力"""
    print("金額入力中...")
    bet_map = {b['num']: b['amount'] for b in bets}

    try:
        # 金額入力欄を取得（馬番と対応）
        inputs = await page.query_selector_all('input[type="text"]')
        print(f"  入力欄数: {len(inputs)}")

        for inp in inputs:
            if not await inp.is_visible():
                continue
            # 入力欄の近くの馬番を特定
            horse_num = await page.evaluate("""
                (el) => {
                    const row = el.closest('tr');
                    if (!row) return null;
                    // 馬番セルを探す
                    const cells = row.querySelectorAll('td');
                    for (const cell of cells) {
                        const t = cell.innerText.trim();
                        if (/^\\d{1,2}$/.test(t) && parseInt(t) >= 1 && parseInt(t) <= 18) {
                            return parseInt(t);
                        }
                    }
                    return null;
                }
            """, inp)

            if horse_num and horse_num in bet_map:
                amount_100 = bet_map[horse_num] // 100
                await inp.fill(str(amount_100))
                await inp.dispatch_event('input')
                await inp.dispatch_event('change')
                await page.keyboard.press('Tab')
                print(f"  {horse_num}番: {amount_100}（¥{bet_map[horse_num]:,}）")
                await page.wait_for_timeout(300)

    except Exception as e:
        print(f"金額入力エラー: {e}")


async def purchase(page, venue, race_num, bets, today):
    total = sum(b['amount'] for b in bets)
    print(f"\n=== 購入: {venue} {race_num}R 合計¥{total:,} ===")
    for b in bets:
        print(f"  {b['num']}番 {b.get('name','')} ¥{b['amount']:,}")

    # レースページへ移動
    ok = await navigate_to_race(page, venue, race_num, today)
    if not ok:
        return False

    await page.screenshot(path="rakuten_01_race.png")

    # 式別「単勝/複勝」を確認（デフォルトで選択済みのはず）
    try:
        await page.click('text=単勝/複勝')
        await page.wait_for_timeout(500)
    except:
        pass

    # 馬券カゴに追加
    await add_to_cart(page, bets)
    await page.screenshot(path="rakuten_02_cart.png")

    # 金額入力
    await input_amounts(page, bets)
    await page.screenshot(path="rakuten_03_amount.png")

    # DRY RUN
    if DRY_RUN:
        print("\n========== DRY RUN MODE ==========")
        print("[テスト] 投票確認画面の直前で停止（実際には投票しません）")
        for b in bets:
            print(f"  {b['num']}番 {b.get('name','')} 単勝 ¥{b['amount']:,}")
        print(f"  合計: ¥{total:,}")
        print("===================================")
        print("✅ DRY RUN完了")
        return True

    # 「投票内容を確認する」ボタン
    print("投票内容を確認する...")
    try:
        await page.click('text=投票内容を確認する')
        await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"  ⚠️ 確認ボタンエラー: {e}")
        return False

    await page.screenshot(path="rakuten_04_confirm.png")

    # 投票金額（合計）を入力
    print(f"投票金額入力: ¥{total:,}")
    try:
        # 投票金額入力欄を探す（確認画面）
        inp = await page.query_selector('input[type="text"]:visible, input[type="number"]:visible')
        if inp:
            await inp.click()
            await inp.fill(str(total))
            await inp.dispatch_event('input')
            await inp.dispatch_event('change')
            print(f"  投票金額入力OK: ¥{total:,}")
        else:
            # フォールバック: 全inputを試す
            all_inputs = await page.query_selector_all('input')
            for i in all_inputs:
                if await i.is_visible():
                    await i.fill(str(total))
                    await i.dispatch_event('change')
                    print(f"  投票金額入力OK（フォールバック）: ¥{total:,}")
                    break
    except Exception as e:
        print(f"  投票金額入力エラー: {e}")

    await page.screenshot(path="rakuten_05_total.png")

    # ダイアログハンドラ
    async def handle_dialog(dialog):
        print(f"  💬 ダイアログ: {dialog.message[:80]}")
        await dialog.accept()
    page.on('dialog', handle_dialog)

    # 「投票する」ボタン（確認画面の赤ボタンをクリック）
    for step in range(2):
        print(f"投票する... (ステップ{step+1})")
        try:
            # 複数のセレクターで試す（確認画面の赤ボタン優先）
            clicked = False
            # voteBtn クラスのAタグをスクロール+クリック
            js_clicked = await page.evaluate("""
                () => {
                    // class=voteBtnを優先
                    const voteBtn = document.querySelector('a.voteBtn, input.voteBtn, button.voteBtn');
                    if (voteBtn) {
                        voteBtn.scrollIntoView({behavior: 'instant', block: 'center'});
                        voteBtn.click();
                        return 'voteBtn:' + voteBtn.tagName;
                    }
                    // フォールバック: テキストで探す
                    const all = document.querySelectorAll('input[type=submit], input[type=button], button, a');
                    for (const el of all) {
                        const v = (el.value || el.innerText || '').trim();
                        if (v === '投票する') {
                            el.scrollIntoView({behavior: 'instant', block: 'center'});
                            el.click();
                            return v + ':' + el.tagName;
                        }
                    }
                    return null;
                }
            """)
            if js_clicked:
                print(f"  JSクリック成功: {js_clicked}")
                clicked = True
            else:
                print("  ⚠️ 投票ボタンが見つかりません")
                break
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  ⚠️ 投票ボタンエラー: {e}")
            break

        text = await page.evaluate("() => document.body.innerText")

        # 投票内容確認画面の場合はもう一度「投票する」を押す
        if '投票内容確認' in text:
            print("  → 投票内容確認画面。ステップ2へ...")
            continue

        # 投票完了判定（確認画面を抜けた後）
        # 「受付番号」「投票が完了」「ありがとうございました」などで判定
        if '受付番号' in text or '投票が完了' in text or 'ありがとうございました' in text:
            await page.screenshot(path="rakuten_06_result.png")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            print("結果:")
            for line in lines[:20]:
                print(f"  {line}")
            print("\n✅ 投票完了！")
            return True

        # 3,000件などの正常完了パターン
        if '投票可能件数' in text and '投票内容確認' not in text:
            await page.screenshot(path="rakuten_06_result.png")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            print("結果:")
            for line in lines[:20]:
                print(f"  {line}")
            print("\n✅ 投票完了！")
            return True

        break

    await page.screenshot(path="rakuten_06_result.png")
    result_text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in result_text.split('\n') if l.strip()]
    print("結果:")
    for line in lines[:20]:
        print(f"  {line}")
    print("\n⚠️ 投票結果不明（スクリーンショット確認）")
    return False


async def main():
    global TODAY

    if not TODAY:
        TODAY = get_today()

    if not COURSE_NAME:
        print("❌ COURSE_NAME が設定されていません")
        return

    print(f"=== 楽天競馬自動購入 ===")
    print(f"DRY_RUN: {DRY_RUN}")
    print(f"会場: {COURSE_NAME} {RACE_NUM}R")
    print(f"買い目: {BETS}")
    print(f"日付: {TODAY}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--dns-prefetch-disable', '--no-sandbox']
        )
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)

        await login(page)
        await get_balance(page)

        result = await purchase(page, COURSE_NAME, RACE_NUM, BETS, TODAY)

        await browser.close()

        if not result:
            print("❌ 購入失敗")
            raise SystemExit(1)
        print("✅ 購入フロー正常終了")


if __name__ == "__main__":
    asyncio.run(main())
