"""Search race-quality filters before placing longshot-axis bets.

The longshot profiles are fixed from prior analysis. This stage searches only
race participation segments: favorite strength, field size, two-year-old races,
and historical-data coverage. Each segment can be included, excluded, or left
unrestricted. Selection is nested walk-forward.

Version: v2026.07.23.3
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


VERSION = "v2026.07.23.3"
MIN_DISCOVERY_RACES = 200
PROFILES = (
    {
        "name": "broad",
        "ratio": 1.10, "pure": 0.03, "odds_min": 5.0, "odds_max": 50.0,
        "delta": 0.00, "rank_min": 2, "partner": 0.35,
    },
    {
        "name": "danger_first",
        "ratio": 1.10, "pure": 0.05, "odds_min": 5.0, "odds_max": 20.0,
        "delta": 0.01, "rank_min": 4, "partner": 0.55,
    },
    {
        "name": "quality",
        "ratio": 1.25, "pure": 0.08, "odds_min": 5.0, "odds_max": 30.0,
        "delta": 0.02, "rank_min": 4, "partner": 0.45,
    },
    {
        "name": "deep",
        "ratio": 1.50, "pure": 0.05, "odds_min": 10.0, "odds_max": 30.0,
        "delta": 0.01, "rank_min": 4, "partner": 0.45,
    },
)


def contexts(features_path: str) -> dict[str, dict]:
    connection = sqlite3.connect(features_path)
    result = {}
    query = (
        "SELECT race_id, MAX(field_size), MAX(age), AVG(h_n_past), "
        "AVG(CASE WHEN h_n_past >= 3 THEN 1.0 ELSE 0.0 END), "
        "AVG(CASE WHEN h_n_past >= 5 THEN 1.0 ELSE 0.0 END), COUNT(*) "
        "FROM features GROUP BY race_id"
    )
    for race_id, field, max_age, avg_past, cover3, cover5, count in connection.execute(query):
        result[str(race_id)] = {
            "field_size": int(field or count),
            "all_two_year": int(max_age or 0) <= 2,
            "avg_past": float(avg_past or 0.0),
            "cover3": float(cover3 or 0.0),
            "cover5": float(cover5 or 0.0),
        }
    connection.close()
    return result


def build(oos_path: str, result_path: str, features_path: str):
    context = contexts(features_path)
    connection = sqlite3.connect(result_path)
    payouts: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for race_id, bet_type, comb, payout in connection.execute(
        "SELECT race_id, bet_type, comb, payout FROM payouts"
    ):
        payouts[str(race_id)][str(bet_type)][str(comb)] = int(payout)
    connection.close()

    records = []
    structures = []
    for race_id, date, rows in iter_races(oos_path):
        if race_id not in payouts or race_id not in context or len(rows) < 6:
            continue
        for row in rows:
            row["ratio"] = row["p_pure"] / max(row["p_market"], 1e-9)
            row["delta"] = row["p_pure"] - row["p_market"]
        universal = [
            row for row in rows
            if row["ratio"] >= 1.10 and row["p_pure"] >= 0.03
            and 5.0 <= row["odds"] < 50.0
        ]
        if not universal:
            continue
        axis = max(universal, key=lambda row: (row["delta"], row["p_pure"], -row["odds"]))
        ranked = [
            row for row in sorted(rows, key=lambda row: (-row["p_combo"], row["num"]))
            if row["num"] != axis["num"]
        ]
        if len(ranked) < 4:
            continue
        favorite = max(rows, key=lambda row: row["p_market"])
        rank = 1 + sum(row["p_market"] > axis["p_market"] for row in rows)
        tickets = ticket_sets(axis["num"], [row["num"] for row in ranked])
        if not structures:
            structures = list(tickets)
        returns, stakes = {}, {}
        for name, (bet_type, combinations_) in tickets.items():
            available = payouts[race_id].get(bet_type)
            if not available:
                returns[name] = math.nan
                stakes[name] = math.nan
            else:
                stakes[name] = 100.0 * len(combinations_)
                returns[name] = float(sum(available.get(ticket, 0) for ticket in combinations_))
        records.append({
            "year": int(date[:4]),
            "ratio": axis["ratio"],
            "pure": axis["p_pure"],
            "delta": axis["delta"],
            "odds": axis["odds"],
            "market_rank": rank,
            "partner_sum": ranked[0]["p_combo"] + ranked[1]["p_combo"],
            "favorite_market": favorite["p_market"],
            "favorite_danger": favorite["p_market"] - favorite["p_combo"],
            **context[race_id],
            "returns": returns,
            "stakes": stakes,
        })
    return records, structures


def filter_grid():
    favorite_bands = (
        ("all", 0.00, 1.01),
        ("weak", 0.00, 0.45),
        ("normal", 0.45, 0.55),
        ("strong", 0.55, 0.65),
        ("dominant", 0.65, 1.01),
    )
    field_bands = (
        ("all", 0, 100),
        ("small", 0, 10),
        ("medium", 10, 12),
        ("large", 12, 100),
    )
    age_modes = ("all", "exclude_all_two", "only_all_two")
    coverage_bands = (
        ("all", 0.00, 1.01),
        ("low", 0.00, 0.60),
        ("medium", 0.60, 0.80),
        ("high", 0.80, 1.01),
    )
    history_bands = (
        ("all", 0.00, 100.0),
        ("short", 0.00, 3.00),
        ("medium", 3.00, 5.00),
        ("long", 5.00, 100.0),
    )
    for favorite, field, age_mode, coverage, history in itertools.product(
        favorite_bands,
        field_bands,
        age_modes,
        coverage_bands,
        history_bands,
    ):
        yield {
            "favorite_band": favorite[0],
            "favorite_min": favorite[1],
            "favorite_max": favorite[2],
            "field_band": field[0],
            "field_min": field[1],
            "field_max": field[2],
            "age_mode": age_mode,
            "coverage_band": coverage[0],
            "cover3_min": coverage[1],
            "cover3_max": coverage[2],
            "history_band": history[0],
            "avg_past_min": history[1],
            "avg_past_max": history[2],
        }


def run(oos_path: str, result_path: str, features_path: str) -> dict:
    records, structures = build(oos_path, result_path, features_path)
    scalar_names = (
        "year", "ratio", "pure", "delta", "odds", "market_rank",
        "partner_sum", "favorite_market", "favorite_danger", "field_size",
        "all_two_year", "avg_past", "cover3", "cover5",
    )
    columns = {
        name: np.array([row[name] for row in records], dtype=float)
        for name in scalar_names
    }
    returns = {
        name: np.array([row["returns"][name] for row in records], dtype=float)
        for name in structures
    }
    stakes = {
        name: np.array([row["stakes"][name] for row in records], dtype=float)
        for name in structures
    }
    filters = list(filter_grid())

    def mask(profile: dict, race_filter: dict, years: tuple[int, ...]):
        selected = np.isin(columns["year"], years)
        selected &= columns["ratio"] >= profile["ratio"]
        selected &= columns["pure"] >= profile["pure"]
        selected &= columns["delta"] >= profile["delta"]
        selected &= columns["odds"] >= profile["odds_min"]
        selected &= columns["odds"] < profile["odds_max"]
        selected &= columns["market_rank"] >= profile["rank_min"]
        selected &= columns["partner_sum"] >= profile["partner"]
        selected &= columns["favorite_market"] >= race_filter["favorite_min"]
        selected &= columns["favorite_market"] < race_filter["favorite_max"]
        selected &= columns["field_size"] >= race_filter["field_min"]
        selected &= columns["field_size"] < race_filter["field_max"]
        if race_filter["age_mode"] == "exclude_all_two":
            selected &= columns["all_two_year"] == 0
        elif race_filter["age_mode"] == "only_all_two":
            selected &= columns["all_two_year"] == 1
        selected &= columns["cover3"] >= race_filter["cover3_min"]
        selected &= columns["cover3"] < race_filter["cover3_max"]
        selected &= columns["avg_past"] >= race_filter["avg_past_min"]
        selected &= columns["avg_past"] < race_filter["avg_past_max"]
        return selected

    walkforward = []
    for test_year, train_years in ((2025, (2024,)), (2026, (2024, 2025))):
        candidates = []
        for profile in PROFILES:
            for race_filter in filters:
                train_mask = mask(profile, race_filter, train_years)
                if int(train_mask.sum()) < MIN_DISCOVERY_RACES:
                    continue
                for structure in structures:
                    result = stats(returns[structure], stakes[structure], train_mask)
                    if result["races"] >= MIN_DISCOVERY_RACES:
                        candidates.append((result["lcb90"], structure, profile, race_filter, result))
        candidates.sort(key=lambda item: item[0], reverse=True)
        if not candidates:
            walkforward.append({"test_year": test_year, "selected": "NO_BET"})
            continue
        _, structure, profile, race_filter, train = candidates[0]
        test = stats(
            returns[structure],
            stakes[structure],
            mask(profile, race_filter, (test_year,)),
        )
        walkforward.append({
            "test_year": test_year,
            "selected": structure,
            "profile": profile,
            "race_filter": race_filter,
            "train": train,
            "decision": "BET" if train["lcb90"] > 100 else "NO_BET",
            "test": test,
        })

    robust = []
    segment_candidates = []
    for profile in PROFILES:
        for race_filter in filters:
            masks = {year: mask(profile, race_filter, (year,)) for year in (2024, 2025, 2026)}
            for structure in structures:
                yearly = {
                    str(year): stats(returns[structure], stakes[structure], selected)
                    for year, selected in masks.items()
                }
                if all(item["races"] >= 100 for item in yearly.values()):
                    overall = stats(
                        returns[structure],
                        stakes[structure],
                        mask(profile, race_filter, (2024, 2025, 2026)),
                    )
                    segment_candidates.append({
                        "structure": structure,
                        "profile": profile,
                        "race_filter": race_filter,
                        "yearly": yearly,
                        "overall": overall,
                        "min_year_roi": min(item["roi"] for item in yearly.values()),
                    })
                if all(
                    item["races"] >= MIN_DISCOVERY_RACES and item["roi"] > 100
                    for item in yearly.values()
                ):
                    overall = stats(
                        returns[structure],
                        stakes[structure],
                        mask(profile, race_filter, (2024, 2025, 2026)),
                    )
                    robust.append({
                        "structure": structure,
                        "profile": profile,
                        "race_filter": race_filter,
                        "yearly": yearly,
                        "overall": overall,
                    })
    robust.sort(key=lambda item: (item["overall"]["lcb90"], item["overall"]["roi"]), reverse=True)

    dimensions = {
        "favorite_band": ("all", "weak", "normal", "strong", "dominant"),
        "field_band": ("all", "small", "medium", "large"),
        "age_mode": ("all", "exclude_all_two", "only_all_two"),
        "coverage_band": ("all", "low", "medium", "high"),
        "history_band": ("all", "short", "medium", "long"),
    }
    best_by_segment = []
    for dimension, values in dimensions.items():
        for value in values:
            for structure in structures:
                eligible = [
                    item for item in segment_candidates
                    if item["race_filter"][dimension] == value
                    and item["structure"] == structure
                ]
                if not eligible:
                    continue
                best = max(
                    eligible,
                    key=lambda item: (
                        item["min_year_roi"],
                        item["overall"]["lcb90"],
                        item["overall"]["roi"],
                    ),
                )
                best_by_segment.append({
                    "dimension": dimension,
                    "segment": value,
                    **best,
                })
    return {
        "version": VERSION,
        "records": len(records),
        "profiles": list(PROFILES),
        "race_filters": len(filters),
        "ticket_structures": structures,
        "walkforward": walkforward,
        "robust_three_year_candidates": robust[:100],
        "best_by_segment": best_by_segment,
        "limitations": [
            "race-participation segments are searched after earlier longshot analysis",
            "segment discovery has a large multiple-testing burden",
            "best-by-segment results require at least 100 races in every year",
            "independent future shadow validation is mandatory",
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
        f"records={result['records']:,} filters={result['race_filters']} "
        f"robust={len(result['robust_three_year_candidates'])}"
    )
    print(json.dumps(result["walkforward"], ensure_ascii=False, indent=2))
    print(json.dumps(result["robust_three_year_candidates"][:5], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
