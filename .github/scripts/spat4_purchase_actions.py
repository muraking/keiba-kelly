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

    # 既存のpageでP122Sに直接アクセス（Cookieを引き継ぐ）
    await page.goto(p122s_url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(3000)
    content = await page.evaluate("() => document.body ? document.body.innerText : ''")
    print(f"P122S内容: {content[:80]}")
    if 'ログイン' in content[:80] or 'エラー' in content[:80]:
        print("P122Sセッション切れ")
        return False
    odds_frame = page

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
        if not clicked:
            print(f"  フレーム内容: {frame_text[:100]}")
            print(f"  フレームHTML: {frame_html[:200]}")

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

        # 金額入力欄をP122S・P121S両方から探す
        await page.wait_for_timeout(2000)
        input_found = False

        # まず全フレームを確認
        all_frames_info = [(f.url[-40:], ) for f in page.frames]
        print(f"  現在フレーム: {[f.url.split('HANDLERR=')[1].split('&')[0] if 'HANDLERR=' in f.url else f.url[-20:] for f in page.frames]}")

        for try_frame in page.frames:
            if 'P121S' in try_frame.url or 'P122S' in try_frame.url:
                try:
                    inputs = await try_frame.query_selector_all("input[type='text'], input[type='number']")
                    if inputs:
                        last_input = inputs[-1]
                        await last_input.fill(str(amount // 100))
                        print(f"  金額入力: {amount}円（{try_frame.url.split('HANDLERR=')[1].split('&')[0]}フレーム）")
                        input_found = True
                        break
                except Exception as e:
                    print(f"  フレームエラー: {e}")
                    continue

        if not input_found:
            print(f"  ⚠️ 金額入力欄が見つかりません")

    # "投票内容確認へ"ボタンをクリック
    print("\n投票内容確認へ...")
    await page.wait_for_timeout(1000)

    # P122Sフレーム内の"投票内容確認へ"ボタンをクリック
    confirmed = False
    # iframeのsrcからP122S URLを取得して直接操作
    iframes = await page.evaluate(
        "() => Array.from(document.querySelectorAll('iframe,frame')).map(f=>({src:f.src,name:f.name}))"
    )
    p122s_frame = None
    for frame in page.frames:
        if 'P122S' in frame.url:
            p122s_frame = frame
            break

    if p122s_frame:
        # フレーム内のボタンを探す
        btns = await p122s_frame.query_selector_all("input[type='submit'], input[type='button'], button, a")
        for btn in btns:
            value = await btn.get_attribute("value") or ""
            text = ""
            try: text = await btn.inner_text()
            except: pass
            if "投票内容確認" in value or "投票内容確認" in text:
                print(f"確認ボタン発見: {value or text}")
                async with page.expect_navigation(timeout=15000):
                    await btn.click()
                print("確認ページへ移動中...")
                await page.wait_for_timeout(3000)
                confirmed = True
                break

    if not confirmed:
        # フォールバック: 全フレームから探す
        for frame in page.frames:
            btns = await frame.query_selector_all("input, button, a")
            for btn in btns:
                value = await btn.get_attribute("value") or ""
                try:
                    text = await btn.inner_text()
                except:
                    text = ""
                if "投票内容確認" in value or "投票内容確認" in text:
                    try:
                        async with page.expect_navigation(timeout=15000):
                            await btn.click()
                        confirmed = True
                        break
                    except:
                        await btn.click()
                        await page.wait_for_timeout(5000)
                        confirmed = True
                        break
            if confirmed:
                break

    if not confirmed:
        print("「投票内容確認へ」ボタンが見つかりません")
        await page.screenshot(path="error_no_confirm_btn.png")
        return False

    # 確認ページ
    await page.screenshot(path="purchase_confirm.png")
    print(f"確認ページ: {page.url}")

    # 暗証番号入力
    print("暗証番号を入力中...")
    pin_input = None
    for frame in page.frames:
        inputs = await frame.query_selector_all("input[type='password'], input[type='text']")
        for inp in inputs:
            name = await inp.get_attribute("name") or ""
            placeholder = await inp.get_attribute("placeholder") or ""
            if "暗証" in name or "PIN" in name.upper() or "暗証" in placeholder:
                pin_input = inp
                break
        if pin_input:
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
    for frame in page.frames:
        btns = await frame.query_selector_all("input[type='submit'], button")
        for btn in btns:
            text = (await btn.inner_text()).strip() if await btn.inner_text() else ""
            value = await btn.get_attribute("value") or ""
            if "投票する" in text or "投票する" in value:
                vote_btn = btn
                break
        if vote_btn:
            break

    if vote_btn:
        print("「投票する」をクリック...")
        await vote_btn.click()
        await page.wait_for_timeout(5000)
        await page.screenshot(path="purchase_result.png")
        print("投票完了！purchase_result.png を確認してください")
        return True
    else:
        print("投票するボタンが見つかりません")
        await page.screenshot(path="error_no_vote_btn.png")
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