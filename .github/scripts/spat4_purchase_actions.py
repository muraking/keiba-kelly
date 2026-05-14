"""
SPAT4 自動投票スクリプト
- 買い目リストをもとにSPAT4で単勝を自動購入
- GitHub Actionsから呼び出される
"""
import asyncio
from playwright.async_api import async_playwright
import json
import os
from datetime import date, timezone, timedelta
from datetime import datetime

# ===== 設定 =====
SPAT4_MEMBERNUM = os.environ.get("SPAT4_MEMBERNUM", "ここに加入者番号を入力")
SPAT4_PASS      = os.environ.get("SPAT4_PASS", "ここにパスワードを入力")
SPAT4_PIN       = os.environ.get("SPAT4_PIN", "ここに暗証番号(4桁)を入力")

# 環境変数から購入情報を取得（GitHub Actionsから渡される）
PLACE_ID  = os.environ.get("PLACE_ID", "19")
RACE_NUM  = int(os.environ.get("RACE_NUM", "1"))
RACE_DATE = os.environ.get("RACE_DATE", date.today().strftime("%Y%m%d"))
# BETS: [{"num": 1, "amount": 200}, {"num": 3, "amount": 300}]
BETS_JSON = os.environ.get("BETS", "[]")

LOGIN_URL = "https://www.spat4.jp/keiba/pc?C_SPHONE=off"
TIMEOUT   = 60000
# =================

async def goto(page, url):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
    except Exception as e:
        print(f"  goto警告: {e}")
    await page.wait_for_timeout(3000)

async def login(page):
    await goto(page, LOGIN_URL)
    await page.fill('input[name="MEMBERNUMR"]', SPAT4_MEMBERNUM)
    await page.fill('input[name="MEMBERIDR"]',  SPAT4_PASS)
    try:
        await page.click('input[type="submit"]')
    except Exception:
        await page.keyboard.press("Enter")
    await page.wait_for_timeout(5000)
    # ログイン後のリダイレクト先ドメインを使用
    base = "/".join(page.url.split("/")[:3])
    print(f"ログイン完了: {page.url}")
    print(f"ベースURL: {base}")
    return base

