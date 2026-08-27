"""Leak-safe OOS audit of strict and secondary rebound candidates (local racing)."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "v2026.08.28.1"
BASE = Path(__file__).resolve().parents[1]
ROOT = BASE if (BASE / "data" / "keiba_local.sqlite").exists() else BASE / "claude_handoff_20260731_private"


def corner(v):
    try:
        return float(str(v).split("-")[-1])
    except (TypeError, ValueError):
        return np.nan


def load():
    with sqlite3.connect(ROOT / "data" / "keiba_local.sqlite") as con:
        have = {r[1] for r in con.execute("pragma table_info(runs)")}
        wanted = ["race_id", "date", "venue", "horse_id", "umaban", "finish_pos",
                  "finish_time", "last_3f", "passing", "field_size", "win_odds",
                  "popularity", "tan_payout", "place_payout"]
        d = pd.read_sql_query("select " + ",".join(c for c in wanted if c in have) + " from runs", con)
    with sqlite3.connect(ROOT / "data" / "ai_index_local.sqlite") as con:
        cols = {r[1] for r in con.execute("pragma table_info(ai_index)")}
        pcol = "p_pure_n" if "p_pure_n" in cols else "p_comb_n"
        ai = pd.read_sql_query(f"select race_id,umaban,{pcol} p from ai_index", con)
    for x in (d, ai):
        x["race_id"] = x.race_id.astype(str)
        x["umaban"] = pd.to_numeric(x.umaban, errors="coerce")
    d = d.merge(ai, on=["race_id", "umaban"], how="left")
    nums = ["finish_pos", "finish_time", "last_3f", "field_size", "win_odds",
            "popularity", "tan_payout", "place_payout", "p"]
    for c in nums:
        if c not in d:
            d[c] = np.nan
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    d = d.dropna(subset=["date", "horse_id", "finish_pos"])
    d = d[d.finish_pos.gt(0)].sort_values(["date", "race_id", "umaban"]).reset_index(drop=True)
    d["field_size"] = d.field_size.fillna(d.groupby("race_id").umaban.transform("count"))
    den = (d.field_size - 1).clip(lower=1)
    d["q_finish"] = 1 - (d.finish_pos - 1) / den
    d["q_time"] = 1 - d.groupby("race_id").finish_time.rank(pct=True, ascending=True)
    d["q_last3f"] = 1 - d.groupby("race_id").last_3f.rank(pct=True, ascending=True)
    d["last_corner"] = d.passing.map(corner)
    d["position_gain"] = d.last_corner - d.finish_pos
    d["q_gain"] = d.groupby("race_id").position_gain.rank(pct=True, ascending=True)
    d["performance"] = d[["q_finish", "q_time", "q_last3f", "q_gain"]].mean(axis=1)

    d = d.sort_values(["horse_id", "date", "race_id"]).reset_index(drop=True)
    g = d.groupby("horse_id", sort=False)
    prior = g.performance.shift(1)
    d["baseline3"] = (prior.groupby(d.horse_id, sort=False).rolling(3, min_periods=2).mean()
                      .reset_index(level=0, drop=True).reindex(d.index))
    d["shock"] = d.baseline3 - d.performance
    d["index_rank"] = d.groupby("race_id").p.rank(ascending=False, method="min")
    g = d.groupby("horse_id", sort=False)
    for c in ["shock", "baseline3", "index_rank", "field_size"]:
        d[c + "_l1"] = g[c].shift(1)
    d["shock_l2"] = g.shock.shift(2)

    # Historical version of the pre-race battle rule: at least 90% of runners
    # have raced at the same venue in 2+ of their immediately preceding 3 starts.
    same = sum(g.venue.shift(k).eq(d.venue).astype("int8") for k in (1, 2, 3))
    d["same_venue_2of3"] = same.ge(2)
    d["battle_quality"] = d.groupby("race_id").same_venue_2of3.transform("mean")
    return d.sort_values(["date", "race_id", "umaban"]).reset_index(drop=True)


def metrics(x):
    n = len(x)
    if not n:
        return {"bets": 0, "races": 0}
    tan = x.tan_payout.fillna(0)
    plc = x.place_payout.fillna(0)
    return {
        "bets": int(n), "races": int(x.race_id.nunique()),
        "win_rate": float(x.finish_pos.eq(1).mean()),
        "place_rate": float(x.finish_pos.le(3).mean()),
        "win_roi": float(tan.sum() / (100 * n)),
        "place_roi": float(plc.sum() / (100 * n)),
        "win_roi_without_largest": float((tan.sum() - tan.max()) / (100 * n)),
        "place_roi_without_largest": float((plc.sum() - plc.max()) / (100 * n)),
        "avg_win_odds": float(x.win_odds.mean()),
        "avg_popularity": float(x.popularity.mean()),
    }


def summarize(frame):
    out = {"overall": metrics(frame)}
    out["monthly"] = {str(k): metrics(v) for k, v in frame.groupby(frame.date.dt.to_period("M"))}
    out["venue"] = {str(k): metrics(v) for k, v in frame.groupby("venue") if len(v) >= 20}
    return out


def run():
    d = load()
    dates = np.array(sorted(d.date.dt.normalize().unique()))
    cut1, cut2 = dates[int(len(dates) * .70)], dates[int(len(dates) * .85)]
    train = d[d.date < cut1]
    q90 = float(train.shock.dropna().quantile(.90))
    med = float(train.shock.dropna().median())
    baseline60 = float(train.baseline3.dropna().quantile(.60))

    upper = (d.field_size_l1 + 1) // 2
    strict_mask = (d.shock_l1.ge(q90) & d.shock_l2.lt(med) &
                   d.baseline3_l1.ge(baseline60) & d.index_rank_l1.le(upper))
    strict = d[strict_mask].copy()
    strict["score"] = strict.shock_l1 * strict.baseline3_l1
    strict = (strict.sort_values(["race_id", "score"], ascending=[True, False])
              .drop_duplicates("race_id"))

    secondary = d[d.shock_l1.ge(q90) & d.battle_quality.ge(.90)].copy()
    secondary = (secondary.sort_values(["race_id", "shock_l1"], ascending=[True, False])
                 .drop_duplicates("race_id"))
    secondary = secondary[~secondary.race_id.isin(set(strict.race_id))]
    strict["tier"] = "strict"
    secondary["tier"] = "secondary"
    picks = pd.concat([strict, secondary], ignore_index=True)

    result = {
        "version": VERSION,
        "definition": {
            "strict": "shock top10%, one-off V, prior baseline top40%, prior AI upper half, max1/race",
            "secondary": "not strict race; battle quality >=90%, shock top10%, max1/race",
            "battle": ">=90% runners had 2+ of prior 3 starts at same venue",
        },
        "date_min": str(d.date.min().date()), "date_max": str(d.date.max().date()),
        "selection_from": str(pd.Timestamp(cut1).date()),
        "oos_from": str(pd.Timestamp(cut2).date()),
        "locked": {"shock_q90": q90, "shock_median": med, "baseline_q60": baseline60},
        "selection": {}, "oos": {},
    }
    for name, frame in (("selection", picks[(picks.date >= cut1) & (picks.date < cut2)]),
                        ("oos", picks[picks.date >= cut2])):
        result[name]["strict"] = summarize(frame[frame.tier.eq("strict")])
        result[name]["secondary"] = summarize(frame[frame.tier.eq("secondary")])
        result[name]["combined"] = summarize(frame)
    outdir = Path(__file__).resolve().parent / "reports"
    outdir.mkdir(exist_ok=True)
    (outdir / "rebound_tier_oos.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    compact = {p: {t: result[p][t]["overall"] for t in ("strict", "secondary", "combined")}
               for p in ("selection", "oos")}
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
