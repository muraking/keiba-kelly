"""Audit the three-year-positive local win2 x hole1 umaren candidate.

Version: v2026.07.27.1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pandas as pd


VERSION = "v2026.07.27.1"
SEARCH = Path(__file__).with_name(
    "search_local_pair_market_structure_v2026.07.27.2.py"
)
SPEC = importlib.util.spec_from_file_location("local_structure", SEARCH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {SEARCH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tickets = MODULE.PAIR.build(args.oos, args.db)
    features = MODULE.race_features(args.oos, args.db)
    data = tickets.merge(features, on="race_id", how="left")
    selected = data[
        data["bet_type"].eq("umaren")
        & data["hole_rank"].eq(1)
        & data["partner_rank"].eq(2)
        & data["product_bin"].astype(str).eq("60-100")
        & data["distance_bin"].astype(str).eq("1601-2000")
    ].copy()
    selected["period"] = (
        selected["date"].dt.year.astype(str)
        + "-"
        + selected["date"].dt.quarter.astype(str).map(lambda value: f"Q{value}")
    )
    yearly = {
        str(year): MODULE.PAIR.metrics(selected[selected["year"].eq(year)])
        for year in (2024, 2025, 2026)
    }
    result = {
        "version": VERSION,
        "condition": (
            "local umaren win2 x hole1; odds product 60-100; distance 1601-2000m"
        ),
        "yearly": yearly,
        "overall": MODULE.PAIR.metrics(selected),
        "quarterly": {
            period: MODULE.PAIR.metrics(group)
            for period, group in selected.groupby("period", sort=True)
        },
        "venue_minimum_20_bets": {
            venue: MODULE.PAIR.metrics(group)
            for venue, group in selected.groupby("venue", sort=True)
            if len(group) >= 20
        },
        "leave_one_venue_out": {
            venue: MODULE.PAIR.metrics(selected[selected["venue"].ne(venue)])
            for venue in sorted(selected["venue"].unique())
        },
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
