"""Audit local pedigree coverage and text quality without changing data.

Version: v2026.07.26.1
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pandas as pd


VERSION = "v2026.07.26.1"
ROOT = Path(r"C:\keiba\data")
PEDIGREE_PATH = ROOT / "pedigree_local.json"
REPORT_PATH = Path(r"C:\keiba\codex_display_test") / (
    f"local_pedigree_quality_{VERSION}.json"
)
FIELDS = (
    "father", "mother", "father_father", "father_mother",
    "mother_father", "mother_mother",
)
BROKEN = re.compile(r"�|E(?:��|�|$)|\uFFFD")


pedigree = json.loads(PEDIGREE_PATH.read_text(encoding="utf-8"))
with sqlite3.connect(ROOT / "features_local.sqlite") as connection:
    features = pd.read_sql_query(
        "SELECT date,horse_id,race_id FROM features", connection,
        parse_dates=["date"],
    )
features["horse_id"] = features["horse_id"].astype(str)
keys = set(map(str, pedigree))
features["covered"] = features["horse_id"].isin(keys)

field_quality = {}
for field in FIELDS:
    values = [str(value.get(field) or "") for value in pedigree.values()]
    nonempty = [value for value in values if value]
    broken = [value for value in nonempty if BROKEN.search(value)]
    field_quality[field] = {
        "nonempty": len(nonempty),
        "nonempty_rate": len(nonempty) / len(values) if values else 0,
        "broken": len(broken),
        "broken_rate_of_nonempty": len(broken) / len(nonempty) if nonempty else 0,
        "unique": len(set(nonempty)),
        "samples": broken[:10],
    }

coverage_by_year = (
    features.assign(year=features["date"].dt.year)
    .groupby("year")["covered"]
    .agg(["count", "sum", "mean"])
    .reset_index()
    .to_dict(orient="records")
)
horse_coverage = (
    features.drop_duplicates("horse_id")["covered"].mean()
    if len(features) else 0
)
report = {
    "version": VERSION,
    "pedigree_records": len(pedigree),
    "feature_rows": len(features),
    "feature_row_coverage": float(features["covered"].mean()),
    "unique_horse_coverage": float(horse_coverage),
    "coverage_by_year": coverage_by_year,
    "field_quality": field_quality,
}
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
