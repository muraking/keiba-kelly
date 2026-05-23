"""
IPAT 通常投票 自動購入スクリプト（馬連）

フロー（通常投票ルート）:
  ログイン
  → 通常投票 → 競馬場名 → レースR
  → 式別(馬連) → 方式(フォーメーション)
  → 1頭目チェック(checkbox) → 次へ
  → 2頭目チェック(checkbox) → 金額入力画面へ
  → 金額入力 → セット → 投票
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


async def check_horse_normal(page, num):
    """通常投票フォーメーション画面でチェックボックスをクリック"""
    # 通常投票の1頭目/2頭目選択画面: checkbox が右端にある
    # 各行: 馬番 | 馬名 | 単勝オッズ | [checkbox]
    result = await page.evaluate(f"""
        () => {{
            // input[type=checkbox] を持つ行から馬番でマッチ
            const rows = document.querySelectorAll('tr');
            for(const row of rows) {{
                const tds = row.querySelectorAll('td');
                if(tds.length < 2) continue;
                const numText = tds[0].innerText.trim();
                if(parseInt(numText) === {num}) {{
                    const cb = row.querySelector('input[type=checkbox]');
                    if(cb) {{
                        cb.click();
                        return 'cb-clicked:' + numText;
                    }}
                    // チェックボックスがない場合は行をクリック
                    row.click();
                    return 'row-click:' + numText;
                }}
            }}
            // フォールバック: label や td から探す
            const allTds = document.querySelectorAll('td');
            for(const td of allTds) {{
                if(td.innerText.trim() === String({num})) {{
                    const row = td.closest('tr');
                    if(row) {{
                        const cb = row.querySelector('input[type=checkbox]');
                        if(cb) {{ cb.click(); return 'cb-fb:' + {num}; }}
                    }}
                }}
            }}
            return false;
        }}
    """)
    if not result:
        # Playwright フォールバック
        try:
            rows = await page.query_selector_all('tr')
            for row in rows:
                cells = await row.query_selector_all('td')
                if cells:
                    first = (await cells[0].inner_text()).strip()
                    if first == str(num) or first == f"{num:02d}":
                        cb = await row.query_selector('input[type=checkbox]')
                        if cb:
                            await cb.click()
                            result = 'cb-playwright'
                        break
        except Exception as e:
            print(f"    {num}番 playwright失敗: {e}")
    print(f"    {num}番: {result or 'NG'}")
    await page.wait_for_timeout(400)
    return bool(result)


async def purchase(page, course_name, race_num, bets):
    total = sum(b['amount'] for b in bets)
    # 全組み合わせ同額（フォーメーション一括）
    unit_amount = bets[0]['amount'] if bets else 100
    print(f"\n購入: {course_name} {race_num}R 馬連 合計¥{total:,}")
    for b in bets:
        print(f"  {b['num1']}-{b['num2']}番 ¥{b['amount']:,}")

    # ① 通常投票
    await page.click('text=通常投票')
    await page.wait_for_timeout(2000)

    # ② 競馬場名
    page_text = await page.evaluate("() => document.body.innerText")
    course_base = course_name.split('(')[0].strip()
    if course_name in page_text:
        click_name = course_name
    elif course_base in page_text:
        click_name = course_base
        print(f"コース名変換: {course_name} → {click_name}")
    else:
        click_name = course_name
        print(f"⚠️ コース名未検出: {course_name}")
    await page.click(f'text={click_name}')
    await page.wait_for_timeout(2000)

    # ③ レース番号
    await page.click(f'text={race_num}R')
    await page.wait_for_timeout(2000)

    # ④ 式別: 馬連
    await page.click('text=馬連')
    await page.wait_for_timeout(2000)
    print("式別→馬連 OK")

    # ⑤ 方式: フォーメーション
    await page.click('text=フォーメーション')
    await page.wait_for_timeout(2000)
    print("フォーメーション OK")

    # ⑥ 1頭目チェック
    axis_nums    = list(dict.fromkeys([b['num1'] for b in bets]))
    partner_nums = list(dict.fromkeys([b['num2'] for b in bets]))
    print(f"1頭目チェック: {axis_nums}")
    for num in axis_nums:
        await check_horse_normal(page, num)

    # 次へ
    await page.click('text=次へ')
    await page.wait_for_timeout(2000)
    print(f"次へ OK: {page.url}")

    # ⑦ 2頭目チェック
    print(f"2頭目チェック: {partner_nums}")
    for num in partner_nums:
        await check_horse_normal(page, num)

    # 金額入力画面へ
    await page.click('text=金額入力画面へ')
    await page.wait_for_timeout(2000)
    print(f"金額入力画面へ OK: {page.url}")

    await page.screenshot(path="ipat_exacta_confirm.png")
    page_text2 = await page.evaluate("() => document.body.innerText")
    print(f"金額入力画面（先頭300文字）:\n{page_text2[:300]}")

    if DRY_RUN:
        print("\n========== DRY RUN MODE ==========")
        for b in bets:
            print(f"  {b['num1']:02d}-{b['num2']:02d} 馬連 ¥{b['amount']:,}")
        print(f"  合計: ¥{total:,}")
        print("===================================")
        print("✅ DRY RUN完了（投票しません）")
        return True

    # ⑧ 金額入力: 「金額[    ]00円」の入力欄に金額/100を入力
    amount_100 = unit_amount // 100
    inp = await page.query_selector('input[name="kingaku"], input[type="text"], input[type="number"]')
    if inp:
        await inp.fill(str(amount_100))
        print(f"金額入力: {amount_100}×100=¥{unit_amount}")
    else:
        print("⚠️ 金額入力欄が見つかりません")

    # セット
    await page.click('text=セット')
    await page.wait_for_timeout(2000)

    # 投票
    page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    await page.click('text=投票')
    await page.wait_for_timeout(3000)

    await page.screenshot(path="ipat_exacta_result.png")
    result_text = await page.evaluate("() => document.body.innerText")
    for line in [l.strip() for l in result_text.split('\n') if l.strip()][:15]:
        print(f"  {line}")

    success = '受付番号' in result_text or 'ありがとう' in result_text
    print(f"\n{'✅ 馬連投票完了！' if success else '⚠️ 投票結果不明'}")
    return success


async def main():
    global COURSE_NAME, RACE_NUM, BETS
    if not COURSE_NAME:
        COURSE_NAME = "東京(日)"
        RACE_NUM = 1
        BETS = [{"num1": 1, "num2": 3, "amount": 100}]

    print(f"=== IPAT自動購入（馬連）===")
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
