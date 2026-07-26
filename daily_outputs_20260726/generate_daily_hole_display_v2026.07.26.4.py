"""Generate today's compact win-top2 / longshot-top3 display.

Version: v2026.07.26.4
"""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

VERSION = "v2026.07.26.4"
TODAY = pd.Timestamp("2026-07-26")
EXCLUDE = {
    "race_id", "date", "venue", "horse_id", "is_win", "is_place",
    "tan_payout", "place_payout", "finish_pos", "is_iruka",
    "obstacle_time", "win_odds", "popularity",
}
ADVANCED = {
    "h_venue_n", "h_venue_winrate", "h_venue_avg_rel", "h_avg_spd3",
    "h_best_spd5", "h_avg_rtop3", "h_rank_std", "dir_x_umaban",
}
GRADE = {"A": 3, "B": 2, "C": 1, "D": 0}


def classifier():
    return HistGradientBoostingClassifier(
        max_iter=180, learning_rate=.055, max_leaf_nodes=31,
        min_samples_leaf=80, l2_regularization=2, random_state=20260726,
    )


def load_live(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def snapshots(live: dict, preday: dict) -> dict:
    return {
        str(race): (
            values.get("t7", {}).get("snapshot")
            or (values.get("t30") if values.get("t30", {}).get("p") else None)
            or preday.get("races", {}).get(str(race), {}).get("preday", {})
        )
        for race, values in live["races"].items()
        if (values.get("t7", {}).get("snapshot")
            or values.get("t30", {}).get("p")
            or preday.get("races", {}).get(str(race), {}).get("preday"))
    }


def load_features(path: Path) -> pd.DataFrame:
    with sqlite3.connect(path) as c:
        d = pd.read_sql_query("select * from features", c)
    d["race_id"] = d.race_id.astype(str)
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    for column in d.columns:
        if column not in {"race_id", "date", "venue", "horse_id"}:
            d[column] = pd.to_numeric(d[column], errors="coerce")
    return d


def apply_live_odds(d: pd.DataFrame, snap: dict) -> pd.DataFrame:
    odds = pd.DataFrame([
        {"race_id": race, "umaban": int(number), "live_odds": float(value)}
        for race, values in snap.items()
        for number, value in values.get("o", {}).items()
    ])
    out = d.merge(odds, on=["race_id", "umaban"], how="left")
    current = out.date.eq(TODAY) & out.live_odds.notna()
    out.loc[current, "win_odds"] = out.loc[current, "live_odds"]
    return out.drop(columns="live_odds")


def workout(path: Path) -> pd.DataFrame:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for horse, entries in raw.items():
        for entry in entries:
            works = entry.get("works") or []
            last = [w.get("last1f") for w in works if isinstance(w.get("last1f"), (int, float))]
            rows.append({
                "horse_id": str(horse), "race_id": str(entry.get("race_id")),
                "tr_n": entry.get("n_works", len(works)),
                "tr_last_min": min(last) if last else np.nan,
                "tr_last_mean": np.mean(last) if last else np.nan,
                "tr_fast": sum(float(w.get("fast_n") or 0) for w in works),
                "tr_grade": max((GRADE.get(str(w.get("grade")), 0) for w in works), default=0),
                "tr_load": max((1 if w.get("load") else 0 for w in works), default=0),
            })
    return pd.DataFrame(rows).drop_duplicates(["race_id", "horse_id"], keep="last")


def predict_local(d: pd.DataFrame, race_ids: set[str]) -> pd.DataFrame:
    numeric = [c for c in d if c not in EXCLUDE and pd.api.types.is_numeric_dtype(d[c])]
    core = [c for c in numeric if not c.startswith("ana_") and c not in ADVANCED]
    features = core + [c for c in numeric if c in ADVANCED]
    return fit_predict(d, race_ids, features)


def predict_jra(d: pd.DataFrame, race_ids: set[str], training: Path) -> pd.DataFrame:
    d = d.copy()
    d.horse_id = d.horse_id.astype(str)
    d = d.merge(workout(training), on=["race_id", "horse_id"], how="left")
    trcols = ["tr_n", "tr_last_min", "tr_last_mean", "tr_fast", "tr_grade", "tr_load"]
    numeric = [c for c in d if c not in EXCLUDE and c not in trcols
               and pd.api.types.is_numeric_dtype(d[c])]
    return fit_predict(d, race_ids, numeric + trcols)


def fit_predict(d: pd.DataFrame, race_ids: set[str], features: list[str]) -> pd.DataFrame:
    train = d[
        d.date.lt(TODAY) & d.win_odds.ge(10) & d.is_place.notna()
    ].copy()
    test = d[d.race_id.isin(race_ids)].copy()
    if test.empty:
        raise RuntimeError("today's feature rows are missing")
    medians = train[features].replace([np.inf, -np.inf], np.nan).median().fillna(0)
    x = train[features].replace([np.inf, -np.inf], np.nan).fillna(medians).astype("float32")
    z = test[features].replace([np.inf, -np.inf], np.nan).fillna(medians).astype("float32")
    fitted = classifier().fit(x, train.is_place.astype(int))
    test["hole_pp"] = fitted.predict_proba(z)[:, 1]
    return test


def proxy_predictions(snap: dict, history: pd.DataFrame) -> pd.DataFrame:
    venue_map = {}
    for race, group in history.groupby(history.race_id.str[4:6]):
        venue_map[str(race)] = str(group.venue.mode().iloc[0])
    rows = []
    for race_id, values in snap.items():
        for number, probability in values["p"].items():
            rows.append({
                "race_id": race_id, "umaban": int(number),
                "venue": venue_map.get(race_id[4:6], ""),
                "hole_pp": np.nan, "proxy_score": float(probability),
            })
    return pd.DataFrame(rows)


def race_meta(preday: dict, features: pd.DataFrame) -> dict:
    output = {}
    for race, values in preday.get("races", {}).items():
        if values.get("meta"):
            output[str(race)] = values["meta"]
    for race, group in features.groupby("race_id"):
        if str(race) not in output:
            number = int(str(race)[-2:])
            output[str(race)] = {
                "venue": str(group.venue.iloc[0]), "race_num": number,
                "race_name": "", "post": "",
            }
    return output


def fmt_horse(prefix: str, number: str, snap: dict, pp=None, buy=None) -> str:
    name = snap["h"].get(number, "")
    wp = float(snap["p"].get(number, 0)) * 100
    odds = float(snap.get("o", {}).get(number, 0))
    suffix = f"　PP{pp * 100:.1f}%" if pp is not None and pd.notna(pp) else ""
    if buy:
        suffix += "　●買い " + "/".join(buy)
    return f"{prefix} {int(number):>2} {name}　WP{wp:>4.1f}%　{odds:>5.1f}倍{suffix}"


def make_race(market: str, race_id: str, snap: dict, group: pd.DataFrame,
              meta: dict, decision: dict, proxy: bool) -> dict:
    win_order = sorted(snap["p"], key=lambda n: float(snap["p"][n]), reverse=True)
    top2 = win_order[:2]
    odds = {n: float(v) for n, v in snap.get("o", {}).items()}
    pp = {str(int(row.umaban)): float(row.hole_pp) for row in group.itertuples()}
    holes = sorted(
        [number for number in snap["h"] if odds.get(number, 0) >= 10 and number in pp],
        key=lambda number: (
            float(snap["p"].get(number, 0)) if proxy else pp[number]
        ), reverse=True,
    )[:3]
    field = len(snap["h"])
    race_num = int(meta.get("race_num") or race_id[-2:])
    fav_p = float(snap["p"].get(top2[0], 0))
    buys = {}
    tickets = []
    if holes and not proxy:
        h1 = holes[0]
        o1, p1 = odds[h1], pp[h1]
        if market == "jra":
            tags = []
            if 20 <= o1 <= 80 and p1 >= .20 and field >= 10:
                tags.append("複勝")
                tickets.append(f"複勝 {int(h1)}")
            if 10 <= o1 <= 20 and p1 >= .20 and field >= 8:
                tags += ["ワイド", "三連複"]
                tickets.append(f"ワイド {int(h1)}-{int(top2[0])}")
                tickets.append(f"三連複 {int(h1)}-{int(top2[0])}-{int(top2[1])}")
            if 10 <= o1 <= 20 and p1 >= .20 and fav_p >= .25 and field >= 10:
                tags.append("馬連")
                tickets.append(f"馬連 {int(h1)}-{int(top2[0])}")
            if tags:
                buys[h1] = list(dict.fromkeys(tags))
        else:
            for rank, number in enumerate(holes, 1):
                tags = []
                value, probability = odds[number], pp[number]
                if rank == 3 and 30 <= value < 50 and field >= 12 and race_num >= 9:
                    tags.append("R1")
                if rank == 3 and 30 <= value < 50 and .16 <= probability < .20 and race_num >= 9:
                    tags.append("R2")
                if rank == 1 and 15 <= value < 20 and .20 <= probability < .25 and .25 <= fav_p < .35:
                    tags.append("R3")
                if tags:
                    buys[number] = tags
                    tickets.append(f"単勝 {int(number)}")
    if proxy and decision.get("action") == "SHADOW_BET":
        axis = str(decision.get("axis"))
        buys[axis] = ["既存判定"]
        tickets = [str(ticket) for ticket in decision.get("tickets", [])]
    return {
        "race_id": race_id, "meta": meta, "top2": top2, "holes": holes,
        "pp": pp, "buys": buys, "tickets": list(dict.fromkeys(tickets)),
        "snapshot": snap, "proxy": proxy,
    }


def render(markets: dict[str, list[dict]], output: Path):
    lines = [
        "# 2026年7月26日 全レース新表示",
        "",
        f"Version: {VERSION}",
        "",
        "> 7分前スナップショットを使った終了後検証表示です。現在は購入できません。",
        "> 本日の特徴行が未保存のため、穴①～穴③は10倍以上の馬を既存WP順に並べた暫定表示です。",
        "> ●買いは新R1～R3ではなく、当時の既存ライブサービス判定です。",
        "> 7分前スナップショットがないレースは30分前指数で補完し、穴候補・買い目は判定不可です。",
        "> 地方の当日馬場脚質フィルターは通過順位データ不足のため未判定です。",
        "",
    ]
    for market, races in markets.items():
        lines += [f"## {'JRA' if market == 'jra' else '地方'}（{len(races)}レース）", ""]
        for row in races:
            meta, snap = row["meta"], row["snapshot"]
            title = f"{meta.get('venue', '')}{meta.get('race_num', '')}R"
            if meta.get("race_name"):
                title += f" {meta['race_name']}"
            lines += [f"### {title}", "", "【勝率上位】"]
            for rank, number in enumerate(row["top2"], 1):
                lines.append(fmt_horse(f"勝{rank}", number, snap))
            lines += ["", "【穴馬候補・暫定WP順】"]
            if row["holes"]:
                for rank, number in enumerate(row["holes"], 1):
                    lines.append(fmt_horse(
                        f"穴{rank}", number, snap, row["pp"][number], row["buys"].get(number)
                    ))
            else:
                lines.append("穴候補なし")
            lines.append("")
            if row["tickets"]:
                lines.append("【当時の既存判定買い目】 " + "／".join(row["tickets"]))
                if market == "local":
                    lines.append("※当日馬場脚質フィルター未判定")
            else:
                lines.append("【見送り】 購入条件に該当なし")
            lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", type=Path, required=True)
    a = p.parse_args()
    results = {}
    machine = {"version": VERSION, "date": str(TODAY.date()), "markets": {}}
    for market in ("jra", "local"):
        live = load_live(a.dir / f"{market}_standalone_live.json")
        preday = load_live(a.dir / f"{market}_standalone_preday.json")
        snap = snapshots(live, preday)
        features = apply_live_odds(load_features(a.dir / f"features_{market}.sqlite"), snap)
        race_ids = set(snap)
        prediction = (
            predict_jra(features, race_ids, a.dir / "training_jra.json")
            if market == "jra" and features.race_id.isin(race_ids).any()
            else predict_local(features, race_ids)
            if market == "local" and features.race_id.isin(race_ids).any()
            else proxy_predictions(snap, features)
        )
        proxy = "proxy_score" in prediction.columns
        meta = race_meta(preday, prediction)
        races = [
            make_race(
                market, race, snap[race], prediction[prediction.race_id.eq(race)],
                meta.get(race, {"venue": "", "race_num": int(race[-2:])}),
                live["races"][race].get("t7", {}).get("decision", {}), proxy,
            )
            for race in sorted(race_ids, key=lambda r: (
                meta.get(r, {}).get("venue", ""), meta.get(r, {}).get("race_num", int(r[-2:]))
            ))
        ]
        results[market] = races
        machine["markets"][market] = races
        print(market, "races", len(races), "buy races", sum(bool(x["tickets"]) for x in races))
    render(results, a.dir / "all_races_display_v2026.07.26.4.md")
    (a.dir / "all_races_display_v2026.07.26.4.json").write_text(
        json.dumps(machine, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
