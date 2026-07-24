"""Inspect JRA pedigree/training JSON coverage without modifying source data.

Version: v2026.07.24.1
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path


VERSION = "v2026.07.24.1"


def describe_json(path: str) -> tuple[object, dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    info = {
        "type": type(data).__name__,
        "length": len(data) if hasattr(data, "__len__") else None,
    }
    if isinstance(data, dict):
        keys = list(data)
        info["key_sample"] = keys[:3]
        sample = data[keys[0]] if keys else None
    elif isinstance(data, list):
        sample = data[0] if data else None
    else:
        sample = data
    info["sample"] = sample
    return data, info


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: script PEDIGREE_JSON TRAINING_JSON JRA_DB")
    pedigree, pedigree_info = describe_json(sys.argv[1])
    training, training_info = describe_json(sys.argv[2])

    connection = sqlite3.connect(sys.argv[3])
    horse_ids = {
        str(row[0]) for row in connection.execute(
            "SELECT DISTINCT horse_id FROM runs WHERE horse_id IS NOT NULL"
        )
    }
    race_horses = connection.execute(
        "SELECT COUNT(*) FROM runs WHERE horse_id IS NOT NULL"
    ).fetchone()[0]
    connection.close()

    pedigree_keys = set(map(str, pedigree)) if isinstance(pedigree, dict) else set()
    training_keys = set(map(str, training)) if isinstance(training, dict) else set()
    result = {
        "version": VERSION,
        "pedigree": pedigree_info,
        "training": training_info,
        "jra_unique_horses": len(horse_ids),
        "jra_rows_with_horse_id": race_horses,
        "pedigree_key_overlap": len(horse_ids & pedigree_keys),
        "training_key_overlap": len(horse_ids & training_keys),
        "pedigree_key_length_counts": dict(Counter(map(len, pedigree_keys))),
        "training_key_length_counts": dict(Counter(map(len, training_keys))),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
