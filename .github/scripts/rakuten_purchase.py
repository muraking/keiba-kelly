"""
楽天競馬 自動購入スクリプト
単勝 → 馬連 → ワイド を順番に処理（1スクリプト・1ログイン）
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
TODAY        = os.environ.get("TODAY", "")

TIMEOUT = 30000

VENUE_TO_CODE = {
    "帯広": "03", "帯広ば": "03", "門別": "04", "盛岡": "06", "水沢": "07",
    "浦和": "08", "船橋": "09", "大井": "10", "川崎": "11",
    "金沢": "12", "笠松": "13", "名古屋": "14", "園田": "17",
    "姫路": "18", "高知": "31", "佐賀":  "32",
}

LOGIN_URL = "https://keiba.rakuten.co.jp/"
BET_URL   = "https://bet.keiba.rakuten.co.jp/bet/odds/"


def get_today():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d")


def build_race_id(venue, race_num, today):
    code = VENUE_TO_CODE.get(venue)
    if not code:
        raise ValueError(f"未対応の会場: {venue}")
    return f"{today}{code}{str(race_num).zfill(8)}"


# ===== ログイン =====
async def login(page):
    print("ログイン中...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)

    await page.screenshot(path="rakuten_login_top.png")
    text = await page.evaluate("() => document.body.innerText")
    print(f"トップページ内容（先頭200文字）: {text[:200]}")

    try:
        await page.click('text=マイページログイン')
    except:
        await page.click('a:has-text("ログイン")')
    await page.wait_for_timeout(2000)
    await page.screenshot(path="rakuten_login_1.png")
    print(f"ログイン画面URL: {page.url}")

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
    pw_text = await page.evaluate("() => document.body.innerText")
    print(f"パスワード画面内容（先頭100文字）: {pw_text[:100]}")

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
    text = await page.evaluate("() => document.body.innerText")
    if "ログアウト" in text or "マイページ" in text:
        print("✅ ログイン成功")
    else:
        print("⚠️ ログイン状態が確認できません")
        await page.screenshot(path="rakuten_login_check.png")


# ===== 残高取得 =====
async def get_balance(page):
    try:
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


# ===== レースページへ移動 =====
async def navigate_to_race(page, venue, race_num, today):
    race_id = build_race_id(venue, race_num, today)
    url = f"{BET_URL}RACEID/{race_id}"
    print(f"  レースページ: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(3000)

    try:
        tab = await page.query_selector(f'a:has-text("{venue}"), li:has-text("{venue}")')
        if tab:
            await tab.click()
            await page.wait_for_timeout(2000)
            print(f"  会場タブクリック: {venue}")
    except Exception as e:
        print(f"  会場タブスキップ: {e}")

    clicked = await page.evaluate(f"""() => {{
        for (const el of document.querySelectorAll('a, td, li, span')) {{
            if (el.innerText?.trim() === '{race_num}R') {{ el.click(); return true; }}
        }}
        return false;
    }}""")
    if clicked:
        await page.wait_for_timeout(2000)
        print(f"  レース番号クリック: {race_num}R")
    else:
        print(f"  レース番号クリック失敗: {race_num}R")

    text = await page.evaluate("() => document.body.innerText")
    ok = "単勝" in text or "複勝" in text
    print(f"  レースページ表示: {'OK' if ok else 'NG'}")
    if not ok:
        await page.screenshot(path="rakuten_race_check.png")
    return ok


# ===== 投票確認→投票 =====
async def confirm_and_vote(page, total, label):
    print(f"  投票内容を確認する...")
    cart_text = await page.evaluate("() => document.body.innerText.slice(0,300)")
    print(f"  確認前ページ: {cart_text[:200]}")

    # 確認ボタンをクリック（旧コード方式: btn-disabledチェックなしでシンプルに）
    confirm_result = await page.evaluate("""() => {
        for (const el of document.querySelectorAll('input[type=submit],input[type=button],button,a')) {
            const t = (el.value || el.innerText || '').trim();
            if (t.includes('投票内容を確認')) {
                el.scrollIntoView({behavior:'instant',block:'center'});
                el.click();
                return el.tagName + ':' + el.className + ':' + t;
            }
        }
        return null;
    }""")
    print(f"  確認ボタン: {confirm_result or 'NG'}")
    if not confirm_result:
        return False
    await page.wait_for_timeout(3000)
    await page.screenshot(path=f"rakuten_confirm_{label}.png")

    # 確認後ページを表示（デバッグ）- エラーテーブルの内容を重点的に取得
    confirm_debug = await page.evaluate("""() => {
        const tables = document.querySelectorAll('table');
        let errorInfo = '';
        for (const t of tables) {
            const text = t.innerText.trim();
            if (text.includes('エラー') || text.includes('番号')) {
                errorInfo += '[TABLE:' + text.slice(0, 300) + '] ';
            }
        }
        const inp = document.querySelector('input[type="text"], input[type="number"], input[type="tel"]');
        const inpInfo = inp ? 'input:' + (inp.name||inp.id||inp.type) + '=' + inp.value : 'no_input';
        const voteBtn = document.querySelector('a.voteBtn, input.voteBtn, button.voteBtn');
        const voteBtnInfo = voteBtn ? 'voteBtn:' + voteBtn.tagName + ':' + voteBtn.className : 'no_voteBtn';
        return errorInfo + ' | ' + inpInfo + ' | ' + voteBtnInfo;
    }""")
    print(f"  確認後詳細: {confirm_debug[:500]}")

    async def handle_dialog(dialog):
        print(f"  💬 ダイアログ: {dialog.message[:80]}")
        await dialog.accept()
    page.on('dialog', handle_dialog)

    # 投票金額入力（キーボード入力でJSに確実に検知させる）
    try:
        inp = await page.query_selector('input[name="verify"]:visible, input[type="text"]:visible, input[type="number"]:visible')
        if inp:
            await inp.click()
            await inp.fill('')  # 一旦クリア
            await page.keyboard.type(str(total), delay=50)  # キーボード入力
            await page.wait_for_timeout(300)
            val = await inp.input_value()
            print(f"  投票金額入力: ¥{total:,} (実際の値: {val})")
        else:
            print(f"  投票金額入力欄なし")
    except Exception as e:
        print(f"  投票金額入力エラー: {e}")

    # 「投票する」ボタン（旧コード: range(2)、確認画面ならステップ2へそのまま再クリック）
    for step in range(2):
        print(f"  投票する（ステップ{step+1}）...")

        clicked = await page.evaluate("""() => {
            const voteBtn = document.querySelector('a.voteBtn, input.voteBtn, button.voteBtn');
            if (voteBtn) {
                voteBtn.scrollIntoView({behavior:'instant',block:'center'});
                voteBtn.click();
                return 'voteBtn:' + voteBtn.tagName;
            }
            for (const el of document.querySelectorAll('input[type=submit],input[type=button],button,a')) {
                if ((el.value||el.innerText||'').trim() === '投票する') {
                    el.scrollIntoView({behavior:'instant',block:'center'});
                    el.click();
                    return '投票する:' + el.tagName;
                }
            }
            // デバッグ: ボタン一覧
            const all = [];
            for (const el of document.querySelectorAll('input[type=submit],input[type=button],button,a')) {
                const t = (el.value||el.innerText||'').trim().slice(0,20);
                if (t) all.push(t);
            }
            return 'NOTFOUND:' + all.slice(0,8).join('|');
        }""")
        print(f"  投票ボタン: {clicked or 'NG'}")
        if not clicked or clicked.startswith('NOTFOUND:'):
            break
        await page.wait_for_timeout(4000)

        text = await page.evaluate("() => document.body.innerText")
        if '/bet/complete' in page.url or '受付番号' in text or '投票完了' in text or '投票が完了' in text or 'ありがとうございました' in text:
            await page.screenshot(path=f"rakuten_done_{label}.png")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            print("  結果:")
            for line in lines[:15]:
                print(f"    {line}")
            print(f"  ✅ 投票完了！")
            return True
        if '投票可能件数' in text and '投票内容確認' not in text:
            await page.screenshot(path=f"rakuten_done_{label}.png")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            print("  結果:")
            for line in lines[:15]:
                print(f"    {line}")
            print(f"  ✅ 投票完了！")
            return True
        if '投票内容確認' in text:
            # 旧コード: 確認画面ならそのままステップ2へ（金額再入力なし）
            print(f"  → 投票内容確認画面。ステップ2へ...")
            continue
        break

    await page.screenshot(path=f"rakuten_unknown_{label}.png")
    result_text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in result_text.split('\n') if l.strip()]
    print("  結果:")
    for line in lines[:15]:
        print(f"    {line}")
    print(f"  ⚠️ 投票結果不明")
    return False


# ===== 単勝・複勝購入 =====
async def purchase_tan(page, venue, race_num, bets, today):
    total = sum(b['amount'] for b in bets)
    print(f"\n{'='*40}")
    print(f"[単勝/複勝] {venue} {race_num}R 合計¥{total:,}")
    for b in bets:
        label = "複勝" if b.get('bet_type') == 'fuku' else "単勝"
        print(f"  {b['num']}番 {b.get('name','')} {label} ¥{b['amount']:,}")

    ok = await navigate_to_race(page, venue, race_num, today)
    if not ok:
        return False

    await page.screenshot(path="rakuten_tan_race.png")

    # カゴクリア（JavaScriptで確認ダイアログをwindow.confirmを上書きしてスキップ）
    await page.evaluate("() => { window._orig_confirm = window.confirm; window.confirm = () => true; }")
    del_result = await page.evaluate("""() => {
        for (const el of document.querySelectorAll('a, button, input')) {
            const t = (el.value || el.innerText || '').trim();
            if (t === '全削除') { el.click(); return 'deleted'; }
        }
        return 'empty';
    }""")
    await page.wait_for_timeout(1500)
    # window.confirmを元に戻す
    await page.evaluate("() => { if(window._orig_confirm) window.confirm = window._orig_confirm; }")
    print(f"  カゴクリア: {del_result}")

    # 式別リンク確認
    shubetsu = await page.evaluate("() => { var r=''; for(const a of document.querySelectorAll('a')){const t=a.innerText.trim(); if(['単勝','複勝','馬連','ワイド','馬単','三連複','三連単'].includes(t))r+=t+'['+a.className+'] ';} return r||'not found'; }")
    print(f"  式別リンク: {shubetsu}")

    # 馬番クリック
    async def click_horse(num, col_offset):
        return await page.evaluate(f"""() => {{
            for (const table of document.querySelectorAll('table')) {{
                let cnt = 0;
                for (const row of table.querySelectorAll('tr')) {{
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 4) continue;
                    const c0 = cells[0]?.innerText?.trim();
                    const c1 = cells[1]?.innerText?.trim();
                    if (!/^[0-9]{{1,2}}$/.test(c0)) continue;
                    const isNum = /^[0-9]{{1,2}}$/.test(c1);
                    cnt++;
                    const numText = isNum ? c1 : String(cnt);
                    const baseIdx = isNum ? 4 : 3;
                    if (numText === '{num}') {{
                        const idx = baseIdx + {col_offset};
                        const a = cells[idx]?.querySelector('a');
                        if (a) {{ a.click(); return 'a:' + numText + ':col' + idx; }}
                        cells[idx]?.click();
                        return 'cell:' + numText + ':col' + idx;
                    }}
                }}
            }}
            return false;
        }}""")

    tan_bets  = [b for b in bets if b.get('bet_type', 'tan') == 'tan']
    fuku_bets = [b for b in bets if b.get('bet_type') == 'fuku']

    for bet in tan_bets:
        r = await click_horse(bet['num'], 0)
        print(f"  {bet['num']}番（単勝）: {r or 'NG'}")
        await page.wait_for_timeout(1000)

    for bet in fuku_bets:
        r = await click_horse(bet['num'], 1)
        print(f"  {bet['num']}番（複勝）: {r or 'NG'}")
        await page.wait_for_timeout(1000)

    # 金額入力
    inputs = await page.query_selector_all('input[type="text"]')
    for inp in inputs:
        if not await inp.is_visible():
            continue
        row_num = await page.evaluate("""(el) => {
            const row = el.closest('tr');
            if (!row) return null;
            for (const cell of row.querySelectorAll('td')) {
                const t = cell.innerText.trim();
                if (/^\\d{1,2}$/.test(t) && +t >= 1 && +t <= 18) return +t;
            }
            return null;
        }""", inp)
        combined = {b['num']: b['amount'] for b in bets}
        if row_num and row_num in combined:
            amount_val = str(combined[row_num] // 100)
            await inp.fill(amount_val)
            await inp.dispatch_event('input')
            await inp.dispatch_event('change')
            await page.keyboard.press('Tab')
            print(f"  {row_num}番金額入力: ¥{combined[row_num]:,}")
            await page.wait_for_timeout(300)

    await page.screenshot(path="rakuten_tan_cart.png")

    if DRY_RUN:
        print(f"  [DRY RUN] 単勝: 確認ボタン押下前で停止")
        return True

    return await confirm_and_vote(page, total, "tan")


# ===== 馬連・ワイド購入 =====
async def purchase_combo(page, venue, race_num, bets, bet_type, today):
    label = '馬連' if bet_type == 'exacta' else 'ワイド'
    total = sum(b['amount'] for b in bets)
    print(f"\n{'='*40}")
    print(f"[{label}] {venue} {race_num}R 合計¥{total:,}")
    for b in bets:
        print(f"  {b['num1']}-{b['num2']}番 ¥{b['amount']:,}")

    ok = await navigate_to_race(page, venue, race_num, today)
    if not ok:
        return False

    await page.screenshot(path=f"rakuten_{bet_type}_race.png")

    # カゴクリア（全削除ボタンをクリック）
    del_result = await page.evaluate("""() => {
        // 全削除ボタンを探す（btn-disabledでも強制クリック）
        for (const el of document.querySelectorAll('a, button, input')) {
            const t = (el.value || el.innerText || '').trim();
            if (t === '全削除') {
                el.click(); return 'deleted';
            }
        }
        return 'empty';
    }""")
    await page.wait_for_timeout(1000)
    print(f"  カゴクリア: {del_result}")

    # 式別リンク確認
    shubetsu = await page.evaluate("() => { var r=''; for(const a of document.querySelectorAll('a')){const t=a.innerText.trim(); if(['単勝','複勝','馬連','ワイド','馬単','三連複','三連単'].includes(t))r+=t+'['+a.className+'] ';} return r||'not found'; }")
    print(f"  式別リンク: {shubetsu}")

    # 通常タブ
    for try_normal in ['通常', '通常投票']:
        try:
            await page.click(f'text={try_normal}', timeout=3000)
            await page.wait_for_timeout(1500)
            print(f"  通常タブ: OK")
            break
        except:
            pass

    # 式別タブ
    tab_candidates = ['馬連', '馬複'] if bet_type == 'exacta' else ['ワイド']
    for try_label in tab_candidates:
        try:
            loc = page.locator(f'a:text-is("{try_label}")')
            if await loc.count() > 0:
                await loc.first.click(timeout=5000)
                await page.wait_for_timeout(1000)
                print(f"  式別タブ '{try_label}': OK")
                break
        except Exception as e:
            print(f"  式別タブ '{try_label}' 失敗: {e}")

    # フォーメーション（ポーリング最大10秒）
    fmt_clicked = False
    for _retry in range(10):
        await page.wait_for_timeout(1000)
        result = await page.evaluate("""() => {
            for (const el of document.querySelectorAll('a, button, td, li, span')) {
                const t = (el.innerText || el.textContent || '').trim();
                if (t.includes('フォーメーション') && t.length < 15) {
                    el.click(); return 'found:' + t;
                }
            }
            return false;
        }""")
        if result:
            fmt_clicked = result
            print(f"  フォーメーション({_retry+1}回目): {fmt_clicked}")
            break
        if _retry == 4:
            pt = await page.evaluate("() => document.body.innerText.slice(0,300)")
            print(f"  [5秒後ページ]: {pt}")

    if not fmt_clicked:
        pt = await page.evaluate("() => document.body.innerText.slice(0,300)")
        print(f"  [10秒後ページ]: {pt}")
        print(f"  ❌ フォーメーション選択失敗 → スキップ")
        return False

    await page.wait_for_timeout(1000)

    # テーブル構造確認
    page_info = await page.evaluate("() => { var t=document.querySelectorAll('table'); var r='tables:'+t.length; for(var i=0;i<Math.min(5,t.length);i++){var rows=t[i].querySelectorAll('tr');r+=' tbl'+i+'('+rows.length+'rows)';for(var j=0;j<Math.min(3,rows.length);j++){var cs=rows[j].querySelectorAll('td,th');r+=' R'+j+'['+Array.from(cs).map(function(c){return (c.innerText.trim()||c.innerHTML.trim()).slice(0,20);}).join('|')+']';}} return r; }")
    print(f"  テーブル構造: {page_info}")

    # 軸・相手
    axis_nums    = list(dict.fromkeys([b['num1'] for b in bets]))
    partner_nums = list(dict.fromkeys([b['num2'] for b in bets]))
    print(f"  馬1（軸）: {axis_nums}")
    print(f"  馬2（相手）: {partner_nums}")

    async def click_combo_horse(num, col_offset):
        ns, ns2 = str(num), f"{num:02d}"
        return await page.evaluate(f"""() => {{
            for (const table of document.querySelectorAll('table')) {{
                for (const row of table.querySelectorAll('tr')) {{
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 5) continue;
                    const c0 = cells[0].innerText.trim();
                    const c1 = cells[1].innerText.trim();
                    const c0ok = c0 === '{ns}' || c0 === '{ns2}';
                    const c1ok = /^[0-9]{{1,2}}$/.test(c1) && (c1 === '{ns}' || c1 === '{ns2}');
                    if (!c0ok && !c1ok) continue;
                    if (!/^[0-9]{{1,2}}$/.test(c0)) continue;
                    const idx = 4 + {col_offset};
                    if (cells.length <= idx) continue;
                    const a = cells[idx].querySelector('a');
                    if (a) {{ a.click(); return 'a:c0=' + c0 + ':col' + idx; }}
                    cells[idx].click();
                    return 'cell:c0=' + c0 + ':col' + idx;
                }}
            }}
            return false;
        }}""")

    for num in axis_nums:
        r = await click_combo_horse(num, 0)
        print(f"    馬1:{num}番: {r or 'NG'}")
        await page.wait_for_timeout(500)

    for num in partner_nums:
        r = await click_combo_horse(num, 1)
        print(f"    馬2:{num}番: {r or 'NG'}")
        await page.wait_for_timeout(500)

    kumi = await page.evaluate("() => { const m=document.body.innerText.match(/組数[：:]?\\s*(\\d+)/); return m?m[1]:'不明'; }")
    print(f"  選択組数: {kumi}")

    # 金額入力（1点あたりの金額を入力）
    unit_amount = bets[0]['amount']
    kumi_int = int(kumi) if kumi and str(kumi).isdigit() else len(bets)
    actual_total = unit_amount * kumi_int
    inp = await page.query_selector('input[type=text]:visible, input[type=number]:visible')
    if inp:
        await inp.fill(str(unit_amount // 100))
        await inp.dispatch_event('change')
        print(f"  金額入力: {unit_amount//100}×100=¥{unit_amount} × {kumi_int}組 = ¥{actual_total}")
    else:
        print(f"  ⚠️ 金額入力欄なし")

    # セット
    try:
        await page.click('text=セット', timeout=5000)
        await page.wait_for_timeout(1000)
        print("  セット: OK")
    except Exception as e:
        print(f"  セット失敗: {e}")

    # セット後カゴ確認
    cart_text = await page.evaluate("() => document.body.innerText.slice(0,400)")
    print(f"  [セット後カゴ]: {cart_text[:300]}")
    cart = await page.evaluate("() => { const m=document.body.innerText.match(/件数[：:]?\\s*(\\d+)/); return m?m[1]:'不明'; }")
    print(f"  カゴ件数: {cart}")

    await page.screenshot(path=f"rakuten_{bet_type}_cart.png")

    if DRY_RUN:
        print(f"  [DRY RUN] {label}: 確認ボタン押下前で停止")
        return True

    return await confirm_and_vote(page, actual_total, bet_type)


# ===== メイン =====
async def main():
    global TODAY
    if not TODAY:
        TODAY = get_today()

    if not COURSE_NAME:
        print("❌ COURSE_NAME が設定されていません")
        return

    # bet_typeでグループ分け
    tan_bets    = [b for b in BETS if b.get('bet_type', 'tan') in ('tan', 'fuku') or 'num' in b and 'num1' not in b]
    exacta_bets = [b for b in BETS if b.get('bet_type') == 'exacta']
    wide_bets   = [b for b in BETS if b.get('bet_type') == 'wide']

    print(f"=== 楽天競馬自動購入 ===")
    print(f"DRY_RUN: {DRY_RUN}")
    print(f"会場: {COURSE_NAME} {RACE_NUM}R / 日付: {TODAY}")
    print(f"単勝/複勝: {len(tan_bets)}点 / 馬連: {len(exacta_bets)}点 / ワイド: {len(wide_bets)}点")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--dns-prefetch-disable', '--no-sandbox'])
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)

        # ログイン（1回）
        await login(page)
        balance = await get_balance(page)

        # 残高ベースで単勝のケリー再計算
        bets_tan = tan_bets[:]
        if balance and balance > 0 and bets_tan:
            print(f"\n残高ベースでハーフケリー再計算: 資金¥{balance:,}")
            recalc = []
            for b in bets_tan:
                norm = b.get('norm', 0)
                odds = b.get('odds', 0)
                if not norm or not odds or odds <= 1:
                    recalc.append(b)
                    continue
                kf = max(0, (norm * odds - 1) / (odds - 1)) * 0.5
                amount = max(100, int(balance * kf / 100) * 100) if kf > 0 else 100
                print(f"  {b['num']}番: norm={norm:.3f} odds={odds} kelly={kf:.3f} → ¥{amount:,}")
                recalc.append({**b, 'amount': amount})
            bets_tan = recalc
            total = sum(b['amount'] for b in bets_tan)
            print(f"  合計: ¥{total:,} / 残高: ¥{balance:,} ({total/balance*100:.1f}%)")
        elif not balance:
            print("⚠️ 残高取得失敗 → 元の金額で投票")

        results = {}

        # ① 単勝・複勝
        if bets_tan:
            print(f"\n{'#'*40}")
            print(f"# STEP 1: 単勝/複勝")
            results['tan'] = await purchase_tan(page, COURSE_NAME, RACE_NUM, bets_tan, TODAY)
            print(f"単勝結果: {'✅ OK' if results['tan'] else '❌ NG'}")
        else:
            print(f"\n# STEP 1: 単勝/複勝 → スキップ（買い目なし）")

        # ② 馬連
        if exacta_bets:
            print(f"\n{'#'*40}")
            print(f"# STEP 2: 馬連")
            results['exacta'] = await purchase_combo(page, COURSE_NAME, RACE_NUM, exacta_bets, 'exacta', TODAY)
            print(f"馬連結果: {'✅ OK' if results['exacta'] else '❌ NG'}")
        else:
            print(f"\n# STEP 2: 馬連 → スキップ（買い目なし）")

        # ③ ワイド
        if wide_bets:
            print(f"\n{'#'*40}")
            print(f"# STEP 3: ワイド")
            results['wide'] = await purchase_combo(page, COURSE_NAME, RACE_NUM, wide_bets, 'wide', TODAY)
            print(f"ワイド結果: {'✅ OK' if results['wide'] else '❌ NG'}")
        else:
            print(f"\n# STEP 3: ワイド → スキップ（買い目なし）")

        await browser.close()

    # サマリー
    print(f"\n{'='*40}")
    print(f"=== 購入結果サマリー ===")
    for k, v in results.items():
        print(f"  {k}: {'✅ OK' if v else '❌ NG'}")

    # 1つでも失敗したらexit 1
    if results and not all(results.values()):
        print("❌ 一部失敗")
        raise SystemExit(1)
    print("✅ 全購入フロー正常終了")


if __name__ == "__main__":
    asyncio.run(main())
