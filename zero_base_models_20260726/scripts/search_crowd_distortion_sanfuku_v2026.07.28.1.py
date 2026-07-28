"""Search pre-race market structures for the fixed win2 x hole3 sanfuku.

Discovery is restricted to 2024. Conditions are frozen and evaluated on
2025, plus 2026 where payout coverage exists. All probabilities are
walk-forward OOS. No result or payout field is used to define a condition.

Version: v2026.07.28.1
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
from itertools import combinations, product
from pathlib import Path

import numpy as np
import pandas as pd


VERSION = "v2026.07.28.1"


def canonical(values) -> str:
    return "-".join(str(int(value)) for value in sorted(values))


def normalize_ticket(value: str) -> str:
    values = re.findall(r"\d+", str(value))
    return canonical(values) if len(values) == 3 else str(value)


def payouts(path: Path) -> dict[str, dict[str, int]]:
    with sqlite3.connect(path) as connection:
        frame = pd.read_sql_query(
            "SELECT race_id,comb,payout FROM payouts WHERE bet_type='sanfuku'",
            connection,
        )
    result: dict[str, dict[str, int]] = {}
    for row in frame.itertuples():
        result.setdefault(str(row.race_id), {})[
            normalize_ticket(row.comb)
        ] = int(row.payout)
    return result


def entropy(values: np.ndarray) -> float:
    positive = values[values > 0]
    total = positive.sum()
    if len(positive) < 2 or total <= 0:
        return 0.0
    probabilities = positive / total
    return float(
        -(probabilities * np.log(probabilities)).sum() / math.log(len(positive))
    )


def make_races(frame: pd.DataFrame, payout_map: dict) -> pd.DataFrame:
    output = []
    for race_id, group in frame.groupby("race_id", sort=False):
        table = payout_map.get(str(race_id))
        if not table:
            continue
        ordered_win = group.sort_values(
            ["p_win", "umaban"], ascending=[False, True]
        )
        winners = ordered_win.head(2)
        longshots = group[group["win_odds"].ge(10)].sort_values(
            ["p_place", "umaban"], ascending=[False, True]
        )
        holes = longshots.head(3)
        if len(winners) < 2 or len(holes) < 3:
            continue
        win_numbers = winners["umaban"].astype(int).tolist()
        hole_numbers = holes["umaban"].astype(int).tolist()
        middle = sorted(set(win_numbers + hole_numbers))
        tickets = {
            canonical((axis, partner, hole))
            for axis, partner, hole in product(
                win_numbers, middle, hole_numbers
            )
            if len({axis, partner, hole}) == 3
        }
        returned = sum(table.get(value, 0) for value in tickets)
        actual = set(
            group.nsmallest(3, "finish_pos")["umaban"].astype(int)
        )
        win_actual = bool(actual & set(win_numbers))
        hole_actual = bool(actual & set(hole_numbers))
        market_rank = group["win_odds"].rank(method="min", ascending=True)
        pp_rank = group["p_place"].rank(method="min", ascending=False)
        hole1_index = holes.index[0]
        favorite_odds = float(group["win_odds"].min())
        failure = (
            "hit" if returned > 0 else
            "both_missing" if not win_actual and not hole_actual else
            "win_side_missing" if not win_actual else
            "hole_side_missing" if not hole_actual else
            "overlap_or_coverage"
        )
        output.append({
            "race_id": str(race_id),
            "date": group["date"].iloc[0],
            "venue": str(group["venue"].iloc[0]),
            "field_size": len(group),
            "tickets": len(tickets),
            "stake": len(tickets) * 100,
            "return": returned,
            "hit": int(returned > 0),
            "failure": failure,
            "wp1": float(winners["p_win"].iloc[0]),
            "wp2": float(winners["p_win"].iloc[1]),
            "wp_gap": float(
                winners["p_win"].iloc[0] - winners["p_win"].iloc[1]
            ),
            "wp_top2": float(winners["p_win"].sum()),
            "wp_entropy": entropy(group["p_win"].to_numpy()),
            "axis_pp_min": float(winners["p_place"].min()),
            "axis_pp_sum": float(winners["p_place"].sum()),
            "axis_odds_max": float(winners["win_odds"].max()),
            "favorite_odds": favorite_odds,
            "hole1_pp": float(holes["p_place"].iloc[0]),
            "hole2_pp": float(holes["p_place"].iloc[1]),
            "hole3_pp": float(holes["p_place"].iloc[2]),
            "hole_pp_sum": float(holes["p_place"].sum()),
            "hole_pp_min": float(holes["p_place"].min()),
            "hole1_odds": float(holes["win_odds"].iloc[0]),
            "hole_avg_odds": float(holes["win_odds"].mean()),
            "hole1_value": float(
                holes["p_place"].iloc[0] * holes["win_odds"].iloc[0]
            ),
            "hole1_market_gap": float(
                market_rank.loc[hole1_index] - pp_rank.loc[hole1_index]
            ),
            "longshot_count": len(longshots),
            "overlap": len(set(win_numbers) & set(hole_numbers)),
        })
    result = pd.DataFrame(output)
    result["year"] = result["date"].dt.year
    return result


def metric(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {
            "races": 0, "tickets": 0, "hits": 0, "hit_rate": 0,
            "stake": 0, "return": 0, "roi": 0, "roi_without_max": 0,
            "max_return_share": 0,
        }
    stake = int(frame["stake"].sum())
    returned = int(frame["return"].sum())
    maximum_index = frame["return"].idxmax()
    reduced_stake = stake - int(frame.loc[maximum_index, "stake"])
    reduced_return = returned - int(frame.loc[maximum_index, "return"])
    return {
        "races": len(frame),
        "tickets": int(frame["tickets"].sum()),
        "hits": int(frame["hit"].sum()),
        "hit_rate": float(frame["hit"].mean() * 100),
        "stake": stake,
        "return": returned,
        "roi": float(100 * returned / stake),
        "roi_without_max": (
            float(100 * reduced_return / reduced_stake)
            if reduced_stake else 0.0
        ),
        "max_return_share": float(frame["return"].max() / returned)
        if returned else 0.0,
    }


def atoms() -> list[tuple[str, str, float]]:
    specs = {
        "field_size": (">=", [10, 12, 14, 16]),
        "wp1": (">=", [.18, .22, .26, .30, .34]),
        "wp_gap": ("<=", [.02, .04, .06, .08, .10]),
        "wp_top2": (">=", [.35, .40, .45, .50, .55]),
        "wp_entropy": (">=", [.80, .85, .90, .93, .95]),
        "axis_pp_min": (">=", [.20, .25, .30, .35, .40]),
        "axis_pp_sum": (">=", [.50, .60, .70, .80, .90]),
        "favorite_odds": (">=", [1.5, 1.8, 2.0, 2.5, 3.0]),
        "axis_odds_max": ("<=", [5, 7, 10, 15, 20]),
        "hole1_pp": (">=", [.12, .15, .18, .22, .26, .30]),
        "hole3_pp": (">=", [.05, .08, .10, .12, .15, .18]),
        "hole_pp_sum": (">=", [.30, .40, .50, .60, .70]),
        "hole1_odds": ("<=", [15, 20, 30, 50, 80]),
        "hole_avg_odds": ("<=", [25, 35, 50, 70, 100]),
        "hole1_value": (">=", [2, 3, 4, 5, 7]),
        "hole1_market_gap": (">=", [2, 3, 4, 5, 6]),
        "longshot_count": ("<=", [3, 4, 5, 6, 8]),
        "overlap": ("==", [0, 1]),
    }
    return [
        (column, operator, float(value))
        for column, (operator, values) in specs.items()
        for value in values
    ]


def apply_atom(frame: pd.DataFrame, atom) -> pd.Series:
    column, operator, value = atom
    if operator == ">=":
        return frame[column].ge(value)
    if operator == "<=":
        return frame[column].le(value)
    return frame[column].eq(value)


def label(atom) -> str:
    column, operator, value = atom
    return f"{column}{operator}{value:g}"


def analyze(frame: pd.DataFrame, market: str) -> dict:
    years = sorted(frame["year"].unique())
    discovery = frame[frame["year"].eq(2024)]
    all_atoms = atoms()
    rules = []
    candidates = [(atom,) for atom in all_atoms]
    candidates.extend(combinations(all_atoms, 2))
    for parts in candidates:
        mask = pd.Series(True, index=discovery.index)
        for atom in parts:
            mask &= apply_atom(discovery, atom)
        selected = discovery[mask]
        if len(selected) < 100:
            continue
        discovery_metric = metric(selected)
        periods = {"2024": discovery_metric}
        for year in years:
            if year == 2024:
                continue
            subset = frame[frame["year"].eq(year)]
            year_mask = pd.Series(True, index=subset.index)
            for atom in parts:
                year_mask &= apply_atom(subset, atom)
            periods[str(year)] = metric(subset[year_mask])
        rules.append({
            "rule": " & ".join(label(atom) for atom in parts),
            "parts": [list(atom) for atom in parts],
            "periods": periods,
        })
    validation_years = [year for year in years if year > 2024]
    confirmed = [
        rule for rule in rules
        if all(
            rule["periods"][str(year)]["races"] >= 50
            and rule["periods"][str(year)]["roi"] >= 100
            and rule["periods"][str(year)]["roi_without_max"] >= 95
            for year in validation_years
        )
    ]
    stable = sorted(
        rules,
        key=lambda rule: min(
            rule["periods"][str(year)]["roi"]
            for year in years
            if rule["periods"][str(year)]["races"] >= 50
        ),
        reverse=True,
    )
    failures = {
        name: {
            "races": len(group),
            "share": float(len(group) / len(frame) * 100),
            "mean_wp1": float(group["wp1"].mean()),
            "mean_wp_gap": float(group["wp_gap"].mean()),
            "mean_axis_pp_min": float(group["axis_pp_min"].mean()),
            "mean_hole1_pp": float(group["hole1_pp"].mean()),
            "mean_hole_pp_sum": float(group["hole_pp_sum"].mean()),
            "mean_hole1_market_gap": float(group["hole1_market_gap"].mean()),
        }
        for name, group in frame.groupby("failure")
    }
    return {
        "version": VERSION,
        "market": market,
        "method": "2024 discovery; later years untouched validation",
        "baseline": {
            str(year): metric(frame[frame["year"].eq(year)])
            for year in years
        },
        "failure_profiles": failures,
        "rules_evaluated_after_discovery_floor": len(rules),
        "confirmed": sorted(
            confirmed,
            key=lambda rule: min(
                rule["periods"][str(year)]["roi"]
                for year in validation_years
            ),
            reverse=True,
        )[:100],
        "best_stable": stable[:100],
        "limitations": [
            "Final win odds proxy seven-minute odds.",
            "Sanfuku odds themselves are unavailable.",
            "JRA payout coverage currently ends in 2025.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--payout-db", type=Path, required=True)
    parser.add_argument("--market", choices=("jra", "local"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frame = pd.read_csv(
        args.oos,
        usecols=[
            "race_id", "date", "venue", "umaban", "finish_pos",
            "win_odds", "p_win", "p_place",
        ],
        parse_dates=["date"],
        dtype={"race_id": str},
    ).dropna()
    races = make_races(frame, payouts(args.payout_db))
    result = analyze(races, args.market)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        args.market, "races", len(races),
        "confirmed", len(result["confirmed"]),
        "best", result["best_stable"][0] if result["best_stable"] else None,
    )


if __name__ == "__main__":
    main()
