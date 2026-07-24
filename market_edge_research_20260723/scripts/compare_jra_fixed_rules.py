"""Compare predeclared JRA betting rules on two OOS probability files.

The rule definitions are fixed in this file before the comparison is run.
This avoids selecting a different profitable grid cell for each model.

Version: v2026.07.24.1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

import analyze_jra_market_roles as market_roles
import analyze_jra_mid_odds as mid_odds
from search_longshot_edges import stats


VERSION = "v2026.07.24.1"

RULES = (
    {
        "name": "nonfavorite_5_10_sanfuku3",
        "analyzer": "market_roles",
        "structure": "sanfuku_3",
        "rule": {
            "regime": "nonfavorite_single_digit",
            "odds_min": 5,
            "odds_max": 10,
            "rank_min": 4,
            "rank_max": 11,
            "favorite_min": 0.0,
            "favorite_max": 1.01,
            "ratio": 1.20,
            "delta": 0.00,
            "partner": 0.45,
            "field_min": 12,
        },
    },
    {
        "name": "mid_8_15_tan1",
        "analyzer": "mid_odds",
        "structure": "tan_1",
        "rule": {
            "odds_min": 8,
            "odds_max": 15,
            "rank_min": 3,
            "rank_max": 7,
            "favorite_min": 0.0,
            "favorite_max": 0.35,
            "ratio": 1.20,
            "delta": 0.00,
            "partner": 0.45,
            "field_min": 12,
        },
    },
    {
        "name": "mid_10_20_wide2",
        "analyzer": "mid_odds",
        "structure": "wide_2",
        "rule": {
            "odds_min": 10,
            "odds_max": 20,
            "rank_min": 3,
            "rank_max": 7,
            "favorite_min": 0.0,
            "favorite_max": 0.35,
            "ratio": 1.20,
            "delta": 0.01,
            "partner": 0.45,
            "field_min": 0,
        },
    },
)


def selected_mask(records: list[dict], rule: dict, year: int) -> np.ndarray:
    selected = np.array([row["year"] == year for row in records])
    checks = (
        ("odds", ">=", rule["odds_min"]),
        ("odds", "<", rule["odds_max"]),
        ("rank", ">=", rule["rank_min"]),
        ("rank", "<", rule["rank_max"]),
        ("favorite_market", ">=", rule["favorite_min"]),
        ("favorite_market", "<", rule["favorite_max"]),
        ("ratio", ">=", rule["ratio"]),
        ("delta", ">=", rule["delta"]),
        ("partner_sum", ">=", rule["partner"]),
        ("field_size", ">=", rule["field_min"]),
    )
    for field, operator, threshold in checks:
        values = np.array([row[field] for row in records], dtype=float)
        selected &= values >= threshold if operator == ">=" else values < threshold
    if "regime" in rule:
        selected &= np.array([row["regime"] == rule["regime"] for row in records])
    return selected


def evaluate(records: list[dict], rule_spec: dict) -> dict:
    structure = rule_spec["structure"]
    returns = np.array(
        [row["returns"][structure] for row in records], dtype=float
    )
    stakes = np.array(
        [row["stakes"][structure] for row in records], dtype=float
    )
    return {
        str(year): stats(
            returns,
            stakes,
            selected_mask(records, rule_spec["rule"], year),
        )
        for year in (2024, 2025)
    }


def run(
    baseline_oos: str,
    enhanced_oos: str,
    result_db: str,
    features_db: str,
) -> dict:
    datasets = {}
    for model, oos_path in (
        ("baseline", baseline_oos),
        ("pedigree_training", enhanced_oos),
    ):
        built = {}
        for analyzer_name, analyzer in (
            ("market_roles", market_roles),
            ("mid_odds", mid_odds),
        ):
            built[analyzer_name], _ = analyzer.build(
                oos_path, result_db, features_db
            )
        datasets[model] = built

    comparisons = []
    for rule_spec in RULES:
        comparisons.append({
            "name": rule_spec["name"],
            "structure": rule_spec["structure"],
            "rule": rule_spec["rule"],
            "models": {
                model: evaluate(
                    datasets[model][rule_spec["analyzer"]], rule_spec
                )
                for model in datasets
            },
        })
    return {
        "version": VERSION,
        "comparison": "same fixed rules on baseline and pedigree/training OOS",
        "rules": comparisons,
        "limitations": [
            "uses final win odds and final tote payouts",
            "rules were motivated by prior grid exploration",
            "2026 untouched shadow validation is required before live use",
        ],
    }


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: script BASELINE_OOS ENHANCED_OOS RESULT_DB FEATURES_DB OUTPUT_JSON"
        )
    result = run(*sys.argv[1:5])
    Path(sys.argv[5]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
