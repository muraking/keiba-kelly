"""Audit the immutable local snapshot used by zero-base model research.

Version: v2026.07.26.1
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


VERSION = "v2026.07.26.1"
DATE_NAMES = ("date", "race_date", "kaisai_date", "target_date")


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def audit_sqlite(path: Path) -> dict:
    result: dict = {
        "file": path.name,
        "bytes": path.stat().st_size,
        "quick_check": None,
        "tables": [],
    }
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as con:
        result["quick_check"] = con.execute("PRAGMA quick_check").fetchone()[0]
        tables = [
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in tables:
            columns = [
                row[1]
                for row in con.execute(f"PRAGMA table_info({quote(table)})")
            ]
            count = con.execute(
                f"SELECT COUNT(*) FROM {quote(table)}"
            ).fetchone()[0]
            item = {"name": table, "rows": count, "columns": columns}
            date_column = next(
                (name for name in DATE_NAMES if name in columns), None
            )
            if date_column:
                minimum, maximum = con.execute(
                    f"SELECT MIN({quote(date_column)}), MAX({quote(date_column)}) "
                    f"FROM {quote(table)}"
                ).fetchone()
                item["date_column"] = date_column
                item["date_min"] = minimum
                item["date_max"] = maximum
            result["tables"].append(item)
    return result


def audit_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    result = {
        "file": path.name,
        "bytes": path.stat().st_size,
        "root_type": type(value).__name__,
    }
    if isinstance(value, (list, dict)):
        result["records"] = len(value)
    if isinstance(value, dict):
        result["sample_keys"] = list(value)[:20]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sqlite_files = sorted(args.data_dir.glob("*.sqlite"))
    json_files = sorted(args.data_dir.glob("*.json"))
    report = {
        "version": VERSION,
        "data_dir": str(args.data_dir.resolve()),
        "sqlite": [audit_sqlite(path) for path in sqlite_files],
        "json": [audit_json(path) for path in json_files],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "sqlite", len(report["sqlite"]),
        "json", len(report["json"]),
        "output", args.output,
    )


if __name__ == "__main__":
    main()
