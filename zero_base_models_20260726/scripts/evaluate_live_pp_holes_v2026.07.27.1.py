"""Evaluate the live rule: top-3 p_place among runners with win odds >= 10.

The input must contain out-of-sample, walk-forward p_place predictions.
Final odds are used as a proxy for the seven-minute odds threshold.

Version: v2026.07.27.1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


VERSION = "v2026.07.27.1"


def metrics(frame: pd.DataFrame) -> dict:
    candidates = frame[frame["win_odds"].ge(10)].copy()
    candidates["hole_rank"] = candidates.groupby("race_id")["p_place"].rank(
        method="first", ascending=False
    )
    selected = candidates[candidates["hole_rank"].le(3)].copy()
    candidate_races = set(candidates["race_id"])
    actual_hit_races = set(
        candidates.loc[candidates["is_place"].eq(1), "race_id"]
    )
    caught_races = set(
        selected.loc[selected["is_place"].eq(1), "race_id"]
    )
    ranks = {
        str(rank): {
            "selections": int(len(group)),
            "places": int(group["is_place"].sum()),
            "place_rate": float(group["is_place"].mean() * 100),
            "mean_odds": float(group["win_odds"].mean()),
        }
        for rank, group in selected.groupby("hole_rank")
    }
    bands = {}
    for label, low, high in (
        ("10-19.9", 10, 20),
        ("20-29.9", 20, 30),
        ("30-49.9", 30, 50),
        ("50+", 50, float("inf")),
    ):
        group = selected[
            selected["win_odds"].ge(low) & selected["win_odds"].lt(high)
        ]
        bands[label] = {
            "selections": int(len(group)),
            "places": int(group["is_place"].sum()),
            "place_rate": (
                float(group["is_place"].mean() * 100) if len(group) else 0.0
            ),
        }
    return {
        "candidate_races": len(candidate_races),
        "races_with_actual_10x_place": len(actual_hit_races),
        "races_caught_by_selected_three": len(caught_races),
        "all_candidate_race_hit_rate": (
            100 * len(caught_races) / len(candidate_races)
            if candidate_races else 0.0
        ),
        "capture_when_10x_horse_places": (
            100 * len(caught_races & actual_hit_races) / len(actual_hit_races)
            if actual_hit_races else 0.0
        ),
        "selections": len(selected),
        "places": int(selected["is_place"].sum()),
        "selection_place_rate": float(selected["is_place"].mean() * 100),
        "mean_selected_per_race": (
            float(len(selected) / len(candidate_races))
            if candidate_races else 0.0
        ),
        "by_hole_rank": ranks,
        "by_win_odds": bands,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--market", choices=("jra", "local"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frame = pd.read_csv(
        args.oos,
        usecols=[
            "race_id", "date", "is_place", "win_odds", "p_place",
        ],
        parse_dates=["date"],
    )
    frame = frame[
        frame["is_place"].notna()
        & frame["win_odds"].notna()
        & frame["p_place"].notna()
    ].copy()
    result = {
        "version": VERSION,
        "market": args.market,
        "rule": "win_odds >= 10; top 3 by walk-forward p_place",
        "overall": metrics(frame),
        "yearly": {
            str(year): metrics(frame[frame["date"].dt.year.eq(year)])
            for year in sorted(frame["date"].dt.year.unique())
        },
        "limitations": [
            "Predictions are walk-forward out-of-sample.",
            "Final win odds proxy the live seven-minute odds threshold.",
            "A race with no runner at 10.0 or higher is not a candidate race.",
        ],
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
