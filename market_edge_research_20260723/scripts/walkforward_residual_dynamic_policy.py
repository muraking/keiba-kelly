"""Dynamic bet policies driven by fully out-of-sample market residuals.

No test-year percentile is used for race-state classification. Thresholds are
absolute and each policy is eligible only when its past one-sided 90% lower
confidence bound exceeds 100%.

Version: v2026.07.23.2
"""

from __future__ import annotations

import csv
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


def tickets_for_race(rows: list[dict]) -> dict[str, tuple[str, list[str]]]:
    market = sorted(rows, key=lambda row: (-row["p_market"], row["num"]))
    combo = sorted(rows, key=lambda row: (-row["p_combo"], row["num"]))
    favorite = market[0]
    favorite_danger = favorite["p_market"] - favorite["p_combo"]
    combo_top = combo[0]
    result: dict[str, tuple[str, list[str]]] = {}

    def strong_policy(min_probability: float, min_delta: float) -> None:
        if (
            combo_top["p_combo"] < min_probability
            or combo_top["delta"] < min_delta
        ):
            return
        partners = [row for row in combo if row["num"] != combo_top["num"]]
        if len(partners) < 3:
            return
        label = f"strong_p{min_probability:.2f}_d{min_delta:.2f}"
        result[f"{label}:umaren_1"] = (
            "umaren",
            [pair(combo_top["num"], partners[0]["num"])],
        )
        result[f"{label}:umaren_2"] = (
            "umaren",
            [pair(combo_top["num"], row["num"]) for row in partners[:2]],
        )
        result[f"{label}:wide_1"] = (
            "wide",
            [pair(combo_top["num"], partners[0]["num"])],
        )
        result[f"{label}:wide_2"] = (
            "wide",
            [pair(combo_top["num"], row["num"]) for row in partners[:2]],
        )
        result[f"{label}:sanfuku_1"] = (
            "sanfuku",
            [
                trio(
                    combo_top["num"],
                    partners[0]["num"],
                    partners[1]["num"],
                )
            ],
        )

    for probability in (0.30, 0.40):
        for delta in (0.00, 0.02):
            strong_policy(probability, delta)

    for danger in (0.02, 0.04):
        if favorite_danger < danger:
            continue
        alternatives = [
            row for row in rows
            if row["num"] != favorite["num"] and row["odds"] < 50
        ]
        alternatives.sort(
            key=lambda row: (-row["ev_combo"], -row["p_combo"], row["num"])
        )
        if len(alternatives) < 4:
            continue
        axis = alternatives[0]
        partners = sorted(
            alternatives[1:], key=lambda row: (-row["p_combo"], row["num"])
        )[:3]
        label = f"danger_d{danger:.2f}"
        result[f"{label}:wide_2"] = (
            "wide",
            [pair(axis["num"], row["num"]) for row in partners[:2]],
        )
        result[f"{label}:umaren_2"] = (
            "umaren",
            [pair(axis["num"], row["num"]) for row in partners[:2]],
        )
        result[f"{label}:sanfuku_3"] = (
            "sanfuku",
            [
                trio(axis["num"], a["num"], b["num"])
                for a, b in itertools.combinations(partners, 2)
            ],
        )
        combo_alternatives = sorted(
            alternatives, key=lambda row: (-row["p_combo"], row["num"])
        )
        combo_axis = combo_alternatives[0]
        combo_partners = combo_alternatives[1:3]
        result[f"{label}:combo_axis_umaren_2"] = (
            "umaren",
            [
                pair(combo_axis["num"], row["num"])
                for row in combo_partners
            ],
        )
        result[f"{label}:combo_axis_wide_2"] = (
            "wide",
            [
                pair(combo_axis["num"], row["num"])
                for row in combo_partners
            ],
        )
        result[f"{label}:ev_top2_umaren_1"] = (
            "umaren",
            [pair(alternatives[0]["num"], alternatives[1]["num"])],
        )
        result[f"{label}:ev_top2_wide_1"] = (
            "wide",
            [pair(alternatives[0]["num"], alternatives[1]["num"])],
        )
        result[f"{label}:ev_box3_umaren_3"] = (
            "umaren",
            [
                pair(a["num"], b["num"])
                for a, b in itertools.combinations(alternatives[:3], 2)
            ],
        )
        result[f"{label}:combo_box3_umaren_3"] = (
            "umaren",
            [
                pair(a["num"], b["num"])
                for a, b in itertools.combinations(combo_alternatives[:3], 2)
            ],
        )
    return result


def load_oos(path: str):
    with open(path, encoding="utf-8", newline="") as source:
        current_race = None
        current_date = ""
        rows = []
        for raw in csv.DictReader(source):
            race_id = raw["race_id"]
            if race_id != current_race:
                if current_race is not None:
                    yield current_race, current_date, rows
                current_race = race_id
                current_date = raw["date"]
                rows = []
            rows.append(
                {
                    "num": int(float(raw["umaban"])),
                    "odds": float(raw["win_odds"]),
                    "p_market": float(raw["p_market"]),
                    "p_combo": float(raw["p_combo"]),
                    "delta": float(raw["delta"]),
                    "ev_combo": float(raw["ev_combo"]),
                }
            )
        if current_race is not None:
            yield current_race, current_date, rows


def run(oos_path: str, result_path: str) -> dict:
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
    for race_id, date, rows in load_oos(oos_path):
        if len(rows) < 4 or race_id not in payouts:
            continue
        joined_races += 1
        year = int(date[:4])
        for name, (bet_type, tickets) in tickets_for_race(rows).items():
            available = payouts[race_id].get(bet_type)
            if not available:
                continue
            stake = 100 * len(tickets)
            returned = sum(available.get(ticket, 0) for ticket in tickets)
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
        "version": "v2026.07.23.2",
        "oos_predictions": oos_path,
        "result_database": result_path,
        "joined_races": joined_races,
        "annual": annual,
        "meta_walkforward": meta,
        "limitation": (
            "ev_combo uses historical final win odds; purchase-time validation "
            "is required before deployment"
        ),
    }


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: script OOS_CSV RESULT_DB OUTPUT_JSON")
    result = run(sys.argv[1], sys.argv[2])
    Path(sys.argv[3]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"joined_races={result['joined_races']:,}")
    print(json.dumps(result["meta_walkforward"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
