"""Context-dependent betting policies using historical AI index probabilities.

Policies switch bet type and ticket count between strong-favorite and
danger-favorite race states. Historical final win odds are used only for this
preliminary screen; purchase-time validation remains mandatory.

Version: v2026.07.23.1
"""

from __future__ import annotations

import itertools
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from walkforward_combo_baseline import MIN_PAST_RACES, summarize


def pair(a: int, b: int) -> str:
    return f"{min(a, b)}-{max(a, b)}"


def trio(a: int, b: int, c: int) -> str:
    return "-".join(map(str, sorted((a, b, c))))


def policy_tickets(rows: list[dict]) -> dict[str, tuple[str, list[str]]]:
    market_total = sum(1.0 / row["odds"] for row in rows)
    for row in rows:
        row["market_p"] = (1.0 / row["odds"]) / market_total
        row["pure_ev"] = row["pure"] * row["odds"]

    market = sorted(rows, key=lambda row: (row["odds"], row["num"]))
    pure = sorted(rows, key=lambda row: (-row["pure"], row["num"]))
    favorite = market[0]
    ratio = favorite["pure"] / max(favorite["market_p"], 1e-9)
    pure_without_favorite = [
        row for row in pure if row["num"] != favorite["num"]
    ]
    value_without_favorite = sorted(
        (
            row for row in rows
            if row["num"] != favorite["num"] and row["odds"] < 50
        ),
        key=lambda row: (-row["pure_ev"], -row["pure"], row["num"]),
    )
    result: dict[str, tuple[str, list[str]]] = {}

    for probability in (0.30, 0.40):
        for min_ratio in (0.90, 1.10):
            if favorite["pure"] < probability or ratio < min_ratio:
                continue
            label = f"strong_p{probability:.2f}_r{min_ratio:.2f}"
            partners = pure_without_favorite[:3]
            if len(partners) >= 1:
                result[f"{label}:umaren_1"] = (
                    "umaren",
                    [pair(favorite["num"], partners[0]["num"])],
                )
                result[f"{label}:wide_1"] = (
                    "wide",
                    [pair(favorite["num"], partners[0]["num"])],
                )
            if len(partners) >= 2:
                result[f"{label}:umaren_2"] = (
                    "umaren",
                    [pair(favorite["num"], row["num"]) for row in partners[:2]],
                )
                result[f"{label}:wide_2"] = (
                    "wide",
                    [pair(favorite["num"], row["num"]) for row in partners[:2]],
                )
                result[f"{label}:sanfuku_1"] = (
                    "sanfuku",
                    [
                        trio(
                            favorite["num"],
                            partners[0]["num"],
                            partners[1]["num"],
                        )
                    ],
                )

    for max_ratio in (0.60, 0.80):
        if ratio > max_ratio or len(value_without_favorite) < 3:
            continue
        label = f"danger_r{max_ratio:.2f}"
        axis = value_without_favorite[0]
        partners = [
            row for row in pure_without_favorite
            if row["num"] != axis["num"]
        ][:3]
        if len(partners) >= 2:
            result[f"{label}:wide_2"] = (
                "wide",
                [pair(axis["num"], row["num"]) for row in partners[:2]],
            )
            result[f"{label}:umaren_2"] = (
                "umaren",
                [pair(axis["num"], row["num"]) for row in partners[:2]],
            )
        if len(partners) >= 3:
            result[f"{label}:sanfuku_3"] = (
                "sanfuku",
                [
                    trio(axis["num"], a["num"], b["num"])
                    for a, b in itertools.combinations(partners[:3], 2)
                ],
            )
    return result


def run(index_path: str, result_path: str) -> dict:
    result_db = sqlite3.connect(result_path)
    payouts: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for race_id, bet_type, comb, payout in result_db.execute(
        "SELECT race_id, bet_type, comb, payout FROM payouts"
    ):
        payouts[str(race_id)][str(bet_type)][str(comb)] = int(payout)
    result_db.close()

    by_policy_year: dict[str, dict[int, list[tuple[int, int, float]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    index_db = sqlite3.connect(index_path)
    cursor = index_db.execute(
        "SELECT race_id, date, umaban, win_odds, "
        "COALESCE(p_pure_n, p_pure) "
        "FROM ai_index WHERE win_odds > 0 "
        "AND COALESCE(p_pure_n, p_pure) IS NOT NULL "
        "ORDER BY race_id, umaban"
    )
    current_race = None
    current_date = ""
    horses: list[dict] = []
    joined_races = 0

    def evaluate(race_id: str | None, date: str, rows: list[dict]) -> None:
        nonlocal joined_races
        if race_id is None or len(rows) < 4 or race_id not in payouts:
            return
        joined_races += 1
        year = int(date[:4])
        for name, (bet_type, tickets) in policy_tickets(rows).items():
            available = payouts[race_id].get(bet_type)
            if not available:
                continue
            stake = 100 * len(tickets)
            returned = sum(available.get(ticket, 0) for ticket in tickets)
            by_policy_year[name][year].append(
                (year, stake, float(returned))
            )

    for race_id, date, umaban, odds, pure in cursor:
        race_id = str(race_id)
        if race_id != current_race:
            evaluate(current_race, current_date, horses)
            current_race = race_id
            current_date = str(date)
            horses = []
        horses.append(
            {"num": int(umaban), "odds": float(odds), "pure": float(pure)}
        )
    evaluate(current_race, current_date, horses)
    index_db.close()

    annual = {
        name: {
            str(year): summarize(rows)
            for year, rows in sorted(years.items())
        }
        for name, years in sorted(by_policy_year.items())
    }
    test_years = sorted(
        {
            year
            for years in by_policy_year.values()
            for year in years
            if year >= 2023
        }
    )
    meta = []
    for test_year in test_years:
        choices = []
        for name, years in by_policy_year.items():
            past = [
                row
                for year, rows in years.items()
                if year < test_year
                for row in rows
            ]
            stats = summarize(past)
            if stats["races"] >= MIN_PAST_RACES:
                choices.append((stats["lcb90_race_roi"], name, stats))
        choices.sort(reverse=True)
        best = choices[0] if choices else None
        if best is None or best[0] <= 100:
            meta.append(
                {"test_year": test_year, "selected": "NO_BET", "past": None}
            )
            continue
        selected = best[1]
        meta.append(
            {
                "test_year": test_year,
                "selected": selected,
                "past": best[2],
                "test": summarize(
                    by_policy_year[selected].get(test_year, [])
                ),
            }
        )
    return {
        "version": "v2026.07.23.1",
        "index_database": index_path,
        "result_database": result_path,
        "joined_races": joined_races,
        "annual": annual,
        "meta_walkforward": meta,
    }


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: script AI_INDEX_DB RESULT_DB OUTPUT_JSON")
    result = run(sys.argv[1], sys.argv[2])
    Path(sys.argv[3]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"joined_races={result['joined_races']:,}")
    print(json.dumps(result["meta_walkforward"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
