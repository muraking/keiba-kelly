# JRA shadow通知サービス

Version: v2026.07.24.2

既存の本番指数と`keiba_ai.live_probs`を変更せず、前日指数と発走前の固定買いルールをDiscordへ通知する検証サービスです。自動購入は行いません。`run`モードでは必要な指数生成エンジンを子プロセスとして自動起動するため、利用者が`live_probs`を別に起動しておく必要はありません。

## 前日指数

既存`live_probs`の前日指数をJRAだけ生成します。Discordは既存の
`DISCORD_WEBHOOK7`、`DISCORD_WEBHOOK_PREDAY`、`DISCORD_WEBHOOK4`の優先順をそのまま使用します。

```powershell
python -X utf8 market_edge_research_20260723/scripts/jra_shadow_service.py `
  --mode preday --workdir C:\keiba
```

送信せず確認する場合は`--dry-run`を追加します。

## 発走前shadow買い目

通常は次の`run`モードを使います。JRAだけの指数生成エンジンを自動起動し、通常のDiscord通知を抑止したうえで、shadowサービスの判定だけを送信します。

```powershell
python -X utf8 market_edge_research_20260723/scripts/jra_shadow_service.py `
  --mode run --workdir C:\keiba --data-dir C:\keiba\data `
  --state C:\keiba\data\jra_shadow_state.json
```

すでに別のプロセスがライブアーカイブを生成している場合だけ、`--mode watch`を使用します。

買い目専用Discordには`DISCORD_WEBHOOK_JRA_SHADOW`を設定します。未設定時は
`DISCORD_WEBHOOK7`、`DISCORD_WEBHOOK_PREDAY`の順にフォールバックします。

## 馬体重

前日指数には使いません。当日は未取得なら「買い確定不可」と表示します。
将来、個体ごとの通常体重と当日増減を十分なOOS期間で検証してから、急変警告を追加します。
馬体重だけを理由に確率を手動補正することはしません。

## 固定ルール

- 単勝1点：8〜15倍、3〜6番人気、弱い1番人気、市場比1.20以上
- ワイド2点：10〜20倍、3〜6番人気、弱い1番人気、市場比1.20以上
- 三連複3点：5〜10倍、4〜10番人気、12頭以上、市場比1.20以上

条件外は`見`です。最終オッズではなく実取得時点のオッズでshadow成績を蓄積します。

## VPS自動起動

VPSには次のWindowsタスクを登録します。

- `KeibaKelly-JRA-Shadow-Live`：毎日8:30に単独`run`モードを起動
- `KeibaKelly-JRA-Shadow-Preday`：毎日18:30に翌日分の前日指数を通知

JRA非開催日は対象レースなしで終了します。
