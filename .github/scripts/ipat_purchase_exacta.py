"""
IPAT SP版 自動購入スクリプト（馬連・ワイド）
オッズ投票ルート：
  ログイン
  → オッズ投票 → 競馬場 → レース
  → 式別から選択 → 馬連（またはワイド）→ フォーメーション
  → 1頭目: #uma1内で a[data-value="馬番"] を $(a).trigger('tap')
  → 次へ
  → 2頭目: #uma2内で a[data-value="馬番"] を $(a).trigger('tap')
  → オッズ選択画面へ → 金額入力 → 投票
"""
import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

IPAT_ID   = os.environ.get("IPAT_ID", "")
IPAT_PIN  = os.environ.get("IPAT_PIN", "")
IPAT_PARS = os.environ.get("IPAT_PARS", "")

COURSE_NAME = os.environ.get("COURSE_NAME", "")
RACE_NUM    = int(os.environ.get("RACE_NUM", "1"))
BETS        = json.loads(os.environ.get("BETS", "[]"))
BET_TYPE    = os.environ.get("BET_TYPE", "exacta")  # exacta=馬連, wide=ワイド
DRY_RUN     = os.environ.get("DRY_RUN", "0") == "1"

LOGIN_URL = "https://www.ipat.jra.go.jp/sp/"
TIMEOUT   = 30000


async def login(page):
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)
    await page.fill('#userid', IPAT_ID)
    await page.fill('#password', IPAT_PIN)
    await page.fill('#pars', IPAT_PARS)
    await page.evaluate("ToSPMenu()")
    await page.wait_for_timeout(3000)
    print(f"ログイン完了: {page.url}")


async def tap_horse(page, page_id, num):
    """指定ページ（#uma1 or #uma2）内で馬番をjQuery tapイベントで選択
    jQuery MobileはSPAなので、display:noneでもDOM上には存在する"""
    # まずjQuery Mobileでページ切り替えを明示的に行う
    await page.evaluate(f"""
        () => {{
            if (typeof $.mobile !== 'undefined') {{
                $.mobile.changePage('#{page_id}', {{transition:'none'}});
            }}
        }}
    """)
    await page.wait_for_timeout(800)
    result = await page.evaluate(f"""
        () => {{
            // display:noneでもIDで取得して操作
            const pageEl = document.getElementById('{page_id}');
            if (!pageEl) return 'no_page:{page_id}';
            const a = pageEl.querySelector('a[data-value="{num}"]');
            if (!a) return 'no_horse:{num}';
            if (typeof $ !== 'undefined') {{
                $(a).trigger('tap');
                return 'tap:' + a.getAttribute('data-value') + ':selected=' + a.classList.contains('selected');
            }}
            ['touchstart','touchend','vclick','click'].forEach(evt => {{
                a.dispatchEvent(new Event(evt, {{bubbles:true, cancelable:true}}));
            }});
            return 'events:' + num;
        }}
    """)
    await page.wait_for_timeout(400)
    print(f"    {num}番: {result}")
    return result and 'no_' not in result


async def click_next(page):
    """「次へ」ボタンをクリック（#uma1内）→ #uma2に遷移"""
    result = await page.evaluate("""
        () => {
            const uma1 = document.getElementById('uma1');
            if (!uma1) return 'no_uma1';
            const links = uma1.querySelectorAll('a');
            for (const a of links) {
                if (a.innerText.trim() === '次へ') {
                    if (typeof $ !== 'undefined') { $(a).trigger('tap'); return 'tap_next'; }
                    a.click(); return 'click_next';
                }
            }
            return 'no_next_btn';
        }
    """)
    await page.wait_for_timeout(2000)
    # jQuery Mobileのページ遷移を待つ
    await page.evaluate("""
        () => {
            if (typeof $.mobile !== 'undefined') {
                $.mobile.changePage('#uma2', {transition:'none'});
            }
        }
    """)
    await page.wait_for_timeout(800)
    print(f"  次へ: {result}")
    return result


async def click_odds_screen(page):
    """「オッズ選択画面へ」ボタンをクリック（#uma2内）→ #odseに遷移"""
    result = await page.evaluate("""
        () => {
            const uma2 = document.getElementById('uma2');
            if (!uma2) return 'no_uma2';
            const links = uma2.querySelectorAll('a');
            for (const a of links) {
                const t = a.innerText.trim();
                if (t === 'オッズ選択画面へ' || t === '金額入力画面へ') {
                    if (typeof $ !== 'undefined') { $(a).trigger('tap'); return 'tap:' + t; }
                    a.click(); return 'click:' + t;
                }
            }
            return 'no_btn';
        }
    """)
    await page.wait_for_timeout(2000)
    # jQuery Mobileのページ遷移を待つ
    await page.evaluate("""
        () => {
            if (typeof $.mobile !== 'undefined') {
                $.mobile.changePage('#odse', {transition:'none'});
            }
        }
    """)
    await page.wait_for_timeout(800)
    print(f"  オッズ選択画面へ: {result}")
    return result


