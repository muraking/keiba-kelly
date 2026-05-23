"""
IPAT SP版 自動購入スクリプト（ワイド）
フォーメーション方式

フロー:
  ログイン
  → オッズ投票 → 会場 → レースR
  → 式別から選択 → 馬連 → フォーメーション
  → 1頭目チェック → 次へ
  → 2頭目チェック → オッズ選択画面へ
  → 組み合わせ右チェック → 金額入力画面へ
  → 1件ごと → 金額入力 → 入力終了 → 投票
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


async def click_text(page, text):
    """page.click と tap() の両方を試みる"""
    try:
        await page.click(f'text={text}')
        return True
    except Exception:
        pass
    # フォールバック: query_selector
    links = await page.query_selector_all('a, button, li')
    for el in links:
        try:
            t = (await el.inner_text()).strip()
            if t == text:
                await el.tap()
                return True
        except Exception:
            continue
    print(f"  ⚠️ '{text}' が見つかりません")
    return False


async def check_horse(page, num):
    """フォーメーション画面で馬番をタップ（data-value=馬番そのまま）"""
    # IPATフォーメーション: <li><a data-value="1" ...>1 馬名 オッズ</a></li>
    # data-valueは馬番そのまま（単勝の1000+num-1とは異なる）
    selector = f'#uma1 a[data-value="{num}"], #uma2 a[data-value="{num}"]'
    try:
        el = await page.query_selector(selector)
        if el:
            await el.tap()
            await page.wait_for_timeout(300)
            # 組数を確認
            bet_num = await page.evaluate("() => { const d = document.querySelector('.betNum dd'); return d ? d.innerText.trim() : '?'; }")
            print(f"    {num}番: tap OK (組数:{bet_num})")
            return True
    except Exception as e:
        print(f"    {num}番 tap失敗: {e}")
    # フォールバック: evaluate でクリック
    result = await page.evaluate(f"""
        () => {{
            const a = document.querySelector('#uma1 a[data-value="{num}"], #uma2 a[data-value="{num}"]');
            if(a) {{ a.click(); return true; }}
            return false;
        }}
    """)
    print(f"    {num}番: evaluate={'OK' if result else 'NG'}")
    await page.wait_for_timeout(300)
    return bool(result)


async def check_combo(page, num1, num2):
    """オッズ選択画面で組み合わせの右チェックボックスをON"""
    n1, n2 = min(num1, num2), max(num1, num2)
    labels = [f"{n1:02d}－{n2:02d}", f"{n1:02d}-{n2:02d}", f"{n1}-{n2}"]

    result = await page.evaluate(f"""
        () => {{
            const labels = {json.dumps(labels)};
            // tr/li 行からラベルを探してチェック
            const rows = document.querySelectorAll('tr, li');
            for(const row of rows) {{
                const text = (row.innerText || '').replace(/\\s+/g,'');
                for(const lbl of labels) {{
                    const clean = lbl.replace(/[\\s－-]/g,'');
                    if(text.includes(clean) || text.includes(lbl.replace('-','－')) || text.includes(lbl)) {{
                        // 行内の最後のリンクまたはチェックボックス
                        const cb = row.querySelector('input[type=checkbox]');
                        if(cb) {{ if(!cb.checked) cb.click(); return 'cb:'+lbl; }}
                        const links = row.querySelectorAll('a');
                        if(links.length) {{
                            const last = links[links.length-1];
                            ['touchstart','touchend','vclick','click'].forEach(e =>
                                last.dispatchEvent(new Event(e, {{bubbles:true}}))
                            );
                            return 'link:'+lbl;
                        }}
                    }}
                }}
            }}
            return false;
        }}
    """)
    print(f"    {n1:02d}-{n2:02d}: {result or 'NG'}")
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

    # ① 単勝と同じ方法でオッズ投票→会場→レース→式別→馬連
    await page.click('text=オッズ投票')
    await page.wait_for_timeout(2000)

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
    await page.click(f'text={race_num}R')
    await page.wait_for_timeout(2000)
    await page.click('text=式別から選択')
    await page.wait_for_timeout(2000)
    await page.click('text=ワイド')
    await page.wait_for_timeout(2000)
    print("式別→馬連 OK")

    # ② フォーメーション選択
    await page.click('text=フォーメーション')
    await page.wait_for_timeout(2000)
    print("フォーメーション OK")

    # ③ 1頭目（軸馬）チェック
    axis_nums    = list(dict.fromkeys([b['num1'] for b in bets]))
    partner_nums = list(dict.fromkeys([b['num2'] for b in bets]))
    print(f"1頭目チェック: {axis_nums}")
    for num in axis_nums:
        await check_horse(page, num)

    # 次へ
    await click_text(page, '次へ')
    await page.wait_for_timeout(2000)
    print("次へ OK")

    # ④ 2頭目（相手馬）チェック
    print(f"2頭目チェック: {partner_nums}")
    for num in partner_nums:
        await check_horse(page, num)

    # オッズ選択画面へ
    await click_text(page, 'オッズ選択画面へ')
    await page.wait_for_timeout(2000)
    print("オッズ選択画面へ OK")

    # ⑤ 組み合わせチェック
    print("組み合わせチェック...")
    for b in bets:
        await check_combo(page, b['num1'], b['num2'])

    count = await page.evaluate(r"""
        () => {
            const m = document.body.innerText.match(/合計件数[：:]\s*(\d+)/);
            return m ? m[1] : '不明';
        }
    """)
    print(f"  件数確認: {count}")

    # 金額入力画面へ
    await click_text(page, '金額入力画面へ')
    await page.wait_for_timeout(2000)
    print("金額入力画面へ OK")

    # ⑥ 1件ごとタブ選択
    await click_text(page, '1件ごと')
    await page.wait_for_timeout(1000)

    # ⑦ 金額入力
    print("金額入力...")
    tel_inputs = await page.query_selector_all('input[type="tel"], input[type="number"]')
    print(f"  入力欄数: {len(tel_inputs)}")

    page_text2 = await page.evaluate("() => document.body.innerText")
    print(f"  金額画面（先頭500文字）: {page_text2[:500]}")

    bet_map = {(min(b['num1'],b['num2']), max(b['num1'],b['num2'])): b['amount'] for b in bets}
    default_amount = bets[0]['amount'] if bets else 100

    combo_pattern = re.compile(r'(\d{1,2})[－\-](\d{1,2})')
    combos_order = []
    for line in [l.strip() for l in page_text2.split('\n') if l.strip()]:
        m = combo_pattern.search(line)
        if m:
            n1, n2 = int(m.group(1)), int(m.group(2))
            key = (min(n1,n2), max(n1,n2))
            if key not in combos_order:
                combos_order.append(key)
    print(f"  組み合わせ順: {combos_order}")

    if combos_order and len(combos_order) == len(tel_inputs):
        for combo, inp in zip(combos_order, tel_inputs):
            amount = bet_map.get(combo, default_amount)
            amt100 = amount // 100
            await inp.fill(str(amt100))
            await inp.dispatch_event('change')
            print(f"  {combo[0]:02d}-{combo[1]:02d}: {amt100}×100=¥{amount}")
            await page.wait_for_timeout(200)
    elif tel_inputs:
        amt100 = default_amount // 100
        for inp in tel_inputs:
            await inp.fill(str(amt100))
            await inp.dispatch_event('change')
            await page.wait_for_timeout(200)
        print(f"  フォールバック: 全欄 ¥{default_amount}")
    else:
        print("  ⚠️ 金額入力欄なし")

    await page.screenshot(path="ipat_wide_confirm.png")

    if DRY_RUN:
        print("\n========== DRY RUN MODE ==========")
        for b in bets:
            print(f"  {b['num1']:02d}-{b['num2']:02d} ワイド ¥{b['amount']:,}")
        print(f"  合計: ¥{total:,}")
        print("===================================")
        print("✅ DRY RUN完了（投票しません）")
        return True

    # ⑧ 入力終了 → 投票
    await click_text(page, '入力終了')
    await page.wait_for_timeout(3000)

    page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))

    pt3 = await page.evaluate("() => document.body.innerText")
    if '合計金額' in pt3 and '受付番号' not in pt3:
        for inp in await page.query_selector_all('input[type="tel"]'):
            if await inp.is_visible():
                await inp.fill(str(total))
                break
        await page.wait_for_timeout(500)

    await click_text(page, '投票')
    await page.wait_for_timeout(3000)

    pt4 = await page.evaluate("() => document.body.innerText")
    if '合計金額' in pt4 and '受付番号' not in pt4:
        for inp in await page.query_selector_all('input[type="tel"]'):
            if await inp.is_visible():
                await inp.fill(str(total))
                break
        await page.wait_for_timeout(500)
        await click_text(page, '投票')
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
