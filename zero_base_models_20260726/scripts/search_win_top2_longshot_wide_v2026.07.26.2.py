"""Search wide tickets pairing win-probability top2 with longshot top3.

No post-race payout threshold is used for selection. The 10x payout share is
reported only as an explanatory diagnostic.
Version: v2026.07.26.2
"""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "v2026.07.26.2"
SPECS = (
    ("hole_rank", "partner_rank", "hole_odds_bin"),
    ("hole_rank", "partner_rank", "hole_odds_bin", "product_bin"),
    ("hole_rank", "partner_rank", "hole_odds_bin", "hole_p_bin"),
    ("hole_rank", "partner_rank", "hole_odds_bin", "partner_p_bin"),
    ("hole_rank", "partner_rank", "hole_odds_bin", "field_bin"),
    ("hole_rank", "partner_rank", "product_bin", "hole_p_bin"),
    ("hole_rank", "partner_rank", "product_bin", "partner_p_bin"),
    ("hole_rank", "partner_rank", "hole_p_bin", "partner_p_bin"),
)


def pair(a: int, b: int) -> str:
    return "-".join(map(str, sorted((a, b))))


def metrics(group: pd.DataFrame) -> dict:
    if group.empty:
        return {"bets": 0, "hits": 0, "roi": 0, "roi_without_max": 0,
                "lcb90": -999, "max_share": None, "return_10x_share": None}
    returns = group["return"].to_numpy()
    units = returns / 100
    total = float(returns.sum())
    se = units.std(ddof=1) / np.sqrt(len(units)) if len(units) > 1 else 999
    return {
        "bets": int(len(group)), "hits": int((returns > 0).sum()),
        "hit_rate": float((returns > 0).mean() * 100),
        "roi": float(total / (len(group) * 100) * 100),
        "roi_without_max": float((total - returns.max()) / (len(group) * 100) * 100),
        "lcb90": float(units.mean() - 1.2816 * se),
        "max_share": float(returns.max() / total) if total else None,
        "return_10x_share": float(returns[returns >= 1000].sum() / total) if total else None,
        "hits_10x": int((returns >= 1000).sum()),
    }


