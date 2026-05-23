"""
IPAT SP版 自動購入スクリプト（ワイド）
馬連と同じフローで式別を「ワイド」に変更
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

    # オッズ投票 → 会場 → レース → 式別から選択 → ワイド
    await page.click('text=オッズ投票')
    await page.wait_for_timeout(2000)

    page_text = await page.evaluate("() => document.body.innerText")
    print(f"会場ページ内容（先頭300文字）: {page_text[:300]}")

    course_base = course_name.split('(')[0].strip()
    if course_name in page_text:
        click_name = course_name
    elif course_base in page_text:
        click_name = course_base
        print(f"コース名変換: {course_name} → {click_name}")
    else:
        click_name = course_name
        print(f"⚠️ コース名が見つからない: {course_name}")

    await page.click(f'text={click_name}')
    await page.wait_for_timeout(2000)
    await page.click(f'text={race_num}R')
    await page.wait_for_timeout(2000)
    await page.click('text=式別から選択')
    await page.wait_for_timeout(2000)
    await page.click('text=ワイド')
    await page.wait_for_timeout(2000)
    print("ワイドオッズ画面 OK")

    # 馬番選択（馬連と同じロジック）
    for bet in bets:
        num1 = bet['num1']
        num2 = bet['num2']
        print(f"  {num1}-{num2}番を選択...")

        for num in [num1, num2]:
            dv = 1000 + (num - 1)
            result = await page.evaluate(f"""
                () => {{
                    const a = document.querySelector('a[data-value="{dv}"]');
                    if(!a) return false;
                    ['touchstart','touchend','vclick','click'].forEach(evt => {{
                        a.dispatchEvent(new Event(evt, {{bubbles:true, cancelable:true}}));
                    }});
                    return true;
                }}
            """)
            if not result:
                try:
                    el = await page.query_selector(f'a[data-value="{dv}"]')
                    if el: await el.tap()
                    result = True
                except: pass
            print(f"    {num}番: {'OK' if result else 'NG'}")
            await page.wait_for_timeout(600)

    count = await page.evaluate(r"""
        () => {
            const text = document.querySelector('#odse')?.innerText || '';
            const m = text.match(/合計件数：(\d+)/);
            return m ? m[1] : '不明';
        }
    """)
    print(f"  選択件数: {count}")

    # 金額入力画面へ
    print("金額入力画面へ...")
    kin_btn = None
    for link in await page.query_selector_all('a'):
        if (await link.inner_text()).strip() == '金額入力画面へ':
            kin_btn = link
            break
    if kin_btn:
        await kin_btn.tap()
        print("  金額入力画面へ tap() OK")
    else:
        print("  ⚠️ 金額入力画面へ ボタンが見つかりません")

    await page.wait_for_selector('#kin', state='visible', timeout=10000)
    print("#kin 表示OK")

    print("金額入力...")
    tel_inputs = await page.query_selector_all('#kin_list input[type="tel"], #kin input[type="tel"]')
    print(f"  tel入力欄数: {len(tel_inputs)}")

    kin_text = await page.evaluate("() => document.querySelector('#kin_list')?.innerText || ''")
    print(f"  kin_list: {kin_text[:300]}")

    combos_in_list = []
    lines = [l.strip() for l in kin_text.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        m1 = re.match(r'^(\d{2})$', lines[i])
        if m1 and i+1 < len(lines):
            m2 = re.match(r'^(\d{2})$', lines[i+1])
            if m2:
                combos_in_list.append((int(m1.group(1)), int(m2.group(1))))
                i += 2
                continue
        i += 1

    print(f"  組み合わせ順: {combos_in_list}")
    bet_map = {(min(b['num1'],b['num2']), max(b['num1'],b['num2'])): b['amount'] for b in bets}

    if combos_in_list and len(combos_in_list) == len(tel_inputs):
        for (n1, n2), inp in zip(combos_in_list, tel_inputs):
            key = (min(n1,n2), max(n1,n2))
            amount = bet_map.get(key, bets[0]['amount'])
            amount_100 = amount // 100
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            print(f"  {n1}-{n2}: {amount_100}（¥{amount:,}）")
            await page.wait_for_timeout(200)
    else:
        unit_amount = bets[0]['amount'] // 100 if bets else 1
        for inp in tel_inputs:
            await inp.fill(str(unit_amount))
            await inp.dispatch_event('change')
            await page.wait_for_timeout(200)
        print(f"  フォールバック: 全欄 {unit_amount}（¥{bets[0]['amount']:,}）")

    print("入力終了...")
    for link in await page.query_selector_all('a'):
        if (await link.inner_text()).strip() == '入力終了':
            await link.tap()
            print("  入力終了 tap() OK")
            break
    await page.wait_for_timeout(3000)

    print(f"合計金額 ¥{total} 入力...")
    for inp in await page.query_selector_all('input[type="tel"]'):
        if await inp.is_visible():
            await inp.fill(str(total))
            print("  合計金額入力OK")
            break

    await page.screenshot(path="ipat_wide_confirm.png")

    if DRY_RUN:
        print("\n========== DRY RUN MODE ==========")
        for b in bets:
            print(f"  {b['num1']}-{b['num2']}番 ワイド ¥{b['amount']:,}")
        print(f"  合計: ¥{total:,}")
        print("===================================")
        print("✅ DRY RUN完了")
        return True

    print("投票...")
    page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    for link in await page.query_selector_all('a'):
        if (await link.inner_text()).strip() == '投票':
            await link.tap()
            print("  投票 tap() OK")
            break
    await page.wait_for_timeout(3000)

    page_text2 = await page.evaluate("() => document.body.innerText")
    if '合計金額入力' in page_text2 and '受付番号' not in page_text2:
        print("合計金額確認画面 → 再入力...")
        for inp in await page.query_selector_all('input[type="tel"]'):
            if await inp.is_visible():
                await inp.fill(str(total))
                print(f"  再入力OK: ¥{total}")
                break
        await page.wait_for_timeout(500)
        for link in await page.query_selector_all('a'):
            if (await link.inner_text()).strip() == '投票':
                await link.tap()
                print("  2回目投票 tap() OK")
                break
        await page.wait_for_timeout(3000)

    await page.screenshot(path="ipat_wide_result.png")
    text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    print("結果:")
    for line in lines[:15]:
        print(f"  {line}")

    success = '受付番号' in text or 'ありがとう' in text
    print(f"\n{'✅ ワイド投票完了！' if success else '⚠️ 投票結果不明'}")
    return success


async def main():
    global COURSE_NAME, RACE_NUM, BETS
    if not COURSE_NAME:
        COURSE_NAME = "東京(土)"
        RACE_NUM = 1
        BETS = [{"num1": 1, "num2": 3, "amount": 100}]

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
