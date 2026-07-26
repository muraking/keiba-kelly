"""Locate 2024 local win/place payouts across copied SQLite databases.

Version: v2026.07.26.1
"""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def inspect(path: Path) -> list[dict]:
    found = []
    try:
        with sqlite3.connect(path) as c:
            tables = [r[0] for r in c.execute(
                "select name from sqlite_master where type='table'"
            )]
            for table in tables:
                columns = [r[1] for r in c.execute(
                    f"pragma table_info({qident(table)})"
                )]
                lower = {x.lower(): x for x in columns}
                date_col = next((lower[x] for x in ("date", "race_date") if x in lower), None)
                race_col = next((lower[x] for x in ("race_id", "raceid") if x in lower), None)
                payout_cols = [
                    col for col in columns
                    if any(key in col.lower() for key in (
                        "payout", "refund", "tan", "fuku", "place",
                    ))
                ]
                if not payout_cols:
                    continue
                item = {
                    "db": str(path), "table": table, "date_col": date_col,
                    "race_col": race_col, "payout_cols": payout_cols,
                }
                if date_col:
                    item["rows_2024"] = c.execute(
                        f"select count(*) from {qident(table)} "
                        f"where cast({qident(date_col)} as text) like '2024%'"
                    ).fetchone()[0]
                found.append(item)
    except sqlite3.Error as error:
        found.append({"db": str(path), "error": str(error)})
    return found


def main():
    p = argparse.ArgumentParser()
    p.add_argument("roots", nargs="+", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    databases = sorted({
        path.resolve()
        for root in a.roots
        for pattern in ("*.sqlite", "*.db")
        for path in root.rglob(pattern)
        if any(key in path.name.lower() for key in ("local", "nar", "chihou"))
    })
    result = [item for db in databases for item in inspect(db)]
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in result:
        if item.get("rows_2024", 0) or item.get("table") == "payouts":
            print(item)


if __name__ == "__main__":
    main()
