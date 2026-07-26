"""Expanded local win-top x longshot umaren/wide market-structure search.

Uses 2024 for discovery, 2025 for validation, and 2026 for confirmation.
No outcome or payout value is used to select a ticket.
Version: v2026.07.27.2
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


VERSION = "v2026.07.27.2"
PAIR_SCRIPT = Path(__file__).with_name(
    "search_win_hole_pair_bets_v2026.07.27.1.py"
)
SPEC = importlib.util.spec_from_file_location("pair_search", PAIR_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {PAIR_SCRIPT}")
PAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAIR)

CONTEXT = (
    "top1_p_bin", "top2_p_bin", "gap_bin", "top2_sum_bin", "p_std_bin",
    "entropy_bin", "fav_odds_bin", "ai_top1_odds_bin", "ai_top1_pop_bin",
    "longshot_count_bin", "distance_bin", "class_bucket", "surface",
    "race_num_bin", "field_bin",
)
SPECS = []
for context in CONTEXT:
    SPECS.extend((
        ("bet_type", "hole_rank", "partner_rank", context),
        ("bet_type", "hole_rank", "partner_rank", "product_bin", context),
        ("bet_type", "hole_rank", "partner_rank", "hole_odds_bin", context),
    ))
for left, right in (
    ("top1_p_bin", "gap_bin"),
    ("top1_p_bin", "fav_odds_bin"),
    ("top2_sum_bin", "fav_odds_bin"),
    ("p_std_bin", "fav_odds_bin"),
    ("entropy_bin", "fav_odds_bin"),
    ("longshot_count_bin", "fav_odds_bin"),
    ("field_bin", "fav_odds_bin"),
    ("race_num_bin", "fav_odds_bin"),
    ("distance_bin", "fav_odds_bin"),
):
    SPECS.append(("bet_type", "hole_rank", "partner_rank", left, right))
for context in (
    "top1_p_bin", "gap_bin", "top2_sum_bin", "p_std_bin", "entropy_bin",
    "fav_odds_bin", "ai_top1_odds_bin", "distance_bin", "class_bucket",
    "race_num_bin",
):
    SPECS.append(("bet_type", "hole_rank", "partner_rank", "venue", context))
SPECS = tuple(SPECS)


def cut(series: pd.Series, edges: list[float], labels: list[str]) -> pd.Series:
    return pd.cut(series, edges, right=False, labels=labels)


def class_bucket(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    if "2歳" in text:
        return "2yo"
    if "3歳" in text:
        return "3yo"
    if "重賞" in text or text in {"G1", "G2", "G3", "Jpn1", "Jpn2", "Jpn3"}:
        return "graded"
    if text.startswith("A"):
        return "A"
    if text.startswith("B"):
        return "B"
    if text.startswith("C"):
        return "C"
    return "other"


def race_features(oos: Path, db: Path) -> pd.DataFrame:
    data = pd.read_csv(oos)
    data["race_id"] = data["race_id"].astype(str)
    rows = []
    for race_id, group in data.groupby("race_id", sort=False):
        ordered = group.sort_values(["p_win", "umaban"], ascending=[False, True])
        probabilities = group["p_win"].clip(lower=1e-12).to_numpy(dtype=float)
        normalized = probabilities / probabilities.sum()
        entropy = -float(np.sum(normalized * np.log(normalized)))
        entropy /= np.log(len(normalized)) if len(normalized) > 1 else 1.0
        top1, top2 = ordered.iloc[0], ordered.iloc[min(1, len(ordered) - 1)]
        favorite = group.sort_values(
            ["win_odds", "umaban"], ascending=[True, True]
        ).iloc[0]
        rows.append({
            "race_id": str(race_id),
            "top1_p": float(top1.p_win),
            "top2_p": float(top2.p_win),
            "gap": float(top1.p_win - top2.p_win),
            "top2_sum": float(top1.p_win + top2.p_win),
            "p_std": float(group["p_win"].std(ddof=0)),
            "entropy": entropy,
            "fav_odds": float(favorite.win_odds),
            "ai_top1_odds": float(top1.win_odds),
            "ai_top1_pop": float(top1.popularity),
            "longshot_count": int(group["win_odds"].ge(10).sum()),
        })
    features = pd.DataFrame(rows)
    with sqlite3.connect(db) as connection:
        meta = pd.read_sql_query(
            """
            SELECT race_id, MAX(distance) AS distance, MAX(surface) AS surface,
                   MAX(race_class) AS race_class
            FROM runs
            GROUP BY race_id
            """,
            connection,
        )
    meta["race_id"] = meta["race_id"].astype(str)
    features = features.merge(meta, on="race_id", how="left")
    features["class_bucket"] = features["race_class"].map(class_bucket)
    features["top1_p_bin"] = cut(
        features["top1_p"], [-np.inf, .20, .30, .40, .50, np.inf],
        ["<.20", ".20-.30", ".30-.40", ".40-.50", ".50+"],
    )
    features["top2_p_bin"] = cut(
        features["top2_p"], [-np.inf, .10, .15, .20, .25, np.inf],
        ["<.10", ".10-.15", ".15-.20", ".20-.25", ".25+"],
    )
    features["gap_bin"] = cut(
        features["gap"], [-np.inf, .05, .10, .20, np.inf],
        ["<.05", ".05-.10", ".10-.20", ".20+"],
    )
    features["top2_sum_bin"] = cut(
        features["top2_sum"], [-np.inf, .35, .45, .55, .65, np.inf],
        ["<.35", ".35-.45", ".45-.55", ".55-.65", ".65+"],
    )
    features["p_std_bin"] = cut(
        features["p_std"], [-np.inf, .03, .05, .08, .12, np.inf],
        ["<.03", ".03-.05", ".05-.08", ".08-.12", ".12+"],
    )
    features["entropy_bin"] = cut(
        features["entropy"], [-np.inf, .65, .75, .85, .92, np.inf],
        ["<.65", ".65-.75", ".75-.85", ".85-.92", ".92+"],
    )
    odds_edges = [-np.inf, 1.5, 2.0, 3.0, 5.0, np.inf]
    odds_labels = ["<1.5", "1.5-2", "2-3", "3-5", "5+"]
    features["fav_odds_bin"] = cut(features["fav_odds"], odds_edges, odds_labels)
    features["ai_top1_odds_bin"] = cut(
        features["ai_top1_odds"], odds_edges, odds_labels
    )
    features["ai_top1_pop_bin"] = cut(
        features["ai_top1_pop"], [-np.inf, 1.5, 2.5, 3.5, 5.5, np.inf],
        ["1", "2", "3", "4-5", "6+"],
    )
    features["longshot_count_bin"] = cut(
        features["longshot_count"], [-np.inf, 3, 6, 9, np.inf],
        ["0-2", "3-5", "6-8", "9+"],
    )
    features["distance_bin"] = cut(
        features["distance"], [-np.inf, 1201, 1601, 2001, np.inf],
        ["<=1200", "1201-1600", "1601-2000", "2001+"],
    )
    return features


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tickets = PAIR.build(args.oos, args.db)
    features = race_features(args.oos, args.db)
    data = tickets.merge(features, on="race_id", how="left")
    exploratory_minimum = 100
    minimum_24_25 = 200
    minimum_26 = 100
    candidates = []
    for columns in SPECS:
        groups = {
            year: {
                key if isinstance(key, tuple) else (key,): group
                for key, group in data[data["year"].eq(year)].groupby(
                    list(columns), observed=True
                )
            }
            for year in (2024, 2025, 2026)
        }
        for key, group24 in groups[2024].items():
            m24 = PAIR.metrics(group24)
            if (
                m24["bets"] < exploratory_minimum
                or m24["roi"] < 100
                or m24["roi_without_max"] < 95
                or m24["max_share"] is None
                or m24["max_share"] > .20
            ):
                continue
            candidates.append({
                "condition": {
                    column: str(value) for column, value in zip(columns, key)
                },
                "2024": m24,
                "2025": PAIR.metrics(groups[2025].get(key, data.iloc[0:0])),
                "2026": PAIR.metrics(groups[2026].get(key, data.iloc[0:0])),
            })
    validated = [
        row for row in candidates
        if row["2024"]["roi_without_max"] >= 100
        and row["2025"]["bets"] >= minimum_24_25
        and row["2025"]["roi"] >= 100
        and row["2025"]["roi_without_max"] >= 100
    ]
    confirmed = [
        row for row in validated
        if row["2026"]["bets"] >= minimum_26
        and row["2026"]["roi"] >= 100
        and row["2026"]["roi_without_max"] >= 100
    ]
    positive_three_year = [
        row for row in candidates
        if row["2024"]["bets"] >= minimum_24_25
        and row["2025"]["bets"] >= minimum_24_25
        and row["2026"]["bets"] >= minimum_26
        and all(row[year]["roi"] >= 100 for year in ("2024", "2025", "2026"))
    ]
    exploratory_confirmed = [
        row for row in candidates
        if row["2024"]["bets"] >= exploratory_minimum
        and row["2025"]["bets"] >= exploratory_minimum
        and row["2026"]["bets"] >= 50
        and all(
            row[year]["roi"] >= 100 and row[year]["roi_without_max"] >= 100
            for year in ("2024", "2025", "2026")
        )
    ]
    confirmed.sort(
        key=lambda row: min(
            row[year]["roi_without_max"] for year in ("2024", "2025", "2026")
        ),
        reverse=True,
    )
    validated.sort(
        key=lambda row: min(
            row[year]["roi_without_max"] for year in ("2024", "2025")
        ),
        reverse=True,
    )
    positive_three_year.sort(
        key=lambda row: min(row[year]["roi"] for year in ("2024", "2025", "2026")),
        reverse=True,
    )
    exploratory_confirmed.sort(
        key=lambda row: min(
            row[year]["roi_without_max"] for year in ("2024", "2025", "2026")
        ),
        reverse=True,
    )
    result = {
        "version": VERSION,
        "ticket_rows": int(len(data)),
        "feature_count": len(CONTEXT),
        "spec_count": len(SPECS),
        "discovery_candidates": len(candidates),
        "validated_2025": len(validated),
        "confirmed_2026": len(confirmed),
        "positive_three_year_before_max_exclusion": len(positive_three_year),
        "exploratory_confirmed_min100_100_50": len(exploratory_confirmed),
        "best_confirmed": confirmed[:200],
        "best_positive_three_year": positive_three_year[:200],
        "best_exploratory_confirmed": exploratory_confirmed[:200],
        "best_validated": validated[:200],
        "note": "2024 discovery, 2025 validation, local 2026 confirmation",
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "rows", len(data), "specs", len(SPECS), "candidates", len(candidates),
        "validated", len(validated), "confirmed", len(confirmed),
    )
    for row in confirmed[:30]:
        print(
            row["condition"],
            [
                (
                    year, row[year]["bets"], round(row[year]["roi"], 1),
                    round(row[year]["roi_without_max"], 1),
                    round(row[year]["lcb90"], 3),
                )
                for year in ("2024", "2025", "2026")
            ],
        )


if __name__ == "__main__":
    main()
