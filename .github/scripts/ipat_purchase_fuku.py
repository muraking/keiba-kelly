"""
IPAT SP版 自動購入スクリプト（複勝）
馬番選択: a[data-value="1000+(馬番-1)"] をクリック
"""
import asyncio
import os
import json
from playwright.async_api import async_playwright

IPAT_ID   = os.environ.get("IPAT_ID", "ここに加入者番号を入力")
IPAT_PIN  = os.environ.get("IPAT_PIN", "ここに暗証番号を入力")
IPAT_PARS = os.environ.get("IPAT_PARS", "ここにP-ARS番号を入力")

COURSE_NAME = os.environ.get("COURSE_NAME", "")
RACE_NUM    = int(os.environ.get("RACE_NUM", "1"))
BETS        = json.loads(os.environ.get("BETS", "[]"))
AUTO_BUY_MAX = int(os.environ.get("AUTO_BUY_MAX", "0") or "0")
AUTO_BUY_MODE = os.environ.get("AUTO_BUY_MODE", "0") == "1"
DRY_RUN     = os.environ.get("DRY_RUN", "0") == "1"

LOGIN_URL = "https://www.ipat.jra.go.jp/sp/"
TIMEOUT   = 30000


async def get_balance(page):
    """IPATログイン後に購入限度額を取得"""
    import re
    try:
        text = await page.evaluate("() => document.body.innerText")
        print(f"残高照会ページ（先頭300文字）: {text[:300]}")

        for pattern in [
            r'購入限度額[\s\n]*([\d,]+)',
            r'残高[：:　\s]*([\d,]+)',
            r'利用可能額[：:　\s]*([\d,]+)',
        ]:
            m = re.search(pattern, text)
            if m:
                v = int(m.group(1).replace(',', ''))
                if 100 <= v <= 10000000:
                    print(f"残高取得（購入限度額）: ¥{v:,}")
                    return v

        print("残高取得失敗 → デフォルト10000円で計算")
        return 10000
    except Exception as e:
        print(f"残高取得エラー: {e} → デフォルト10000円")
        return 10000

