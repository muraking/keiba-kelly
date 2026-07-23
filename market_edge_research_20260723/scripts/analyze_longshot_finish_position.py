"""Test whether longshot axes should be placed first, second, or third.

Position selection uses only prior years. Races are segmented by favorite
strength and field size, then the position with the best training LCB90 is
carried into the following year. No realized result is used for classification.

Version: v2026.07.24.1
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from search_longshot_edges import stats
from search_longshot_race_filters import PROFILES, build


VERSION = "v2026.07.24.1"
POSITIONS = {
    "first": "santan_first_2",
    "second": "santan_second_2",
    "third": "santan_third_2",
}
MIN_SEGMENT_RACES = 100


def favorite_band(value: float) -> str:
    if value < 0.45:
        return "weak"
    if value < 0.55:
        return "normal"
    return "strong"


def field_band(value: float) -> str:
    if value < 10:
        return "small"
    if value < 12:
        return "medium"
    return "large"


def run(oos_path: str, result_path: str, features_path: str) -> dict:
    records, _ = build(oos_path, result_path, features_path)
    scalar_names = (
        "year", "ratio", "pure", "delta", "odds", "market_rank",
        "partner_sum", "favorite_market", "field_size",
    )
    columns = {
        name: np.array([row[name] for row in records], dtype=float)
        for name in scalar_names
    }
    returns = {
        key: np.array([row["returns"][structure] for row in records], dtype=float)
        for key, structure in POSITIONS.items()
    }
    stakes = {
        key: np.array([row["stakes"][structure] for row in records], dtype=float)
        for key, structure in POSITIONS.items()
    }
    segments = np.array([
        f"{favorite_band(row['favorite_market'])}_{field_band(row['field_size'])}"
        for row in records
    ])

    def profile_mask(profile: dict, years: tuple[int, ...]) -> np.ndarray:
        selected = np.isin(columns["year"], years)
        selected &= columns["ratio"] >= profile["ratio"]
        selected &= columns["pure"] >= profile["pure"]
        selected &= columns["delta"] >= profile["delta"]
        selected &= columns["odds"] >= profile["odds_min"]
        selected &= columns["odds"] < profile["odds_max"]
        selected &= columns["market_rank"] >= profile["rank_min"]
        selected &= columns["partner_sum"] >= profile["partner"]
        return selected

    evaluations = []
    for profile in PROFILES:
        for test_year, train_years in ((2025, (2024,)), (2026, (2024, 2025))):
            train_base = profile_mask(profile, train_years)
            test_base = profile_mask(profile, (test_year,))
            decisions = []
            adaptive_returns = np.full(len(records), math.nan)
            adaptive_stakes = np.full(len(records), math.nan)

            for segment in sorted(set(segments)):
                train_segment = train_base & (segments == segment)
                choices = []
                for position in POSITIONS:
                    result = stats(
                        returns[position], stakes[position], train_segment
                    )
                    if result["races"] >= MIN_SEGMENT_RACES:
                        choices.append((result["lcb90"], position, result))
                if not choices:
                    continue
                choices.sort(reverse=True)
                _, position, train_result = choices[0]
                decision = "BET" if train_result["lcb90"] > 100 else "NO_BET"
                test_segment = test_base & (segments == segment)
                test_result = stats(
                    returns[position], stakes[position], test_segment
                )
                decisions.append({
                    "segment": segment,
                    "position": position,
                    "decision": decision,
                    "train": train_result,
                    "test": test_result,
                })
                if decision == "BET":
                    adaptive_returns[test_segment] = returns[position][test_segment]
                    adaptive_stakes[test_segment] = stakes[position][test_segment]

            eligible = np.isfinite(adaptive_stakes)
            adaptive = stats(
                adaptive_returns,
                adaptive_stakes,
                eligible,
            )
            fixed = {
                position: stats(
                    returns[position], stakes[position], test_base
                )
                for position in POSITIONS
            }
            evaluations.append({
                "profile": profile,
                "test_year": test_year,
                "decisions": decisions,
                "adaptive": adaptive,
                "fixed": fixed,
            })

    return {
        "version": VERSION,
        "records": len(records),
        "minimum_segment_races": MIN_SEGMENT_RACES,
        "method": "favorite strength x field size; prior-year LCB90 selection",
        "evaluations": evaluations,
        "limitations": [
            "segment and threshold discovery still require future shadow validation",
            "the position model uses race context, not a dedicated ordinal horse model",
        ],
    }


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: script OOS_CSV RESULT_DB FEATURES_DB OUTPUT_JSON")
    result = run(sys.argv[1], sys.argv[2], sys.argv[3])
    Path(sys.argv[4]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"version={VERSION} records={result['records']:,}")
    for item in result["evaluations"]:
        print(
            item["profile"]["name"],
            item["test_year"],
            "adaptive",
            item["adaptive"],
        )


if __name__ == "__main__":
    main()
