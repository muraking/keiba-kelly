"""Evaluate OOS AI rankings across single and combination bet types.

The AI index database is joined to the result database by race_id. Strategy
selection uses only years before each test year and falls back to NO_BET unless
the one-sided 90% lower confidence bound exceeds 100%.

Version: v2026.07.23.2
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from walkforward_combo_baseline import MIN_PAST_RACES, combinations, summarize


def ranked_variants(rows: list[dict]) -> dict[str, list[int]]:
    market_total = sum(1.0 / row["odds"] for row in rows)
    for row in rows:
        row["market_p"] = (1.0 / row["odds"]) / market_total
        row["residual"] = row["comb"] / max(row["market_p"], 1e-9)
        row["hybrid"] = (row["comb"] * row["market_p"]) ** 0.5

    variants = {
        "market": sorted(rows, key=lambda row: (row["odds"], row["num"])),
        "ai_comb": sorted(rows, key=lambda row: (-row["comb"], row["num"])),
        "ai_pure": sorted(rows, key=lambda row: (-row["pure"], row["num"])),
        "hybrid": sorted(rows, key=lambda row: (-row["hybrid"], row["num"])),
        "residual": sorted(
            rows, key=lambda row: (-row["residual"], row["num"])
        ),
    }
    market_favorite = variants["market"][0]
    if market_favorite["comb"] < 0.8 * market_favorite["market_p"]:
        variants["danger_excluded"] = [
            row for row in variants["ai_comb"]
            if row["num"] != market_favorite["num"]
        ]
    return {
        name: [row["num"] for row in ranked]
        for name, ranked in variants.items()
    }


def gated_candidates(rows: list[dict]) -> dict[str, tuple[str, list[str]]]:
    """Small, predeclared set of race filters to limit strategy mining."""
    rankings = ranked_variants(rows)
    market_by_num = {row["num"]: row for row in rows}
    favorite = rankings["market"][0]
    favorite_row = market_by_num[favorite]
    favorite_ratio = favorite_row["comb"] / max(
        favorite_row["market_p"], 1e-9
    )
    max_comb = max(row["comb"] for row in rows)
    ai_disagrees = rankings["ai_comb"][0] != favorite
    max_residual = max(row["residual"] for row in rows)
    selected: dict[str, tuple[str, list[str]]] = {}

    def add(prefix: str, ranking: str, ticket_names: tuple[str, ...]) -> None:
        for ticket_name, value in combinations(rankings[ranking]).items():
            if ticket_name in ticket_names:
                selected[f"{prefix}:{ticket_name}"] = value

    if favorite_ratio >= 1.0:
        add(
            "safe_favorite",
            "hybrid",
            ("tan_r1", "wide_top2", "umaren_top2", "sanfuku_top3"),
        )
    if favorite_ratio < 0.8 and "danger_excluded" in rankings:
        add(
            "danger_excluded",
            "danger_excluded",
            (
                "wide_top2",
                "umaren_top2",
                "sanfuku_top3",
                "santan_box3",
            ),
        )
    if ai_disagrees and max_residual >= 1.25:
        add(
            "disagree_value",
            "residual",
            ("wide_top2", "umaren_top2", "sanfuku_top3"),
        )
    if max_comb >= 0.35:
        add(
            "high_confidence",
            "ai_comb",
            ("tan_r1", "wide_top2", "umaren_top2", "sanfuku_top3"),
        )
    return selected


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

    index_db = sqlite3.connect(index_path)
    cursor = index_db.execute(
        "SELECT race_id, date, umaban, win_odds, "
        "COALESCE(p_pure_n, p_pure), COALESCE(p_comb_n, p_comb) "
        "FROM ai_index "
        "WHERE win_odds > 0 AND COALESCE(p_pure_n, p_pure) IS NOT NULL "
        "AND COALESCE(p_comb_n, p_comb) IS NOT NULL "
        "ORDER BY race_id, umaban"
    )
    by_strategy_year: dict[str, dict[int, list[tuple[int, int, float]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    current_race = None
    current_date = ""
    horses: list[dict] = []
    joined_races = 0

    def evaluate(race_id: str | None, date: str, rows: list[dict]) -> None:
        nonlocal joined_races
        if race_id is None or len(rows) < 3 or race_id not in payouts:
            return
        joined_races += 1
        year = int(date[:4])
        for rank_name, ranked in ranked_variants(rows).items():
            for ticket_name, (bet_type, tickets) in combinations(ranked).items():
                available = payouts[race_id].get(bet_type)
                if not available or not tickets:
                    continue
                stake = 100 * len(tickets)
                returned = sum(available.get(ticket, 0) for ticket in tickets)
                name = f"{rank_name}:{ticket_name}"
                by_strategy_year[name][year].append(
                    (year, stake, float(returned))
                )
        for name, (bet_type, tickets) in gated_candidates(rows).items():
            available = payouts[race_id].get(bet_type)
            if not available or not tickets:
                continue
            stake = 100 * len(tickets)
            returned = sum(available.get(ticket, 0) for ticket in tickets)
            by_strategy_year[name][year].append(
                (year, stake, float(returned))
            )

    for race_id, date, umaban, odds, pure, comb in cursor:
        race_id = str(race_id)
        if race_id != current_race:
            evaluate(current_race, current_date, horses)
            current_race = race_id
            current_date = str(date)
            horses = []
        horses.append(
            {
                "num": int(umaban),
                "odds": float(odds),
                "pure": float(pure),
                "comb": float(comb),
            }
        )
    evaluate(current_race, current_date, horses)
    index_db.close()

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
        selected = best[1]
        meta.append(
            {
                "test_year": test_year,
                "selected": selected,
                "past": best[2],
                "test": summarize(
                    by_strategy_year[selected].get(test_year, [])
                ),
            }
        )
    return {
        "version": "v2026.07.23.2",
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
