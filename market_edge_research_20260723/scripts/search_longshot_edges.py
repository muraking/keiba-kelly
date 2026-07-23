"""Nested walk-forward search for longshot-axis betting edges.

One universal longshot candidate is selected per race using only fully OOS
probabilities. A fixed grid of interpretable filters and ticket structures is
searched on past years, then evaluated unchanged on the next year.

Version: v2026.07.23.2
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


VERSION = "v2026.07.23.2"
Z90 = 1.2815515655446004
MIN_DISCOVERY_RACES = 200


def pair(a: int, b: int) -> str:
    return f"{min(a, b)}-{max(a, b)}"


def trio(a: int, b: int, c: int) -> str:
    return "-".join(map(str, sorted((a, b, c))))


def ticket_sets(axis: int, partners: list[int]) -> dict[str, tuple[str, list[str]]]:
    p1, p2, p3, p4 = partners[:4]
    return {
        "tan_1": ("tan", [str(axis)]),
        "fuku_1": ("fuku", [str(axis)]),
        "umaren_1": ("umaren", [pair(axis, p1)]),
        "umaren_2": ("umaren", [pair(axis, x) for x in (p1, p2)]),
        "umaren_3": ("umaren", [pair(axis, x) for x in (p1, p2, p3)]),
        "wide_1": ("wide", [pair(axis, p1)]),
        "wide_2": ("wide", [pair(axis, x) for x in (p1, p2)]),
        "wide_3": ("wide", [pair(axis, x) for x in (p1, p2, p3)]),
        "sanfuku_1": ("sanfuku", [trio(axis, p1, p2)]),
        "sanfuku_3": (
            "sanfuku",
            [trio(axis, a, b) for a, b in itertools.combinations((p1, p2, p3), 2)],
        ),
        "sanfuku_6": (
            "sanfuku",
            [trio(axis, a, b) for a, b in itertools.combinations((p1, p2, p3, p4), 2)],
        ),
        "santan_first_2": ("santan", [f"{axis}>{p1}>{p2}", f"{axis}>{p2}>{p1}"]),
        "santan_first_6": (
            "santan",
            [f"{axis}>{a}>{b}" for a, b in itertools.permutations((p1, p2, p3), 2)],
        ),
        "santan_second_2": (
            "santan",
            [f"{p1}>{axis}>{p2}", f"{p2}>{axis}>{p1}"],
        ),
        "santan_third_2": (
            "santan",
            [f"{p1}>{p2}>{axis}", f"{p2}>{p1}>{axis}"],
        ),
        "santan_box_6": (
            "santan",
            [
                ">".join(map(str, order))
                for order in itertools.permutations((axis, p1, p2), 3)
            ],
        ),
    }


def iter_races(path: str):
    with open(path, encoding="utf-8", newline="") as source:
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
                    "p_pure": float(raw["p_struct"]),
                    "p_combo": float(raw["p_combo"]),
                }
            )
        if current is not None:
            yield current, date, rows


def build_dataset(oos_path: str, result_path: str) -> tuple[list[dict], list[str]]:
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
        if race_id not in payouts or len(rows) < 6:
            continue
        for row in rows:
            row["ratio"] = row["p_pure"] / max(row["p_market"], 1e-9)
            row["delta"] = row["p_pure"] - row["p_market"]
        eligible = [
            row for row in rows
            if row["ratio"] >= 1.10
            and row["p_pure"] >= 0.03
            and 5.0 <= row["odds"] < 50.0
        ]
        if not eligible:
            continue
        axis = max(
            eligible,
            key=lambda row: (row["delta"], row["p_pure"], -row["odds"]),
        )
        partners = [
            row for row in sorted(
                rows, key=lambda row: (-row["p_combo"], row["num"])
            )
            if row["num"] != axis["num"]
        ]
        if len(partners) < 4:
            continue
        favorite = max(rows, key=lambda row: row["p_market"])
        market_rank = 1 + sum(
            row["p_market"] > axis["p_market"] for row in rows
        )
        tickets = ticket_sets(
            axis["num"], [row["num"] for row in partners]
        )
        if not structures:
            structures = list(tickets)
        returns = {}
        stakes = {}
        for name, (bet_type, combinations_) in tickets.items():
            available = payouts[race_id].get(bet_type)
            if not available:
                returns[name] = math.nan
                stakes[name] = math.nan
                continue
            stakes[name] = 100.0 * len(combinations_)
            returns[name] = float(
                sum(available.get(ticket, 0) for ticket in combinations_)
            )
        records.append(
            {
                "year": int(date[:4]),
                "ratio": axis["ratio"],
                "pure": axis["p_pure"],
                "delta": axis["delta"],
                "odds": axis["odds"],
                "market_rank": market_rank,
                "partner_sum": partners[0]["p_combo"] + partners[1]["p_combo"],
                "favorite_danger": favorite["p_market"] - favorite["p_combo"],
                "field_size": len(rows),
                "returns": returns,
                "stakes": stakes,
            }
        )
    return records, structures


def stats(returns: np.ndarray, stakes: np.ndarray, mask: np.ndarray) -> dict:
    valid = mask & np.isfinite(returns) & np.isfinite(stakes)
    n = int(valid.sum())
    if n == 0:
        return {"races": 0, "bets": 0, "roi": 0.0, "lcb90": -999.0}
    race_roi = 100.0 * returns[valid] / stakes[valid]
    roi = float(100.0 * returns[valid].sum() / stakes[valid].sum())
    se = float(race_roi.std(ddof=1) / math.sqrt(n)) if n > 1 else 999.0
    total_return = float(returns[valid].sum())
    return {
        "races": n,
        "bets": int(stakes[valid].sum() / 100.0),
        "roi": round(roi, 3),
        "lcb90": round(float(race_roi.mean() - Z90 * se), 3),
        "max_payout_share": round(
            float(returns[valid].max() / total_return)
            if total_return > 0
            else 0.0,
            5,
        ),
    }


def rule_grid():
    for ratio, pure, odds_min, odds_max, rank_min, delta, partner, danger, field in itertools.product(
        (1.10, 1.25, 1.50, 2.00),
        (0.03, 0.05, 0.08),
        (5.0, 10.0),
        (20.0, 30.0, 50.0),
        (2, 4, 6),
        (0.00, 0.01, 0.02),
        (0.35, 0.45, 0.55),
        (-1.0, 0.02),
        (0, 10, 14),
    ):
        if odds_min >= odds_max:
            continue
        yield {
            "ratio": ratio,
            "pure": pure,
            "odds_min": odds_min,
            "odds_max": odds_max,
            "rank_min": rank_min,
            "delta": delta,
            "partner": partner,
            "danger": danger,
            "field": field,
        }


def run(oos_path: str, result_path: str) -> dict:
    records, structures = build_dataset(oos_path, result_path)
    columns = {
        name: np.array([row[name] for row in records], dtype=float)
        for name in (
            "year",
            "ratio",
            "pure",
            "delta",
            "odds",
            "market_rank",
            "partner_sum",
            "favorite_danger",
            "field_size",
        )
    }
    returns = {
        name: np.array([row["returns"][name] for row in records], dtype=float)
        for name in structures
    }
    stakes = {
        name: np.array([row["stakes"][name] for row in records], dtype=float)
        for name in structures
    }
    rules = list(rule_grid())

    def mask_for(rule: dict, years: tuple[int, ...]) -> np.ndarray:
        mask = np.isin(columns["year"], years)
        mask &= columns["ratio"] >= rule["ratio"]
        mask &= columns["pure"] >= rule["pure"]
        mask &= columns["delta"] >= rule["delta"]
        mask &= columns["odds"] >= rule["odds_min"]
        mask &= columns["odds"] < rule["odds_max"]
        mask &= columns["market_rank"] >= rule["rank_min"]
        mask &= columns["partner_sum"] >= rule["partner"]
        if rule["danger"] >= 0:
            mask &= columns["favorite_danger"] >= rule["danger"]
        if rule["field"] > 0:
            mask &= columns["field_size"] >= rule["field"]
        return mask

    walkforward = []
    for test_year, train_years in ((2025, (2024,)), (2026, (2024, 2025))):
        candidates = []
        for rule in rules:
            train_mask = mask_for(rule, train_years)
            if int(train_mask.sum()) < MIN_DISCOVERY_RACES:
                continue
            for structure in structures:
                train_stats = stats(
                    returns[structure], stakes[structure], train_mask
                )
                if train_stats["races"] < MIN_DISCOVERY_RACES:
                    continue
                candidates.append(
                    (train_stats["lcb90"], structure, rule, train_stats)
                )
        candidates.sort(key=lambda item: item[0], reverse=True)
        if not candidates:
            walkforward.append(
                {"test_year": test_year, "selected": "NO_BET"}
            )
            continue
        _, structure, rule, train_stats = candidates[0]
        test_mask = mask_for(rule, (test_year,))
        test_stats = stats(returns[structure], stakes[structure], test_mask)
        walkforward.append(
            {
                "test_year": test_year,
                "selected": structure,
                "rule": rule,
                "train": train_stats,
                "decision": (
                    "BET" if train_stats["lcb90"] > 100.0 else "NO_BET"
                ),
                "test": test_stats,
            }
        )

    robust = []
    for rule in rules:
        yearly_masks = {
            year: mask_for(rule, (year,)) for year in (2024, 2025, 2026)
        }
        for structure in structures:
            yearly = {
                str(year): stats(
                    returns[structure], stakes[structure], mask
                )
                for year, mask in yearly_masks.items()
            }
            if all(
                item["races"] >= MIN_DISCOVERY_RACES
                and item["roi"] > 100.0
                for item in yearly.values()
            ):
                all_mask = mask_for(rule, (2024, 2025, 2026))
                overall = stats(
                    returns[structure], stakes[structure], all_mask
                )
                robust.append(
                    {
                        "structure": structure,
                        "rule": rule,
                        "yearly": yearly,
                        "overall": overall,
                    }
                )
    robust.sort(
        key=lambda item: (
            item["overall"]["lcb90"],
            item["overall"]["roi"],
        ),
        reverse=True,
    )
    return {
        "version": VERSION,
        "records": len(records),
        "grid_rules": len(rules),
        "ticket_structures": structures,
        "walkforward": walkforward,
        "robust_three_year_candidates": robust[:50],
        "limitations": [
            "large fixed grid creates multiple-testing risk",
            "2024 discovery, 2025 validation, and 2026 confirmation are primary",
            "historical odds may differ from purchase-time odds",
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
        f"records={result['records']:,} grid={result['grid_rules']:,} "
        f"robust={len(result['robust_three_year_candidates'])}"
    )
    print(json.dumps(result["walkforward"], ensure_ascii=False, indent=2))
    print(
        json.dumps(
            result["robust_three_year_candidates"][:5],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
