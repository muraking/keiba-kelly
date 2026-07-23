"""Walk-forward evaluation of underbet longshots used as the ticket axis.

A longshot must be both unpopular by odds and positively rated by the fully
OOS pure model relative to market probability. One axis horse is selected per
race before evaluating win/place and combination bet structures.

Version: v2026.07.23.4
"""

from __future__ import annotations

import itertools
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from walkforward_combo_baseline import MIN_PAST_RACES, summarize
from walkforward_residual_dynamic_policy import load_oos


LONGSHOT_RULES = (
    # name, minimum pure/market ratio, minimum pure probability, odds range
    ("balanced", 1.25, 0.05, 5.0, 30.0),
    ("clear_edge", 1.50, 0.05, 5.0, 40.0),
    ("deep_value", 2.00, 0.03, 10.0, 50.0),
    ("strong_value", 1.50, 0.08, 5.0, 30.0),
)


def pair(a: int, b: int) -> str:
    return f"{min(a, b)}-{max(a, b)}"


def trio(a: int, b: int, c: int) -> str:
    return "-".join(map(str, sorted((a, b, c))))


def longshot_tickets(rows: list[dict]) -> dict[str, tuple[str, list[str]]]:
    for row in rows:
        row["ratio"] = row["p_struct"] / max(row["p_market"], 1e-9)
        row["pure_delta"] = row["p_struct"] - row["p_market"]
    result: dict[str, tuple[str, list[str]]] = {}
    combo_ranked = sorted(
        rows, key=lambda row: (-row["p_combo"], row["num"])
    )

    for rule, ratio_min, pure_min, odds_min, odds_max in LONGSHOT_RULES:
        eligible = [
            row for row in rows
            if ratio_min <= row["ratio"]
            and pure_min <= row["p_struct"]
            and odds_min <= row["odds"] < odds_max
        ]
        if not eligible:
            continue
        # Prefer absolute probability edge, then pure probability.
        axis = max(
            eligible,
            key=lambda row: (
                row["pure_delta"],
                row["p_struct"],
                -row["odds"],
            ),
        )
        partners = [
            row for row in combo_ranked if row["num"] != axis["num"]
        ][:4]
        if len(partners) < 3:
            continue
        prefix = f"{rule}_axis"
        result[f"{prefix}:tan"] = ("tan", [str(axis["num"])])
        result[f"{prefix}:fuku"] = ("fuku", [str(axis["num"])])
        result[f"{prefix}:umaren_1"] = (
            "umaren",
            [pair(axis["num"], partners[0]["num"])],
        )
        result[f"{prefix}:umaren_2"] = (
            "umaren",
            [pair(axis["num"], row["num"]) for row in partners[:2]],
        )
        result[f"{prefix}:wide_1"] = (
            "wide",
            [pair(axis["num"], partners[0]["num"])],
        )
        result[f"{prefix}:wide_2"] = (
            "wide",
            [pair(axis["num"], row["num"]) for row in partners[:2]],
        )
        result[f"{prefix}:sanfuku_1"] = (
            "sanfuku",
            [
                trio(
                    axis["num"],
                    partners[0]["num"],
                    partners[1]["num"],
                )
            ],
        )
        result[f"{prefix}:sanfuku_3"] = (
            "sanfuku",
            [
                trio(axis["num"], a["num"], b["num"])
                for a, b in itertools.combinations(partners[:3], 2)
            ],
        )
        result[f"{prefix}:santan_first_2"] = (
            "santan",
            [
                f"{axis['num']}>{a['num']}>{b['num']}"
                for a, b in itertools.permutations(partners[:2], 2)
            ],
        )
        partner_probability = (
            partners[0]["p_combo"] + partners[1]["p_combo"]
        )
        for minimum in (0.45, 0.55):
            if partner_probability >= minimum:
                for ticket_name in (
                    "tan",
                    "fuku",
                    "umaren_1",
                    "umaren_2",
                    "wide_1",
                    "wide_2",
                    "sanfuku_1",
                    "sanfuku_3",
                    "santan_first_2",
                ):
                    base_name = f"{prefix}:{ticket_name}"
                    if base_name in result:
                        result[
                            f"{base_name}_partner{minimum:.2f}"
                        ] = result[base_name]
    return result


def load_rows(path: str):
    for race_id, date, raw_rows in load_oos(path):
        rows = []
        for row in raw_rows:
            # load_oos intentionally reads only the common columns.
            rows.append(row)
        yield race_id, date, rows


def run(oos_path: str, result_path: str) -> dict:
    # Read p_struct as well as the columns shared by the residual policy.
    import csv

    def races():
        with open(oos_path, encoding="utf-8", newline="") as source:
            current = None
            date = ""
            rows = []
            for raw in csv.DictReader(source):
                race_id = raw["race_id"]
                if race_id != current:
                    if current is not None:
                        yield current, date, rows
                    current = race_id
                    date = raw["date"]
                    rows = []
                rows.append(
                    {
                        "num": int(float(raw["umaban"])),
                        "odds": float(raw["win_odds"]),
                        "p_market": float(raw["p_market"]),
                        "p_struct": float(raw["p_struct"]),
                        "p_combo": float(raw["p_combo"]),
                    }
                )
            if current is not None:
                yield current, date, rows

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
    joined_races = 0
    selected_races = 0
    for race_id, date, rows in races():
        if len(rows) < 4 or race_id not in payouts:
            continue
        joined_races += 1
        tickets = longshot_tickets(rows)
        if tickets:
            selected_races += 1
        year = int(date[:4])
        for name, (bet_type, combinations_) in tickets.items():
            available = payouts[race_id].get(bet_type)
            if not available:
                continue
            stake = 100 * len(combinations_)
            returned = sum(
                available.get(ticket, 0) for ticket in combinations_
            )
            by_policy_year[name][year].append(
                (year, stake, float(returned))
            )

    annual = {
        name: {
            str(year): summarize(rows)
            for year, rows in sorted(years.items())
        }
        for name, years in sorted(by_policy_year.items())
    }
    overall = {}
    for name, years in sorted(by_policy_year.items()):
        all_rows = [
            row for year_rows in years.values() for row in year_rows
        ]
        stats = summarize(all_rows)
        year_stats = [
            summarize(year_rows) for year_rows in years.values()
        ]
        stats["profitable_years"] = sum(
            item["roi"] > 100.0 for item in year_stats
        )
        stats["evaluated_years"] = len(year_stats)
        overall[name] = stats
    test_years = sorted(
        {
            year
            for years in by_policy_year.values()
            for year in years
            if year >= 2025
        }
    )
    meta = []
    for test_year in test_years:
        choices = []
        for name, years in by_policy_year.items():
            past = [
                row
                for year, items in years.items()
                if year < test_year
                for row in items
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
        "version": "v2026.07.23.4",
        "oos_predictions": oos_path,
        "result_database": result_path,
        "joined_races": joined_races,
        "selected_races_any_rule": selected_races,
        "annual": annual,
        "overall": overall,
        "meta_walkforward": meta,
        "limitations": [
            "historical win odds may differ from purchase-time odds",
            "candidate definitions are fixed before reading these results",
        ],
    }


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: script OOS_CSV RESULT_DB OUTPUT_JSON")
    result = run(sys.argv[1], sys.argv[2])
    Path(sys.argv[3]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"joined={result['joined_races']:,} "
        f"selected={result['selected_races_any_rule']:,}"
    )
    print(json.dumps(result["meta_walkforward"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
