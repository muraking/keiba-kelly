# JRA shadow通知サービス

Version: v2026.07.24.1

既存の本番指数と`keiba_ai.live_probs`を変更せず、前日指数と発走前の固定買いルールをDiscordへ通知する検証サービスです。自動購入は行いません。

## 前日指数

既存`live_probs`の前日指数をJRAだけ生成します。Discordは既存の
`DISCORD_WEBHOOK7`、`DISCORD_WEBHOOK_PREDAY`、`DISCORD_WEBHOOK4`の優先順をそのまま使用します。

```powershell
python -X utf8 market_edge_research_20260723/scripts/jra_shadow_service.py `
  --mode preday --workdir C:\keiba
```

送信せず確認する場合は`--dry-run`を追加します。

## 発走前shadow買い目

既存`live_probs`が発走前に保存する`ai_live_archive_YYYY_MM.json`を監視します。

```powershell
python -X utf8 market_edge_research_20260723/scripts/jra_shadow_service.py `
  --mode watch --data-dir C:\keiba\data `
  --state C:\keiba\data\jra_shadow_state.json
```

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
