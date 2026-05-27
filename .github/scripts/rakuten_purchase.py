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
BET_NORMAL_URL = "https://bet.keiba.rakuten.co.jp/bet/purchase/"


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
        print("⚠️ 購入限度額取得失敗 → None")
        return None
    except Exception as e:
        print(f"⚠️ 残高取得エラー: {e}")
        return None


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
    """現在ページの単勝・複勝オッズを取得"""
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
    """単勝・複勝をクリックして馬券カゴに追加"""
    print("馬券カゴに追加中...")

    tan_bets = [b for b in bets if b.get('bet_type', 'tan') == 'tan']
    fuku_bets = [b for b in bets if b.get('bet_type') == 'fuku']

    async def click_horse(num, col_offset):
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
                        let baseIdx, numText;
                        if (col1IsNum) {{
                            numText = col1; baseIdx = 4;
                        }} else {{
                            horseCount++;
                            numText = String(horseCount); baseIdx = 3;
                        }}
                        if (numText === '{num}') {{
                            const idx = baseIdx + {col_offset};
                            const a = cells[idx]?.querySelector('a');
                            if (a) {{ a.click(); return 'a_click:' + cells[idx].innerText.trim(); }}
                            cells[idx]?.click();
                            return 'cell_click';
                        }}
                    }}
                }}
                return false;
            }}
        """)
        return clicked

    for bet in tan_bets:
        num = bet['num']
        print(f"  {num}番（単勝）を選択...")
        try:
            clicked = await click_horse(num, 0)
            print(f"    {num}番: {clicked}")
            await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"    {num}番 エラー: {e}")

    for bet in fuku_bets:
        num = bet['num']
        print(f"  {num}番（複勝）を選択...")
        try:
            clicked = await click_horse(num, 1)
            print(f"    {num}番複勝: {clicked}")
            await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"    {num}番複勝 エラー: {e}")

    await page.wait_for_timeout(1000)

    cart_count = await page.evaluate(r"""
        () => {
            const text = document.body.innerText;
            const m = text.match(/件数[：:]?\s*(\d+)/);
            return m ? m[1] : '不明';
        }
    """)
    print(f"カゴ件数: {cart_count}")


async def add_to_cart_combo(page, bets, bet_type):
    """馬連・ワイドをフォーメーション方式でカゴに追加"""
    label = '馬連' if bet_type == 'exacta' else 'ワイド'
    print(f"{label}フォーメーション選択中...")

    if bet_type == 'exacta':
        tab_labels = ['馬連', '馬複']
    else:
        tab_labels = ['ワイド']

    # 「通常」タブをクリックして式別タブを表示
    for try_normal in ['通常', '通常投票']:
        try:
            await page.click(f'text={try_normal}', timeout=3000)
            await page.wait_for_timeout(1500)
            print(f"  {try_normal}タブ クリックOK")
            break
        except Exception as e:
            print(f"  {try_normal}タブ失敗: {e}")

    # 式別タブをクリック
    tab_clicked = False
    tab_label = tab_labels[0]
    for try_label in tab_labels:
        try:
            loc = page.locator(f'a:text-is("{try_label}")')
            cnt = await loc.count()
            print(f"  式別タブ '{try_label}' 候補数: {cnt}")
            if cnt > 0:
                await loc.first.click(timeout=5000)
                await page.wait_for_timeout(1000)
                tab_label = try_label
                print(f"  式別タブ '{try_label}' OK")
                tab_clicked = True
                break
        except Exception as e:
            print(f"  式別タブ '{try_label}' 失敗: {e}")

    if not tab_clicked:
        pt = await page.evaluate("() => document.body.innerText.slice(0,400)")
        print(f"  ページテキスト: {pt}")

    # ② フォーメーション方式をクリック（ポーリング方式・最大10秒）
    fmt_clicked = False
    for _retry in range(10):
        await page.wait_for_timeout(1000)
        result = await page.evaluate(
            "() => {"
            "  const els = document.querySelectorAll('a, button, td, li, span');"
            "  for (const el of els) {"
            "    const t = (el.innerText || el.textContent || '').trim();"
            "    if (t.includes('フォーメーション') && t.length < 15) {"
            "      el.click(); return 'found:' + t;"
            "    }"
            "  }"
            "  return false;"
            "}"
        )
        if result:
            fmt_clicked = result
            print(f"  フォーメーション発見({_retry+1}回目): {fmt_clicked}")
            break
        # 5秒経過時にページ内容をデバッグ出力
        if _retry == 4:
            pt = await page.evaluate("() => document.body.innerText.slice(0, 400)")
            print(f"  [5秒後ページ内容]: {pt}")

    if not fmt_clicked:
        pt = await page.evaluate("() => document.body.innerText.slice(0, 400)")
        print(f"  [10秒後ページ内容]: {pt}")
        print("  ⚠️ フォーメーション選択失敗 → スキップ")
        return False

    await page.wait_for_timeout(1000)
    print("  フォーメーション OK")

    # ③ ページ構造をダンプ（詳細版）
    page_info = await page.evaluate("() => { var t=document.querySelectorAll('table'); var r='tables:'+t.length; for(var i=0;i<Math.min(5,t.length);i++){var rows=t[i].querySelectorAll('tr');r+=' tbl'+i+'('+rows.length+'rows)';for(var j=0;j<Math.min(3,rows.length);j++){var cs=rows[j].querySelectorAll('td,th');r+=' R'+j+'['+Array.from(cs).map(function(c){return (c.innerText.trim()||c.innerHTML.trim()).slice(0,20);}).join('|')+']';}} return r; }")
    print(f"  テーブル構造: {page_info}")

    # 軸馬・相手馬
    axis_nums    = list(dict.fromkeys([b['num1'] for b in bets]))
    partner_nums = list(dict.fromkeys([b['num2'] for b in bets]))
    print(f"  馬1（軸）: {axis_nums}")
    print(f"  馬2（相手）: {partner_nums}")

    async def click_combo_horse(num, col_offset):
        """フォーメーションの馬番ボタンをクリック
        col_offset: 0=馬1列(cells[4]=kaime1), 1=馬2列(cells[5]=kaime2)
        cells[0]=枠番(=馬番), cells[1]=馬名, cells[4+offset]=ボタン
        """
        num_str = str(num)
        num_str2 = f"{num:02d}"
        clicked = await page.evaluate(
            f"() => {{"
            f"  const tables = document.querySelectorAll('table');"
            f"  for (const table of tables) {{"
            f"    const rows = table.querySelectorAll('tr');"
            f"    for (const row of rows) {{"
            f"      const cells = row.querySelectorAll('td');"
            f"      if (cells.length < 5) continue;"
            f"      const c0 = cells[0].innerText.trim();"
            f"      const c1 = cells[1].innerText.trim();"
            f"      const c0ok = c0 === '{num_str}' || c0 === '{num_str2}';"
            f"      const c1ok = /^[0-9]{{1,2}}$/.test(c1) && (c1 === '{num_str}' || c1 === '{num_str2}');"
            f"      if (!c0ok && !c1ok) continue;"
            f"      if (!/^[0-9]{{1,2}}$/.test(c0)) continue;"
            f"      const idx = 4 + {col_offset};"
            f"      if (cells.length <= idx) continue;"
            f"      const a = cells[idx].querySelector('a');"
            f"      if (a) {{ a.click(); return 'a_click:c0=' + c0 + ':col' + idx; }}"
            f"      cells[idx].click();"
            f"      return 'cell_click:c0=' + c0 + ':col' + idx;"
            f"    }}"
            f"  }}"
            f"  return false;"
            f"}}"
        )
        return clicked

    print("  フォーメーション構造確認: cells[0]=枠番(馬番), cells[4]=馬1ボタン, cells[5]=馬2ボタン")

    print(f"  馬1（軸）: {axis_nums}")
    for num in axis_nums:
        result = await click_combo_horse(num, 0)
        print(f"    馬1:{num}番: {result or 'NG'}")
        await page.wait_for_timeout(500)

    print(f"  馬2（相手）: {partner_nums}")
    for num in partner_nums:
        result = await click_combo_horse(num, 1)
        print(f"    馬2:{num}番: {result or 'NG'}")
        await page.wait_for_timeout(500)

    # 組数確認
    kumi = await page.evaluate("() => { var m=document.body.innerText.match(/組数[：:]?\s*(\d+)/); return m?m[1]:'不明'; }")
    print(f"  選択組数: {kumi}")

    # ⑥ 金額入力
    unit_amount = bets[0]['amount'] if bets else 100
    inp = await page.query_selector('input[type=text]:visible, input[type=number]:visible')
    if inp:
        await inp.fill(str(unit_amount // 100))
        await inp.dispatch_event('change')
        print(f"  金額入力OK: {unit_amount//100}×100=¥{unit_amount}")
    else:
        for d in str(unit_amount // 100):
            try:
                await page.click(f'text={d}', timeout=2000)
                await page.wait_for_timeout(200)
            except: pass
        print(f"  数字ボタン入力: {unit_amount//100}")

    # ⑦ セット
    try:
        await page.click('text=セット', timeout=5000)
        await page.wait_for_timeout(1000)
        print("  セットOK")
    except Exception as e:
        print(f"  セット失敗: {e}")

    cart = await page.evaluate("() => { var m=document.body.innerText.match(/件数[：:]?\s*(\d+)/); return m?m[1]:'不明'; }")
    print(f"カゴ件数: {cart}")
    return True


async def input_amounts(page, bets):
    """各馬の金額を入力（単勝/複勝対応）"""
    print("金額入力中...")
    tan_map = {b['num']: b['amount'] for b in bets if b.get('bet_type', 'tan') == 'tan'}
    fuku_map = {b['num']: b['amount'] for b in bets if b.get('bet_type') == 'fuku'}
    combined_map = {**tan_map}
    combined_map.update({num: amt for num, amt in fuku_map.items() if num not in combined_map})

    try:
        inputs = await page.query_selector_all('input[type="text"]')
        print(f"  入力欄数: {len(inputs)}")

        for inp in inputs:
            if not await inp.is_visible():
                continue
            horse_num = await page.evaluate("""
                (el) => {
                    const row = el.closest('tr');
                    if (!row) return null;
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

            if horse_num and horse_num in combined_map:
                amount_100 = combined_map[horse_num] // 100
                await inp.fill(str(amount_100))
                await inp.dispatch_event('input')
                await inp.dispatch_event('change')
                await page.keyboard.press('Tab')
                print(f"  {horse_num}番: {amount_100}（¥{combined_map[horse_num]:,}）")
                await page.wait_for_timeout(300)

    except Exception as e:
        print(f"金額入力エラー: {e}")


async def purchase(page, venue, race_num, bets, today):
    total = sum(b['amount'] for b in bets)
    print(f"\n=== 購入: {venue} {race_num}R 合計¥{total:,} ===")
    for b in bets:
        if 'num1' in b:
            _lbl = '馬連' if b.get('bet_type') == 'exacta' else 'ワイド'
            print(f"  {b['num1']}-{b['num2']}番 {_lbl} ¥{b['amount']:,}")
        else:
            print(f"  {b['num']}番 {b.get('name','')} ¥{b['amount']:,}")

    ok = await navigate_to_race(page, venue, race_num, today)
    if not ok:
        return False

    await page.screenshot(path="rakuten_01_race.png")

    # 式別タブの実際のHTMLを確認
    shubetsu_info = await page.evaluate("() => { var r=''; var links=document.querySelectorAll('a'); for(var i=0;i<links.length;i++){var t=links[i].innerText.trim(); if(['単勝','複勝','馬連','ワイド','馬単','三連複','三連単','枠連','枠単'].indexOf(t)>=0){r+=t+'['+links[i].className+'] ';}} return r||'not found'; }")
    print(f"  式別リンク: {shubetsu_info}")

    combo_bets = [b for b in bets if b.get('bet_type') in ('exacta', 'wide')]
    tan_fuku_bets = [b for b in bets if b.get('bet_type') not in ('exacta', 'wide')]

    if combo_bets:
        bet_type = combo_bets[0].get('bet_type')
        label = '馬連' if bet_type == 'exacta' else 'ワイド'
        cart_ok = await add_to_cart_combo(page, combo_bets, bet_type)
        await page.screenshot(path=f"rakuten_02_cart_{bet_type}.png")
        if cart_ok is False:
            print("  ❌ フォーメーション失敗のため購入スキップ")
            return False
        if DRY_RUN:
            print("\n========== DRY RUN MODE ==========")
            print(f"[テスト] {label}投票確認画面の直前で停止（実際には投票しません）")
            for b in combo_bets:
                print(f"  {b['num1']:02d}-{b['num2']:02d} {label} ¥{b['amount']:,}")
            print(f"  合計: ¥{total:,}")
            print("===================================")
            print("✅ DRY RUN完了")
            return True
    else:
        try:
            await page.click('text=単勝/複勝')
            await page.wait_for_timeout(500)
        except:
            pass
        await add_to_cart(page, tan_fuku_bets)
        await page.screenshot(path="rakuten_02_cart.png")
        await input_amounts(page, tan_fuku_bets)
        await page.screenshot(path="rakuten_03_amount.png")
        if DRY_RUN:
            print("\n========== DRY RUN MODE ==========")
            print("[テスト] 投票確認画面の直前で停止（実際には投票しません）")
            for b in tan_fuku_bets:
                bet_type_label = "複勝" if b.get('bet_type') == 'fuku' else "単勝"
                print(f"  {b['num']}番 {b.get('name','')} {bet_type_label} ¥{b['amount']:,}")
            print(f"  合計: ¥{total:,}")
            print("===================================")
            print("✅ DRY RUN完了")
            return True

    # 「投票内容を確認する」ボタン
    print("投票内容を確認する...")
    cart_text = await page.evaluate("() => document.body.innerText.slice(0,500)")
    print(f"  確認前ページ(先頭500): {cart_text[:300]}")
    try:
        confirm_result = await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input[type=submit], input[type=button]');
                for(const inp of inputs) {
                    if(inp.value && inp.value.includes('投票内容を確認')) {
                        inp.scrollIntoView({behavior:'instant',block:'center'});
                        inp.click();
                        return 'input:' + inp.value;
                    }
                }
                const btns = document.querySelectorAll('button');
                for(const btn of btns) {
                    if(btn.innerText && btn.innerText.includes('投票内容を確認')) {
                        btn.scrollIntoView({behavior:'instant',block:'center'});
                        btn.click();
                        return 'button:' + btn.innerText.trim();
                    }
                }
                const links = document.querySelectorAll('a.voteBtn, a.confirmBtn, a[class*=vote], a[class*=confirm]');
                for(const a of links) {
                    if(a.innerText && a.innerText.includes('投票内容を確認')) {
                        a.scrollIntoView({behavior:'instant',block:'center'});
                        a.click();
                        return 'a-class:' + a.className;
                    }
                }
                const allA = document.querySelectorAll('a');
                for(const a of allA) {
                    if(a.innerText && a.innerText.trim() === '投票内容を確認する') {
                        a.scrollIntoView({behavior:'instant',block:'center'});
                        a.click();
                        return 'a-exact:' + (a.href||'') + ' class:' + a.className;
                    }
                }
                const allElems = document.querySelectorAll('a, button, input');
                const matches = [];
                for(const el of allElems) {
                    const t = (el.innerText || el.value || '').trim();
                    if(t.includes('投票')) matches.push(el.tagName+':'+t.slice(0,30)+' href:'+(el.href||'')+' class:'+el.className);
                }
                return 'debug:' + matches.join(' | ');
            }
        """)
        print(f"  確認ボタン結果: {confirm_result}")
        if confirm_result and not confirm_result.startswith('debug:'):
            await page.wait_for_timeout(3000)
            confirm_url = page.url
            confirm_text = await page.evaluate("() => document.body.innerText.slice(0,300)")
            print(f"  確認後URL: {confirm_url}")
            print(f"  確認後テキスト: {confirm_text[:200]}")
        else:
            print("  ⚠️ 確認ボタンが見つかりません")
            return False
    except Exception as e:
        print(f"  ⚠️ 確認ボタンエラー: {e}")
        return False

    await page.screenshot(path="rakuten_04_confirm.png")

    # 投票金額（合計）を入力
    print(f"投票金額入力: ¥{total:,}")
    try:
        inp = await page.query_selector('input[type="text"]:visible, input[type="number"]:visible')
        if inp:
            await inp.click()
            await inp.fill(str(total))
            await inp.dispatch_event('input')
            await inp.dispatch_event('change')
            print(f"  投票金額入力OK: ¥{total:,}")
        else:
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

    async def handle_dialog(dialog):
        print(f"  💬 ダイアログ: {dialog.message[:80]}")
        await dialog.accept()
    page.on('dialog', handle_dialog)

    # 「投票する」ボタン
    for step in range(2):
        print(f"投票する... (ステップ{step+1})")
        try:
            js_clicked = await page.evaluate("""
                () => {
                    const voteBtn = document.querySelector('a.voteBtn, input.voteBtn, button.voteBtn');
                    if (voteBtn) {
                        voteBtn.scrollIntoView({behavior: 'instant', block: 'center'});
                        voteBtn.click();
                        return 'voteBtn:' + voteBtn.tagName;
                    }
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
            else:
                print("  ⚠️ 投票ボタンが見つかりません")
                break
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  ⚠️ 投票ボタンエラー: {e}")
            break

        text = await page.evaluate("() => document.body.innerText")

        if '投票内容確認' in text:
            print("  → 投票内容確認画面。ステップ2へ...")
            continue

        if '受付番号' in text or '投票が完了' in text or 'ありがとうございました' in text:
            await page.screenshot(path="rakuten_06_result.png")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            print("結果:")
            for line in lines[:20]:
                print(f"  {line}")
            print("\n✅ 投票完了！")
            return True

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
        balance = await get_balance(page)

        bets = BETS[:]
        if balance and balance > 0:
            import math as _math
            print(f"\n残高ベースでハーフケリー再計算: 資金¥{balance:,}")
            recalc_bets = []
            for b in bets:
                norm = b.get('norm', 0)
                odds = b.get('odds', 0)
                if not norm or not odds or odds <= 1:
                    recalc_bets.append(b)
                    continue
                kf = max(0, (norm * odds - 1) / (odds - 1)) * 0.5
                amount = max(100, int(balance * kf / 100) * 100) if kf > 0 else 100
                print(f"  {b['num']}番: norm={norm:.3f} odds={odds} kelly={kf:.3f} → ¥{amount:,}")
                recalc_bets.append({**b, 'amount': amount})
            bets = recalc_bets
            total = sum(b['amount'] for b in bets)
            print(f"  合計: ¥{total:,} / 残高: ¥{balance:,} ({total/balance*100:.1f}%)")
        else:
            bets = BETS[:]
            print("⚠️ 残高取得失敗 → 元の金額で投票")

        result = await purchase(page, COURSE_NAME, RACE_NUM, bets, TODAY)

        await browser.close()

        if not result:
            print("❌ 購入失敗")
            raise SystemExit(1)
        print("✅ 購入フロー正常終了")


if __name__ == "__main__":
    asyncio.run(main())
