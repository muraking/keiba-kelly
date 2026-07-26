"""Build local OOS roles with the advanced-feature longshot place score.

Version: v2026.07.26.1
"""
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

VERSION = "v2026.07.26.1"
EXCLUDE = {
    "race_id", "date", "venue", "horse_id", "is_win", "is_place",
    "tan_payout", "place_payout", "finish_pos", "is_iruka",
    "obstacle_time", "win_odds", "popularity",
}
ADVANCED = {
    "h_venue_n", "h_venue_winrate", "h_venue_avg_rel", "h_avg_spd3",
    "h_best_spd5", "h_avg_rtop3", "h_rank_std", "dir_x_umaban",
}


def model():
    return HistGradientBoostingClassifier(
        max_iter=180, learning_rate=.055, max_leaf_nodes=31,
        min_samples_leaf=80, l2_regularization=2, random_state=20260726,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--baseline-oos", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()

    with sqlite3.connect(a.db) as c:
        d = pd.read_sql_query("select * from features", c)
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    d["race_id"] = d.race_id.astype(str)
    for column in d.columns:
        if column not in {"race_id", "date", "venue", "horse_id"}:
            d[column] = pd.to_numeric(d[column], errors="coerce")
    d = d[d.win_odds.ge(10) & d.is_place.notna()].copy()
    numeric = [
        c for c in d if c not in EXCLUDE
        and pd.api.types.is_numeric_dtype(d[c])
    ]
    core = [c for c in numeric if not c.startswith("ana_") and c not in ADVANCED]
    features = core + [c for c in numeric if c in ADVANCED]

    predictions = []
    for year in (2024, 2025, 2026):
        train = d[d.date.dt.year.lt(year)]
        test = d[d.date.dt.year.eq(year)].copy()
        medians = train[features].replace([np.inf, -np.inf], np.nan).median().fillna(0)
        train_x = train[features].replace([np.inf, -np.inf], np.nan).fillna(medians).astype("float32")
        test_x = test[features].replace([np.inf, -np.inf], np.nan).fillna(medians).astype("float32")
        fitted = model().fit(train_x, train.is_place.astype(int))
        test["p_place_advanced"] = fitted.predict_proba(test_x)[:, 1]
        predictions.append(test[["race_id", "umaban", "p_place_advanced"]])

    advanced = pd.concat(predictions, ignore_index=True)
    baseline = pd.read_csv(a.baseline_oos)
    baseline["race_id"] = baseline.race_id.astype(str)
    output = baseline.merge(advanced, on=["race_id", "umaban"], how="left")
    longshot = output.win_odds.ge(10) & output.p_place_advanced.notna()
    output.loc[longshot, "p_place"] = output.loc[longshot, "p_place_advanced"]
    output.drop(columns="p_place_advanced").to_csv(a.output, index=False)
    print(VERSION, "rows", len(output), "advanced longshots", int(longshot.sum()))


if __name__ == "__main__":
    main()
