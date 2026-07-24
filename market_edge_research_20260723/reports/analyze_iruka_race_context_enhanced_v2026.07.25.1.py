"""Test Iruka presence as race context for enhanced-index win selections.

Discovery: 2024 H1, validation: 2024 H2, untouched OOS: 2025.
Version: v2026.07.25.1
"""

from __future__ import annotations

import itertools
import sqlite3

import numpy as np
import pandas as pd


OOS = r"C:\keiba\codex_display_test\jra_enhanced_iruka_oos.csv"
DB = r"C:\keiba\data\ai_index_jra.sqlite"


def metrics(frame: pd.DataFrame) -> tuple[int, int, float, float]:
    n = len(frame)
    hits = int(frame["is_win"].sum())
    returned = frame.loc[frame["is_win"] == 1, "tan_payout"].fillna(0).sum()
    return n, hits, hits / n * 100 if n else 0, returned / n if n else 0


def main() -> None:
    frame = pd.read_csv(OOS, parse_dates=["date"])
    with sqlite3.connect(DB) as connection:
        flags = pd.read_sql_query(
            "SELECT race_id,umaban,is_iruka FROM ai_index", connection
        )
    for value in (frame, flags):
        value["race_id"] = value["race_id"].astype(str)
        value["umaban"] = pd.to_numeric(value["umaban"], errors="coerce").astype("Int64")
    flags = flags.drop_duplicates(["race_id", "umaban"], keep="last")
    frame = frame.merge(flags, on=["race_id", "umaban"], how="left")
    frame["is_iruka"] = frame["is_iruka"].fillna(0)
    frame["struct_rank"] = frame.groupby("race_id")["p_struct"].rank(
        ascending=False, method="first"
    )
    frame["market_rank"] = frame.groupby("race_id")["win_odds"].rank(
        ascending=True, method="first"
    )
    frame["market_rank"] = frame["popularity"].fillna(frame["market_rank"])
    frame["field"] = frame.groupby("race_id")["race_id"].transform("size")
    iruka = frame[frame["is_iruka"] > 0].copy()
    iruka = iruka.sort_values(["race_id", "p_struct"], ascending=[True, False])
    iruka = iruka.drop_duplicates("race_id")
    context = iruka.set_index("race_id")[[
        "struct_rank", "market_rank", "p_struct", "p_market", "win_odds",
    ]].rename(columns=lambda column: f"iruka_{column}")
    frame = frame.join(context, on="race_id", how="inner")
    frame["iruka_gap"] = frame["iruka_market_rank"] - frame["iruka_struct_rank"]
    frame["period"] = "oos"
    frame.loc[
        (frame["date"].dt.year == 2024) & (frame["date"].dt.month <= 6), "period"
    ] = "discover"
    frame.loc[
        (frame["date"].dt.year == 2024) & (frame["date"].dt.month > 6), "period"
    ] = "validate"

    contexts: list[tuple[str, pd.Series]] = [
        ("ALL_IRUKA_RACES", pd.Series(True, index=frame.index)),
    ]
    for value in (1, 2, 3, 4, 5, 6):
        contexts.append((f"IRUKA_STRUCT<={value}", frame["iruka_struct_rank"] <= value))
    for value in (0, 1, 2, 3):
        contexts.append((f"IRUKA_GAP>={value}", frame["iruka_gap"] >= value))
    for value in (.04, .05, .06, .08, .10):
        contexts.append((f"IRUKA_P>={value:.2f}", frame["iruka_p_struct"] >= value))
    for value in (10, 12, 14):
        contexts.append((f"FIELD>={value}", frame["field"] >= value))

    selectors = [
        ("STRUCT_TOP1", frame["struct_rank"] == 1),
        ("STRUCT_TOP2", frame["struct_rank"] == 2),
        ("STRUCT_TOP3", frame["struct_rank"] == 3),
        ("STRUCT_TOP1_NON_IRUKA", (frame["struct_rank"] == 1) & (frame["is_iruka"] == 0)),
        ("STRUCT_TOP2_NON_IRUKA", (frame["struct_rank"] == 2) & (frame["is_iruka"] == 0)),
    ]
    rows = []
    for select_name, select_mask in selectors:
        candidate_contexts = contexts.copy()
        for (left_name, left), (right_name, right) in itertools.combinations(
            contexts[1:], 2
        ):
            if left_name.split("<")[0].split(">")[0] == right_name.split("<")[0].split(">")[0]:
                continue
            candidate_contexts.append((f"{left_name}&{right_name}", left & right))
        for context_name, context_mask in candidate_contexts:
            subset = frame[select_mask & context_mask]
            row = {"rule": f"{select_name}|{context_name}"}
            passed = True
            for period in ("discover", "validate", "oos"):
                n, hits, hit_rate, roi = metrics(subset[subset["period"] == period])
                row.update({
                    f"{period}_n": n, f"{period}_hits": hits,
                    f"{period}_hit_rate": hit_rate, f"{period}_roi": roi,
                })
                if period != "oos" and (n < 80 or hits < 8 or roi < 100):
                    passed = False
            if passed:
                rows.append(row)
    result = pd.DataFrame(rows)
    print(f"RACES WITH IRUKA: {frame['race_id'].nunique():,}")
    if result.empty:
        print("NO race-context rule passed discovery+validation.")
        return
    result = result.sort_values(
        ["oos_roi", "oos_hits", "oos_n"], ascending=[False, False, False]
    )
    print(result.head(40).to_string(index=False))
    print("\nThree-period >=100:")
    stable = result[result["oos_roi"] >= 100]
    print(stable.head(20).to_string(index=False) if len(stable) else "NONE")
    if len(stable):
        print("\nRisk audit:")
        rng = np.random.default_rng(20260725)
        candidate_lookup = {}
        for select_name, select_mask in selectors:
            for context_name, context_mask in contexts:
                candidate_lookup[f"{select_name}|{context_name}"] = (
                    select_mask & context_mask
                )
            for (left_name, left), (right_name, right) in itertools.combinations(
                contexts[1:], 2
            ):
                if left_name.split("<")[0].split(">")[0] == right_name.split("<")[0].split(">")[0]:
                    continue
                candidate_lookup[
                    f"{select_name}|{left_name}&{right_name}"
                ] = select_mask & left & right
        for rule in stable["rule"].head(10):
            subset = frame[candidate_lookup[rule]].copy()
            returns = np.where(
                subset["is_win"] == 1, subset["tan_payout"].fillna(0), 0
            ).astype(float)
            simulations = returns[
                rng.integers(0, len(returns), size=(10000, len(returns)))
            ].mean(axis=1)
            oos = subset[subset["period"] == "oos"]
            print(
                rule,
                f"all={metrics(subset)}",
                f"LCB90={np.quantile(simulations, .05):.1f}%",
                f"selected_iruka={subset['is_iruka'].mean():.1%}",
                f"avg_selected_odds={subset['win_odds'].mean():.1f}",
                f"OOS_max_payout_share="
                f"{oos['tan_payout'].fillna(0).max() / max(1, oos.loc[oos['is_win'] == 1, 'tan_payout'].fillna(0).sum()):.1%}",
            )


if __name__ == "__main__":
    main()
