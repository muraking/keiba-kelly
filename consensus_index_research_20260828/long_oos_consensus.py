"""Long OOS proxy for normal-index x Taichi x lap top-three consensus."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "v2026.08.28.3"
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from all_information_draw_leadership_oos import merge_time_index
from keiba_ai.all_information_roi_research import load, score, split4
from keiba_ai.energy_stamina_research import load_runs, make_features
from keiba_ai.lap_theory_oos_research import add_lap_theory_features


def pct_high(x: pd.Series, race: pd.Series) -> pd.Series:
    return x.groupby(race, sort=False).rank(ascending=True, pct=True).mul(100)


def metrics(x: pd.DataFrame) -> dict:
    if x.empty:
        return {"bets": 0, "races": 0}
    tan = x.ret_win.fillna(0); plc = x.ret_place.fillna(0)
    return {
        "bets": int(len(x)), "races": int(x.race_id.nunique()),
        "win_rate": float(x.is_win.mean()), "place_rate": float(x.is_place.mean()),
        "win_roi": float(tan.sum() / (100 * len(x))),
        "place_roi": float(plc.sum() / (100 * len(x))),
        "win_roi_trim_largest": float((tan.sum() - tan.max()) / (100 * len(x))),
        "place_roi_trim_largest": float((plc.sum() - plc.max()) / (100 * len(x))),
        "avg_odds": float(x.win_odds.mean()),
    }


def run(tag: str):
    base, cols = load(tag)
    base, ti_cols = merge_time_index(base, tag)
    cols += [c for c in ti_cols if c not in cols]
    base["split"], cuts = split4(base)
    base = score(base, cols)
    base["ret_win"] = np.where(base.is_win.eq(1), base.tan_payout.fillna(base.win_odds * 100), 0)
    base["ret_place"] = np.where(base.is_place.eq(1), base.place_payout.fillna(0), 0)

    raw = load_runs(BASE / "data" / f"keiba_{tag}.sqlite",
                    "2023-07-01" if tag == "local" else None)
    ef = make_features(raw)
    ef = add_lap_theory_features(ef)
    ef = ef.sort_values(["horse_id", "date", "race_id"]).reset_index(drop=True)
    hg = ef.groupby("horse_id", sort=False)
    same_n = sum(hg.venue.shift(k).eq(ef.venue).astype("int8") for k in (1, 2, 3))
    ef["hist_same"] = same_n.ge(2)
    ef["hist_ok"] = hg.cumcount().ge(3)
    ef["lap_score"] = (ef.lap_pressure_resist.fillna(0)
                       + ef.lap_finish_scenario_fit.fillna(0)
                       + .25 * ef.lap_profile_match.fillna(-1))
    keep = ["race_id", "umaban", "distance_energy", "hist_same", "hist_ok", "lap_score"]
    z = base.merge(ef[keep].drop_duplicates(["race_id", "umaban"]),
                   on=["race_id", "umaban"], how="left")
    g = z.groupby("race_id", sort=False)
    z["normal_q"] = pct_high(z.p_meta_pure, z.race_id)
    ti_parts = [pct_high(z[c], z.race_id) for c in
                ("ti_same_venue_max", "ti_same_distance_max", "ti_max5")
                if c in z and z[c].notna().any()]
    z["ti_q"] = pd.concat(ti_parts, axis=1).mean(axis=1) if ti_parts else z.normal_q
    z["energy_q"] = pct_high(z.distance_energy, z.race_id).fillna(50)
    z["history_q"] = np.where(z.hist_same, 100, np.where(z.hist_ok, 65, 40))
    z["taichi_proxy"] = (.55 * z.normal_q + .20 * z.ti_q.fillna(z.normal_q)
                         + .15 * z.energy_q + .10 * z.history_q)
    z["normal_rank"] = g.p_meta_pure.rank(ascending=False, method="first")
    z["taichi_rank"] = g.taichi_proxy.rank(ascending=False, method="first")
    z["lap_rank"] = g.lap_score.rank(ascending=False, method="first")
    common = z[z.normal_rank.le(3) & z.taichi_rank.le(3) & z.lap_rank.le(3)].copy()
    common["consensus_score"] = z[["normal_q", "energy_q"]].mean(axis=1)
    one = (common.sort_values(["race_id", "taichi_proxy"], ascending=[True, False])
           .drop_duplicates("race_id"))
    odds10 = common[common.win_odds.ge(10)].copy()
    odds10_one = (odds10.sort_values(["race_id", "taichi_proxy"], ascending=[True, False])
                  .drop_duplicates("race_id"))

    result = {"version": VERSION, "market": tag, "cuts": cuts,
              "warning": "Taichi is a historical fixed-weight proxy; live Sol-TI model output and trouble +/- are unavailable historically",
              "rules": {}}
    for part in ("select", "oos"):
        x = common[common.split.eq(part)]
        x1 = one[one.split.eq(part)]
        x10 = odds10[odds10.split.eq(part)]
        x10one = odds10_one[odds10_one.split.eq(part)]
        result["rules"][part] = {
            "buy_all_common": metrics(x),
            "one_best_common_per_race": metrics(x1),
            "buy_all_common_nonfav": metrics(x[x.popularity.gt(1)]),
            "one_best_common_nonfav": metrics(x1[x1.popularity.gt(1)]),
            "buy_all_common_odds10plus": metrics(x10),
            "one_best_common_odds10plus": metrics(x10one),
            "all_common_odds2_10": metrics(x[x.win_odds.between(2, 10, inclusive="left")]),
            "one_best_odds2_10": metrics(x1[x1.win_odds.between(2, 10, inclusive="left")]),
        }
    outdir = Path(__file__).resolve().parent / "reports"; outdir.mkdir(exist_ok=True)
    (outdir / f"long_oos_consensus_{tag}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--market", choices=("local", "jra"), required=True)
    run(ap.parse_args().market)