async def get_kumi_count(page, page_id):
    """選択組数を取得"""
    kumi = await page.evaluate(f"""
        () => {{
            const el = document.getElementById('{page_id}');
            if (!el) return '?';
            const dd = el.querySelector('.betNum dd');
            return dd ? dd.innerText.trim() : '?';
        }}
    """)
    return kumi


async def purchase(page, course_name, race_num, bets, bet_type):
    bet_label = '馬連' if bet_type == 'exacta' else 'ワイド'
    total = sum(b['amount'] for b in bets)
    unit_amount = bets[0]['amount'] if bets else 100

    print(f"\n購入: {course_name} {race_num}R {bet_label} 合計¥{total:,}")
    for b in bets:
        print(f"  {b['num1']}-{b['num2']}番 ¥{b['amount']:,}")

    # ① オッズ投票
    await page.evaluate("""
        () => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                if (a.innerText.trim() === 'オッズ投票') { a.click(); return; }
            }
        }
    """)
    await page.wait_for_timeout(2000)
    print(f"オッズ投票: {page.url}")

    # ② 競馬場選択
    course_base = course_name.split('(')[0].strip()
    page_text = await page.evaluate("() => document.body.innerText")
    click_name = course_name if course_name in page_text else (course_base if course_base in page_text else course_name)
    if click_name != course_name:
        print(f"コース名変換: {course_name} → {click_name}")
    await page.evaluate(f"""
        () => {{
            const links = document.querySelectorAll('a');
            for (const a of links) {{
                if (a.innerText.trim() === '{click_name}') {{ a.click(); return; }}
            }}
        }}
    """)
    await page.wait_for_timeout(2000)

    # ③ レース番号
    await page.evaluate(f"""
        () => {{
            const links = document.querySelectorAll('a');
            for (const a of links) {{
                if (a.innerText.trim() === '{race_num}R') {{ a.click(); return; }}
            }}
        }}
    """)
    await page.wait_for_timeout(2000)
    print(f"レース選択: {race_num}R")

    # ④ 式別から選択
    await page.evaluate("""
        () => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                if (a.innerText.trim() === '式別から選択') { a.click(); return; }
            }
        }
    """)
    await page.wait_for_timeout(2000)

    # ⑤ 式別（馬連 or ワイド）
    await page.evaluate(f"""
        () => {{
            const links = document.querySelectorAll('a');
            for (const a of links) {{
                if (a.innerText.trim() === '{bet_label}') {{ a.click(); return; }}
            }}
        }}
    """)
    await page.wait_for_timeout(2000)
    print(f"式別→{bet_label}: OK")

    # ⑥ フォーメーション
    await page.evaluate("""
        () => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                if (a.innerText.trim() === 'フォーメーション') { a.click(); return; }
            }
        }
    """)
    await page.wait_for_timeout(2000)
    print("フォーメーション: OK")

    # ⑦ 1頭目選択（#uma1）
    axis_nums    = list(dict.fromkeys([b['num1'] for b in bets]))
    partner_nums = list(dict.fromkeys([b['num2'] for b in bets]))
    print(f"1頭目選択: {axis_nums}")
    for num in axis_nums:
        await tap_horse(page, 'uma1', num)

    kumi1 = await get_kumi_count(page, 'uma1')
    print(f"1頭目組数: {kumi1}")

    # ⑧ 次へ
    await click_next(page)

    # ⑨ 2頭目選択（#uma2）
    print(f"2頭目選択: {partner_nums}")
    for num in partner_nums:
        await tap_horse(page, 'uma2', num)

    kumi2 = await get_kumi_count(page, 'uma2')
    print(f"2頭目組数（最終）: {kumi2}")

    if kumi2 == '0' or kumi2 == '?':
        print("⚠️ 組数0 → 選択失敗の可能性")

    await page.screenshot(path=f"ipat_{bet_type}_selected.png")

    if DRY_RUN:
        print(f"\n========== DRY RUN MODE ==========")
        for b in bets:
            print(f"  {b['num1']:02d}-{b['num2']:02d} {bet_label} ¥{b['amount']:,}")
        print(f"  合計: ¥{total:,} / 組数: {kumi2}")
        print("===================================")
        print("✅ DRY RUN完了（投票しません）")
        return True

    # ⑩ オッズ選択画面へ
    await click_odds_screen(page)
    await page.screenshot(path=f"ipat_{bet_type}_odds.png")

    # ⑪ オッズ選択画面で全選択（ページ内全選択）
    select_result = await page.evaluate("""
        () => {
            const odse = document.getElementById('odse');
            if (!odse) return 'no_odse';
            const btn = odse.querySelector('a[data-role="oddsselectall"]');
            if (btn && typeof $ !== 'undefined') {
                $(btn).trigger('tap');
                return 'tapped_selectall';
            }
            if (btn) { btn.click(); return 'clicked_selectall'; }
            return 'no_selectall_btn';
        }
    """)
    await page.wait_for_timeout(1000)

    # 合計件数確認
    kumi_odse = await page.evaluate("""
        () => {
            const odse = document.getElementById('odse');
            const text = odse?.innerText || '';
            const m = text.match(/合計件数[：:]\\s*(\\d+)/);
            return m ? m[1] : '?';
        }
    """)
    print(f"  オッズ選択: {select_result} / 合計件数: {kumi_odse}件")

    if kumi_odse == '0' or kumi_odse == '?':
        print("⚠️ オッズ選択0件 → スキップ")
        return False

    await page.screenshot(path=f"ipat_{bet_type}_odds_selected.png")

    # ⑫ 金額入力画面へ
    await page.evaluate("""
        () => {
            const odse = document.getElementById('odse');
            if (!odse) return;
            const links = odse.querySelectorAll('a');
            for (const a of links) {
                if (a.innerText.trim() === '金額入力画面へ') {
                    if (typeof $ !== 'undefined') { $(a).trigger('tap'); return; }
                    a.click(); return;
                }
            }
        }
    """)
    await page.wait_for_timeout(2000)
    await page.screenshot(path=f"ipat_{bet_type}_amount.png")

    page_text2 = await page.evaluate("() => document.body.innerText")
    print(f"金額入力画面（先頭200文字）: {page_text2[:200]}")

    # ⑬ 金額入力
    amount_100 = unit_amount // 100
    inp = await page.query_selector('input[type="tel"], input[type="text"], input[type="number"]')
    if inp and await inp.is_visible():
        await inp.fill(str(amount_100))
        await inp.dispatch_event('change')
        print(f"金額入力: {amount_100}×100=¥{unit_amount}")
    else:
        print("⚠️ 金額入力欄が見つかりません")

    # ⑮ セット
    await page.evaluate("""
        () => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                if (a.innerText.trim() === 'セット') { a.click(); return; }
            }
        }
    """)
    await page.wait_for_timeout(2000)
    print("セット: OK")

    await page.screenshot(path=f"ipat_{bet_type}_confirm.png")

    # ⑯ 投票（ダイアログ自動accept）
    async def handle_dialog(dialog):
        try:
            print(f"  ダイアログ: {dialog.message[:60]}")
            await dialog.accept()
        except Exception:
            pass
    page.on('dialog', handle_dialog)

    await page.evaluate("""
        () => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                if (a.innerText.trim() === '投票') { a.click(); return; }
            }
        }
    """)
    await page.wait_for_timeout(3000)

    # 合計金額確認画面が出た場合は再入力
    page_text3 = await page.evaluate("() => document.body.innerText")
    if '合計金額' in page_text3 and '受付番号' not in page_text3:
        print("合計金額入力画面 → 再入力")
        inp2 = await page.query_selector('input[type="tel"]')
        if inp2 and await inp2.is_visible():
            await inp2.fill(str(total))
            await inp2.dispatch_event('change')
        await page.evaluate("""
            () => {
                const links = document.querySelectorAll('a');
                for (const a of links) {
                    if (a.innerText.trim() === '投票') { a.click(); return; }
                }
            }
        """)
        await page.wait_for_timeout(3000)

    await page.screenshot(path=f"ipat_{bet_type}_result.png")
    result_text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in result_text.split('\n') if l.strip()]
    print("結果:")
    for line in lines[:15]:
        print(f"  {line}")

    success = '受付番号' in result_text or 'ありがとう' in result_text
    print(f"\n{'✅ ' + bet_label + '投票完了！' if success else '⚠️ 投票結果不明'}")
    return success


async def main():
    global COURSE_NAME, RACE_NUM, BETS, BET_TYPE

    if not COURSE_NAME:
        COURSE_NAME = "東京(日)"
        RACE_NUM = 11
        BETS = [{"num1": 1, "num2": 6, "amount": 100}, {"num1": 1, "num2": 9, "amount": 100}]
        BET_TYPE = "exacta"

    bet_label = '馬連' if BET_TYPE == 'exacta' else 'ワイド'
    print(f"=== IPAT自動購入（{bet_label}）===")
    print(f"DRY_RUN: {DRY_RUN}")
    print(f"会場: {COURSE_NAME} {RACE_NUM}R")
    print(f"買い目: {BETS}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)
        await login(page)
        result = await purchase(page, COURSE_NAME, RACE_NUM, BETS, BET_TYPE)
        await browser.close()
        if not result:
            raise SystemExit(1)
        print("✅ 購入フロー正常終了")

if __name__ == "__main__":
    asyncio.run(main())