def build(oos: Path, db: Path) -> pd.DataFrame:
    d = pd.read_csv(oos, parse_dates=["date"])
    d["race_id"] = d.race_id.astype(str)
    with sqlite3.connect(db) as c:
        payout = pd.read_sql_query(
            "select race_id,comb,payout from payouts where bet_type='wide'", c
        )
    payout.race_id = payout.race_id.astype(str)
    pay = {(r.race_id, str(r.comb)): float(r.payout) for r in payout.itertuples()}
    covered = set(payout.race_id)
    rows = []
    for race_id, group in d.groupby("race_id", sort=False):
        race_id = str(race_id)
        if race_id not in covered:
            continue
        win_order = group.sort_values(["p_win", "umaban"], ascending=[False, True])
        holes = group[group.win_odds.ge(10)].sort_values(
            ["p_place", "umaban"], ascending=[False, True]
        ).head(3)
        for hole_rank, hole in enumerate(holes.itertuples(), 1):
            # Keep partner_rank as the absolute p_win rank. If a longshot is
            # itself in the top two, do not silently substitute the third horse.
            for partner_rank, partner in enumerate(win_order.head(2).itertuples(), 1):
                if int(partner.umaban) == int(hole.umaban):
                    continue
                ticket = pair(int(hole.umaban), int(partner.umaban))
                rows.append({
                    "race_id": race_id, "date": hole.date, "venue": hole.venue,
                    "hole_rank": hole_rank, "partner_rank": partner_rank,
                    "hole": int(hole.umaban), "partner": int(partner.umaban),
                    "hole_odds": float(hole.win_odds),
                    "partner_odds": float(partner.win_odds),
                    "odds_product": float(hole.win_odds * partner.win_odds),
                    "hole_p": float(hole.p_place), "partner_p": float(partner.p_win),
                    "field": int(hole.field_size),
                    "return": pay.get((race_id, ticket), 0.0),
                })
    frame = pd.DataFrame(rows)
    frame["year"] = frame.date.dt.year
    frame["hole_odds_bin"] = pd.cut(
        frame.hole_odds, [10, 15, 20, 30, 50, 80, np.inf], right=False,
        labels=["10-15", "15-20", "20-30", "30-50", "50-80", "80+"],
    )
    frame["product_bin"] = pd.cut(
        frame.odds_product, [0, 30, 60, 100, 200, np.inf], right=False,
        labels=["<30", "30-60", "60-100", "100-200", "200+"],
    )
    frame["hole_p_bin"] = pd.cut(
        frame.hole_p, [-np.inf, .12, .16, .20, .25, np.inf], right=False,
        labels=["<.12", ".12-.16", ".16-.20", ".20-.25", ".25+"],
    )
    frame["partner_p_bin"] = pd.cut(
        frame.partner_p, [-np.inf, .15, .25, .35, np.inf], right=False,
        labels=["<.15", ".15-.25", ".25-.35", ".35+"],
    )
    frame["field_bin"] = pd.cut(
        frame.field, [0, 7, 9, 11, np.inf], labels=["<=7", "8-9", "10-11", "12+"]
    )
    return frame


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--oos", type=Path, required=True)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--market", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    d = build(a.oos, a.db)
    baseline = {
        str(year): metrics(d[d.year.eq(year)]) for year in (2024, 2025, 2026)
    }
    candidates = []
    for spec in SPECS:
        groups = {
            year: {key if isinstance(key, tuple) else (key,): group
                   for key, group in d[d.year.eq(year)].groupby(list(spec), observed=True)}
            for year in (2024, 2025, 2026)
        }
        for key, group24 in groups[2024].items():
            m24 = metrics(group24)
            if m24["bets"] < 100 or m24["max_share"] is None or m24["max_share"] > .20:
                continue
            candidates.append({
                "condition": {column: str(value) for column, value in zip(spec, key)},
                "2024": m24,
                "2025": metrics(groups[2025].get(key, d.iloc[0:0])),
                "2026": metrics(groups[2026].get(key, d.iloc[0:0])),
            })
    validated = [
        row for row in candidates
        if row["2024"]["roi"] >= 100 and row["2024"]["roi_without_max"] >= 100
        and row["2025"]["roi"] >= 100 and row["2025"]["roi_without_max"] >= 100
        and row["2025"]["bets"] >= 100
    ]
    confirmed = [
        row for row in validated
        if row["2026"]["roi"] >= 100 and row["2026"]["roi_without_max"] >= 100
        and row["2026"]["bets"] >= 50
    ]
    sort_key = lambda row: min(
        row[year]["roi_without_max"]
        for year in (("2024", "2025", "2026") if a.market == "local" else ("2024", "2025"))
    )
    validated.sort(key=sort_key, reverse=True)
    confirmed.sort(key=sort_key, reverse=True)
    result = {
        "version": VERSION, "market": a.market, "rows": len(d),
        "baseline": baseline, "candidates_2024": len(candidates),
        "validated_2025": len(validated), "confirmed_2026": len(confirmed),
        "confirmed": confirmed[:100], "best_validated": validated[:200],
        "note": "10x payout is diagnostic only; no result payout threshold selects a bet",
    }
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(a.market, "rows", len(d), "validated", len(validated), "confirmed", len(confirmed))
    for row in (confirmed if a.market == "local" else validated)[:20]:
        print(row["condition"], [
            (year, round(row[year]["roi"], 1), round(row[year]["roi_without_max"], 1),
             row[year]["bets"], round((row[year]["return_10x_share"] or 0) * 100, 1))
            for year in ("2024", "2025", "2026")
        ])


if __name__ == "__main__":
    main()
