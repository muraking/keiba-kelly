"""
IPAT SP版 自動購入スクリプト（複勝専用）
"""
import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

IPAT_ID   = os.environ.get("IPAT_ID", "")
IPAT_PIN  = os.environ.get("IPAT_PIN", "")
IPAT_PARS = os.environ.get("IPAT_PARS", "")

COURSE_NAME  = os.environ.get("COURSE_NAME", "")
RACE_NUM     = int(os.environ.get("RACE_NUM", "1"))
BETS         = json.loads(os.environ.get("BETS", "[]"))
AUTO_BUY_MAX = int(os.environ.get("AUTO_BUY_MAX", "0") or "0")
AUTO_BUY_MODE = os.environ.get("AUTO_BUY_MODE", "0") == "1"
DRY_RUN      = os.environ.get("DRY_RUN", "0") == "1"

LOGIN_URL = "https://www.ipat.jra.go.jp/sp/"
TIMEOUT   = 30000


async def get_balance(page):
    try:
        text = await page.evaluate("() => document.body.innerText")
        for pattern in [r'購入限度額[\s\n]*([\d,]+)', r'残高[：:　\s]*([\d,]+)']:
            m = re.search(pattern, text)
            if m:
                v = int(m.group(1).replace(',', ''))
                if 100 <= v <= 10000000:
                    print(f"残高取得: ¥{v:,}")
                    return v
        print("残高取得失敗 → デフォルト10000円")
        return 10000
    except Exception as e:
        print(f"残高取得エラー: {e}")
        return 10000


