"""Inspect inputs needed for same-day track-bias validation.

Version: v2026.07.25.1
"""

from pathlib import Path
import sqlite3

import pandas as pd


ROOT = Path(r"C:\keiba\data")


for circuit in ("local", "jra"):
    with sqlite3.connect(ROOT / f"features_{circuit}.sqlite") as connection:
        feature_stats = pd.read_sql_query(
            """
            SELECT COUNT(*) n,
                   MIN(h_avg_early3) min_early,
                   AVG(h_avg_early3) avg_early,
                   MAX(h_avg_early3) max_early,
                   SUM(h_avg_early3 IS NULL) null_early
            FROM features
            """,
            connection,
        )
    with sqlite3.connect(ROOT / f"keiba_{circuit}.sqlite") as connection:
        samples = pd.read_sql_query(
            """
            SELECT date, venue, race_num, num_horses, umaban, finish_pos, passing
            FROM runs
            WHERE passing IS NOT NULL AND passing <> ''
              AND finish_pos IS NOT NULL
            ORDER BY date DESC, venue, race_num, finish_pos
            LIMIT 20
            """,
            connection,
        )
    print(f"\n[{circuit}] FEATURE STATS")
    print(feature_stats.to_string(index=False))
    print(f"\n[{circuit}] PASSING SAMPLES")
    print(samples.to_string(index=False))
