# JRA shadow通知サービス

Version: v2026.07.25.2

既存の本番指数と`keiba_ai.live_probs`を変更せず、血統・調教込みの独立指数と固定買いルールをDiscordへ通知する検証サービスです。`live_probs`のimport・起動・アーカイブ監視は行わず、自動購入もしません。

## 前日指数

既存`live_probs`の前日指数をJRAだけ生成します。Discordは既存の
`DISCORD_WEBHOOK7`、`DISCORD_WEBHOOK_PREDAY`、`DISCORD_WEBHOOK4`の優先順をそのまま使用します。

```powershell
python -X utf8 market_edge_research_20260723/scripts/jra_standalone_live.py `
  --mode preday --data-dir C:\keiba\data
```

送信せず確認する場合は`--dry-run`を追加します。

## 発走前shadow買い目

当日モードは単独で待機し、発走30分前と7分前を処理します。

```powershell
python -X utf8 market_edge_research_20260723/scripts/jra_standalone_live.py `
  --mode live --data-dir C:\keiba\data `
  --state C:\keiba\data\jra_standalone_live.json
```

処理順は、前日に全レース指数、発走30分前に実測馬体重で再計算、発走7分前に単勝オッズを取得して市場差と買い目を判定、です。

専用Discordには`JRA_STANDALONE_WEBHOOK`を設定します。未設定時は
`DISCORD_WEBHOOK7`、`DISCORD_WEBHOOK_PREDAY`の順にフォールバックします。
再起動時は保存済み状態を読み込み、送信済みの前日・30分前・7分前通知を重複送信しません。

## 馬体重

前日指数には使いません。当日は未取得なら「買い確定不可」と表示します。
将来、個体ごとの通常体重と当日増減を十分なOOS期間で検証してから、急変警告を追加します。
馬体重だけを理由に確率を手動補正することはしません。

## 固定ルール

- 三連複3点：10〜20倍、3〜6番人気、弱い1番人気、12頭以上
- AI純確率と市場確率の差2ポイント以上
- 相手は市場合成確率上位3頭、軸から2頭を選ぶ3点

条件外は`見`です。最終オッズではなく実取得時点のオッズでshadow成績を蓄積します。

## VPS自動起動

VPSには次のWindowsタスクを登録します。

- `KeibaKelly-JRA-Shadow-Live`：毎日8:30に単独`live`モードを起動
- `KeibaKelly-JRA-Shadow-Preday`：毎日18:30に翌日分の前日指数を通知

JRA非開催日は対象レースなしで終了します。