def calc_kelly_amounts(bets, bankroll, kelly_fraction=0.5, min_amount=100, unit=100):
    result = []
    for bet in bets:
        p = bet.get('norm', 0)
        odds = bet.get('odds', 1.0)
        b = odds - 1.0
        if p <= 0 or b <= 0:
            amount = min_amount
        else:
            kelly = max(0, (b * p - (1 - p)) / b)
            amount = max(int(bankroll * kelly * kelly_fraction / unit) * unit, min_amount)
        result.append({**bet, 'amount': amount})
        print(f"  {bet['num']}番: ¥{amount:,}")
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
    # bet_typeがtanのもののみ（fukuは別スクリプトで処理）
    tan_bets = [b for b in bets if b.get('bet_type') == 'fuku']
    if not tan_bets:
        print("単勝買い目なし → スキップ")
        return True

    total = sum(b['amount'] for b in tan_bets)
    print(f"\n購入: {course_name} {race_num}R 複勝合計¥{total:,}")
    for b in tan_bets:
        print(f"  {b['num']}番 ¥{b['amount']:,}")

    await page.click('text=オッズ投票')
    await page.wait_for_timeout(2000)

    page_text = await page.evaluate("() => document.body.innerText")
    print(f"会場ページ内容（先頭200文字）: {page_text[:200]}")

    course_base = course_name.split('(')[0].strip()
    click_name = course_name if course_name in page_text else (course_base if course_base in page_text else course_name)
    if click_name != course_name:
        print(f"コース名変換: {course_name} → {click_name}")

    await page.click(f'text={click_name}')
    await page.wait_for_timeout(2000)
    await page.click(f'text={race_num}R')
    await page.wait_for_timeout(2000)
    await page.click('text=式別から選択')
    await page.wait_for_timeout(2000)
    await page.click('text=複勝')
    await page.wait_for_timeout(2000)
    print("複勝オッズ画面 OK")

    # 馬番選択
    print("馬番選択...")
    for bet in tan_bets:
        num = bet['num']
        data_val = 1000 + (num - 1)
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
    print(f"  選択件数: {count}")

    if count == '0' or count == '不明':
        print("  フォールバック: tap()で選択...")
        for bet in tan_bets:
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

    # 金額入力画面へ
    print("金額入力画面へ...")
    kin_btn = await page.query_selector('#odse a:has-text("金額入力画面へ")')
    if not kin_btn:
        links = await page.query_selector_all('a')
        for link in links:
            if (await link.inner_text()).strip() == '金額入力画面へ':
                kin_btn = link
                break
    if kin_btn:
        await kin_btn.tap()
        print("  tap() OK")

    await page.wait_for_selector('#kin', state='visible', timeout=10000)
    print("#kin 表示OK")

    # 金額入力
    tel_inputs = await page.query_selector_all('#kin_list input[type="tel"], #kin input[type="tel"]')
    kin_text = await page.evaluate("() => document.querySelector('#kin_list')?.innerText || ''")
    print(f"  kin_list: {kin_text[:100]}")

    horse_nums = []
    for line in kin_text.split("\n"):
        m = re.match(r'^(\d{2})$', line.strip())
        if m:
            horse_nums.append(int(m.group(1)))
    print(f"  馬番順: {horse_nums}")

    bet_map = {b['num']: b['amount'] for b in tan_bets}
    if len(horse_nums) == len(tel_inputs):
        for num, inp in zip(horse_nums, tel_inputs):
            amount_100 = bet_map.get(num, 0) // 100
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            print(f"  {num}番: {amount_100}×100=¥{amount_100*100:,}")
            await page.wait_for_timeout(200)
    else:
        for bet, inp in zip(sorted(tan_bets, key=lambda b: b['num']), tel_inputs):
            amount_100 = bet['amount'] // 100
            await inp.fill(str(amount_100))
            await inp.dispatch_event('change')
            print(f"  {bet['num']}番: {amount_100}×100=¥{bet['amount']:,}")
            await page.wait_for_timeout(200)

    # 入力終了
    end_btn = None
    for link in await page.query_selector_all('a'):
        if (await link.inner_text()).strip() == '入力終了':
            end_btn = link
            break
    if end_btn:
        await end_btn.tap()
        print("入力終了 tap() OK")
    await page.wait_for_timeout(3000)

    # 合計金額入力
    for inp in await page.query_selector_all('input[type="tel"]'):
        if await inp.is_visible():
            await inp.fill(str(total))
            print(f"合計金額入力: ¥{total:,}")
            break

    await page.screenshot(path="ipat_fuku_confirm.png")

    if DRY_RUN:
        print(f"\n===== DRY RUN =====")
        for b in tan_bets:
            print(f"  {b['num']}番 複勝 ¥{b['amount']:,}")
        print(f"  合計: ¥{total:,}")
        print("✅ DRY RUN完了（投票しませんでした）")
        return True

    async def handle_dialog(dialog):
        try:
            await dialog.accept()
        except Exception:
            pass
    page.on('dialog', handle_dialog)

    vote_btn = None
    for link in await page.query_selector_all('a'):
        if (await link.inner_text()).strip() == '投票':
            vote_btn = link
            break
    if vote_btn:
        await vote_btn.tap()
        print("投票 tap() OK")
    await page.wait_for_timeout(4000)

    await page.screenshot(path="ipat_fuku_result.png")
    text = await page.evaluate("() => document.body.innerText")
    for line in [l.strip() for l in text.split('\n') if l.strip()][:15]:
        print(f"  {line}")

    success = '受付番号' in text or 'ありがとう' in text
    print(f"\n{'✅ 投票完了！' if success else '⚠️ 投票結果不明'}")
    return success


async def main():
    global BETS
    if isinstance(BETS, dict):
        BETS = [BETS]

    print(f"=== IPAT自動購入（複勝）===")
    print(f"会場: {COURSE_NAME} {RACE_NUM}R")
    print(f"買い目: {BETS}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(has_touch=True, viewport={'width': 390, 'height': 844})
        page = await context.new_page()
        page.set_default_timeout(TIMEOUT)

        await login(page)

        if AUTO_BUY_MODE and BETS and 'norm' in BETS[0]:
            print("自動購入モード: 残高取得→ハーフケリー計算")
            bankroll = await get_balance(page)
            BETS = calc_kelly_amounts(BETS, bankroll)
            await login(page)
        else:
            print("PWAの金額をそのまま使用")

        if AUTO_BUY_MAX > 0:
            total = sum(b['amount'] for b in BETS)
            if total > AUTO_BUY_MAX:
                ratio = AUTO_BUY_MAX / total
                for b in BETS:
                    b['amount'] = max(int(b['amount'] * ratio / 100) * 100, 100)
                print(f"最大投資額キャップ適用: ¥{sum(b['amount'] for b in BETS):,}")

        result = await purchase(page, COURSE_NAME, RACE_NUM, BETS)
        await browser.close()
        return result

if __name__ == "__main__":
    asyncio.run(main())
