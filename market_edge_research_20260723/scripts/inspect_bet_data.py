"""Inspect SQLite tables and columns relevant to multi-bet research.

Version: v2026.07.23.2
"""

from __future__ import annotations

import sqlite3
import sys


KEYWORDS = (
    "odds",
    "payout",
    "refund",
    "tan",
    "fuku",
    "wide",
    "umaren",
    "renpuku",
    "rentan",
    "trio",
    "trifecta",
)


def main(paths: list[str]) -> None:
    for path in paths:
        print(f"\nDB {path}")
        with sqlite3.connect(path) as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' ORDER BY name"
            ).fetchall()
            for (table,) in tables:
                columns = connection.execute(
                    f'PRAGMA table_info("{table.replace(chr(34), chr(34) * 2)}")'
                ).fetchall()
                names = [column[1] for column in columns]
                relevant = [
                    name for name in names
                    if any(keyword in name.lower() for keyword in KEYWORDS)
                ]
                print(
                    f"{table}: rows="
                    f"{connection.execute(f'SELECT COUNT(*) FROM \"{table}\"').fetchone()[0]:,}"
                )
                print(f"  columns={','.join(names)}")
                if relevant:
                    print(f"  bet-related={','.join(relevant)}")
            table_names = {table[0] for table in tables}
            if "payouts" in table_names:
                print("  payout summary:")
                summary = connection.execute(
                    "SELECT p.bet_type, COUNT(*), COUNT(DISTINCT p.race_id), "
                    "MIN(r.date), MAX(r.date), MIN(p.payout), MAX(p.payout) "
                    "FROM payouts p "
                    "LEFT JOIN ("
                    "SELECT race_id, MIN(date) AS date FROM runs GROUP BY race_id"
                    ") r ON r.race_id = p.race_id "
                    "GROUP BY p.bet_type ORDER BY p.bet_type"
                ).fetchall()
                for row in summary:
                    print(f"    {row}")
                samples = connection.execute(
                    "SELECT bet_type, comb, payout FROM payouts "
                    "ORDER BY race_id, bet_type LIMIT 30"
                ).fetchall()
                print(f"  payout samples={samples}")


if __name__ == "__main__":
    main(sys.argv[1:])
