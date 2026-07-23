"""Analyze JRA mid-priced axes with explicit bet and skip rules.

Rules are selected on 2024 only and evaluated on the complete 2025 OOS year.
One axis per race is chosen among 4-20 odds and market ranks 2-10.

Version: v2026.07.24.1
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


VERSION = "v2026.07.24.1"
MIN_TRAIN_RACES = 100


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
        axes = [
            row for row in rows
            if 4.0 <= row["odds"] < 20.0 and 2 <= row["rank"] <= 10
        ]
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
                returns[name] = float(win_payout.get((race_id, axis["num"]), 0))
                stakes[name] = 100.0
                continue
            available = payouts[race_id].get(bet_type)
            if not available:
                returns[name] = math.nan
                stakes[name] = math.nan
            else:
                returns[name] = float(
                    sum(available.get(ticket, 0) for ticket in combinations_)
                )
                stakes[name] = 100.0 * len(combinations_)
        records.append({
            "year": int(date[:4]),
            "odds": axis["odds"],
            "rank": axis["rank"],
            "ratio": axis["ratio"],
            "pure": axis["p_pure"],
            "delta": axis["delta"],
            "partner_sum": ranked[0]["p_combo"] + ranked[1]["p_combo"],
            "favorite_market": favorite["p_market"],
            "field_size": len(rows),
            "returns": returns,
            "stakes": stakes,
        })
    return records, structures


def rules():
    odds_bands = ((4, 8), (5, 10), (7, 12), (8, 15), (10, 20))
    rank_bands = ((2, 5), (3, 7), (4, 9), (5, 11))
    favorite_bands = (
        ("all", 0.0, 1.01),
        ("weak", 0.0, 0.35),
        ("normal", 0.35, 0.50),
        ("strong", 0.50, 1.01),
    )
    for odds, rank, favorite, ratio, delta, partner, field in itertools.product(
        odds_bands,
        rank_bands,
        favorite_bands,
        (1.00, 1.10, 1.20),
        (0.00, 0.01, 0.02),
        (0.35, 0.45, 0.55),
        (0, 12, 16),
    ):
        yield {
            "odds_min": odds[0], "odds_max": odds[1],
            "rank_min": rank[0], "rank_max": rank[1],
            "favorite_band": favorite[0],
            "favorite_min": favorite[1], "favorite_max": favorite[2],
            "ratio": ratio, "delta": delta, "partner": partner,
            "field_min": field,
        }


def run(oos_path: str, result_path: str, features_path: str) -> dict:
    records, structures = build(oos_path, result_path, features_path)
    names = (
        "year", "odds", "rank", "ratio", "pure", "delta",
        "partner_sum", "favorite_market", "field_size",
    )
    columns = {
        name: np.array([row[name] for row in records], dtype=float)
        for name in names
    }
    returns = {
        name: np.array([row["returns"][name] for row in records], dtype=float)
        for name in structures
    }
    stakes = {
        name: np.array([row["stakes"][name] for row in records], dtype=float)
        for name in structures
    }

    def mask(rule: dict, year: int):
        selected = columns["year"] == year
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
        if int(train_mask.sum()) < MIN_TRAIN_RACES:
            continue
        for structure in structures:
            train = stats(returns[structure], stakes[structure], train_mask)
            if train["races"] < MIN_TRAIN_RACES:
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

    selected_by_structure = []
    for structure in structures:
        eligible = [
            item for item in candidates if item["structure"] == structure
        ]
        if not eligible:
            continue
        selected_by_structure.append(max(
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
        and item["test"]["races"] >= 75
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
        "selected_by_structure": selected_by_structure,
        "repeatable_candidates": repeatable[:100],
        "limitations": [
            "rules are searched on one training year",
            "2025 is the only complete independent JRA payout year",
            "future shadow validation remains mandatory",
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
    print(json.dumps(result["selected_by_structure"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
