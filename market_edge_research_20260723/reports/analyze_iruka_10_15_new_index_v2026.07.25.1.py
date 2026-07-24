"""Test Iruka 10-15x subsets against the current leakage-safe JRA index.

Discovery: through 2023, validation: 2024, untouched OOS: 2025 onward.
Version: v2026.07.25.1
"""

from __future__ import annotations

import itertools
import sqlite3

import numpy as np
import pandas as pd


DB = r"C:\keiba\data\ai_index_jra.sqlite"


def metrics(frame: pd.DataFrame) -> tuple[int, int, float, float]:
    n = len(frame)
    hits = int(frame["is_win"].sum())
    returned = frame.loc[frame["is_win"] == 1, "tan_payout"].fillna(0).sum()
    return n, hits, hits / n * 100 if n else 0, returned / n if n else 0


def main() -> None:
    connection = sqlite3.connect(DB)
    frame = pd.read_sql_query(
        "SELECT race_id,date,p_pure_n,win_odds,popularity,is_win,tan_payout,is_iruka "
        "FROM ai_index",
        connection,
        parse_dates=["date"],
    )
    connection.close()
    for column in (
        "p_pure_n", "win_odds", "popularity", "is_win", "tan_payout", "is_iruka",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["date", "p_pure_n", "win_odds"])
    frame["ai_rank"] = frame.groupby("race_id")["p_pure_n"].rank(
        ascending=False, method="first"
    )
    frame["market_rank"] = frame.groupby("race_id")["win_odds"].rank(
        ascending=True, method="first"
    )
    frame["market_rank"] = frame["popularity"].fillna(frame["market_rank"])
    frame["rank_gap"] = frame["market_rank"] - frame["ai_rank"]
    frame["field"] = frame.groupby("race_id")["race_id"].transform("size")
    favorite = frame.groupby("race_id")["p_pure_n"].transform("max")
    frame["favorite_p"] = favorite
    base = frame[
        (frame["is_iruka"].fillna(0) > 0)
        & frame["win_odds"].between(10, 15, inclusive="left")
    ].copy()
    base["period"] = np.select(
        [base["date"].dt.year <= 2023, base["date"].dt.year == 2024],
        ["discover", "validate"],
        default="oos",
    )

    filters: list[tuple[str, pd.Series]] = [("ALL", pd.Series(True, index=base.index))]
    for value in (1, 2, 3, 4, 5, 6):
        filters.append((f"AI<={value}", base["ai_rank"] <= value))
    for value in (0, 1, 2, 3):
        filters.append((f"GAP>={value}", base["rank_gap"] >= value))
    for value in (.04, .05, .06, .07, .08, .10):
        filters.append((f"P>={value:.2f}", base["p_pure_n"] >= value))
    for value in (10, 12, 14):
        filters.append((f"FIELD>={value}", base["field"] >= value))
    for value in (.20, .25, .30, .35):
        filters.append((f"FAV<{value:.2f}", base["favorite_p"] < value))

    candidates = filters.copy()
    useful = [item for item in filters if item[0] != "ALL"]
    for (left_name, left), (right_name, right) in itertools.combinations(useful, 2):
        if left_name.split("<")[0].split(">")[0] == right_name.split("<")[0].split(">")[0]:
            continue
        candidates.append((f"{left_name}&{right_name}", left & right))

    rows = []
    for name, mask in candidates:
        subset = base[mask]
        result = {"rule": name}
        valid_candidate = True
        for period in ("discover", "validate", "oos"):
            n, hits, hit_rate, roi = metrics(subset[subset["period"] == period])
            result.update({
                f"{period}_n": n, f"{period}_hits": hits,
                f"{period}_hit_rate": hit_rate, f"{period}_roi": roi,
            })
            if period != "oos" and (n < 60 or hits < 5 or roi < 100):
                valid_candidate = False
        if valid_candidate:
            rows.append(result)
    result = pd.DataFrame(rows)
    print(f"BASE 10-15x: {len(base):,}")
    for period in ("discover", "validate", "oos"):
        print(period, metrics(base[base["period"] == period]))
    if result.empty:
        print("NO RULE passed discovery+validation prerequisites")
        return
    result = result.sort_values(
        ["oos_roi", "oos_hits", "oos_n"], ascending=[False, False, False]
    )
    print("\nRules fixed by discovery+validation; OOS shown only afterward:")
    print(result.head(30).to_string(index=False))
    print("\nYearly for OOS-positive rules:")
    for rule in result.loc[result["oos_roi"] >= 100, "rule"].head(10):
        mask = dict(candidates)[rule]
        print(f"\n{rule}")
        for year, group in base[mask].groupby(base.loc[mask, "date"].dt.year):
            print(year, metrics(group))


if __name__ == "__main__":
    main()
