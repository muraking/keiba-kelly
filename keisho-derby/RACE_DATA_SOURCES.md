# 2026 race data sources

- JRA racecourse course data: https://www.jra.go.jp/facilities/
- JRA race class and earned-money rules: https://www.jra.go.jp/keiba/rules/class.html

- JRA開催日割・重賞: https://www.jra.go.jp/news/202509/092201.html
- JRA 2026重賞一覧: https://www.jra.go.jp/datafile/seiseki/replay/2026/jyusyo.html
- NAR 2026ダートグレード一覧: https://www.keiba.go.jp/dirtgraderace/2026/racelist/index.html
- NAR競馬場コース一覧: https://www.keiba.go.jp/guide/course/

`scripts/build-official-races.mjs` がJRA平地重賞と地方開催ダートグレードを
`race-program-2026.js`へ変換する。障害競走は障害能力・障害レース画面が未実装のため除外する。

ゲーム内は1か月4週制なので、公式開催日を同月内の第1〜4週へ変換する。
元の日付は `officialDate` として保持し、レース選択画面に表示する。
# コースレイアウト

- JRA公式「競馬場・コース紹介」 https://www.jra.go.jp/facilities/index.html
- 地方競馬全国協会「コース一覧」 https://www.keiba.go.jp/guide/course/
- 地方競馬全国協会「地方競馬総合ガイドブック 2026」 https://www.keiba.go.jp/about/guidebook.html

`course-layout-data.js` の中心線座標は、上記公式上面図をゲーム用Canvas座標へ独自に再構成したもの。公式画像は収録しない。
