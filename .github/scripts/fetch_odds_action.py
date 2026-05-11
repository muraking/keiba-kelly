“””
SPAT4 オッズ取得（GitHub Actions用・毎回ログイン方式）
Cookieを使わず毎回ログインするため期限切れ問題なし
“””
import asyncio, os, json, re, sys, requests, base64
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

SPAT4_MEMBERNUM = os.environ.get(“SPAT4_MEMBERNUM”, “”)
SPAT4_PASS      = os.environ.get(“SPAT4_PASS”, “”)
GH_TOKEN        = os.environ.get(“GH_TOKEN”, “”)
GH_USER   = “muraking”
GH_REPO   = “keiba-kelly”
GH_BRANCH = “main”
GH_FILE   = “data/indices.json”
PLACE_ID  = os.environ.get(“PLACE_ID”, “”)
RACE_NUM  = int(os.environ.get(“RACE_NUM”, “1”))
RACE_DATE = os.environ.get(“RACE_DATE”, “”)
TODAY_JST = os.environ.get(“TODAY_JST”, “”)
LOGIN_URL = “https://www.spat4.jp/keiba/pc?C_SPHONE=off”
TIMEOUT   = 60000

def now_jst():
return datetime.now(timezone(timedelta(hours=9)))

async def login(page):
“”“SPAT4にログインしてwww2セッションを確立”””
await page.goto(LOGIN_URL, wait_until=“domcontentloaded”, timeout=TIMEOUT)
await page.wait_for_timeout(5000)
await page.fill(‘input[name=“MEMBERNUMR”]’, SPAT4_MEMBERNUM)
await page.fill(‘input[name=“MEMBERIDR”]’, SPAT4_PASS)
print(“入力完了”)

```
# フォームsubmit
try:
    async with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
        await page.evaluate("""
            () => {
                for(const form of document.querySelectorAll('form')){
                    if(form.querySelector('[name="MEMBERNUMR"]')){
                        form.submit(); return;
                    }
                }
            }
        """)
    await page.wait_for_timeout(3000)
except Exception as e:
    print(f"ナビゲーション: {e}")

print(f"ログイン後URL: {page.url}")
return True
```

