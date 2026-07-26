"""Search leakage-safe win-top2 x longshot-top3 umaren/wide rules.

2024 is discovery, 2025 is untouched validation, and local 2026 is a second
confirmation year. Result payouts never select a ticket.
Version: v2026.07.27.1
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


VERSION = "v2026.07.27.1"
YEARS = (2024, 2025, 2026)
SPECS = (
    ("bet_type", "hole_rank", "partner_rank", "hole_odds_bin"),
    ("bet_type", "hole_rank", "partner_rank", "product_bin"),
    ("bet_type", "hole_rank", "partner_rank", "hole_p_bin"),
    ("bet_type", "hole_rank", "partner_rank", "partner_p_bin"),
    ("bet_type", "hole_rank", "partner_rank", "field_bin"),
    ("bet_type", "hole_rank", "partner_rank", "race_num_bin"),
    ("bet_type", "hole_rank", "partner_rank", "hole_odds_bin", "product_bin"),
    ("bet_type", "hole_rank", "partner_rank", "hole_odds_bin", "hole_p_bin"),
    ("bet_type", "hole_rank", "partner_rank", "hole_odds_bin", "partner_p_bin"),
    ("bet_type", "hole_rank", "partner_rank", "hole_odds_bin", "field_bin"),
    ("bet_type", "hole_rank", "partner_rank", "hole_odds_bin", "race_num_bin"),
    ("bet_type", "hole_rank", "partner_rank", "product_bin", "hole_p_bin"),
    ("bet_type", "hole_rank", "partner_rank", "product_bin", "partner_p_bin"),
    ("bet_type", "hole_rank", "partner_rank", "product_bin", "field_bin"),
    ("bet_type", "hole_rank", "partner_rank", "product_bin", "race_num_bin"),
    ("bet_type", "hole_rank", "partner_rank", "hole_p_bin", "partner_p_bin"),
    ("bet_type", "hole_rank", "partner_rank", "hole_p_bin", "field_bin"),
    ("bet_type", "hole_rank", "partner_rank", "partner_p_bin", "field_bin"),
    ("bet_type", "hole_rank", "partner_rank", "venue", "hole_odds_bin"),
    ("bet_type", "hole_rank", "partner_rank", "venue", "product_bin"),
    ("bet_type", "hole_rank", "partner_rank", "venue", "hole_p_bin"),
)


def pair(a: int, b: int) -> str:
    return "-".join(map(str, sorted((a, b))))


def metrics(group: pd.DataFrame) -> dict:
    if group.empty:
        return {
            "bets": 0, "races": 0, "hits": 0, "hit_rate": 0.0, "roi": 0.0,
            "roi_without_max": 0.0, "lcb90": -999.0, "max_share": None,
        }
    returns = group["return"].to_numpy(dtype=float)
    units = returns / 100.0
    total = float(returns.sum())
    se = units.std(ddof=1) / np.sqrt(len(units)) if len(units) > 1 else 999.0
    return {
        "bets": int(len(group)),
        "races": int(group["race_id"].nunique()),
        "hits": int((returns > 0).sum()),
        "hit_rate": float((returns > 0).mean() * 100),
        "roi": float(total / len(group)),
        "roi_without_max": float((total - returns.max()) / len(group)),
        "lcb90": float(units.mean() - 1.2816 * se),
        "max_share": float(returns.max() / total) if total else None,
    }


def build(oos: Path, db: Path) -> pd.DataFrame:
    prediction = pd.read_csv(oos, parse_dates=["date"])
    prediction["race_id"] = prediction["race_id"].astype(str)
    with sqlite3.connect(db) as connection:
        payout = pd.read_sql_query(
            """
            SELECT race_id, bet_type, comb, payout
            FROM payouts
            WHERE bet_type IN ('wide', 'umaren')
            """,
            connection,
        )
        race_meta = pd.read_sql_query(
            "SELECT race_id, MAX(race_num) AS race_num FROM runs GROUP BY race_id",
            connection,
        )
    payout["race_id"] = payout["race_id"].astype(str)
    race_meta["race_id"] = race_meta["race_id"].astype(str)
    race_num = dict(zip(race_meta["race_id"], race_meta["race_num"]))
    pay = {
        (str(row.race_id), str(row.bet_type), str(row.comb)): float(row.payout)
        for row in payout.itertuples()
    }
    covered = {
        bet_type: set(payout.loc[payout["bet_type"].eq(bet_type), "race_id"])
        for bet_type in ("wide", "umaren")
    }

    rows = []
    for race_id, group in prediction.groupby("race_id", sort=False):
        race_id = str(race_id)
        win_order = group.sort_values(["p_win", "umaban"], ascending=[False, True])
        holes = group[group["win_odds"].ge(10)].sort_values(
            ["p_place", "umaban"], ascending=[False, True]
        ).head(3)
        for hole_rank, hole in enumerate(holes.itertuples(), 1):
            for partner_rank, partner in enumerate(win_order.head(2).itertuples(), 1):
                if int(hole.umaban) == int(partner.umaban):
                    continue
                comb = pair(int(hole.umaban), int(partner.umaban))
                common = {
                    "race_id": race_id, "date": hole.date, "venue": hole.venue,
                    "race_num": int(race_num.get(race_id) or 0),
                    "hole_rank": hole_rank, "partner_rank": partner_rank,
                    "hole": int(hole.umaban), "partner": int(partner.umaban),
                    "hole_odds": float(hole.win_odds),
                    "partner_odds": float(partner.win_odds),
                    "odds_product": float(hole.win_odds * partner.win_odds),
                    "hole_p": float(hole.p_place), "partner_p": float(partner.p_win),
                    "field": int(hole.field_size),
                }
                for bet_type in ("wide", "umaren"):
                    if race_id in covered[bet_type]:
                        rows.append({
                            **common, "bet_type": bet_type,
                            "return": pay.get((race_id, bet_type, comb), 0.0),
                        })

    frame = pd.DataFrame(rows)
    frame["year"] = frame["date"].dt.year
    frame["hole_odds_bin"] = pd.cut(
        frame["hole_odds"], [10, 15, 20, 30, 50, 80, np.inf], right=False,
        labels=["10-15", "15-20", "20-30", "30-50", "50-80", "80+"],
    )
    frame["product_bin"] = pd.cut(
        frame["odds_product"], [0, 30, 60, 100, 200, np.inf], right=False,
        labels=["<30", "30-60", "60-100", "100-200", "200+"],
    )
    frame["hole_p_bin"] = pd.cut(
        frame["hole_p"], [-np.inf, .12, .16, .20, .25, np.inf], right=False,
        labels=["<.12", ".12-.16", ".16-.20", ".20-.25", ".25+"],
    )
    frame["partner_p_bin"] = pd.cut(
        frame["partner_p"], [-np.inf, .15, .25, .35, np.inf], right=False,
        labels=["<.15", ".15-.25", ".25-.35", ".35+"],
    )
    frame["field_bin"] = pd.cut(
        frame["field"], [0, 7, 9, 11, np.inf],
        labels=["<=7", "8-9", "10-11", "12+"],
    )
    frame["race_num_bin"] = pd.cut(
        frame["race_num"], [0, 4, 7, 10, np.inf],
        labels=["1-3", "4-6", "7-9", "10+"],
    )
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--market", choices=("jra", "local"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    data = build(args.oos, args.db)
    minimum = 100 if args.market == "jra" else 200
    baseline = {
        bet_type: {
            str(year): metrics(data[data["year"].eq(year) & data["bet_type"].eq(bet_type)])
            for year in YEARS
        }
        for bet_type in ("wide", "umaren")
    }
    candidates = []
    for spec in SPECS:
        groups = {
            year: {
                key if isinstance(key, tuple) else (key,): group
                for key, group in data[data["year"].eq(year)].groupby(
                    list(spec), observed=True
                )
            }
            for year in YEARS
        }
        for key, discovery in groups[2024].items():
            m24 = metrics(discovery)
            if (
                m24["bets"] < minimum
                or m24["max_share"] is None
                or m24["max_share"] > .20
                or m24["roi"] < 100
                or m24["roi_without_max"] < 95
            ):
                continue
            row = {
                "condition": {
                    column: str(value) for column, value in zip(spec, key)
                },
                "2024": m24,
                "2025": metrics(groups[2025].get(key, data.iloc[0:0])),
                "2026": metrics(groups[2026].get(key, data.iloc[0:0])),
            }
            candidates.append(row)

    validated = [
        row for row in candidates
        if row["2025"]["bets"] >= minimum
        and row["2024"]["roi_without_max"] >= 100
        and row["2025"]["roi"] >= 100
        and row["2025"]["roi_without_max"] >= 100
    ]
    confirmed = [
        row for row in validated
        if row["2026"]["bets"] >= 100
        and row["2026"]["roi"] >= 100
        and row["2026"]["roi_without_max"] >= 100
    ]
    evaluation_years = ("2024", "2025", "2026") if args.market == "local" else (
        "2024", "2025"
    )
    score = lambda row: min(
        row[year]["roi_without_max"] for year in evaluation_years
    )
    candidates.sort(
        key=lambda row: min(row["2024"]["roi_without_max"], row["2025"]["roi_without_max"]),
        reverse=True,
    )
    validated.sort(key=score, reverse=True)
    confirmed.sort(key=score, reverse=True)
    result = {
        "version": VERSION,
        "market": args.market,
        "ticket_rows": int(len(data)),
        "minimum_bets": minimum,
        "baseline": baseline,
        "discovery_candidates": len(candidates),
        "validated_2025": len(validated),
        "confirmed_2026": len(confirmed),
        "best_confirmed": confirmed[:100],
        "best_validated": validated[:200],
        "best_discovery_candidates": candidates[:100],
        "selection_note": "No result payout or hit status is used as a condition.",
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        args.market, "rows", len(data), "candidates", len(candidates),
        "validated", len(validated), "confirmed", len(confirmed),
    )
    selected = confirmed if args.market == "local" else validated
    for row in selected[:20]:
        print(
            row["condition"],
            [
                (
                    year, row[year]["bets"], round(row[year]["roi"], 1),
                    round(row[year]["roi_without_max"], 1),
                    round(row[year]["lcb90"], 3),
                )
                for year in evaluation_years
            ],
        )


if __name__ == "__main__":
    main()
