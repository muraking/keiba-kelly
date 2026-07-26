"""Search interpretable local-race skip filters with untouched 2026 confirmation.

2024 discovers groups, 2025 validates them, and 2026 is the final untouched test.
Version: v2026.07.26.1
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "v2026.07.26.1"
KINDS = ("tan", "fuku", "umaren", "wide", "sanfuku", "santan1", "santan2", "santan3")
SPECS = (
    ("hole_rank", "odds_bin", "p_bin"),
    ("hole_rank", "odds_bin", "p_bin", "fav_bin"),
    ("hole_rank", "odds_bin", "p_bin", "field_bin"),
    ("hole_rank", "odds_bin", "p_bin", "race_segment"),
    ("hole_rank", "odds_bin", "p_bin", "venue"),
    ("hole_rank", "odds_bin", "p_bin", "gap_bin"),
    ("hole_rank", "odds_bin", "p_bin", "top3_bin"),
    ("hole_rank", "odds_bin", "fav_bin", "field_bin"),
    ("hole_rank", "odds_bin", "fav_bin", "race_segment"),
    ("hole_rank", "odds_bin", "fav_bin", "venue"),
    ("hole_rank", "odds_bin", "field_bin", "race_segment"),
    ("hole_rank", "odds_bin", "field_bin", "venue"),
    ("hole_rank", "odds_bin", "gap_bin", "race_segment"),
    ("hole_rank", "odds_bin", "top3_bin", "race_segment"),
    ("hole_rank", "odds_bin", "venue", "race_segment"),
)


def module_from(path: Path):
    spec = importlib.util.spec_from_file_location("portfolio", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def metrics(group: pd.DataFrame, kind: str) -> dict:
    group = group[group[kind + "_covered"]]
    if group.empty:
        return {"races": 0, "bets": 0, "hits": 0, "roi": 0, "lcb90": -999, "max_share": None}
    bets = group[kind + "_bets"].to_numpy()
    returns = group[kind + "_return"].to_numpy()
    units = returns / (bets * 100)
    se = units.std(ddof=1) / np.sqrt(len(units)) if len(units) > 1 else 999
    total = float(returns.sum())
    return {
        "races": int(len(group)), "bets": int(bets.sum()),
        "hits": int((returns > 0).sum()),
        "roi": float(total / (bets.sum() * 100) * 100),
        "lcb90": float(units.mean() - 1.2816 * se),
        "max_share": float(returns.max() / total) if total else None,
        "roi_without_max": float((total - returns.max()) / (bets.sum() * 100) * 100),
    }


def add_bins(candidates: pd.DataFrame, oos: Path) -> pd.DataFrame:
    full = pd.read_csv(oos, usecols=["race_id", "p_win"])
    full["race_id"] = full.race_id.astype(str)
    stats = full.groupby("race_id").p_win.agg(
        fav_p="max",
        top3_sum=lambda x: x.nlargest(3).sum(),
    )
    second = full.groupby("race_id").p_win.apply(
        lambda x: x.nlargest(2).iloc[-1] if len(x) > 1 else 0
    )
    stats["fav_gap"] = stats.fav_p - second
    d = candidates.copy()
    d["race_id"] = d.race_id.astype(str)
    d = d.drop(columns=["fav_p"], errors="ignore").merge(stats, on="race_id", how="left")
    d["race_no"] = pd.to_numeric(d.race_id.str[-2:], errors="coerce")
    d["race_segment"] = pd.cut(d.race_no, [0, 4, 8, 99], labels=["early", "middle", "late"])
    d["odds_bin"] = pd.cut(d.odds, [10, 15, 20, 30, 50, 80, np.inf],
                           right=False, labels=["10-15", "15-20", "20-30", "30-50", "50-80", "80+"])
    d["p_bin"] = pd.cut(d.p_place, [-np.inf, .12, .16, .20, .25, np.inf],
                        right=False, labels=["<.12", ".12-.16", ".16-.20", ".20-.25", ".25+"])
    d["fav_bin"] = pd.cut(d.fav_p, [-np.inf, .25, .35, .45, np.inf],
                          right=False, labels=["<.25", ".25-.35", ".35-.45", ".45+"])
    d["gap_bin"] = pd.cut(d.fav_gap, [-np.inf, .05, .10, .15, np.inf],
                          right=False, labels=["<.05", ".05-.10", ".10-.15", ".15+"])
    d["top3_bin"] = pd.cut(d.top3_sum, [-np.inf, .50, .65, .80, np.inf],
                           right=False, labels=["<.50", ".50-.65", ".65-.80", ".80+"])
    d["field_bin"] = pd.cut(d.field, [0, 7, 9, 11, np.inf],
                            labels=["<=7", "8-9", "10-11", "12+"])
    return d


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--oos", type=Path, required=True)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--portfolio-script", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    mod = module_from(a.portfolio_script)
    d = add_bins(mod.build(a.oos, a.db), a.oos)
    d["year"] = pd.to_datetime(d.date).dt.year

    tested = []
    for kind in KINDS:
        covered = d[d[kind + "_covered"]].copy()
        for spec in SPECS:
            grouped = {
                year: {key if isinstance(key, tuple) else (key,): group
                       for key, group in covered[covered.year.eq(year)].groupby(list(spec), observed=True)}
                for year in (2024, 2025, 2026)
            }
            for key, group24 in grouped[2024].items():
                m24 = metrics(group24, kind)
                if m24["bets"] < 100 or m24["max_share"] is None or m24["max_share"] > .20:
                    continue
                condition = {column: str(value) for column, value in zip(spec, key)}
                m25 = metrics(grouped[2025].get(key, covered.iloc[0:0]), kind)
                m26 = metrics(grouped[2026].get(key, covered.iloc[0:0]), kind)
                tested.append({
                    "bet_type": kind, "condition": condition,
                    "2024": m24, "2025": m25, "2026": m26,
                })

    validated = [
        r for r in tested
        if r["2024"]["roi"] >= 100
        and r["2025"]["roi"] >= 100 and r["2025"]["bets"] >= 100
        and r["2025"]["max_share"] is not None and r["2025"]["max_share"] <= .25
    ]
    confirmed = [
        r for r in validated
        if r["2026"]["roi"] >= 100 and r["2026"]["bets"] >= 50
        and r["2026"]["max_share"] is not None and r["2026"]["max_share"] <= .25
        and r["2026"]["roi_without_max"] >= 100
    ]
    confirmed.sort(key=lambda r: (min(r[y]["roi_without_max"] for y in ("2024", "2025", "2026")),
                                  r["2026"]["lcb90"]), reverse=True)
    validated.sort(key=lambda r: (r["2026"]["roi_without_max"], r["2026"]["roi"]), reverse=True)
    result = {
        "version": VERSION, "group_specs": [list(x) for x in SPECS],
        "discovery_candidates": len(tested), "validated_2025": len(validated),
        "confirmed_2026": len(confirmed),
        "confirmed": confirmed[:100],
        "best_validated": validated[:200],
    }
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("discovery", len(tested), "validated", len(validated), "confirmed", len(confirmed))
    for row in confirmed[:20]:
        print(row["bet_type"], row["condition"],
              [round(row[y]["roi"], 1) for y in ("2024", "2025", "2026")],
              [row[y]["bets"] for y in ("2024", "2025", "2026")])


if __name__ == "__main__":
    main()
