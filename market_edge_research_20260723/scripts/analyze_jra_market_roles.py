"""Analyze two JRA market roles: non-favorite short odds and weak favorites.

The discovery year is 2024 and the complete OOS test year is 2025.

Version: v2026.07.24.2
"""

from __future__ import annotations

import itertools
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from search_longshot_edges import iter_races, stats, ticket_sets


VERSION = "v2026.07.24.2"
MIN_TRAIN_RACES = 100
MIN_WEAK_FAVORITE_RACES = 50


def build(oos_path: str, result_path: str, features_path: str):
    connection = sqlite3.connect(result_path)
    payouts = defaultdict(lambda: defaultdict(dict))
    for race_id, bet_type, comb, payout in connection.execute(
        "SELECT race_id, bet_type, comb, payout FROM payouts"
    ):
        payouts[str(race_id)][str(bet_type)][str(comb)] = int(payout)
    connection.close()

    connection = sqlite3.connect(features_path)
    win_payout = {
        (str(race_id), int(umaban)): int(payout or 0)
        for race_id, umaban, payout in connection.execute(
            "SELECT race_id, umaban, tan_payout FROM features "
            "WHERE date >= '2024-01-01' AND date < '2026-01-01'"
        )
    }
    connection.close()

    records = []
    structures = []
    for race_id, date, rows in iter_races(oos_path):
        if race_id not in payouts or len(rows) < 6 or date[:4] not in ("2024", "2025"):
            continue
        for row in rows:
            row["ratio"] = row["p_pure"] / max(row["p_market"], 1e-9)
            row["delta"] = row["p_pure"] - row["p_market"]
            row["rank"] = 1 + sum(
                other["p_market"] > row["p_market"] for other in rows
            )

        groups = {
            "nonfavorite_single_digit": [
                row for row in rows
                if 2.0 <= row["odds"] < 10.0 and 2 <= row["rank"] <= 10
            ],
            "weak_favorite": [
                row for row in rows
                if 3.0 <= row["odds"] < 8.0 and row["rank"] == 1
            ],
        }
        for regime, axes in groups.items():
            if not axes:
                continue
            axis = max(
                axes,
                key=lambda row: (row["delta"], row["p_pure"], -row["odds"]),
            )
            ranked = [
                row for row in sorted(
                    rows, key=lambda row: (-row["p_combo"], row["num"])
                )
                if row["num"] != axis["num"]
            ]
            if len(ranked) < 4:
                continue
            favorite = max(rows, key=lambda row: row["p_market"])
            tickets = ticket_sets(axis["num"], [row["num"] for row in ranked])
            tickets["tan_1"] = ("tan", [str(axis["num"])])
            if not structures:
                structures = list(tickets)
            returns, stakes = {}, {}
            for name, (bet_type, combinations_) in tickets.items():
                if name == "tan_1":
                    returns[name] = float(
                        win_payout.get((race_id, axis["num"]), 0)
                    )
                    stakes[name] = 100.0
                    continue
                available = payouts[race_id].get(bet_type)
                if not available:
                    returns[name] = math.nan
                    stakes[name] = math.nan
                else:
                    returns[name] = float(
                        sum(
                            available.get(ticket, 0)
                            for ticket in combinations_
                        )
                    )
                    stakes[name] = 100.0 * len(combinations_)
            records.append({
                "regime": regime,
                "year": int(date[:4]),
                "odds": axis["odds"],
                "rank": axis["rank"],
                "ratio": axis["ratio"],
                "delta": axis["delta"],
                "partner_sum": ranked[0]["p_combo"] + ranked[1]["p_combo"],
                "favorite_market": favorite["p_market"],
                "field_size": len(rows),
                "returns": returns,
                "stakes": stakes,
            })
    return records, structures


