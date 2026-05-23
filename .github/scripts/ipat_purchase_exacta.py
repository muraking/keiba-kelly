"""
IPAT SP版 自動購入スクリプト（馬連）
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
    """jQuery tapでテキストリンクをクリック（jQuery Mobile対応）"""
    result = await page.evaluate(f"""
        () => {{
            // 全ページのリンクからテキスト一致を探す
            const links = document.querySelectorAll('a');
            for(const a of links) {{
                if(a.innerText.trim() === '{text}') {{
                    if(typeof $ !== 'undefined') {{
                        $(a).trigger('tap');
                        return 'jquery-tap';
                    }}
                    a.click();
                    return 'click';
                }}
            }}
            return false;
        }}
    """)
    if result:
        print(f"  '{text}': {result}")
        return True
    # フォールバック: page.click
    try:
        await page.click(f'text={text}')
        print(f"  '{text}': page.click OK")
        return True
    except Exception as e:
        print(f"  ⚠️ '{text}' が見つかりません: {e}")
        return False


async def check_horse(page, num):
    """フォーメーション画面で馬番をタップ
    jQuery Mobileで非アクティブページのDOMも残るため
    evaluate内でdisplay:blockにしてからクリック
    """
    result = await page.evaluate(f"""
        () => {{
            // #uma1または#uma2のa[data-value]を探す（非表示でもOK）
            const pages = ['#uma1','#uma2'];
            for(const pid of pages) {{
                const a = document.querySelector(pid + ' a[data-value="{num}"]');
                if(!a) continue;
                // 非表示の場合は一時的に表示
                const pg = document.querySelector(pid);
                const origDisplay = pg ? pg.style.display : '';
                const origVis = pg ? pg.style.visibility : '';
                if(pg) {{ pg.style.display='block'; pg.style.visibility='visible'; }}
                // jQuery tapで選択
                if(typeof $ !== 'undefined') {{
                    $(a).trigger('tap');
                    const cls = a.className;
                    return 'jquery-tap:' + cls;
                }}
                // フォールバック: touchstart+touchend
                const touch = new Touch({{
                    identifier: Date.now(), target: a,
                    clientX: 200, clientY: 300, screenX: 200, screenY: 300,
                    pageX: 200, pageY: 300, radiusX: 1, radiusY: 1, rotationAngle: 0, force: 1
                }});
                a.dispatchEvent(new TouchEvent('touchstart', {{
                    bubbles:true, cancelable:true,
                    touches:[touch], targetTouches:[touch], changedTouches:[touch]
                }}));
                a.dispatchEvent(new TouchEvent('touchend', {{
                    bubbles:true, cancelable:true,
                    touches:[], targetTouches:[], changedTouches:[touch]
                }}));
                return 'touch:' + a.className;
            }}
            return false;
        }}
    """)
    print(f"    {num}番: {result or 'NG'}")
    await page.wait_for_timeout(400)
    return bool(result)


async def check_combo(page, num1, num2):
    """オッズ選択画面で組み合わせをjQuery tapで選択
    #odse span.horseCombi に全角ハイフンで馬番が入る
    """
    n1, n2 = min(num1, num2), max(num1, num2)
    label = f"{n1:02d}\uff0d{n2:02d}"  # 全角ハイフン（－）

    result = await page.evaluate(f"""
        () => {{
            const labels = ['{n1:02d}\uff0d{n2:02d}', '{n1:02d}-{n2:02d}', '{n1}-{n2}'];
            // #odseページを一時的に表示
            const odse = document.querySelector('#odse');
            if(odse) {{ odse.style.display='block'; odse.style.visibility='visible'; }}
            const spans = document.querySelectorAll('#odse span.horseCombi');
            for(const sp of spans) {{
                const t = sp.innerText.trim();
                for(const lbl of labels) {{
                    if(t === lbl || t.replace(/\uff0d/g,'-') === lbl.replace(/\uff0d/g,'-')) {{
                        const a = sp.closest('a');
                        if(a && typeof $ !== 'undefined') {{
                            $(a).trigger('tap');
                            return 'jquery-tap:' + t + ' cls:' + a.className;
                        }}
                        const touch = new Touch({{
                            identifier: Date.now(), target: a,
                            clientX: 200, clientY: 300, screenX: 200, screenY: 300,
                            pageX: 200, pageY: 300, radiusX: 1, radiusY: 1, rotationAngle: 0, force: 1
                        }});
                        a.dispatchEvent(new TouchEvent('touchstart', {{
                            bubbles:true, cancelable:true,
                            touches:[touch], targetTouches:[touch], changedTouches:[touch]
                        }}));
                        a.dispatchEvent(new TouchEvent('touchend', {{
                            bubbles:true, cancelable:true,
                            touches:[], targetTouches:[], changedTouches:[touch]
                        }}));
                        return 'touch:' + t;
                    }}
                }}
            }}
            return 'not-found(total:' + spans.length + ')';
        }}
    """)
    print(f"    {n1:02d}-{n2:02d}: {result}")
    await page.wait_for_timeout(300)
    return result and 'not-found' not in result


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
    print(f"\n購入: {course_name} {race_num}R 馬連 合計¥{total:,}")
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
    await page.click('text=馬連')
    await page.wait_for_timeout(3000)  # 式別→馬連の画面遷移を待つ
    url1 = page.url
    print(f"式別→馬連 OK: {url1}")

    # ② フォーメーション選択（通常/ながし/ボックス/フォーメーション画面）
    page_text_f = await page.evaluate("() => document.body.innerText")
    print(f"  フォーメーション画面テキスト（先頭200文字）: {page_text_f[:200]}")
    await page.click('text=フォーメーション')
    await page.wait_for_timeout(3000)  # フォーメーション→1頭目選択の遷移を待つ
    url2 = page.url
    print(f"フォーメーション OK: {url2}")

    # ③ 1頭目（軸馬）チェック
    axis_nums    = list(dict.fromkeys([b['num1'] for b in bets]))
    partner_nums = list(dict.fromkeys([b['num2'] for b in bets]))
    await page.screenshot(path="ipat_exacta_uma1.png")
    # HTML構造確認（削除済み）
    print(f"1頭目チェック: {axis_nums}")
    for num in axis_nums:
        await check_horse(page, num)

    # 次へ（2頭目選択画面へ遷移）
    page_text_1 = await page.evaluate("() => document.body.innerText")
    print(f"  1頭目選択後テキスト（先頭200文字）: {page_text_1[:200]}")
    await click_text(page, '次へ')
    await page.wait_for_timeout(3000)
    url3 = page.url
    print(f"次へ OK: {url3}")

    # ④ 2頭目（相手馬）チェック
    page_text_2 = await page.evaluate("() => document.body.innerText")
    print(f"  2頭目選択画面テキスト（先頭200文字）: {page_text_2[:200]}")
    print(f"2頭目チェック: {partner_nums}")
    for num in partner_nums:
        await check_horse(page, num)

    # オッズ選択画面へ
    await click_text(page, 'オッズ選択画面へ')
    # #odseのhorseCombiが出現するまで最大10秒待機
    for _w in range(10):
        cnt = await page.evaluate("() => document.querySelectorAll('#odse span.horseCombi').length")
        if cnt > 0:
            print(f"  #odse horseCombi: {cnt}件 ({_w+1}秒待機)")
            break
        await page.wait_for_timeout(1000)
    else:
        print("  ⚠️ #odse horseCombi が出現しませんでした")
    url4 = page.url
    print(f"オッズ選択画面へ OK: {url4}")

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

    await page.screenshot(path="ipat_exacta_confirm.png")

    if DRY_RUN:
        print("\n========== DRY RUN MODE ==========")
        for b in bets:
            print(f"  {b['num1']:02d}-{b['num2']:02d} 馬連 ¥{b['amount']:,}")
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