def calc_kelly_amounts(bets, bankroll, kelly_fraction=0.5, min_amount=100, unit=100):
    import math
    result = []
    for bet in bets:
        p = bet.get('norm', 0)
        odds = bet.get('odds', 1.0)
        b = odds - 1.0

        if p <= 0 or b <= 0:
            amount = min_amount
        else:
            kelly = (b * p - (1 - p)) / b
            kelly = max(0, kelly)
            half_kelly = kelly * kelly_fraction
            amount = int(bankroll * half_kelly / unit) * unit
            amount = max(amount, min_amount)

        result.append({**bet, 'amount': amount})
        print(f"  {bet['num']}番: p={p:.3f} odds={odds} kelly={kelly_fraction*((b*p-(1-p))/b if b>0 and p>0 else 0):.3f} → ¥{amount:,}")

    total = sum(b['amount'] for b in result)
    print(f"  合計: ¥{total:,} / 残高: ¥{bankroll:,} ({total/bankroll*100:.1f}%)")
    return result

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
    # tanのみ処理（fukuは別スクリプト）
    bets = [b for b in bets if b.get('bet_type') == 'fuku']
    if not bets:
        print("複勝買い目なし → スキップ")
        return True

    total = sum(b['amount'] for b in bets)
    print(f"\n購入: {course_name} {race_num}R 合計¥{total:,}")
    for b in bets:
        print(f"  {b['num']}番 ¥{b['amount']:,}")

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
    await page.click('text=複勝')
    await page.wait_for_timeout(2000)
    print("複勝オッズ画面 OK")

    print("馬番選択...")
    for bet in bets:
        num = bet['num']
        data_val = 2000 + (num - 1)  # 複勝はdata-valueが2000番台
        result = await page.evaluate(f"""
            () => {{
                const a = document.querySelector('a[data-value="{data_val}"]');
                if(!a) return false;
                ['touchstart','touchend','vclick','click'].forEach(evt => {{
                    a.dispatchEvent(new Event(evt, {{bubbles:true, cancelable:true}}));
                }});
                return true;
            }}
        """)
        print(f"  {num}番（data-value={data_val}）: {'OK' if result else 'NG'}")
        await page.wait_for_timeout(800)

    count = await page.evaluate(r"""
        () => {
            const text = document.querySelector('#odse')?.innerText || '';
            const m = text.match(/合計件数：(\d+)/);
            return m ? m[1] : '不明';
        }
    """)
    print(f"  選択件数確認: {count}")

    if count == '0' or count == '不明':
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

    print("金額入力画面へ...")
    kin_btn = await page.query_selector('#odse a:has-text("金額入力画面へ")')
    if not kin_btn:
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

    await page.wait_for_selector('#kin', state='visible', timeout=10000)
    print("#kin 表示OK")

    print("金額入力...")
    tel_inputs = await page.query_selector_all('#kin_list input[type="tel"], #kin input[type="tel"]')
    print(f"  tel入力欄数: {len(tel_inputs)}")

    kin_text = await page.evaluate("() => document.querySelector('#kin_list')?.innerText || ''")
    print(f"  kin_list: {kin_text[:200]}")

    bet_map = {b['num']: b['amount'] for b in bets}

    import re
    horse_nums_in_list = []
    lines = [l.strip() for l in kin_text.split("\n") if l.strip()]
    for line in lines:
        m = re.match(r'^(\d{2})$', line)
        if m:
            horse_nums_in_list.append(int(m.group(1)))

    print(f"  kin_list馬番順: {horse_nums_in_list}")

    if len(horse_nums_in_list) == len(tel_inputs):
        for horse_num, inp in zip(horse_nums_in_list, tel_inputs):
            amount = bet_map.get(horse_num, 0)
            amount_100 = amount // 100
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            print(f"  {horse_num}番: {amount_100}（¥{amount:,}）")
            await page.wait_for_timeout(200)
    else:
        print(f"  フォールバック: 馬番順ソートで入力")
        bets_sorted = sorted(bets, key=lambda b: b['num'])
        for bet, inp in zip(bets_sorted, tel_inputs):
            amount_100 = bet['amount'] // 100
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            print(f"  {bet['num']}番: {amount_100}（¥{bet['amount']:,}）")
            await page.wait_for_timeout(200)

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

    print(f"合計金額 ¥{total} 入力...")
    all_tels2 = await page.query_selector_all('input[type="tel"]')
    for inp in all_tels2:
        if await inp.is_visible():
            await inp.fill(str(total))
            print("  合計金額入力OK")
            break

    await page.screenshot(path="ipat_fuku_confirm.png")

    if DRY_RUN:
        print("\n========== DRY RUN MODE ==========")
        print(f"[テスト] 以下の内容で投票する直前です（実際には投票しません）")
        for b in bets:
            print(f"  {b['num']}番 {b['name']} 複勝 ¥{b['amount']:,}")
        print(f"  合計: ¥{sum(b['amount'] for b in bets):,}")
        print("===================================")
        print("✅ DRY RUN完了（投票は行いませんでした）")
        return True

    async def handle_dialog(dialog):
        try:
            print(f"  ダイアログ: {dialog.message}")
            await dialog.accept()
        except Exception:
            pass
    page.on('dialog', handle_dialog)

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
    await page.wait_for_timeout(4000)

    await page.screenshot(path="ipat_fuku_result.png")
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
    if isinstance(BETS, dict):
        BETS = [BETS]
    if not COURSE_NAME:
        COURSE_NAME = "東京(土)"
        RACE_NUM = 1
        BETS = [{"num": 3, "amount": 100}, {"num": 5, "amount": 100}]

    print(f"=== IPAT自動購入（複勝）===")
    print(f"会場: {COURSE_NAME} {RACE_NUM}R")
    print(f"買い目: {BETS}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)

        await login(page)

        if AUTO_BUY_MODE and BETS and 'norm' in BETS[0]:
            print("\n自動購入モード: 残高取得→ハーフケリー計算")
            bankroll = await get_balance(page)
            BETS = calc_kelly_amounts(BETS, bankroll)
            print("再ログイン中...")
            await login(page)
            print("再ログイン完了")
        else:
            print("購入ボタンモード: PWAの金額をそのまま使用")

        if AUTO_BUY_MAX > 0:
            total = sum(b['amount'] for b in BETS)
            if total > AUTO_BUY_MAX:
                ratio = AUTO_BUY_MAX / total
                for b in BETS:
                    b['amount'] = max(int(b['amount'] * ratio / 100) * 100, 100)
                new_total = sum(b['amount'] for b in BETS)
                print(f"最大投資額キャップ: ¥{total:,} → ¥{new_total:,} (上限¥{AUTO_BUY_MAX:,})")

        result = await purchase(page, COURSE_NAME, RACE_NUM, BETS)

        await browser.close()
        return result

if __name__ == "__main__":
    asyncio.run(main())