def rules():
    favorite_bands = (
        ("all", 0.0, 1.01),
        ("weak", 0.0, 0.35),
        ("normal", 0.35, 0.50),
        ("strong", 0.50, 1.01),
    )
    for odds, rank, favorite, ratio, delta, partner, field in itertools.product(
        ((2, 5), (3, 7), (4, 8), (5, 10)),
        ((2, 4), (2, 6), (3, 7), (4, 11)),
        favorite_bands,
        (1.00, 1.10, 1.20),
        (0.00, 0.01, 0.02),
        (0.35, 0.45, 0.55),
        (0, 12, 16),
    ):
        yield {
            "regime": "nonfavorite_single_digit",
            "odds_min": odds[0], "odds_max": odds[1],
            "rank_min": rank[0], "rank_max": rank[1],
            "favorite_band": favorite[0],
            "favorite_min": favorite[1], "favorite_max": favorite[2],
            "ratio": ratio, "delta": delta, "partner": partner,
            "field_min": field,
        }
    for odds, ratio, delta, partner, field in itertools.product(
        ((3, 4.5), (3.5, 5), (4, 6), (5, 8)),
        (0.90, 1.00, 1.10),
        (-0.03, 0.00, 0.01),
        (0.35, 0.45, 0.55),
        (0, 12, 16),
    ):
        yield {
            "regime": "weak_favorite",
            "odds_min": odds[0], "odds_max": odds[1],
            "rank_min": 1, "rank_max": 2,
            "favorite_band": "axis_is_favorite",
            "favorite_min": 0.0, "favorite_max": 1.01,
            "ratio": ratio, "delta": delta, "partner": partner,
            "field_min": field,
        }


def run(oos_path: str, result_path: str, features_path: str) -> dict:
    records, structures = build(oos_path, result_path, features_path)
    names = (
        "year", "odds", "rank", "ratio", "delta",
        "partner_sum", "favorite_market", "field_size",
    )
    columns = {
        name: np.array([row[name] for row in records], dtype=float)
        for name in names
    }
    regimes = np.array([row["regime"] for row in records])
    returns = {
        name: np.array([row["returns"][name] for row in records], dtype=float)
        for name in structures
    }
    stakes = {
        name: np.array([row["stakes"][name] for row in records], dtype=float)
        for name in structures
    }

    def mask(rule: dict, year: int):
        selected = regimes == rule["regime"]
        selected &= columns["year"] == year
        selected &= columns["odds"] >= rule["odds_min"]
        selected &= columns["odds"] < rule["odds_max"]
        selected &= columns["rank"] >= rule["rank_min"]
        selected &= columns["rank"] < rule["rank_max"]
        selected &= columns["favorite_market"] >= rule["favorite_min"]
        selected &= columns["favorite_market"] < rule["favorite_max"]
        selected &= columns["ratio"] >= rule["ratio"]
        selected &= columns["delta"] >= rule["delta"]
        selected &= columns["partner_sum"] >= rule["partner"]
        selected &= columns["field_size"] >= rule["field_min"]
        return selected

    candidates = []
    for rule in rules():
        train_mask = mask(rule, 2024)
        minimum = (
            MIN_WEAK_FAVORITE_RACES
            if rule["regime"] == "weak_favorite"
            else MIN_TRAIN_RACES
        )
        if int(train_mask.sum()) < minimum:
            continue
        for structure in structures:
            train = stats(returns[structure], stakes[structure], train_mask)
            if train["races"] < minimum:
                continue
            test = stats(
                returns[structure], stakes[structure], mask(rule, 2025)
            )
            candidates.append({
                "structure": structure,
                "rule": rule,
                "train": train,
                "test": test,
            })

    selected = []
    for regime in ("nonfavorite_single_digit", "weak_favorite"):
        for structure in structures:
            eligible = [
                item for item in candidates
                if item["rule"]["regime"] == regime
                and item["structure"] == structure
            ]
            if eligible:
                selected.append(max(
                    eligible,
                    key=lambda item: (
                        item["train"]["lcb90"],
                        item["train"]["roi"],
                    ),
                ))

    repeatable = [
        item for item in candidates
        if item["train"]["roi"] > 100
        and item["test"]["roi"] > 100
        and item["test"]["races"] >= (
            40
            if item["rule"]["regime"] == "weak_favorite"
            else 75
        )
    ]
    repeatable.sort(
        key=lambda item: (
            item["test"]["lcb90"],
            item["test"]["roi"],
        ),
        reverse=True,
    )
    return {
        "version": VERSION,
        "records": len(records),
        "minimum_train_races": MIN_TRAIN_RACES,
        "minimum_weak_favorite_races": MIN_WEAK_FAVORITE_RACES,
        "selected_by_regime_and_structure": selected,
        "repeatable_candidates": repeatable[:150],
        "limitations": [
            "rules are searched on one training year",
            "repeatable candidates use 2025 for post-hoc discovery",
            "2026 confirmation is required before live adoption",
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
        f"repeatable={len(result['repeatable_candidates'])}"
    )
    print(json.dumps(
        result["selected_by_regime_and_structure"],
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
