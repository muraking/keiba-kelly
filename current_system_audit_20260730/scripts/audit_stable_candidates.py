#!/usr/bin/env python3
"""Stable-candidate diagnostics for the 2026-07-30 current-system audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


VERSION = "v2026.07.30.2"
KEYS = (
    ("WIN_ALL", "T8"),
    ("PLACE_ALL", "T7"),
    ("PLACE_ALL", "T8"),
    ("W4", "T7"),
    ("W4", "T8"),
    ("U4", "T7"),
    ("U4", "T8"),
)


def metrics(frame: pd.DataFrame) -> dict:
    stake = float(frame["stake"].sum())
    payout = float(frame["payout"].sum())
    if frame.empty or stake <= 0:
        return {"races": 0, "tickets": 0, "roi": None, "profit": 0}
    return {
        "races": int(len(frame)),
        "tickets": int(frame["ticket_n"].sum()),
        "roi": round(100.0 * payout / stake, 2),
        "profit": round(payout - stake),
    }


def max_removed(frame: pd.DataFrame, count: int) -> dict:
    if frame.empty:
        return metrics(frame)
    trimmed = frame.drop(frame.nlargest(min(count, len(frame)), "payout").index)
    return metrics(trimmed)


def bootstrap_roi(frame: pd.DataFrame, seed: int, n_boot: int = 10_000) -> dict:
    if frame.empty:
        return {"p05": None, "median": None, "p95": None, "prob_gt_100": None}
    rng = np.random.default_rng(seed)
    stake = frame["stake"].to_numpy(dtype=float)
    payout = frame["payout"].to_numpy(dtype=float)
    values = np.empty(n_boot)
    for start in range(0, n_boot, 500):
        size = min(500, n_boot - start)
        sample = rng.integers(0, len(frame), size=(size, len(frame)))
        values[start : start + size] = (
            payout[sample].sum(axis=1) / stake[sample].sum(axis=1) * 100.0
        )
    return {
        "p05": round(float(np.quantile(values, 0.05)), 2),
        "median": round(float(np.median(values)), 2),
        "p95": round(float(np.quantile(values, 0.95)), 2),
        "prob_gt_100": round(float(np.mean(values > 100.0)), 4),
    }


def grouped(frame: pd.DataFrame, column: str) -> list[dict]:
    rows = []
    for value, group in frame.groupby(column, dropna=False):
        rows.append({column: str(value), **metrics(group)})
    return rows


def audit(path: Path, seed: int) -> dict:
    usecols = [
        "fold", "date", "venue", "strategy_id", "target_set",
        "ticket_n", "stake", "payout",
    ]
    source = pd.read_csv(path, usecols=usecols)
    source["date"] = pd.to_datetime(source["date"])
    source["year"] = source["date"].dt.year
    source["half"] = np.where(
        source["date"] <= source["date"].min()
        + (source["date"].max() - source["date"].min()) / 2,
        "early",
        "late",
    )
    result = {
        "version": VERSION,
        "source": str(path),
        "date_min": str(source["date"].min().date()),
        "date_max": str(source["date"].max().date()),
        "candidates": [],
    }
    for offset, (strategy_id, target_set) in enumerate(KEYS):
        frame = source[
            (source["strategy_id"] == strategy_id)
            & (source["target_set"] == target_set)
        ].copy()
        if frame.empty:
            continue
        result["candidates"].append({
            "strategy_id": strategy_id,
            "target_set": target_set,
            "overall": metrics(frame),
            "without_top1_payout": max_removed(frame, 1),
            "without_top3_payouts": max_removed(frame, 3),
            "bootstrap_race_resampling": bootstrap_roi(frame, seed + offset),
            "by_year": grouped(frame, "year"),
            "by_fold": grouped(frame, "fold"),
            "by_half": grouped(frame, "half"),
            "by_venue": sorted(
                grouped(frame, "venue"),
                key=lambda row: row["races"],
                reverse=True,
            ),
        })
    return result


def markdown(result: dict) -> str:
    lines = [
        f"# Stable candidate audit {result['version']}",
        "",
        f"- source: `{result['source']}`",
        f"- OOS: {result['date_min']}〜{result['date_max']}",
        "",
        "| strategy | target | races | tickets | ROI | top1除外 | top3除外 | "
        "bootstrap 5% | P(ROI>100) | early | late |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["candidates"]:
        halves = {item["half"]: item for item in row["by_half"]}
        lines.append(
            f"| {row['strategy_id']} | {row['target_set']} | "
            f"{row['overall']['races']} | {row['overall']['tickets']} | "
            f"{row['overall']['roi']:.2f}% | "
            f"{row['without_top1_payout']['roi']:.2f}% | "
            f"{row['without_top3_payouts']['roi']:.2f}% | "
            f"{row['bootstrap_race_resampling']['p05']:.2f}% | "
            f"{100 * row['bootstrap_race_resampling']['prob_gt_100']:.1f}% | "
            f"{halves['early']['roi']:.2f}% | {halves['late']['roi']:.2f}% |"
        )
    lines.extend([
        "",
        "## 注意",
        "",
        "- bootstrapはレース単位再標本化であり、将来成績を保証しない。",
        "- 同じOOSで複数戦略を比較しているため、候補確定ではなく前向き検証対象とする。",
        "- オッズはDB収録時点の値。7分前運用では価格変動による劣化を別途測る必要がある。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_prefix", type=Path)
    parser.add_argument("--seed", type=int, default=20260730)
    args = parser.parse_args()
    result = audit(args.input, args.seed)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{args.output_prefix}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Path(f"{args.output_prefix}.md").write_text(
        markdown(result),
        encoding="utf-8",
    )
    print(markdown(result))


if __name__ == "__main__":
    main()
