"""Walk-forward baseline for market-ranked combination bets.

This deliberately uses only pre-race win odds to define selections. It establishes
the hurdle that later OOS AI probabilities must beat.

Version: v2026.07.23.1
"""

from __future__ import annotations

import itertools
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path


MIN_PAST_RACES = 500
LCB_Z = 1.2815515655446004  # one-sided 90%


def combinations(ranked: list[int]) -> dict[str, tuple[str, list[str]]]:
    top = ranked[:5]
    result: dict[str, tuple[str, list[str]]] = {}

    def pairs(nums: list[int]) -> list[str]:
        return [f"{a}-{b}" for a, b in itertools.combinations(sorted(nums), 2)]

    def triples(nums: list[int]) -> list[str]:
        return [
            "-".join(map(str, trio))
            for trio in itertools.combinations(sorted(nums), 3)
        ]

    if len(top) >= 1:
        result["tan_r1"] = ("tan", [str(top[0])])
    if len(top) >= 2:
        result["umaren_top2"] = ("umaren", pairs(top[:2]))
        result["wide_top2"] = ("wide", pairs(top[:2]))
    if len(top) >= 3:
        result["umaren_box3"] = ("umaren", pairs(top[:3]))
        result["wide_box3"] = ("wide", pairs(top[:3]))
        result["sanfuku_top3"] = ("sanfuku", triples(top[:3]))
        result["santan_order3"] = (
            "santan",
            [f"{top[0]}>{top[1]}>{top[2]}"],
        )
        result["santan_box3"] = (
            "santan",
            [
                ">".join(map(str, order))
                for order in itertools.permutations(top[:3], 3)
            ],
        )
    if len(top) >= 4:
        result["umaren_axis1_to4"] = (
            "umaren",
            [f"{min(top[0], x)}-{max(top[0], x)}" for x in top[1:4]],
        )
        result["wide_axis1_to4"] = (
            "wide",
            [f"{min(top[0], x)}-{max(top[0], x)}" for x in top[1:4]],
        )
        result["sanfuku_axis1_2to4"] = (
            "sanfuku",
            [
                "-".join(map(str, sorted((top[0], a, b))))
                for a, b in itertools.combinations(top[1:4], 2)
            ],
        )
        result["sanfuku_box4"] = ("sanfuku", triples(top[:4]))
        result["santan_axis1_2to4"] = (
            "santan",
            [
                f"{top[0]}>{a}>{b}"
                for a, b in itertools.permutations(top[1:4], 2)
            ],
        )
    return result


def lcb90(race_rois: list[float]) -> float:
    if len(race_rois) < 2:
        return float("-inf")
    mean = sum(race_rois) / len(race_rois)
    variance = sum((value - mean) ** 2 for value in race_rois) / (
        len(race_rois) - 1
    )
    return mean - LCB_Z * math.sqrt(variance / len(race_rois))


def summarize(rows: list[tuple[int, int, float]]) -> dict[str, float | int]:
    races = len(rows)
    stake = sum(row[1] for row in rows)
    payout = sum(row[2] for row in rows)
    race_rois = [
        100.0 * row[2] / row[1] for row in rows if row[1] > 0
    ]
    return {
        "races": races,
        "bets": stake // 100,
        "roi": round(100.0 * payout / stake, 3) if stake else 0.0,
        "lcb90_race_roi": round(lcb90(race_rois), 3),
        "max_payout_share": (
            round(max((row[2] for row in rows), default=0.0) / payout, 5)
            if payout
            else 0.0
        ),
    }


def run(db_path: str) -> dict:
    connection = sqlite3.connect(db_path)
    payout_rows = connection.execute(
        "SELECT race_id, bet_type, comb, payout FROM payouts"
    )
    payouts: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for race_id, bet_type, comb, payout in payout_rows:
        payouts[str(race_id)][str(bet_type)][str(comb)] = int(payout)

    runs = connection.execute(
        "SELECT race_id, date, umaban, win_odds "
        "FROM runs WHERE finish_pos IS NOT NULL AND win_odds > 0 "
        "ORDER BY race_id, win_odds, popularity, umaban"
    )
    by_strategy_year: dict[str, dict[int, list[tuple[int, int, float]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    current_race = None
    current_date = ""
    ranked: list[int] = []

    def evaluate(race_id: str | None, date: str, nums: list[int]) -> None:
        if race_id is None or len(nums) < 2 or race_id not in payouts:
            return
        year = int(date[:4])
        for name, (bet_type, tickets) in combinations(nums).items():
            available = payouts[race_id].get(bet_type)
            if not available or not tickets:
                continue
            stake = 100 * len(tickets)
            returned = sum(available.get(ticket, 0) for ticket in tickets)
            by_strategy_year[name][year].append(
                (year, stake, float(returned))
            )

    for race_id, date, umaban, _ in runs:
        race_id = str(race_id)
        if race_id != current_race:
            evaluate(current_race, current_date, ranked)
            current_race = race_id
            current_date = str(date)
            ranked = []
        if int(umaban) not in ranked:
            ranked.append(int(umaban))
    evaluate(current_race, current_date, ranked)
    connection.close()

    annual = {
        name: {
            str(year): summarize(rows)
            for year, rows in sorted(years.items())
        }
        for name, years in sorted(by_strategy_year.items())
    }

    test_years = sorted(
        {
            year
            for years in by_strategy_year.values()
            for year in years
            if year >= 2023
        }
    )
    meta = []
    for test_year in test_years:
        choices = []
        for name, years in by_strategy_year.items():
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
        if best is None or best[0] <= 100.0:
            meta.append(
                {"test_year": test_year, "selected": "NO_BET", "past": None}
            )
            continue
        name = best[1]
        test = summarize(by_strategy_year[name].get(test_year, []))
        meta.append(
            {
                "test_year": test_year,
                "selected": name,
                "past": best[2],
                "test": test,
            }
        )
    return {
        "version": "v2026.07.23.1",
        "database": db_path,
        "annual": annual,
        "meta_walkforward": meta,
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: script DB_PATH OUTPUT_JSON")
    result = run(sys.argv[1])
    output = Path(sys.argv[2])
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result["meta_walkforward"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
