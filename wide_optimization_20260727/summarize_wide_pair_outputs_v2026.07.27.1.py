"""Summarize wide pair OOS predictions and late/balanced race segments.

Version: v2026.07.27.1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score


VERSION = "v2026.07.27.1"


def top_k(frame: pd.DataFrame, probability: str, k: int) -> pd.DataFrame:
    return (
        frame.sort_values(
            ["race_id", probability, "comb"],
            ascending=[True, False, True],
        )
        .groupby("race_id", sort=False)
        .head(k)
    )


def metrics(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {
            "bets": 0, "races": 0, "hits": 0, "hit_rate": 0.0,
            "roi": 0.0, "roi_without_max": 0.0,
        }
    returns = frame["return"].to_numpy(dtype=float)
    total = float(returns.sum())
    return {
        "bets": int(len(frame)),
        "races": int(frame["race_id"].nunique()),
        "bets_per_race": float(len(frame) / frame["race_id"].nunique()),
        "hits": int((returns > 0).sum()),
        "hit_rate": float((returns > 0).mean() * 100),
        "roi": float(total / len(frame)),
        "roi_without_max": float((total - returns.max()) / len(frame)),
        "max_payout": float(returns.max()),
        "max_share": float(returns.max() / total) if total else None,
    }


def strategies(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    win = frame[frame["axis_source"].eq("win")]
    place = frame[frame["axis_source"].eq("place")]
    return {
        "current_win_axis_max6": win,
        "win_axis1_max3": win[win["axis_rank"].eq(1)],
        "place_axis1_max3": place[place["axis_rank"].eq(1)],
        "pair_probability_top1": top_k(place, "pred_wide_hit_probability", 1),
        "pair_probability_top2": top_k(place, "pred_wide_hit_probability", 2),
        "pair_probability_top3": top_k(place, "pred_wide_hit_probability", 3),
        "independent_product_top1": top_k(place, "prob_independent", 1),
        "independent_product_top2": top_k(place, "prob_independent", 2),
        "independent_product_top3": top_k(place, "prob_independent", 3),
    }


def calibration(frame: pd.DataFrame, market: str) -> list[dict]:
    rows = []
    y = frame["target_wide_hit"].to_numpy(dtype=int)
    for name in (
        "prob_independent", "prob_logistic", "prob_hist_gb",
        "pred_wide_hit_probability",
    ):
        probability = np.clip(frame[name].to_numpy(dtype=float), 1e-6, 1 - 1e-6)
        rows.append({
            "market": market, "model": name, "rows": len(frame),
            "logloss": log_loss(y, probability),
            "brier": brier_score_loss(y, probability),
            "auc": roc_auc_score(y, probability),
        })
    bins = pd.qcut(
        frame["pred_wide_hit_probability"], 10, duplicates="drop"
    )
    for interval, group in frame.groupby(bins, observed=True):
        rows.append({
            "market": market, "model": "calibration_bin",
            "probability_bin": str(interval), "rows": len(group),
            "predicted_mean": group["pred_wide_hit_probability"].mean(),
            "actual_hit_rate": group["target_wide_hit"].mean(),
        })
    return rows


def process(path: Path, market: str) -> tuple[list, list, list, list, list]:
    frame = pd.read_csv(path, parse_dates=["date"])
    frame["race_num"] = pd.to_numeric(
        frame["race_id"].astype(str).str[-2:], errors="coerce"
    )
    frame["late_balanced"] = (
        frame["race_num"].ge(7)
        & frame["race_place_gap"].lt(.05)
        & frame["race_win_entropy"].ge(.85)
    )
    comparison, yearly, venue, segments = [], [], [], []
    available = strategies(frame)
    for name, selected in available.items():
        comparison.append({"market": market, "strategy": name, **metrics(selected)})
        for year, group in selected.groupby("year"):
            yearly.append({
                "market": market, "strategy": name, "year": int(year),
                **metrics(group),
            })
        for location, group in selected.groupby("venue"):
            if len(group) >= 30:
                venue.append({
                    "market": market, "strategy": name, "venue": location,
                    **metrics(group),
                })
        segments.append({
            "market": market, "strategy": name,
            "segment": "late_r7plus_place_gap_lt05_entropy_ge085",
            **metrics(selected[selected["late_balanced"]]),
        })
    patterns = []
    current = frame[frame["axis_source"].eq("win")]
    for (axis_rank, hole_rank), group in current.groupby(
        ["axis_rank", "hole_rank"]
    ):
        patterns.append({
            "market": market, "axis_rank": int(axis_rank),
            "hole_rank": int(hole_rank), **metrics(group),
        })
    return comparison, yearly, venue, segments, patterns, calibration(frame, market)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    collections = [[] for _ in range(6)]
    for market in ("jra", "local"):
        path = args.output / f"{market}_wide_pair_oos_predictions.csv.gz"
        if not path.exists():
            continue
        result = process(path, market)
        for target, values in zip(collections, result):
            target.extend(values)
    names = (
        "strategy_comparison.csv", "strategy_by_year.csv",
        "strategy_by_venue.csv", "current_segment_report.csv",
        "current_six_patterns.csv", "wide_pair_calibration.csv",
    )
    for name, rows in zip(names, collections):
        pd.DataFrame(rows).to_csv(args.output / name, index=False)
    manifest = {
        "version": VERSION,
        "markets": sorted({
            row["market"] for collection in collections for row in collection
            if "market" in row
        }),
        "purchase_time_wide_odds": False,
        "ev_strategy_status": "blocked_by_missing_historical_purchase_odds",
        "files": list(names),
    }
    (args.output / "summary_manifest_v2026.07.27.1.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
