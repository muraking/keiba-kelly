"""Evaluate win-top2 x longshot-top3 sanfuku and PP/top2 association.

Selection uses walk-forward OOS p_win/p_place. Longshots require final win
odds >= 10. Final tote payouts evaluate the fixed formation.

Version: v2026.07.28.1
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


VERSION = "v2026.07.28.1"


def ticket(numbers) -> str:
    return "-".join(str(int(number)) for number in sorted(numbers))


def normalize_ticket(value: str) -> str:
    numbers = [int(number) for number in re.findall(r"\d+", str(value))]
    return ticket(numbers) if len(numbers) == 3 else str(value)


def load_payouts(path: Path) -> dict[str, dict[str, int]]:
    with sqlite3.connect(path) as connection:
        frame = pd.read_sql_query(
            "SELECT race_id,comb,payout FROM payouts "
            "WHERE bet_type='sanfuku'",
            connection,
        )
    result: dict[str, dict[str, int]] = {}
    for row in frame.itertuples():
        result.setdefault(str(row.race_id), {})[
            normalize_ticket(str(row.comb))
        ] = int(row.payout)
    return result


def build_bets(frame: pd.DataFrame, payouts: dict) -> pd.DataFrame:
    rows = []
    for race_id, group in frame.groupby("race_id", sort=False):
        winners = group.sort_values(
            ["p_win", "umaban"], ascending=[False, True]
        ).head(2)
        holes = group[group["win_odds"].ge(10)].sort_values(
            ["p_place", "umaban"], ascending=[False, True]
        ).head(3)
        if len(winners) < 2 or len(holes) < 1:
            continue
        win_numbers = winners["umaban"].astype(int).tolist()
        hole_numbers = holes["umaban"].astype(int).tolist()
        middle = sorted(set(win_numbers + hole_numbers))
        tickets = {
            ticket((axis, partner, hole))
            for axis, partner, hole in product(
                win_numbers, middle, hole_numbers
            )
            if len({axis, partner, hole}) == 3
        }
        if not tickets or str(race_id) not in payouts:
            continue
        table = payouts[str(race_id)]
        returned = sum(table.get(value, 0) for value in tickets)
        rows.append({
            "race_id": str(race_id),
            "date": group["date"].iloc[0],
            "tickets": len(tickets),
            "stake": 100 * len(tickets),
            "return": returned,
            "hit": int(returned > 0),
            "max_return": returned,
            "overlap": len(set(win_numbers) & set(hole_numbers)),
        })
    return pd.DataFrame(rows)


def bet_metrics(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {
            "races": 0, "tickets": 0, "hits": 0, "hit_rate": 0,
            "stake": 0, "return": 0, "roi": 0,
        }
    stake, returned = int(frame["stake"].sum()), int(frame["return"].sum())
    return {
        "races": len(frame),
        "tickets": int(frame["tickets"].sum()),
        "mean_tickets_per_race": float(frame["tickets"].mean()),
        "hits": int(frame["hit"].sum()),
        "hit_rate": float(frame["hit"].mean() * 100),
        "stake": stake,
        "return": returned,
        "roi": float(100 * returned / stake),
        "roi_without_max_return": float(
            100 * (returned - frame["max_return"].max())
            / (stake - frame.loc[frame["max_return"].idxmax(), "stake"])
        ) if len(frame) > 1 and stake > frame["stake"].min() else 0.0,
        "max_return_share": float(frame["max_return"].max() / returned)
        if returned else 0.0,
        "races_with_win_hole_overlap": int(frame["overlap"].gt(0).sum()),
    }


def pp_link(frame: pd.DataFrame) -> dict:
    data = frame.copy()
    data["is_top2"] = data["finish_pos"].le(2).astype(int)
    bins = [-0.001, .05, .10, .15, .20, .25, .30, .40, .50, .70, 1.001]
    labels = [
        "0-5%", "5-10%", "10-15%", "15-20%", "20-25%", "25-30%",
        "30-40%", "40-50%", "50-70%", "70-100%",
    ]
    data["pp_band"] = pd.cut(data["p_place"], bins=bins, labels=labels)
    bands = {}
    for label, group in data.groupby("pp_band", observed=True):
        bands[str(label)] = {
            "horses": len(group),
            "mean_pp": float(group["p_place"].mean() * 100),
            "actual_place_rate": float(group["is_place"].mean() * 100),
            "actual_top2_rate": float(group["is_top2"].mean() * 100),
            "top2_share_among_places": float(
                group["is_top2"].sum() / group["is_place"].sum() * 100
            ) if group["is_place"].sum() else 0.0,
        }
    return {
        "horses": len(data),
        "pearson_pp_vs_top2": float(data["p_place"].corr(data["is_top2"])),
        "spearman_pp_vs_top2": float(
            data["p_place"].corr(data["is_top2"], method="spearman")
        ),
        "auc_pp_for_top2": float(roc_auc_score(data["is_top2"], data["p_place"])),
        "bands": bands,
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
            "race_id", "date", "umaban", "finish_pos", "is_place",
            "win_odds", "p_win", "p_place",
        ],
        parse_dates=["date"],
        dtype={"race_id": str},
    ).dropna(subset=["p_win", "p_place", "win_odds", "finish_pos"])
    payouts = load_payouts(args.payout_db)
    bets = build_bets(frame, payouts)
    years = sorted(frame["date"].dt.year.unique())
    report = {
        "version": VERSION,
        "market": args.market,
        "formation": [
            "win1,win2",
            "win1,win2,hole1,hole2,hole3",
            "hole1,hole2,hole3",
        ],
        "selection": "win=top2 p_win; hole=top3 p_place among win_odds>=10",
        "sanfuku": {
            "overall": bet_metrics(bets),
            "yearly": {
                str(year): bet_metrics(bets[bets["date"].dt.year.eq(year)])
                for year in years
            },
        },
        "pp_top2_link": {
            "overall": pp_link(frame),
            "yearly": {
                str(year): pp_link(frame[frame["date"].dt.year.eq(year)])
                for year in years
            },
        },
        "limitations": [
            "Walk-forward OOS model probabilities are used.",
            "Final odds proxy the seven-minute longshot threshold.",
            "Final tote sanfuku payouts are used.",
        ],
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
