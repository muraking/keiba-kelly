"""Test running style and prior same-day track bias on local R1-R3 longshots.

Only completed earlier races at the same date/venue/surface form the bias.
Version: v2026.07.26.3
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "v2026.07.26.3"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def last_corner(value) -> float:
    numbers = re.findall(r"\d+", str(value))
    return float(numbers[-1]) if numbers else np.nan


def bias_frame(db: Path) -> pd.DataFrame:
    with sqlite3.connect(db) as c:
        runs = pd.read_sql_query(
            """select race_id,date,venue,surface,race_num,num_horses,
                      umaban,finish_pos,passing from runs""",
            c, parse_dates=["date"],
        )
    runs["race_id"] = runs.race_id.astype(str)
    top3 = runs[runs.finish_pos.between(1, 3) & runs.passing.notna()].copy()
    top3["corner"] = top3.passing.map(last_corner)
    top3["corner_rel"] = top3.corner / top3.num_horses.clip(lower=1)
    race = (
        top3.groupby(["date", "venue", "surface", "race_num", "race_id"], as_index=False)
        .corner_rel.mean()
        .sort_values(["date", "venue", "surface", "race_num"])
    )
    keys = ["date", "venue", "surface"]
    race["prior_bias"] = race.groupby(keys).corner_rel.transform(
        lambda values: values.rolling(3, min_periods=3).mean().shift(1)
    )
    race["prior_races"] = race.groupby(keys).cumcount()
    return race[["race_id", "prior_bias", "prior_races"]]


def select(frame: pd.DataFrame, condition: dict) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for column, value in condition.items():
        mask &= frame[column].astype(str).eq(str(value))
    return frame[mask]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--oos", type=Path, required=True)
    p.add_argument("--features-db", type=Path, required=True)
    p.add_argument("--runs-db", type=Path, required=True)
    p.add_argument("--portfolio-script", type=Path, required=True)
    p.add_argument("--search-script", type=Path, required=True)
    p.add_argument("--edge-audit", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()

    portfolio = load_module("portfolio", a.portfolio_script)
    search = load_module("edge_search", a.search_script)
    candidates = search.add_bins(portfolio.build(a.oos, a.runs_db), a.oos)
    candidates["date"] = pd.to_datetime(candidates.date)
    candidates["year"] = candidates.date.dt.year

    with sqlite3.connect(a.features_db) as c:
        style = pd.read_sql_query("select race_id,umaban,h_avg_early3 from features", c)
    style["race_id"] = style.race_id.astype(str)
    style["umaban"] = pd.to_numeric(style.umaban, errors="coerce")
    candidates = (
        candidates.merge(style.drop_duplicates(["race_id", "umaban"]),
                         left_on=["race_id", "axis"], right_on=["race_id", "umaban"], how="left")
        .merge(bias_frame(a.runs_db), on="race_id", how="left")
    )
    candidates["style"] = pd.cut(
        candidates.h_avg_early3,
        [-np.inf, .25, .50, .75, np.inf],
        labels=["escape", "stalk", "close", "deep"],
    )
    candidates["bias_side"] = np.where(
        candidates.prior_bias.le(.38), "front",
        np.where(candidates.prior_bias.ge(.48), "closer", "neutral"),
    )
    candidates["style_match"] = (
        (candidates.bias_side.eq("front") & candidates.h_avg_early3.le(.40))
        | (candidates.bias_side.eq("closer") & candidates.h_avg_early3.ge(.60))
    )

    audit = json.loads(a.edge_audit.read_text(encoding="utf-8"))
    strict = set(audit["strict_all_years_without_max"])
    rules = [row for row in audit["audits"] if row["rule_id"] in strict]
    frames = []
    for rule in rules:
        chosen = select(candidates[candidates.tan_covered], rule["condition"]).copy()
        chosen["rule_id"] = rule["rule_id"]
        frames.append(chosen)
    union = pd.concat(frames).drop_duplicates(["race_id", "axis"])

    variants = {
        "all": pd.Series(True, index=union.index),
        "escape": union.style.eq("escape"),
        "stalk": union.style.eq("stalk"),
        "close": union.style.eq("close"),
        "deep": union.style.eq("deep"),
        "front_group": union.h_avg_early3.le(.40),
        "closer_group": union.h_avg_early3.ge(.60),
        "bias_available": union.prior_races.ge(3) & union.prior_bias.notna(),
        "bias_style_match": union.prior_races.ge(3) & union.style_match,
        "bias_style_mismatch": union.prior_races.ge(3) & ~union.style_match
                               & union.bias_side.ne("neutral"),
        "front_bias_match": union.prior_races.ge(3) & union.bias_side.eq("front")
                            & union.h_avg_early3.le(.40),
        "closer_bias_match": union.prior_races.ge(3) & union.bias_side.eq("closer")
                             & union.h_avg_early3.ge(.60),
        "front_bias_nonfront": union.prior_races.ge(3) & union.bias_side.eq("front")
                               & union.h_avg_early3.gt(.40),
        "closer_bias_noncloser": union.prior_races.ge(3) & union.bias_side.eq("closer")
                                 & union.h_avg_early3.lt(.60),
        "neutral_bias": union.prior_races.ge(3) & union.bias_side.eq("neutral"),
    }

    results = {}
    for name, mask in variants.items():
        chosen = union[mask]
        results[name] = {
            str(year): search.metrics(chosen[chosen.year.eq(year)], "tan")
            for year in (2024, 2025, 2026)
        }
    confirmed = [
        name for name, periods in results.items()
        if name != "all"
        and all(periods[str(year)]["bets"] >= (50 if year < 2026 else 25)
                and periods[str(year)]["roi"] >= 100
                and periods[str(year)]["roi_without_max"] >= 100
                for year in (2024, 2025, 2026))
    ]
    report = {
        "version": VERSION,
        "definitions": {
            "escape": "h_avg_early3 <= .25",
            "stalk": ".25 < h_avg_early3 <= .50",
            "close": ".50 < h_avg_early3 <= .75",
            "deep": "h_avg_early3 > .75",
            "front_bias": "mean last-corner relative position of top3 in prior 3 races <= .38",
            "closer_bias": "same measure >= .48",
        },
        "rows_union": len(union), "confirmed_variants": confirmed,
        "results": results,
        "limitations": [
            "running style is a pre-race historical proxy, not the realized style in the target race",
            "same-day bias uses only the prior three completed races",
            "2026 is partial year and final odds are used",
        ],
    }
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("rows", len(union), "confirmed", confirmed)
    for name, periods in results.items():
        print(name, [(year, round(periods[str(year)]["roi"], 1),
                      round(periods[str(year)].get("roi_without_max", 0), 1),
                      periods[str(year)]["bets"]) for year in (2024, 2025, 2026)])


if __name__ == "__main__":
    main()
