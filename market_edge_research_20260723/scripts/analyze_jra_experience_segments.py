"""Test JRA market-role bets by race class, age, experience and data quality.

All segment definitions are fixed before looking at 2025. Each
regime/structure/segment is scored on 2024, and only the best 2024 LCB rule is
carried unchanged into the complete 2025 OOS period.

Version: v2026.07.24.2
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from analyze_jra_market_roles import build
from search_longshot_edges import stats


VERSION = "v2026.07.24.2"
MIN_TRAIN = 50


def race_group(name: str) -> str:
    text = str(name or "")
    if "新馬" in text:
        return "newcomer"
    if "未勝利" in text:
        return "maiden"
    if "1勝" in text or "500万" in text:
        return "class1"
    if "2勝" in text or "1000万" in text:
        return "class2"
    if "3勝" in text or "1600万" in text:
        return "class3"
    if any(word in text for word in (
        "オープン", "リステッド", "OP", "L", "GI", "GII", "GIII",
    )):
        return "open"
    return "other"


def exp_group(value: int) -> str:
    if value == 0:
        return "exp0"
    if value == 1:
        return "exp1"
    if value <= 3:
        return "exp2_3"
    return "exp4plus"


def enrich(records: list[dict], result_path: str, features_path: str) -> None:
    connection = sqlite3.connect(result_path)
    classes = {
        str(race_id): race_group(label)
        for race_id, label in connection.execute(
            "SELECT race_id, MAX(COALESCE(race_class, '') || ' ' || "
            "COALESCE(race_name, '')) FROM runs GROUP BY race_id"
        )
    }
    connection.close()

    connection = sqlite3.connect(features_path)
    by_race: dict[str, list[tuple]] = defaultdict(list)
    for row in connection.execute(
        "SELECT race_id, umaban, age, h_n_past, h_avg_pos3, h_avg_spd3 "
        "FROM features WHERE date >= '2024-01-01' AND date < '2026-01-01'"
    ):
        by_race[str(row[0])].append(row[1:])
    connection.close()

    for record in records:
        rows = by_race.get(record["race_id"], [])
        axis = next(
            (row for row in rows if int(row[0]) == int(record["axis_num"])),
            None,
        )
        past = int((axis[2] if axis else 0) or 0)
        experienced = [row for row in rows if int((row[2] or 0)) >= 2]
        complete = [
            row for row in rows
            if row[3] is not None and row[4] is not None
        ]
        record.update({
            "race_group": classes.get(record["race_id"], "other"),
            "axis_age": int((axis[1] if axis else 0) or 0),
            "axis_exp": past,
            "axis_exp_group": exp_group(past),
            "rookie_share": (
                sum(int((row[2] or 0)) <= 1 for row in rows) / len(rows)
                if rows else 1.0
            ),
            "experienced_share": len(experienced) / len(rows) if rows else 0.0,
            "complete_share": len(complete) / len(rows) if rows else 0.0,
        })


def segments() -> list[dict]:
    result = [{"name": "all", "checks": {}}]
    for value in ("newcomer", "maiden", "class1", "class2", "class3", "open", "other"):
        result.append({"name": f"race_{value}", "checks": {"race_group": value}})
    for value in ("exp0", "exp1", "exp2_3", "exp4plus"):
        result.append({"name": f"axis_{value}", "checks": {"axis_exp_group": value}})
    result.extend([
        {"name": "age2", "checks": {"axis_age": 2}},
        {"name": "age3", "checks": {"axis_age": 3}},
        {"name": "age4plus", "checks": {"axis_age_min": 4}},
        {"name": "rookie_low", "checks": {"rookie_max": 0.20}},
        {"name": "rookie_mid", "checks": {"rookie_min": 0.20, "rookie_max": 0.50}},
        {"name": "rookie_high", "checks": {"rookie_min": 0.50}},
        {"name": "coverage80", "checks": {"complete_min": 0.80}},
        {"name": "coverage60", "checks": {"complete_min": 0.60}},
        {"name": "experienced80", "checks": {"experienced_min": 0.80}},
    ])
    # Predeclared combinations that directly test the user's hypotheses.
    for race in ("newcomer", "maiden", "class1", "open"):
        for exp in ("exp0", "exp1", "exp2_3", "exp4plus"):
            result.append({
                "name": f"race_{race}__axis_{exp}",
                "checks": {"race_group": race, "axis_exp_group": exp},
            })
    for race in ("maiden", "class1", "open"):
        result.append({
            "name": f"race_{race}__coverage80",
            "checks": {"race_group": race, "complete_min": 0.80},
        })
    return result


def run(oos_path: str, result_path: str, features_path: str) -> dict:
    records, structures = build(oos_path, result_path, features_path)
    enrich(records, result_path, features_path)

    years = np.array([row["year"] for row in records])
    regimes = np.array([row["regime"] for row in records])
    returns = {
        name: np.array([row["returns"][name] for row in records], dtype=float)
        for name in structures
    }
    stakes = {
        name: np.array([row["stakes"][name] for row in records], dtype=float)
        for name in structures
    }

    def segment_mask(segment: dict, year: int, regime: str) -> np.ndarray:
        selected = (years == year) & (regimes == regime)
        checks = segment["checks"]
        for index, row in enumerate(records):
            if not selected[index]:
                continue
            ok = True
            for key, value in checks.items():
                if key == "axis_age_min":
                    ok &= row["axis_age"] >= value
                elif key == "rookie_min":
                    ok &= row["rookie_share"] >= value
                elif key == "rookie_max":
                    ok &= row["rookie_share"] < value
                elif key == "complete_min":
                    ok &= row["complete_share"] >= value
                elif key == "experienced_min":
                    ok &= row["experienced_share"] >= value
                else:
                    ok &= row[key] == value
            selected[index] = ok
        return selected

    evaluated = []
    for regime in ("nonfavorite_single_digit", "weak_favorite"):
        for segment in segments():
            train_mask = segment_mask(segment, 2024, regime)
            if int(train_mask.sum()) < MIN_TRAIN:
                continue
            test_mask = segment_mask(segment, 2025, regime)
            for structure in structures:
                train = stats(returns[structure], stakes[structure], train_mask)
                test = stats(returns[structure], stakes[structure], test_mask)
                if train["races"] >= MIN_TRAIN:
                    evaluated.append({
                        "regime": regime,
                        "segment": segment["name"],
                        "checks": segment["checks"],
                        "structure": structure,
                        "train": train,
                        "test": test,
                    })

    selected = []
    for regime in ("nonfavorite_single_digit", "weak_favorite"):
        for structure in structures:
            eligible = [
                item for item in evaluated
                if item["regime"] == regime and item["structure"] == structure
            ]
            if eligible:
                selected.append(max(
                    eligible,
                    key=lambda item: (item["train"]["lcb90"], item["train"]["roi"]),
                ))

    repeatable = [
        item for item in evaluated
        if item["train"]["roi"] > 100
        and item["test"]["roi"] > 100
        and item["test"]["races"] >= 40
    ]
    repeatable.sort(
        key=lambda item: (item["test"]["lcb90"], item["test"]["roi"]),
        reverse=True,
    )
    return {
        "version": VERSION,
        "records": len(records),
        "minimum_train_races": MIN_TRAIN,
        "selected_2024_then_2025": selected,
        "repeatable_posthoc": repeatable[:200],
        "limitations": [
            "segment definitions are predeclared but best-segment selection still has multiplicity",
            "repeatable_posthoc candidates are not live rules",
            "2026 or later untouched confirmation is mandatory",
        ],
    }


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: script OOS_CSV RESULT_DB FEATURES_DB OUTPUT_JSON")
    result = run(sys.argv[1], sys.argv[2], sys.argv[3])
    Path(sys.argv[4]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"version={VERSION} records={result['records']:,} "
        f"repeatable={len(result['repeatable_posthoc'])}"
    )


if __name__ == "__main__":
    main()
