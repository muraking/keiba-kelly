"""Predefined rule audit for three-way index consensus, with untouched OOS."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "v2026.08.28.5"
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from all_information_draw_leadership_oos import merge_time_index
from keiba_ai.all_information_roi_research import load, score, split4
from keiba_ai.energy_stamina_research import load_runs, make_features
from keiba_ai.lap_theory_oos_research import add_lap_theory_features


def pct_high(x, race):
    return x.groupby(race, sort=False).rank(ascending=True, pct=True).mul(100)


def metric(x, ret):
    if x.empty:
        return {"bets": 0, "races": 0, "roi": None}
    v = x[ret].fillna(0)
    return {
        "bets": int(len(x)), "races": int(x.race_id.nunique()),
        "days": int(x.date.dt.normalize().nunique()),
        "bets_per_day": float(len(x) / max(1, x.date.dt.normalize().nunique())),
        "hit": float(v.gt(0).mean()), "roi": float(v.sum() / (100 * len(x))),
        "trim_roi": float((v.sum() - v.max()) / (100 * len(x))),
        "largest_share": float(v.max() / v.sum()) if v.sum() else 0.0,
        "avg_odds": float(x.win_odds.mean()),
        "positive_months": int(sum(g[ret].fillna(0).sum() > 100 * len(g)
                                   for _, g in x.groupby(x.date.dt.to_period("M")))),
        "months": int(x.date.dt.to_period("M").nunique()),
    }


def build(tag, return_full=False):
    base, cols = load(tag)
    base, ti_cols = merge_time_index(base, tag)
    cols += [c for c in ti_cols if c not in cols]
    base["split"], cuts = split4(base)
    base = score(base, cols)
    base["ret_win"] = np.where(base.is_win.eq(1), base.tan_payout.fillna(base.win_odds * 100), 0)
    base["ret_place"] = np.where(base.is_place.eq(1), base.place_payout.fillna(0), 0)

    raw = load_runs(BASE / "data" / f"keiba_{tag}.sqlite", "2023-07-01" if tag == "local" else None)
    ef = add_lap_theory_features(make_features(raw))
    ef = ef.sort_values(["horse_id", "date", "race_id"]).reset_index(drop=True)
    hg = ef.groupby("horse_id", sort=False)
    same_n = sum(hg.venue.shift(k).eq(ef.venue).astype("int8") for k in (1, 2, 3))
    ef["hist_same"] = same_n.ge(2); ef["hist_ok"] = hg.cumcount().ge(3)
    ef["lap_score"] = (ef.lap_pressure_resist.fillna(0) + ef.lap_finish_scenario_fit.fillna(0)
                       + .25 * ef.lap_profile_match.fillna(-1))
    keep = ["race_id", "umaban", "distance_energy", "hist_same", "hist_ok", "lap_score"]
    z = base.merge(ef[keep].drop_duplicates(["race_id", "umaban"]),
                   on=["race_id", "umaban"], how="left")
    g = z.groupby("race_id", sort=False)
    z["n"] = g.umaban.transform("count")
    z["normal_q"] = pct_high(z.p_meta_pure, z.race_id)
    ti_parts = [pct_high(z[c], z.race_id) for c in
                ("ti_same_venue_max", "ti_same_distance_max", "ti_max5")
                if c in z and z[c].notna().any()]
    z["ti_q"] = pd.concat(ti_parts, axis=1).mean(axis=1) if ti_parts else z.normal_q
    z["energy_q"] = pct_high(z.distance_energy, z.race_id).fillna(50)
    z["history_q"] = np.where(z.hist_same, 100, np.where(z.hist_ok, 65, 40))
    z["taichi_proxy"] = (.55*z.normal_q + .20*z.ti_q.fillna(z.normal_q)
                         + .15*z.energy_q + .10*z.history_q)
    z["normal_rank"] = g.p_meta_pure.rank(ascending=False, method="first")
    z["taichi_rank"] = g.taichi_proxy.rank(ascending=False, method="first")
    z["lap_rank"] = g.lap_score.rank(ascending=False, method="first")
    z["market_rank"] = g.p_market.rank(ascending=False, method="first")
    z["rank_sum"] = z.normal_rank + z.taichi_rank + z.lap_rank
    z["model_market_gap"] = z.market_rank - z.normal_rank
    z["model_ev"] = z.p_meta_pure * z.win_odds
    pm = z.p_market.clip(lower=1e-9)
    pm = pm / pm.groupby(z.race_id, sort=False).transform("sum")
    z["entropy"] = (-(pm * np.log(pm)).groupby(z.race_id, sort=False).transform("sum")
                    / np.log(z.n.clip(lower=2)))
    z["history_quality"] = z.hist_same.groupby(z.race_id, sort=False).transform("mean")
    common = z[z.normal_rank.le(3) & z.taichi_rank.le(3) & z.lap_rank.le(3)].copy()
    return (z, common, cuts) if return_full else (common, cuts)


def masks(x):
    return {
        "baseline": np.ones(len(x), dtype=bool),
        "nonfav": x.popularity.gt(1),
        "odds3_6": x.win_odds.between(3, 6, inclusive="left"),
        "odds6_10": x.win_odds.between(6, 10, inclusive="left"),
        "odds10_20": x.win_odds.between(10, 20, inclusive="left"),
        "odds20_50": x.win_odds.between(20, 50, inclusive="left"),
        "normal1": x.normal_rank.eq(1), "taichi1": x.taichi_rank.eq(1),
        "lap1": x.lap_rank.eq(1), "all_top2": x[["normal_rank", "taichi_rank", "lap_rank"]].max(axis=1).le(2),
        "rank_sum_le5": x.rank_sum.le(5), "rank_sum_le6": x.rank_sum.le(6),
        "underbet1": x.model_market_gap.ge(1), "underbet2": x.model_market_gap.ge(2),
        "ev_ge08": x.model_ev.ge(.8), "ev_ge10": x.model_ev.ge(1.0), "ev_ge12": x.model_ev.ge(1.2),
        "entropy_low": x.entropy.lt(.75),
        "entropy_mid": x.entropy.between(.75, .90, inclusive="left"),
        "entropy_high": x.entropy.ge(.90),
        "field_le8": x.n.le(8), "field9_12": x.n.between(9, 12), "field_ge13": x.n.ge(13),
        "history75": x.history_quality.ge(.75),
        "odds10_underbet": x.win_odds.ge(10) & x.model_market_gap.ge(1),
        "nonfav_rank5": x.popularity.gt(1) & x.rank_sum.le(5),
    }


def run(tag):
    x, cuts = build(tag)
    rules = masks(x)
    result = {"version": VERSION, "market": tag, "cuts": cuts,
              "policy": "all rules predefined; selection chooses candidates, OOS untouched",
              "warning": "historical Taichi fixed-weight proxy", "rules": {}}
    for name, mask in rules.items():
        pool = x[mask].copy()
        one = (pool.sort_values(["race_id", "taichi_proxy"], ascending=[True, False])
               .drop_duplicates("race_id"))
        result["rules"][name] = {}
        for period in ("select", "oos"):
            result["rules"][name][period] = {}
            for mode, q in (("all", pool[pool.split.eq(period)]), ("one", one[one.split.eq(period)])):
                result["rules"][name][period][mode] = {
                    "win": metric(q, "ret_win"), "place": metric(q, "ret_place")}
    minimum = 100 if tag == "local" else 50
    selected = []
    for name, r in result["rules"].items():
        for mode in ("all", "one"):
            for ticket in ("win", "place"):
                s = r["select"][mode][ticket]
                if s["bets"] >= minimum and s["roi"] is not None and s["roi"] >= .90:
                    selected.append({"rule": name, "mode": mode, "ticket": ticket,
                                     "selection": s, "oos": r["oos"][mode][ticket]})
    result["selection_candidates"] = selected
    out = Path(__file__).resolve().parent / "reports" / f"consensus_rule_research_{tag}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"market": tag, "candidates": selected}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=("local", "jra"), required=True)
    run(ap.parse_args().market)
