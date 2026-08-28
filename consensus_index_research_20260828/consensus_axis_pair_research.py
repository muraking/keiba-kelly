"""Consensus horse as axis: predefined quinella/wide one- and two-point audit."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from all_information_draw_leadership_oos import pair_values
from consensus_index_research_20260828.consensus_rule_research import build, metric
from keiba_ai.energy_quality_bet_research import load_canonical_payouts

VERSION = "v2026.08.28.1"


def partners(z, axis, kind, count):
    q = z.merge(axis[["race_id", "axis_umaban"]], on="race_id", how="inner")
    q = q[q.umaban.ne(q.axis_umaban)].copy()
    if kind == "model":
        q = q.sort_values(["race_id", "p_meta_pure"], ascending=[True, False])
    elif kind == "taichi":
        q = q.sort_values(["race_id", "taichi_proxy"], ascending=[True, False])
    elif kind == "market":
        q = q.sort_values(["race_id", "p_market"], ascending=[True, False])
    elif kind == "underbet":
        q = q[q.model_market_gap.ge(1) & q.popularity.gt(1)]
        q = q.sort_values(["race_id", "model_market_gap", "p_meta_pure"],
                          ascending=[True, False, False])
    elif kind == "value_hole":
        q = q[q.popularity.ge(4) & q.win_odds.between(8, 50, inclusive="left")]
        q = q.sort_values(["race_id", "model_ev", "p_meta_pure"], ascending=[True, False, False])
    elif kind == "lap_hole":
        q = q[q.popularity.ge(4) & q.win_odds.between(8, 50, inclusive="left")
              & q.lap_rank.le((q.n / 2).clip(lower=3))]
        q = q.sort_values(["race_id", "lap_score", "p_meta_pure"], ascending=[True, False, False])
    else:
        raise ValueError(kind)
    return q.groupby("race_id", sort=False).head(count).copy()


def run(tag):
    z, common, cuts = build(tag, return_full=True)
    axis = (common.sort_values(["race_id", "taichi_proxy"], ascending=[True, False])
            .drop_duplicates("race_id")[["race_id", "umaban"]]
            .rename(columns={"umaban": "axis_umaban"}))
    payouts = load_canonical_payouts(BASE / "data" / f"keiba_{tag}.sqlite")
    result = {"version": VERSION, "market": tag, "cuts": cuts,
              "policy": "consensus best axis; predefined partner families; equal 100-yen tickets",
              "strategies": {}, "selection_candidates": []}
    minimum = 100 if tag == "local" else 50
    for family in ("model", "taichi", "market", "underbet", "value_hole", "lap_hole"):
        for count in (1, 2):
            pool = partners(z, axis, family, count)
            for bet in ("umaren", "wide"):
                q = pair_values(pool, payouts, bet)
                name = f"{family}{count}_{bet}"
                result["strategies"][name] = {}
                for period in ("select", "oos"):
                    x = q[q.split.eq(period)].copy()
                    result["strategies"][name][period] = metric(x, "_pair_ret")
                s = result["strategies"][name]["select"]
                if s["bets"] >= minimum and s["roi"] is not None and s["roi"] >= .90:
                    result["selection_candidates"].append({
                        "strategy": name, "selection": s,
                        "oos": result["strategies"][name]["oos"]})
    out = Path(__file__).resolve().parent / "reports" / f"consensus_axis_pair_{tag}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"market": tag, "candidates": result["selection_candidates"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=("local", "jra"), required=True)
    run(ap.parse_args().market)
