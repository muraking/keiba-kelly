"""
IPAT SP版 自動購入スクリプト（単勝）
馬番選択: a[data-value="1000+(馬番-1)"] をクリック
"""
import asyncio
import os
import json
from playwright.async_api import async_playwright

IPAT_ID   = os.environ.get("IPAT_ID", "63598202")
IPAT_PIN  = os.environ.get("IPAT_PIN", "1869")
IPAT_PARS = os.environ.get("IPAT_PARS", "9484")

COURSE_NAME = os.environ.get("COURSE_NAME", "")
RACE_NUM    = int(os.environ.get("RACE_NUM", "1"))
BETS        = json.loads(os.environ.get("BETS", "[]"))

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
    print(f"\n購入: {course_name} {race_num}R 合計¥{total:,}")
    for b in bets:
        print(f"  {b['num']}番 ¥{b['amount']:,}")

    # オッズ投票 → 会場 → レース → 式別から選択 → 単勝
    await page.click('text=オッズ投票')
    await page.wait_for_timeout(2000)
    await page.click(f'text={course_name}')
    await page.wait_for_timeout(2000)
    await page.click(f'text={race_num}R')
    await page.wait_for_timeout(2000)
    await page.click('text=式別から選択')
    await page.wait_for_timeout(2000)
    await page.click('text=単勝')
    await page.wait_for_timeout(2000)
    print("単勝オッズ画面 OK")

    # 馬番選択: data-value = 1000 + (馬番 - 1)
    # jQuery Mobileのタップイベントを発火させる
    print("馬番選択...")
    for bet in bets:
        num = bet['num']
        data_val = 1000 + (num - 1)
        result = await page.evaluate(f"""
            () => {{
                const a = document.querySelector('a[data-value="{data_val}"]');
                if(!a) return false;
                // jQuery Mobileはvclickイベントを使用
                ['touchstart','touchend','vclick','click'].forEach(evt => {{
                    a.dispatchEvent(new Event(evt, {{bubbles:true, cancelable:true}}));
                }});
                return true;
            }}
        """)
        print(f"  {num}番（data-value={data_val}）: {'OK' if result else 'NG'}")
        await page.wait_for_timeout(800)

    # 件数確認
    count = await page.evaluate(r"""
        () => {
            const text = document.querySelector('#odse')?.innerText || '';
            const m = text.match(/合計件数：(\d+)/);
            return m ? m[1] : '不明';
        }
    """)
    print(f"  選択件数確認: {count}")
    
    if count == '0' or count == '不明':
        # フォールバック: Playwright の tap() を使用
        print("  フォールバック: tap()で選択...")
        for bet in bets:
            num = bet['num']
            data_val = 1000 + (num - 1)
            try:
                el = await page.query_selector(f'a[data-value="{data_val}"]')
                if el:
                    await el.tap()
                    print(f"    {num}番 tap() OK")
                    await page.wait_for_timeout(500)
            except Exception as e:
                print(f"    {num}番 tap() NG: {e}")
        
        count2 = await page.evaluate(r"""
            () => {
                const text = document.querySelector('#odse')?.innerText || '';
                const m = text.match(/合計件数：(\d+)/);
                return m ? m[1] : '不明';
            }
        """)
        print(f"  再確認件数: {count2}")

    # 「金額入力画面へ」をtap()でクリック
    print("金額入力画面へ...")
    kin_btn = await page.query_selector('#odse a:has-text("金額入力画面へ")')
    if not kin_btn:
        # フォールバック
        links = await page.query_selector_all('a')
        for link in links:
            t = (await link.inner_text()).strip()
            if t == '金額入力画面へ':
                kin_btn = link
                break
    if kin_btn:
        await kin_btn.tap()
        print("  金額入力画面へ tap() OK")
    else:
        print("  ⚠️ 金額入力画面へ ボタンが見つかりません")

    # #kinが表示されるまで待機
    await page.wait_for_selector('#kin', state='visible', timeout=10000)
    print("#kin 表示OK")

    # kin_list から馬番と入力欄の対応を取得
    print("金額入力...")
    tel_inputs = await page.query_selector_all('#kin_list input[type="tel"], #kin input[type="tel"]')
    print(f"  tel入力欄数: {len(tel_inputs)}")

    # kin_listのテキストから馬番を解析
    kin_text = await page.evaluate("() => document.querySelector('#kin_list')?.innerText || ''")
    print(f"  kin_list: {kin_text[:200]}")

    # 馬番→金額のマップ
    bet_map = {b['num']: b['amount'] for b in bets}

    # kin_listのテキストから馬番順を解析
    import re
    horse_nums_in_list = []
    lines = [l.strip() for l in kin_text.split("\n") if l.strip()]
    for line in lines:
        m = re.match(r'^(\d{2})$', line)
        if m:
            horse_nums_in_list.append(int(m.group(1)))

    print(f"  kin_list馬番順: {horse_nums_in_list}")

    if len(horse_nums_in_list) == len(tel_inputs):
        # 馬番マッチングで入力
        for horse_num, inp in zip(horse_nums_in_list, tel_inputs):
            amount = bet_map.get(horse_num, 0)
            amount_100 = amount // 100
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            print(f"  {horse_num}番: {amount_100}（¥{amount:,}）")
            await page.wait_for_timeout(200)
    else:
        # フォールバック: 馬番順にソートして入力
        print(f"  フォールバック: 馬番順ソートで入力")
        bets_sorted = sorted(bets, key=lambda b: b['num'])
        for bet, inp in zip(bets_sorted, tel_inputs):
            amount_100 = bet['amount'] // 100
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            print(f"  {bet['num']}番: {amount_100}（¥{bet['amount']:,}）")
            await page.wait_for_timeout(200)

    # 「入力終了」をtap()でクリック
    print("入力終了...")
    end_btn = None
    links = await page.query_selector_all('a')
    for link in links:
        t = (await link.inner_text()).strip()
        if t == '入力終了':
            end_btn = link
            break
    if end_btn:
        await end_btn.tap()
        print("  入力終了 tap() OK")
    else:
        print("  ⚠️ 入力終了 が見つかりません")
    await page.wait_for_timeout(3000)

    # 合計金額を入力
    print(f"合計金額 ¥{total} 入力...")
    all_tels2 = await page.query_selector_all('input[type="tel"]')
    for inp in all_tels2:
        if await inp.is_visible():
            await inp.fill(str(total))
            print("  合計金額入力OK")
            break

    await page.screenshot(path="ipat_buy_confirm.png")

    # 「投票」をtap()でクリック
    print("投票...")
    vote_btn = None
    links = await page.query_selector_all('a')
    for link in links:
        t = (await link.inner_text()).strip()
        if t == '投票':
            vote_btn = link
            break
    if vote_btn:
        await vote_btn.tap()
        print("  投票 tap() OK")
    else:
        print("  ⚠️ 投票ボタンが見つかりません")
    await page.wait_for_timeout(2000)

    # 全ダイアログを自動でOK
    async def handle_dialog(dialog):
        try:
            print(f"  ダイアログ: {dialog.message}")
            await dialog.accept()
        except Exception:
            pass  # 既に処理済みの場合は無視
    page.on('dialog', handle_dialog)
    await page.wait_for_timeout(2000)

    # 「合計金額入力」画面が残っている場合は再度「投票」をtap
    page_text = await page.evaluate("() => document.body.innerText")
    if '合計金額入力' in page_text and '受付番号' not in page_text:
        print("合計金額確認画面 → 再度合計金額入力して投票...")
        all_tels3 = await page.query_selector_all('input[type="tel"]')
        for inp in all_tels3:
            if await inp.is_visible():
                await inp.fill(str(total))
                print(f"  合計金額再入力OK: ¥{total}")
                break
        await page.wait_for_timeout(500)
        links2 = await page.query_selector_all('a')
        for link in links2:
            t = (await link.inner_text()).strip()
            if t == '投票':
                await link.tap()
                print("  2回目投票 tap() OK")
                break
        await page.wait_for_timeout(3000)

    await page.screenshot(path="ipat_buy_result.png")
    text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    print("結果:")
    for line in lines[:15]:
        print(f"  {line}")

    success = '受付番号' in text or 'ありがとう' in text
    print(f"\n{'✅ 投票完了！' if success else '⚠️ 投票結果不明'}")
    return success

async def main():
    global COURSE_NAME, RACE_NUM, BETS
    if not COURSE_NAME:
        COURSE_NAME = "東京(土)"
        RACE_NUM = 1
        BETS = [{"num": 3, "amount": 100}, {"num": 5, "amount": 100}]

    print(f"=== IPAT自動購入 ===")
    print(f"会場: {COURSE_NAME} {RACE_NUM}R")
    print(f"買い目: {BETS}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)

        await login(page)
        result = await purchase(page, COURSE_NAME, RACE_NUM, BETS)

        input("\nEnterで終了...")
        await browser.close()
        return result

if __name__ == "__main__":
    asyncio.run(main())
