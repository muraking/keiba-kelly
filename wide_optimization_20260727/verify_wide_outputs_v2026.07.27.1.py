"""Regression checks for wide optimization outputs.

Version: v2026.07.27.1
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


VERSION = "v2026.07.27.1"
OUTPUT = Path(__file__).with_name("outputs")


def one(frame: pd.DataFrame, expression: str) -> pd.Series:
    selected = frame.query(expression)
    assert len(selected) == 1, expression
    return selected.iloc[0]


def main() -> None:
    comparison = pd.read_csv(OUTPUT / "strategy_comparison.csv")
    patterns = pd.read_csv(OUTPUT / "current_six_patterns.csv")
    segments = pd.read_csv(OUTPUT / "current_segment_report.csv")
    calibration = pd.read_csv(OUTPUT / "wide_pair_calibration.csv")
    assert set(comparison["market"]) == {"jra", "local"}
    assert len(patterns) == 12
    assert one(
        comparison,
        "market == 'jra' and strategy == 'current_win_axis_max6'",
    )["bets"] == 19511
    assert one(
        comparison,
        "market == 'local' and strategy == 'current_win_axis_max6'",
    )["bets"] == 117013
    late = one(
        segments,
        "market == 'jra' and strategy == 'independent_product_top2'",
    )
    assert 99 < late["roi"] < 101
    logistic = calibration[calibration["model"].eq("prob_logistic")]["brier"].mean()
    independent = calibration[
        calibration["model"].eq("prob_independent")
    ]["brier"].mean()
    assert logistic < independent
    for market in ("jra", "local"):
        report = json.loads(
            (
                OUTPUT
                / f"strategy_comparison_{market}_v2026.07.27.3.json"
            ).read_text(encoding="utf-8")
        )
        assert report["version"] == "v2026.07.27.3"
    print(VERSION, "wide optimization regression checks passed")


if __name__ == "__main__":
    main()
