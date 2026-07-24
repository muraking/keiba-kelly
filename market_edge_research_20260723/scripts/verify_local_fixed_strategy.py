"""Re-evaluate the frozen local strategy against OOS predictions and payouts.

This script performs no parameter search. It calls the same decision function
used by the live service and reports annual ROI by fixed rule.

Version: v2026.07.25.3
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

from local_shadow_strategy import VERSION as STRATEGY_VERSION
from local_shadow_strategy import evaluate_snapshot


VERSION = "v2026.07.25.3"


def payout_map(path: Path) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    for race_id, bet_type, combination, payout in connection.execute(
        "SELECT race_id, bet_type, comb, payout FROM payouts"
    ):
        result[str(race_id)][str(bet_type)][str(combination)] = int(payout)
    connection.close()
    return result


def contexts(path: Path) -> dict[str, dict]:
    result = {}
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    query = (
        "SELECT race_id, MAX(field_size), MAX(age), AVG(h_n_past), "
        "AVG(CASE WHEN h_n_past >= 3 THEN 1.0 ELSE 0.0 END), COUNT(*) "
        "FROM features GROUP BY race_id"
    )
    for race_id, field, max_age, average, cover3, count in connection.execute(query):
        result[str(race_id)] = {
            "field_size": int(field or count),
            "all_two_year": int(max_age or 0) <= 2,
            "avg_past": float(average or 0.0),
            "cover3": float(cover3 or 0.0),
        }
    connection.close()
    return result


def races(path: Path):
    with path.open(encoding="utf-8", newline="") as source:
        current, date, rows = None, "", []
        for row in csv.DictReader(source):
            race_id = row["race_id"]
            if current is not None and race_id != current:
                yield current, date, rows
                rows = []
            current, date = race_id, row["date"]
            rows.append(row)
        if current is not None:
            yield current, date, rows


def summarize(items: list[tuple[int, int]]) -> dict:
    stake = sum(item[0] for item in items)
    returned = sum(item[1] for item in items)
    race_rois = [100.0 * returned_ / stake_ for stake_, returned_ in items if stake_]
    mean = sum(race_rois) / len(race_rois) if race_rois else 0.0
    variance = (
        sum((value - mean) ** 2 for value in race_rois) / (len(race_rois) - 1)
        if len(race_rois) > 1 else math.inf
    )
    lcb90 = mean - 1.6448536269514722 * math.sqrt(variance / len(race_rois))
    return {
        "races": len(items),
        "bets": stake // 100,
        "stake": stake,
        "return": returned,
        "roi": round(100.0 * returned / stake, 3) if stake else 0.0,
        "lcb90": round(lcb90, 3),
        "max_payout_share": round(
            max((item[1] for item in items), default=0) / returned, 5
        ) if returned else 0.0,
    }


def run(oos_path: Path, database_path: Path, features_path: Path) -> dict:
    payouts = payout_map(database_path)
    race_context = contexts(features_path)
    results: dict[str, dict[int, list[tuple[int, int]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    decisions = defaultdict(int)
    for race_id, date, rows in races(oos_path):
        available = payouts.get(race_id)
        if not available or race_id not in race_context:
            continue
        snapshot = {
            "p": {row["umaban"]: float(row["p_struct"]) for row in rows},
            "o": {row["umaban"]: float(row["win_odds"]) for row in rows},
            "context": race_context[race_id],
        }
        decision = evaluate_snapshot(snapshot)
        decisions[decision["action"]] += 1
        if decision["action"] != "SHADOW_BET":
            continue
        bet_type = {
            "三連単": "santan", "三連複": "sanfuku",
            "馬連": "umaren", "ワイド": "wide", "単勝": "tan",
        }[decision["bet_type"]]
        table = available.get(bet_type)
        if not table:
            continue
        stake = 100 * len(decision["tickets"])
        returned = sum(table.get(ticket, 0) for ticket in decision["tickets"])
        results[decision["rule"]][int(date[:4])].append((stake, returned))
    annual = {
        rule: {str(year): summarize(items) for year, items in sorted(years.items())}
        for rule, years in results.items()
    }
    overall = {
        rule: summarize([item for items in years.values() for item in items])
        for rule, years in results.items()
    }
    return {
        "version": VERSION,
        "strategy_version": STRATEGY_VERSION,
        "method": "frozen live decision function; no parameter search",
        "decisions": dict(decisions),
        "annual": annual,
        "overall": overall,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("oos", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("features", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = run(args.oos, args.database, args.features)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
