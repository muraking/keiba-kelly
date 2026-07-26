"""Audit a deduplicated JRA win-top x longshot pair-bet portfolio.

Version: v2026.07.27.3
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


VERSION = "v2026.07.27.3"
SEARCH = Path(__file__).with_name("search_win_hole_pair_bets_v2026.07.27.1.py")
SPEC = importlib.util.spec_from_file_location("pair_search", SEARCH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {SEARCH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def select(data: pd.DataFrame) -> pd.DataFrame:
    strict_wide = (
        data["bet_type"].eq("wide")
        & data["hole_rank"].eq(1)
        & data["partner_rank"].eq(1)
        & data["product_bin"].astype(str).eq("100-200")
        & data["race_num_bin"].astype(str).eq("1-3")
    )
    strict_umaren = (
        data["bet_type"].eq("umaren")
        & data["hole_rank"].eq(3)
        & data["partner_rank"].eq(1)
        & data["product_bin"].astype(str).eq("100-200")
        & data["partner_p_bin"].astype(str).eq(".15-.25")
    )
    selected = data[strict_wide | strict_umaren].copy()
    selected["rule"] = "J-W1"  # wide
    selected.loc[strict_umaren[strict_wide | strict_umaren].to_numpy(), "rule"] = "J-U1"
    return selected.drop_duplicates(["race_id", "bet_type", "hole", "partner"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = MODULE.build(args.oos, args.db)
    chosen = select(data)

    by_rule = {
        rule: {
            str(year): MODULE.metrics(
                chosen[chosen["rule"].eq(rule) & chosen["year"].eq(year)]
            )
            for year in (2024, 2025)
        }
        for rule in ("J-W1", "J-U1")
    }
    yearly = {
        str(year): MODULE.metrics(chosen[chosen["year"].eq(year)])
        for year in (2024, 2025)
    }
    dates = chosen.groupby(chosen["date"].dt.date).agg(
        bets=("return", "size"), races=("race_id", "nunique")
    )
    chosen["period"] = (
        chosen["date"].dt.year.astype(str)
        + "-"
        + np.where(chosen["date"].dt.month.le(6), "H1", "H2")
    )
    half_year = {
        period: MODULE.metrics(group)
        for period, group in chosen.groupby("period", sort=True)
    }
    venue = {
        name: MODULE.metrics(group)
        for name, group in chosen.groupby("venue", sort=True)
        if len(group) >= 30
    }
    leave_one_venue_out = {
        str(year): {
            name: MODULE.metrics(
                chosen[chosen["year"].eq(year) & chosen["venue"].ne(name)]
            )
            for name in sorted(chosen.loc[chosen["year"].eq(year), "venue"].unique())
        }
        for year in (2024, 2025)
    }
    result = {
        "version": VERSION,
        "rules": {
            "J-W1": (
                "wide: hole1 x win1; odds product 100-200; race number 1-3"
            ),
            "J-U1": (
                "umaren: hole3 x win1; odds product 100-200; "
                "win1 probability .15-.25"
            ),
        },
        "by_rule": by_rule,
        "portfolio_yearly": yearly,
        "portfolio_overall": MODULE.metrics(chosen),
        "half_year": half_year,
        "venue_minimum_30_bets": venue,
        "leave_one_venue_out": leave_one_venue_out,
        "active_days": int(len(dates)),
        "average_bets_per_active_day": float(dates["bets"].mean()),
        "average_races_per_active_day": float(dates["races"].mean()),
        "duplicate_tickets_removed": int(
            len(data.loc[data.index.intersection(chosen.index)]) - len(chosen)
        ),
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
