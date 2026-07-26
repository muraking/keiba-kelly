"""Validate wide six-ticket boxes after strict field-experience exclusions.

Version: v2026.07.26.2
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path

import pandas as pd

VERSION = "v2026.07.26.2"
WIDE_SCRIPT = Path(__file__).with_name(
    "search_win_top2_longshot_wide_v2026.07.26.2.py"
)
SPEC = importlib.util.spec_from_file_location("wide_search", WIDE_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {WIDE_SCRIPT}")
WIDE_SEARCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WIDE_SEARCH)
build = WIDE_SEARCH.build
metrics = WIDE_SEARCH.metrics


def eligible_races(db: Path) -> tuple[pd.DataFrame, dict]:
    with sqlite3.connect(db) as connection:
        runs = pd.read_sql_query(
            """
            SELECT race_id, date, venue, race_name, horse_id, umaban, age
            FROM runs
            ORDER BY date, race_id, umaban
            """,
            connection,
        )
    runs["race_id"] = runs["race_id"].astype(str)
    runs["date"] = pd.to_datetime(runs["date"])
    runs["horse_key"] = runs["horse_id"].fillna("").astype(str)
    missing_id = runs["horse_key"].eq("")
    runs.loc[missing_id, "horse_key"] = (
        "missing:" + runs.loc[missing_id, "race_id"] + ":"
        + runs.loc[missing_id, "umaban"].astype(str)
    )

    # cumcount is calculated after chronological sorting and therefore uses
    # only starts strictly before the current race.
    runs["prior_same_venue"] = runs.groupby(
        ["horse_key", "venue"], sort=False
    ).cumcount()
    runs["is_two_year_old"] = runs["age"].eq(2)
    runs["is_debut_race"] = runs["race_name"].fillna("").str.contains("新馬")
    runs["insufficient_venue_history"] = runs["prior_same_venue"].lt(3)

    race = runs.groupby("race_id", sort=False).agg(
        date=("date", "first"),
        venue=("venue", "first"),
        starters=("umaban", "size"),
        has_two_year_old=("is_two_year_old", "any"),
        is_debut_race=("is_debut_race", "any"),
        has_inexperienced_runner=("insufficient_venue_history", "any"),
        min_prior_same_venue=("prior_same_venue", "min"),
    )
    race["eligible"] = ~(
        race["has_two_year_old"]
        | race["is_debut_race"]
        | race["has_inexperienced_runner"]
    )
    audit = {
        "all_races": int(len(race)),
        "two_year_old_races": int(race["has_two_year_old"].sum()),
        "debut_races": int(race["is_debut_race"].sum()),
        "inexperienced_field_races": int(race["has_inexperienced_runner"].sum()),
        "eligible_races": int(race["eligible"].sum()),
    }
    return race.reset_index(), audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tickets = build(args.oos, args.db)
    race, audit = eligible_races(args.db)
    eligible_ids = set(race.loc[race["eligible"], "race_id"])
    selected = tickets[tickets["race_id"].isin(eligible_ids)].copy()

    result = {
        "version": VERSION,
        "market": args.market,
        "definition": {
            "two_year_old": "exclude a race when any runner age=2",
            "debut": "exclude race_name containing 新馬",
            "venue_experience": (
                "every runner must have at least 3 prior starts at today's venue"
            ),
            "local_transfer": (
                "proxied by venue experience because transfer history is not stored"
            ),
            "tickets": (
                "p_win absolute top2 x p_place top3 among win_odds>=10; "
                "same-horse pairs skipped"
            ),
        },
        "database_audit": audit,
        "ticket_rows_before_filter": int(len(tickets)),
        "ticket_rows_after_filter": int(len(selected)),
        "eligible_oos_races": int(selected["race_id"].nunique()),
        "yearly": {
            str(year): {
                "races": int(selected.loc[selected["year"].eq(year), "race_id"].nunique()),
                **metrics(selected[selected["year"].eq(year)]),
            }
            for year in sorted(selected["year"].unique())
        },
        "overall": metrics(selected),
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
