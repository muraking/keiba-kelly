"""Find all-odds Iruka patterns using the pedigree/training JRA OOS index.

Discovery: 2024 H1, validation: 2024 H2, untouched OOS: 2025.
Odds are used only to calculate market rank/return, never as a selection band.
Version: v2026.07.25.1
"""

from __future__ import annotations

import itertools
import sqlite3

import pandas as pd


OOS = r"C:\keiba\codex_display_test\jra_enhanced_iruka_oos.csv"
INDEX_DB = r"C:\keiba\data\ai_index_jra.sqlite"


def metrics(frame: pd.DataFrame) -> tuple[int, int, float, float]:
    n = len(frame)
    hits = int(frame["is_win"].sum())
    returned = frame.loc[frame["is_win"] == 1, "tan_payout"].fillna(0).sum()
    return n, hits, hits / n * 100 if n else 0, returned / n if n else 0


def main() -> None:
    frame = pd.read_csv(OOS, parse_dates=["date"])
    connection = sqlite3.connect(INDEX_DB)
    iruka = pd.read_sql_query(
        "SELECT race_id,umaban,is_iruka FROM ai_index", connection
    )
    connection.close()
    frame["race_id"] = frame["race_id"].astype(str)
    iruka["race_id"] = iruka["race_id"].astype(str)
    frame["umaban"] = pd.to_numeric(frame["umaban"], errors="coerce").astype("Int64")
    iruka["umaban"] = pd.to_numeric(iruka["umaban"], errors="coerce").astype("Int64")
    iruka = iruka.drop_duplicates(["race_id", "umaban"], keep="last")
    frame = frame.merge(iruka, on=["race_id", "umaban"], how="left")
    frame = frame[frame["is_iruka"].fillna(0) > 0].copy()
    frame["ai_rank"] = frame.groupby("race_id")["p_struct"].rank(
        ascending=False, method="first"
    )
    frame["combo_rank"] = frame.groupby("race_id")["p_combo"].rank(
        ascending=False, method="first"
    )
    frame["market_rank"] = frame.groupby("race_id")["win_odds"].rank(
        ascending=True, method="first"
    )
    frame["market_rank"] = frame["popularity"].fillna(frame["market_rank"])
    frame["rank_gap"] = frame["market_rank"] - frame["ai_rank"]
    frame["combo_gap"] = frame["market_rank"] - frame["combo_rank"]
    frame["field"] = frame.groupby("race_id")["race_id"].transform("size")
    frame["favorite_p"] = frame.groupby("race_id")["p_market"].transform("max")
    frame["period"] = "oos"
    frame.loc[
        (frame["date"].dt.year == 2024) & (frame["date"].dt.month <= 6), "period"
    ] = "discover"
    frame.loc[
        (frame["date"].dt.year == 2024) & (frame["date"].dt.month > 6), "period"
    ] = "validate"

    filters: list[tuple[str, pd.Series]] = [
        ("ALL", pd.Series(True, index=frame.index))
    ]
    for value in (1, 2, 3, 4, 5, 6):
        filters += [
            (f"STRUCT_RANK<={value}", frame["ai_rank"] <= value),
            (f"COMBO_RANK<={value}", frame["combo_rank"] <= value),
        ]
    for value in (0, 1, 2, 3):
        filters += [
            (f"STRUCT_GAP>={value}", frame["rank_gap"] >= value),
            (f"COMBO_GAP>={value}", frame["combo_gap"] >= value),
        ]
    for value in (.04, .05, .06, .07, .08, .10, .12):
        filters += [
            (f"STRUCT_P>={value:.2f}", frame["p_struct"] >= value),
            (f"COMBO_P>={value:.2f}", frame["p_combo"] >= value),
        ]
    for value in (.00, .01, .02, .03):
        filters.append((f"DELTA>={value:.2f}", frame["delta"] >= value))
    for value in (10, 12, 14):
        filters.append((f"FIELD>={value}", frame["field"] >= value))
    for value in (.20, .25, .30, .35):
        filters.append((f"FAVORITE<{value:.2f}", frame["favorite_p"] < value))

    candidates = filters.copy()
    useful = [item for item in filters if item[0] != "ALL"]
    for (left_name, left), (right_name, right) in itertools.combinations(useful, 2):
        left_family = left_name.split("<")[0].split(">")[0]
        right_family = right_name.split("<")[0].split(">")[0]
        if left_family == right_family:
            continue
        candidates.append((f"{left_name}&{right_name}", left & right))

    rows = []
    for name, mask in candidates:
        subset = frame[mask]
        row = {"rule": name}
        acceptable = True
        for period in ("discover", "validate", "oos"):
            n, hits, hit_rate, roi = metrics(subset[subset["period"] == period])
            row.update({
                f"{period}_n": n, f"{period}_hits": hits,
                f"{period}_hit_rate": hit_rate, f"{period}_roi": roi,
            })
            if period != "oos" and (n < 100 or hits < 8 or roi < 100):
                acceptable = False
        if acceptable:
            rows.append(row)

    print(f"IRUKA enhanced OOS rows: {len(frame):,}")
    for period in ("discover", "validate", "oos"):
        print(period, metrics(frame[frame["period"] == period]))
    result = pd.DataFrame(rows)
    if result.empty:
        print("NO RULE passed both discovery and validation.")
        return
    result = result.sort_values(
        ["oos_roi", "oos_hits", "oos_n"], ascending=[False, False, False]
    )
    print("\nRules that passed discovery and validation (all odds):")
    print(result.head(40).to_string(index=False))
    stable = result[
        (result["oos_roi"] >= 100)
        & (result["oos_n"] >= 100)
        & (result["oos_hits"] >= 8)
    ]
    print("\nStable three-period candidates:")
    print(stable.head(20).to_string(index=False) if len(stable) else "NONE")


if __name__ == "__main__":
    main()