async def get_odds(page, place_id, race_num, race_date):
“”“ログイン済みのwww2セッションでオッズ取得”””
# www2.spat4.jpでオッズページにアクセス
base = page.url.replace(“https://www.spat4.jp”, “https://www2.spat4.jp”)
if “www2” not in page.url:
base = “https://www2.spat4.jp”

```
# ログイン後のドメインを使用（www2 or www3など）
from urllib.parse import urlparse
parsed = urlparse(page.url)
base_domain = f"{parsed.scheme}://{parsed.netloc}"
url = f"{base_domain}/keiba/pc?HANDLERR=P120S&RACEDAYR={race_date}&PLACEIDR={place_id}&RACER={race_num}"
print(f"オッズURL: {url}")
await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
await page.wait_for_timeout(8000)
print(f"現在URL: {page.url}")

# セッション切れ確認
text = await page.evaluate("() => document.body ? document.body.innerText : ''")
if 'ログイン' in text[:50] or 'エラー' in text[:50]:
    print(f"セッション切れ: {text[:100]}")
    return None

# iframeのsrcを取得してP122Sを探す
iframes = await page.evaluate("""
    () => Array.from(document.querySelectorAll('iframe,frame')).map(f=>({src:f.src,name:f.name}))
""")
print(f"iframe: {iframes}")

# P122SのURLを直接取得
p122s_url = None
for iframe in iframes:
    if 'P122S' in iframe.get('src', ''):
        p122s_url = iframe['src']
        break

if p122s_url:
    # P122Sページに直接アクセスしてオッズ取得
    print(f"P122S直接アクセス: {p122s_url}")
    p122s_page = await page.context.new_page()
    await p122s_page.goto(p122s_url, wait_until="domcontentloaded", timeout=TIMEOUT)
    await p122s_page.wait_for_timeout(3000)
    body = await p122s_page.evaluate("() => document.body ? document.body.innerText : ''")
    await p122s_page.close()
    result = parse_odds(body)
    if result:
        return result

# フォールバック: page.framesから探す
target_frame = None
for attempt in range(3):
    for frame in page.frames:
        if 'P122S' in frame.url:
            target_frame = frame
            break
    if target_frame:
        break
    await page.wait_for_timeout(3000)

if target_frame:
    body = await target_frame.evaluate("() => document.body ? document.body.innerText : ''")
    return parse_odds(body)

print("P122Sなし → メインページからパース")
return parse_odds(text)
```

def parse_odds(text):
result = {}
for line in text.split(’\n’):
parts = re.split(r’\s{2,}|\t’, line.strip())
parts = [p.strip().replace(’,’,’’) for p in parts if p.strip()]
nums, tan, fuku = [], None, None
for p in parts:
if re.match(r’^\d{1,2}$’, p) and 1 <= int(p) <= 18:
nums.append(int(p))
elif re.match(r’^\d+.\d+$’, p):
v = float(p)
if 1.0 <= v < 9999.9 and tan is None: tan = v
elif re.match(r’^\d+.?\d*-\d+.?\d*$’, p):
fuku = p
elif re.match(r’^\d{3,}$’, p):
v = float(p)
if 1.0 <= v < 9999 and tan is None: tan = v
num = nums[1] if len(nums) >= 2 else (nums[0] if nums else None)
if not num or (tan is None and fuku is None): continue
if num not in result:
e = {}
if tan: e[“tan”] = tan
if fuku:
fp = fuku.split(”-”)
try:
fmin = float(fp[0])
if fmin > 0:
e[“fuku_min”] = fmin
if len(fp) > 1: e[“fuku_max”] = float(fp[1])
except: pass
result[num] = e
return result

def save_to_github(place_id, race_num, odds, today_jst):
api_url = f”https://api.github.com/repos/{GH_USER}/{GH_REPO}/contents/{GH_FILE}”
headers = {“Authorization”: f”token {GH_TOKEN}”, “Accept”: “application/vnd.github.v3+json”}
for attempt in range(3):
r = requests.get(api_url, headers=headers)
if not r.ok: return False
sha = r.json()[“sha”]
data = json.loads(base64.b64decode(r.json()[“content”].replace(”\n”,””)).decode())
if “dates” not in data: data[“dates”] = {}
if today_jst not in data[“dates”]: data[“dates”][today_jst] = {}
if “odds” not in data[“dates”][today_jst]: data[“dates”][today_jst][“odds”] = {}
if place_id not in data[“dates”][today_jst][“odds”]:
data[“dates”][today_jst][“odds”][place_id] = {}
data[“dates”][today_jst][“odds”][place_id][race_num] = odds
data[“dates”][today_jst][“odds_updated”] = now_jst().isoformat()
json_str = json.dumps(data, ensure_ascii=False, indent=2)
body = {
“message”: f”odds {place_id} {race_num}R {now_jst().strftime(’%H:%M’)}”,
“content”: base64.b64encode(json_str.encode()).decode(),
“sha”: sha, “branch”: GH_BRANCH
}
r2 = requests.put(api_url, headers=headers, json=body)
if r2.status_code in [200, 201]:
print(“GitHub保存成功”)
return True
if r2.status_code == 409:
continue
return False

async def main():
print(f”オッズ取得: PLACE_ID={PLACE_ID} RACE_NUM={RACE_NUM} DATE={RACE_DATE}”)
async with async_playwright() as p:
browser = await p.chromium.launch(headless=True)
page = await browser.new_page()
page.set_default_timeout(TIMEOUT)
await login(page)
odds = await get_odds(page, PLACE_ID, RACE_NUM, RACE_DATE)
await browser.close()
if not odds:
print(“オッズ取得失敗”)
sys.exit(1)
print(f”{len(odds)}頭取得成功”)
save_to_github(PLACE_ID, RACE_NUM, odds, TODAY_JST)

if **name** == “**main**”:
asyncio.run(main())