"""
IPAT SP版 自動購入スクリプト（ワイド）
馬連と全く同じフローで式別を「ワイド」に変更
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
DRY_RUN     = os.environ.get("DRY_RUN", "0") == "1"

LOGIN_URL = "https://www.ipat.jra.go.jp/sp/"
TIMEOUT   = 30000


async def tap_text(page, text):
    el = await page.query_selector(f'text={text}')
    if not el:
        for link in await page.query_selector_all('a, button'):
            t = (await link.inner_text()).strip()
            if t == text:
                el = link
                break
    if el:
        await el.tap()
        return True
    print(f"  ⚠️ '{text}' が見つかりません")
    return False


async def check_horse(page, num):
    result = await page.evaluate(f"""
        () => {{
            const rows = document.querySelectorAll('tr, li, div[class*="row"], [data-num]');
            for(const row of rows) {{
                const text = row.innerText || '';
                const m = text.match(/^\\s*(\\d{{1,2}})\\s/);
                if(m && parseInt(m[1]) === {num}) {{
                    const cb = row.querySelector('input[type=checkbox]');
                    if(cb) {{ if(!cb.checked) cb.click(); return 'checkbox:' + {num}; }}
                }}
            }}
            const dv = {1000 + (num - 1)};
            const a = document.querySelector(`a[data-value="${{dv}}"]`);
            if(a) {{
                ['touchstart','touchend','vclick','click'].forEach(evt =>
                    a.dispatchEvent(new Event(evt, {{bubbles:true}}))
                );
                return 'link:' + {num};
            }}
            return false;
        }}
    """)
    if not result:
        try:
            el = await page.query_selector(f'a[data-value="{1000 + (num - 1)}"]')
            if el:
                await el.tap()
                result = 'tap'
        except Exception as e:
            print(f"    tap失敗: {e}")
    print(f"    {num}番: {result}")
    await page.wait_for_timeout(500)
    return bool(result)


async def check_combo(page, num1, num2):
    n1 = min(num1, num2)
    n2 = max(num1, num2)
    label = f"{n1:02d}-{n2:02d}"
    label_alt = f"{n1}-{n2}"

    result = await page.evaluate(f"""
        () => {{
            const labels = ['{label}', '{label_alt}'];
            const rows = document.querySelectorAll('tr, li, div[class*="row"], .combo-row');
            for(const row of rows) {{
                const text = (row.innerText || '').replace(/\\s/g, '');
                for(const lbl of labels) {{
                    if(text.includes(lbl)) {{
                        const cb = row.querySelector('input[type=checkbox]');
                        if(cb) {{ if(!cb.checked) cb.click(); return 'checked:' + lbl; }}
                        const links = row.querySelectorAll('a');
                        if(links.length > 0) {{
                            const last = links[links.length - 1];
                            ['touchstart','touchend','vclick','click'].forEach(evt =>
                                last.dispatchEvent(new Event(evt, {{bubbles:true}}))
                            );
                            return 'link:' + lbl;
                        }}
                    }}
                }}
            }}
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while(node = walker.nextNode()) {{
                const t = node.textContent.trim().replace(/\\s/g,'');
                for(const lbl of labels) {{
                    if(t === lbl) {{
                        const row2 = node.parentElement.closest('tr, li, div');
                        if(row2) {{
                            const cb2 = row2.querySelector('input[type=checkbox]');
                            if(cb2) {{ if(!cb2.checked) cb2.click(); return 'walker:' + lbl; }}
                        }}
                    }}
                }}
            }}
            return false;
        }}
    """)
    print(f"    {label}: {result}")
    await page.wait_for_timeout(400)
    return bool(result)


async def login(page):
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)
    await page.fill('#userid', IPAT_ID)
    await page.fill('#password', IPAT_PIN)
    await page.fill('#pars', IPAT_PARS)
    await page.evaluate("ToSPMenu()")
    await page.wait_for_timeout(3000)
    print(f"ログイン完了: {page.url}")


async def purchase(page, course_name, race_num, bets):
    total = sum(b['amount'] for b in bets)
    print(f"\n購入: {course_name} {race_num}R ワイド 合計¥{total:,}")
    for b in bets:
        print(f"  {b['num1']}-{b['num2']}番 ¥{b['amount']:,}")

    # ① オッズ投票 → 会場 → レース
    await tap_text(page, 'オッズ投票')
    await page.wait_for_timeout(2000)

    page_text = await page.evaluate("() => document.body.innerText")
    course_base = course_name.split('(')[0].strip()
    click_name = course_name if course_name in page_text else (course_base if course_base in page_text else course_name)
    if click_name != course_name:
        print(f"コース名変換: {course_name} → {click_name}")

    await tap_text(page, click_name)
    await page.wait_for_timeout(2000)
    await tap_text(page, f'{race_num}R')
    await page.wait_for_timeout(2000)

    # ② 式別から選択 → ワイド
    await tap_text(page, '式別から選択')
    await page.wait_for_timeout(2000)
    await tap_text(page, 'ワイド')
    await page.wait_for_timeout(2000)

    # ③ フォーメーション
    await tap_text(page, 'フォーメーション')
    await page.wait_for_timeout(2000)
    print("フォーメーション選択 OK")

    # ④ 1頭目チェック
    axis_nums = list(dict.fromkeys([b['num1'] for b in bets]))
    partner_nums = list(dict.fromkeys([b['num2'] for b in bets]))

    print(f"1頭目チェック: {axis_nums}")
    for num in axis_nums:
        await check_horse(page, num)
    await tap_text(page, '次へ')
    await page.wait_for_timeout(2000)
    print("1頭目 → 次へ OK")

    # ⑤ 2頭目チェック
    print(f"2頭目チェック: {partner_nums}")
    for num in partner_nums:
        await check_horse(page, num)
    await tap_text(page, 'オッズ選択画面へ')
    await page.wait_for_timeout(2000)
    print("2頭目 → オッズ選択画面へ OK")

    # ⑥ 組み合わせチェック
    print("組み合わせチェック...")
    for b in bets:
        await check_combo(page, b['num1'], b['num2'])

    count = await page.evaluate(r"""
        () => {
            const m = document.body.innerText.match(/合計件数[：:]\s*(\d+)/);
            return m ? m[1] : '不明';
        }
    """)
    print(f"  選択件数: {count}")
    await page.wait_for_timeout(500)

    await tap_text(page, '金額入力画面へ')
    await page.wait_for_timeout(2000)
    print("金額入力画面へ OK")

    # ⑦ 金額入力
    await tap_text(page, '1件ごと')
    await page.wait_for_timeout(1000)

    tel_inputs = await page.query_selector_all('input[type="tel"], input[type="number"]')
    print(f"  入力欄数: {len(tel_inputs)}")

    page_text2 = await page.evaluate("() => document.body.innerText")
    print(f"  金額入力画面（先頭500文字）: {page_text2[:500]}")

    bet_map = {(min(b['num1'],b['num2']), max(b['num1'],b['num2'])): b['amount'] for b in bets}
    default_amount = bets[0]['amount'] if bets else 100

    combo_pattern = re.compile(r'(\d{1,2})[－\-](\d{1,2})')
    combos_order = []
    for line in [l.strip() for l in page_text2.split('\n') if l.strip()]:
        m = combo_pattern.search(line)
        if m:
            n1, n2 = int(m.group(1)), int(m.group(2))
            combos_order.append((min(n1,n2), max(n1,n2)))

    print(f"  組み合わせ順: {combos_order}")

    if combos_order and len(combos_order) == len(tel_inputs):
        for combo, inp in zip(combos_order, tel_inputs):
            amount = bet_map.get(combo, default_amount)
            amount_100 = amount // 100
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            print(f"  {combo[0]:02d}-{combo[1]:02d}: {amount_100}×100=¥{amount}")
            await page.wait_for_timeout(200)
    elif tel_inputs:
        amount_100 = default_amount // 100
        for inp in tel_inputs:
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            await page.wait_for_timeout(200)
        print(f"  フォールバック: 全欄 ¥{default_amount}")
    else:
        print("  ⚠️ 金額入力欄が見つかりません")

    await page.screenshot(path="ipat_wide_confirm.png")

    if DRY_RUN:
        print("\n========== DRY RUN MODE ==========")
        for b in bets:
            print(f"  {b['num1']:02d}-{b['num2']:02d} ワイド ¥{b['amount']:,}")
        print(f"  合計: ¥{total:,}")
        print("===================================\n✅ DRY RUN完了（投票しません）")
        return True

    # ⑧ 入力終了 → 投票
    await tap_text(page, '入力終了')
    await page.wait_for_timeout(3000)

    page_text3 = await page.evaluate("() => document.body.innerText")
    if '合計金額' in page_text3 and '受付番号' not in page_text3:
        for inp in await page.query_selector_all('input[type="tel"]'):
            if await inp.is_visible():
                await inp.fill(str(total))
                print(f"  合計: ¥{total}")
                break
        await page.wait_for_timeout(500)

    page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await tap_text(page, '投票')
    await page.wait_for_timeout(3000)

    page_text4 = await page.evaluate("() => document.body.innerText")
    if '合計金額' in page_text4 and '受付番号' not in page_text4:
        for inp in await page.query_selector_all('input[type="tel"]'):
            if await inp.is_visible():
                await inp.fill(str(total))
                break
        await page.wait_for_timeout(500)
        await tap_text(page, '投票')
        await page.wait_for_timeout(3000)

    await page.screenshot(path="ipat_wide_result.png")
    result_text = await page.evaluate("() => document.body.innerText")
    for line in [l.strip() for l in result_text.split('\n') if l.strip()][:15]:
        print(f"  {line}")

    success = '受付番号' in result_text or 'ありがとう' in result_text
    print(f"\n{'✅ ワイド投票完了！' if success else '⚠️ 投票結果不明'}")
    return success


async def main():
    global COURSE_NAME, RACE_NUM, BETS
    if not COURSE_NAME:
        COURSE_NAME = "東京(日)"
        RACE_NUM = 1
        BETS = [{"num1": 2, "num2": 4, "amount": 100},
                {"num1": 2, "num2": 5, "amount": 100}]

    print(f"=== IPAT自動購入（ワイド）===")
    print(f"会場: {COURSE_NAME} {RACE_NUM}R")
    print(f"買い目: {BETS}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)
        await login(page)
        result = await purchase(page, COURSE_NAME, RACE_NUM, BETS)
        await browser.close()
        if not result:
            raise SystemExit(1)

if __name__ == "__main__":
    asyncio.run(main())