async def purchase(page, base, bets):
    """
    買い目リストでSPAT4に投票する
    bets: [{"num": 馬番, "amount": 金額}, ...]
    """
    # オッズページへ移動
    odds_url = f"{base}/keiba/pc?HANDLERR=P120S&RACEDAYR={RACE_DATE}&PLACEIDR={PLACE_ID}&RACER={RACE_NUM}"
    print(f"オッズページへ: {odds_url}")
    await goto(page, odds_url)

    # フレーム読み込みを最大3回待つ
    odds_frame = None
    vote_frame = None
    confirm_frame = None

    for attempt in range(3):
        for frame in page.frames:
            if "P122S" in frame.url:
                odds_frame = frame
            if "P121S" in frame.url:
                vote_frame = frame
        if odds_frame:
            break
        print(f"  フレーム待機中... ({attempt+1}/3) frames={[f.url[-30:] for f in page.frames]}")
        await page.wait_for_timeout(3000)

    # iframeのsrcからP122S URLを直接取得して新ページでアクセス
    iframes = await page.evaluate(
        "() => Array.from(document.querySelectorAll('iframe,frame')).map(f=>f.src)"
    )
    p122s_url = next((s for s in iframes if 'P122S' in s), None)
    if not p122s_url and odds_frame:
        p122s_url = odds_frame.url

    if not p122s_url:
        print("P122Sフレームが見つかりません")
        return False

    print(f"オッズフレーム: {p122s_url}")

    # P120Sページのフレームとしてアクセス（直接gotoしない）
    # odds_frameはすでにP120Sのフレームから取得済み
    if odds_frame:
        content = await odds_frame.evaluate("() => document.body ? document.body.innerText : ''")
        full_html = await odds_frame.evaluate("() => document.body ? document.body.innerHTML : ''")
        print(f"P122S内容: {content[:80]}")
        print(f"P122S HTML(3000): {full_html[:3000]}")
        if 'ログイン' in content[:80]:
            print("P122Sセッション切れ")
            return False
    else:
        print("P122Sフレームなし")
        return False

    # 各馬番の単勝オッズをクリックして選択
    for bet in bets:
        horse_num = bet["num"]
        amount = bet["amount"]
        print(f"\n{horse_num}番を選択中...")

        # P122Sフレームのデバッグ: ページ内容確認
        if not clicked if 'clicked' in dir() else True:
            pass
        clicked = False

        # まずフレームのHTMLを確認してセレクターを特定
        frame_text = await odds_frame.evaluate("() => document.body ? document.body.innerText : ''")
        frame_html = await odds_frame.evaluate("() => document.body ? document.body.innerHTML.substring(0,500) : ''")
        # 常にHTML構造を出力して確認
        print(f"  フレームHTML先頭: {frame_html[:300]}")
        v_url_val = await odds_frame.evaluate("() => document.getElementById('_v_url')?.value || 'none'")
        print(f"  フレーム_v_url: {v_url_val}")
        if not clicked:
            print(f"  フレーム内容: {frame_text[:100]}")

        # 方法1: テーブル行から馬番を探す
        rows = await odds_frame.query_selector_all("tr")
        for row in rows:
            cells = await row.query_selector_all("td")
            texts = [(await c.inner_text()).strip() for c in cells]
            nums = [t for t in texts if t == str(horse_num) or t == f"{horse_num:02d}"]
            if nums:
                links = await row.query_selector_all("a")
                if links:
                    await links[0].click()
                    print(f"  {horse_num}番 単勝クリック完了（tr/td方式）")
                    clicked = True
                    break

        # 方法2: aタグのテキストから馬番を探す
        if not clicked:
            links = await odds_frame.query_selector_all("a")
            for link in links:
                t = (await link.inner_text()).strip()
                if t == str(horse_num) or t == f"{horse_num:02d}" or t.startswith(f"{horse_num:02d}"):
                    await link.click()
                    print(f"  {horse_num}番 単勝クリック完了（aタグ方式）")
                    clicked = True
                    break

        # 方法3: input[value]から探す
        if not clicked:
            inputs = await odds_frame.query_selector_all("input")
            for inp in inputs:
                val = await inp.get_attribute("value") or ""
                if val == str(horse_num) or val == f"{horse_num:02d}":
                    await inp.click()
                    print(f"  {horse_num}番 単勝クリック完了（input方式）")
                    clicked = True
                    break
                    clicked = True
                    await page.wait_for_timeout(1000)
                    break

        if not clicked:
            print(f"  {horse_num}番が見つかりません")
            continue

        # 投票フレームを再取得
        await page.wait_for_timeout(1500)
        for frame in page.frames:
            if "P121S" in frame.url:
                vote_frame = frame
                break

        if not vote_frame:
            print("  投票フレームが見つかりません")
            continue



        # 金額入力欄をP121Sから探す（TEXTMONEY_N形式）
        await page.wait_for_timeout(1000)
        input_found = False

        for try_frame in page.frames:
            if "P121S" in try_frame.url:
                try:
                    # TEXTMONEY_N の入力欄を探す（馬番ごとに1つずつ追加される）
                    money_inputs = await try_frame.query_selector_all("input[name^='TEXTMONEY']")
                    if money_inputs:
                        # 最後のTEXTMONEY入力欄に金額入力
                        last = money_inputs[-1]
                        iname = await last.get_attribute('name')
                        val_str = str(amount // 100)
                        # JavaScriptで直接値をセット
                        await try_frame.evaluate(
                            f"() => {{ const el = document.querySelector('input[name={iname}]'); if(el){{ el.value='{val_str}'; el.dispatchEvent(new Event('change')); el.dispatchEvent(new Event('input')); }} }}"
                        )
                        await page.wait_for_timeout(300)
                        val = await last.evaluate("el => el.value")
                        print(f"  金額入力: {amount}円 → name={iname} val={val}")
                        input_found = True
                except Exception as e:
                    print(f"  エラー: {e}")
                break

        if not input_found:
            print(f"  ⚠️ 金額入力欄が見つかりません")


    # "投票内容確認へ"ボタンをクリック
    print("\n投票内容確認へ...")
    await page.wait_for_timeout(1000)

    # 全フレームから「投票内容確認へ」ボタンを探す（P121S優先）
    confirmed = False
    await page.wait_for_timeout(2000)

    # フレーム優先順位: P121S → P122S → その他
    search_frames = sorted(page.frames, key=lambda f: (0 if 'P121S' in f.url else 1 if 'P122S' in f.url else 2))

    for frame in search_frames:
        try:
            btns = await frame.query_selector_all("input, button, a")
            for btn in btns:
                value = await btn.get_attribute("value") or ""
                text = ""
                try: text = await btn.inner_text()
                except: pass
                if "投票内容確認" in value or "投票内容確認" in text:
                    fname = frame.url.split('HANDLERR=')[1].split('&')[0] if 'HANDLERR=' in frame.url else 'unknown'
                    print(f"確認ボタン発見: {value or text}（{fname}フレーム）")
                    try:
                        async with page.expect_navigation(timeout=15000):
                            await btn.click()
                    except:
                        await btn.click()
                        await page.wait_for_timeout(5000)
                    print("確認ページへ移動中...")
                    # P121Sのフレームが暗証番号入力画面に変わるまで待つ
                    for wait_i in range(10):
                        await page.wait_for_timeout(2000)
                        # 全フレームのv_urlを確認
                        for chk_frame in page.frames:
                            try:
                                chk_v = await chk_frame.evaluate("() => document.getElementById('_v_url')?.value || ''")
                                if chk_v and '/pc/err' not in chk_v and '/pc/od' not in chk_v:
                                    print(f"  新フレーム検知: {chk_v} ({chk_frame.url.split('HANDLERR=')[1].split('&')[0] if 'HANDLERR=' in chk_frame.url else '?'})")
                            except: pass
                        # P121Sの内容確認
                        for chk_frame in page.frames:
                            if 'P121S' in chk_frame.url:
                                try:
                                    p121_txt = await chk_frame.evaluate("() => document.body ? document.body.innerText.substring(0,50) : ''")
                                    print(f"  P121S内容({wait_i+1}): {p121_txt}")
                                    if '暗証' in p121_txt or 'PIN' in p121_txt or '確認' in p121_txt:
                                        print("  暗証番号画面に遷移確認")
                                        break
                                except: pass
                        else:
                            continue
                        break
                    confirmed = True
                    break
        except Exception as e:
            print(f"フレームエラー: {e}")
            continue
        if confirmed:
            break

    if not confirmed:
        print("「投票内容確認へ」ボタンが見つかりません")
        await page.screenshot(path="error_no_confirm_btn.png")
        return False

    # 確認ページ
    await page.screenshot(path="purchase_confirm.png")
    print(f"確認ページ: {page.url}")

    # 確認ページのフレーム状態を確認してから暗証番号入力
    print("暗証番号を入力中...")
    await page.wait_for_timeout(3000)
    
    # 全フレームの内容を確認
    for frame in page.frames:
        fname = frame.url.split('HANDLERR=')[1].split('&')[0] if 'HANDLERR=' in frame.url else frame.url[-20:]
        try:
            ftxt = await frame.evaluate("() => document.body ? document.body.innerText.substring(0,100) : ''")
            finputs = await frame.query_selector_all("input")
            input_types = []
            for inp in finputs:
                t = await inp.get_attribute("type") or "text"
                n = await inp.get_attribute("name") or ""
                input_types.append(f"{t}:{n}")
            print(f"  フレーム{fname}: {ftxt[:50]} inputs={input_types[:5]}")
        except: pass

    # 全フレームのinput状況を再確認
    print("確認後フレーム状況:")
    for frame in page.frames:
        fname = frame.url.split('HANDLERR=')[1].split('&')[0] if 'HANDLERR=' in frame.url else '?'
        try:
            v = await frame.evaluate("() => document.getElementById('_v_url')?.value || ''")
            txt = await frame.evaluate("() => document.body ? document.body.innerText.substring(0,60) : ''")
            inps = await frame.query_selector_all("input")
            ilist = []
            for inp in inps:
                t = await inp.get_attribute("type") or "text"
                n = await inp.get_attribute("name") or ""
                ilist.append(f"{t}:{n}")
            print(f"  {fname} v_url={v} inputs={ilist[:6]}")
            if txt.strip():
                print(f"    内容: {txt[:60]}")
        except: pass

    pin_input = None
    pin_frame = None
    for frame in page.frames:
        inputs = await frame.query_selector_all("input[type='password'], input[type='text'], input[type='number']")
        for inp in inputs:
            name = (await inp.get_attribute("name") or "").upper()
            placeholder = await inp.get_attribute("placeholder") or ""
            id_attr = (await inp.get_attribute("id") or "").upper()
            if any(k in name for k in ["暗証","PIN","ANSHO","PASS","ANSHOU"]) or                any(k in id_attr for k in ["暗証","PIN","ANSHO","PASS"]) or                "暗証" in placeholder:
                pin_input = inp
                pin_frame = frame
                break
        if pin_input:
            break

    # 見つからない場合: 数字4桁入力欄を探す
    if not pin_input:
        for frame in page.frames:
            inputs = await frame.query_selector_all("input[maxlength='4'], input[size='4']")
            if inputs:
                pin_input = inputs[0]
                pin_frame = frame
                print(f"  maxlength=4のinputをPINとして使用")
                break

    # 暗証番号欄が見つからない場合は最初のテキスト入力を試す
    if not pin_input:
        for frame in page.frames:
            inputs = await frame.query_selector_all("input")
            for inp in inputs:
                type_ = await inp.get_attribute("type") or "text"
                if type_ in ["text", "password", "tel", "number"]:
                    pin_input = inp
                    break
            if pin_input:
                break

    if pin_input:
        await pin_input.fill(SPAT4_PIN)
        print("暗証番号入力完了")
    else:
        print("暗証番号入力欄が見つかりません")
        await page.screenshot(path="error_no_pin.png")
        return False

    # 合計金額入力
    total = sum(b["amount"] for b in bets)
    print(f"合計金額入力: {total}円")
    amount_inputs = []
    for frame in page.frames:
        inputs = await frame.query_selector_all("input")
        for inp in inputs:
            type_ = await inp.get_attribute("type") or "text"
            if type_ in ["text", "number"]:
                amount_inputs.append(inp)

    if len(amount_inputs) >= 2:
        await amount_inputs[-1].fill(str(total))
        print("合計金額入力完了")


    # "投票する"ボタンをクリック
    vote_btn = None
    print("投票ボタン検索:")
    for frame in page.frames:
        fname = frame.url.split("HANDLERR=")[1].split("&")[0] if "HANDLERR=" in frame.url else "?"
        try:
            btns = await frame.query_selector_all("input, button, a")
            btn_list = []
            for btn in btns:
                text = ""
                try: text = (await btn.inner_text()).strip()
                except: pass
                value = await btn.get_attribute("value") or ""
                btype = await btn.get_attribute("type") or ""
                if text or value:
                    btn_list.append(f"{btype}:{value}:{text[:10]}")
                if any(k in text or k in value for k in ["投票する","投　票","投票実行","VOTE"]):
                    vote_btn = btn
                    print(f"  投票ボタン発見({fname}): {value or text}")
                    break
            print(f"  {fname} buttons: {btn_list[:8]}")
        except Exception as e:
            print(f"  {fname}: error {e}")
        if vote_btn:
            break

    if vote_btn:
        print("「投票する」をクリック...")
        try:
            async with page.expect_navigation(timeout=15000):
                await vote_btn.click()
        except:
            await vote_btn.click()
            await page.wait_for_timeout(5000)
        print(f"投票後URL: {page.url}")
        # 受付番号を確認
        for frame in page.frames:
            try:
                txt = await frame.evaluate("() => document.body ? document.body.innerText : ''")
                if '受付' in txt or '完了' in txt or '番号' in txt:
                    print(f"✅ 投票完了: {txt[:100]}")
                    return True
            except: pass
        print("投票完了（受付確認できず）")
        return True
    else:
        print("投票するボタンが見つかりません")
        return False

async def main():
    bets = json.loads(BETS_JSON)
    if not bets:
        print("買い目がありません")
        return

    JST = timezone(timedelta(hours=9))
    print(f"=== SPAT4 自動投票 {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"場所: {PLACE_ID} / レース: {RACE_NUM}R / 日付: {RACE_DATE}")
    print(f"買い目: {bets}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)

        base = await login(page)
        result = await purchase(page, base, bets)

        if result:
            print("\n✅ 投票成功")
        else:
            print("\n❌ 投票失敗")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())