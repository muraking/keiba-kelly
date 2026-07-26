"""Audit temporal/venue robustness of longshot-ranked tickets.

Version: v2026.07.26.4
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path

import pandas as pd

VERSION = "v2026.07.26.4"


def load_portfolio_module(path: Path):
    spec = importlib.util.spec_from_file_location("portfolio", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def mask_for(d: pd.DataFrame, rule: dict) -> pd.Series:
    lo, hi = rule["odds"]
    return (
        d.hole_rank.le(rule["hole_rank"])
        & d.odds.between(lo, hi)
        & d.p_place.ge(rule["pmin"])
        & d.fav_p.ge(rule["fav_pmin"])
        & d.field.ge(rule["field_min"])
    )


def robust_summary(x: pd.DataFrame, kind: str, summary) -> dict:
    x = x[x[kind + "_covered"]].copy()
    base = summary(x, kind)
    if x.empty:
        return base
    returns = x[kind + "_return"]
    bets = int(x[kind + "_bets"].sum())
    without_max = float((returns.sum() - returns.max()) / (bets * 100) * 100) if bets else 0
    base["roi_without_largest_return"] = without_max
    return base


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--oos", type=Path, required=True)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--portfolio-script", type=Path, required=True)
    p.add_argument("--portfolio-json", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--discovery-year", type=int, default=2024)
    a = p.parse_args()

    mod = load_portfolio_module(a.portfolio_script)
    d = mod.build(a.oos, a.db)
    portfolio = json.loads(a.portfolio_json.read_text(encoding="utf-8"))
    rules = portfolio["all_rules"]
    discovery_year = str(a.discovery_year)
    next_year = str(a.discovery_year + 1)

    selected_exploratory = {}
    selected_discovery = {}
    for kind in ("tan", "fuku", "umaren", "wide", "sanfuku", "santan1", "santan2", "santan3"):
        eligible = [
            r for r in rules
            if r["bet_type"] == kind
            and r["periods"][discovery_year]["bets"] >= 100
            and r["periods"].get(next_year, {}).get("bets", 0) >= 50
        ]
        if not eligible:
            continue
        selected_exploratory[kind] = max(
            eligible,
            key=lambda r: min(r["periods"][discovery_year]["roi"], r["periods"][next_year]["roi"]),
        )
        discovery = [
            r for r in eligible
            if r["periods"][discovery_year]["max_share"] is not None
            and r["periods"][discovery_year]["max_share"] <= .20
        ]
        if discovery:
            selected_discovery[kind] = max(
                discovery,
                key=lambda r: (r["periods"][discovery_year]["lcb90"], r["periods"][discovery_year]["roi"]),
            )

    def audit_rules(selected):
        audits = {}
        for kind, rule in selected.items():
            x = d[mask_for(d, rule)].copy()
            x["year_month"] = x.date.dt.strftime("%Y-%m")
            annual = {
                str(y): robust_summary(x[x.date.dt.year.eq(y)], kind, mod.summary)
                for y in (2024, 2025, 2026)
            }
            monthly = {
                k: robust_summary(g, kind, mod.summary)
                for k, g in x.groupby("year_month")
            }
            venue = {
                str(k): robust_summary(g, kind, mod.summary)
                for k, g in x[x.date.dt.year.isin((2024, 2025))].groupby("venue")
            }
            audits[kind] = {"rule": rule, "annual": annual, "monthly": monthly, "venue": venue}
        return audits

    audits_exploratory = audit_rules(selected_exploratory)
    audits_discovery = audit_rules(selected_discovery)

    with sqlite3.connect(a.db) as c:
        coverage = pd.read_sql_query(
            """select substr(r.date,1,4) year,p.bet_type,
                      count(distinct p.race_id) races,min(r.date) min_date,max(r.date) max_date
               from payouts p join runs r on r.race_id=p.race_id
               group by 1,2 order by 1,2""",
            c,
        ).to_dict("records")

    result = {
        "version": VERSION,
        "method": {
            "discovery": f"highest {discovery_year} LCB90 with >=100 bets and max payout share <=20%; {next_year} untouched",
            "exploratory_stable": f"best minimum ROI across {discovery_year} and {next_year}; retrospective screen",
        },
        "payout_coverage": coverage,
        "discovery_audits": audits_discovery,
        "exploratory_stable_audits": audits_exploratory,
    }
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for kind, audit in audits_discovery.items():
        first, second = audit["annual"][discovery_year], audit["annual"][next_year]
        print("discovery", kind, round(first["roi"], 1), round(second["roi"], 1),
              "without-max", round(first["roi_without_largest_return"], 1),
              round(second["roi_without_largest_return"], 1))


if __name__ == "__main__":
    main()
