"""Audit overlap and temporal/venue stability of confirmed local skip rules.

Version: v2026.07.26.1
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

import pandas as pd

VERSION = "v2026.07.26.1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def select(d: pd.DataFrame, condition: dict) -> pd.DataFrame:
    mask = pd.Series(True, index=d.index)
    for column, value in condition.items():
        mask &= d[column].astype(str).eq(str(value))
    return d[mask]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--oos", type=Path, required=True)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--portfolio-script", type=Path, required=True)
    p.add_argument("--search-script", type=Path, required=True)
    p.add_argument("--search-json", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()

    portfolio = load_module("portfolio", a.portfolio_script)
    search = load_module("edge_search", a.search_script)
    d = search.add_bins(portfolio.build(a.oos, a.db), a.oos)
    d["date"] = pd.to_datetime(d.date)
    d["year"] = d.date.dt.year
    d["year_month"] = d.date.dt.strftime("%Y-%m")
    rules = json.loads(a.search_json.read_text(encoding="utf-8"))["confirmed"]

    audits = []
    selected_sets = {}
    selected_frames = {}
    for index, rule in enumerate(rules, 1):
        kind = rule["bet_type"]
        chosen = select(d[d[kind + "_covered"]], rule["condition"]).copy()
        rule_id = f"R{index}"
        selected_sets[rule_id] = set(zip(chosen.race_id.astype(str), chosen.axis.astype(int), [kind] * len(chosen)))
        selected_frames[rule_id] = chosen
        audits.append({
            "rule_id": rule_id, "bet_type": kind, "condition": rule["condition"],
            "annual": {
                str(year): search.metrics(chosen[chosen.year.eq(year)], kind)
                for year in (2024, 2025, 2026)
            },
            "monthly": {
                str(month): search.metrics(group, kind)
                for month, group in chosen.groupby("year_month")
            },
            "venue": {
                str(venue): {
                    str(year): search.metrics(group[group.year.eq(year)], kind)
                    for year in (2024, 2025, 2026)
                }
                for venue, group in chosen.groupby("venue")
            },
        })

    overlap = {}
    ids = list(selected_sets)
    for i, left in enumerate(ids):
        for right in ids[i + 1:]:
            union = selected_sets[left] | selected_sets[right]
            overlap[left + ":" + right] = (
                len(selected_sets[left] & selected_sets[right]) / len(union) if union else 0
            )

    strict_ids = [
        audit["rule_id"] for audit in audits
        if all(audit["annual"][str(year)]["roi_without_max"] >= 100 for year in (2024, 2025, 2026))
    ]
    combined = {}
    for kind in ("tan", "wide"):
        frames = [
            selected_frames[rule_id]
            for rule_id in strict_ids
            if next(a for a in audits if a["rule_id"] == rule_id)["bet_type"] == kind
        ]
        if not frames:
            continue
        union = pd.concat(frames).drop_duplicates(["race_id", "axis"])
        combined[kind] = {
            "rule_ids": [rule_id for rule_id in strict_ids
                         if next(a for a in audits if a["rule_id"] == rule_id)["bet_type"] == kind],
            "annual": {
                str(year): search.metrics(union[union.year.eq(year)], kind)
                for year in (2024, 2025, 2026)
            },
        }

    result = {
        "version": VERSION, "rules_audited": len(audits),
        "strict_all_years_without_max": strict_ids,
        "audits": audits, "pairwise_jaccard": overlap,
        "combined_strict": combined,
    }
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("strict", strict_ids)
    for kind, row in combined.items():
        print(kind, row["rule_ids"],
              [(year, round(row["annual"][year]["roi"], 1),
                round(row["annual"][year]["roi_without_max"], 1),
                row["annual"][year]["bets"]) for year in ("2024", "2025", "2026")])


if __name__ == "__main__":
    main()
