"""Inspect data inputs for the hidden-longshot model without changing data.

Version: v2026.07.25.2
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(r"C:\keiba\data")
OOS_ROOT = Path(r"C:\keiba\codex_display_test")


def inspect_db(path: Path) -> None:
    print(f"\nDB {path.name}")
    with sqlite3.connect(path) as connection:
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", connection
        )["name"].tolist()
        print("tables", tables)
        for table in tables:
            columns = pd.read_sql_query(f"PRAGMA table_info({table})", connection)
            print(table, columns["name"].tolist())


def main() -> None:
    inspect_db(ROOT / "keiba_local.sqlite")
    inspect_db(ROOT / "keiba_jra.sqlite")
    inspect_db(ROOT / "features_local.sqlite")
    inspect_db(ROOT / "features_jra.sqlite")
    for path in (
        OOS_ROOT / "oos_predictions_local_full_2026.07.23.5.csv",
        OOS_ROOT / "oos_predictions_jra_full_2026.07.23.5.csv",
        OOS_ROOT / "jra_enhanced_iruka_oos.csv",
    ):
        if path.exists():
            print("\nCSV", path.name, pd.read_csv(path, nrows=1).columns.tolist())
    for circuit in ("local", "jra"):
        oos = pd.read_csv(
            OOS_ROOT / f"oos_predictions_{circuit}_full_2026.07.23.5.csv",
            usecols=["race_id", "date"],
        )
        oos["race_id"] = oos["race_id"].astype(str)
        with sqlite3.connect(ROOT / f"keiba_{circuit}.sqlite") as connection:
            payouts = pd.read_sql_query(
                "SELECT bet_type, COUNT(*) AS n, MIN(comb) AS sample "
                "FROM payouts GROUP BY bet_type ORDER BY bet_type",
                connection,
            )
            payout_races = set(
                pd.read_sql_query(
                    "SELECT DISTINCT race_id FROM payouts", connection
                )["race_id"].astype(str)
            )
        print("\nPAYOUT TYPES", circuit)
        print(payouts.to_string(index=False))
        oos["year"] = pd.to_datetime(oos["date"]).dt.year
        coverage = (
            oos.drop_duplicates("race_id")
            .assign(has_payout=lambda frame: frame["race_id"].isin(payout_races))
            .groupby("year")["has_payout"]
            .agg(["count", "sum", "mean"])
        )
        print("\nPAYOUT RACE COVERAGE", circuit)
        print(coverage.to_string())


if __name__ == "__main__":
    main()
