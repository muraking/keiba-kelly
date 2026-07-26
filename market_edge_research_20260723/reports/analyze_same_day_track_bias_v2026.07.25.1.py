"""Validate longshots matched to same-day, already-observed track bias.

Only races completed earlier at the same date/venue/surface are used to
classify the bias. Current p_struct supplies the pre-race index.

Version: v2026.07.25.1
"""

from __future__ import annotations

import json
import re
import sqlite3
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd


VERSION = "v2026.07.25.1"
ROOT = Path(r"C:\keiba\data")
WORK = Path(r"C:\keiba\codex_display_test")
REPORT = WORK / f"same_day_track_bias_{VERSION}.json"


def last_corner(value: object) -> float:
    numbers = re.findall(r"\d+", str(value))
    return float(numbers[-1]) if numbers else np.nan


def load(circuit: str) -> tuple[pd.DataFrame, dict[tuple[str, str, str], float]]:
    oos = pd.read_csv(
        WORK / f"oos_predictions_{circuit}_full_2026.07.23.5.csv",
        parse_dates=["date"],
    )
    with sqlite3.connect(ROOT / f"features_{circuit}.sqlite") as connection:
        features = pd.read_sql_query(
            "SELECT race_id,umaban,h_avg_early3 FROM features", connection
        )
    with sqlite3.connect(ROOT / f"keiba_{circuit}.sqlite") as connection:
        runs = pd.read_sql_query(
            """
            SELECT race_id,date,venue,race_num,surface,num_horses,umaban,
                   finish_pos,passing
            FROM runs
            """,
            connection,
            parse_dates=["date"],
        )
        payout_rows = pd.read_sql_query(
            "SELECT race_id,bet_type,comb,payout FROM payouts", connection
        )
    for frame in (oos, features, runs, payout_rows):
        frame["race_id"] = frame["race_id"].astype(str)
    for frame in (oos, features, runs):
        frame["umaban"] = pd.to_numeric(frame["umaban"], errors="coerce").astype("Int64")

    top3 = runs[
        runs["finish_pos"].between(1, 3) & runs["passing"].notna()
    ].copy()
    top3["corner"] = top3["passing"].map(last_corner)
    top3["corner_rel"] = top3["corner"] / top3["num_horses"].clip(lower=1)
    race_bias = (
        top3.groupby(
            ["date", "venue", "surface", "race_num", "race_id"], as_index=False
        )["corner_rel"]
        .mean()
        .sort_values(["date", "venue", "surface", "race_num"])
    )
    group_keys = ["date", "venue", "surface"]
    race_bias["prior_bias"] = race_bias.groupby(group_keys)["corner_rel"].transform(
        lambda values: values.expanding().mean().shift(1)
    )
    race_bias["prior_races"] = race_bias.groupby(group_keys).cumcount()
    metadata = runs[
        ["race_id", "date", "venue", "surface", "race_num"]
    ].drop_duplicates("race_id", keep="last")
    metadata = metadata.merge(
        race_bias[["race_id", "prior_bias", "prior_races"]],
        on="race_id",
        how="left",
    )
    merged = (
        oos.merge(metadata, on="race_id", how="inner", suffixes=("", "_run"))
        .merge(
            features.drop_duplicates(["race_id", "umaban"], keep="last"),
            on=["race_id", "umaban"],
            how="left",
        )
    )
    payouts = {
        (row.race_id, str(row.bet_type), str(row.comb)): float(row.payout)
        for row in payout_rows.itertuples()
    }
    return merged, payouts


def pair(a: int, b: int) -> str:
    return "-".join(map(str, sorted((a, b))))


def trio(a: int, b: int, c: int) -> str:
    return "-".join(map(str, sorted((a, b, c))))


def make_tickets(kind: str, axes: list[int], index_order: list[int]) -> list[str]:
    if kind == "tan":
        return [str(axis) for axis in axes]
    result: list[str] = []
    for axis in axes:
        partners = [number for number in index_order if number != axis]
        if kind in ("umaren", "wide") and partners:
            result.append(pair(axis, partners[0]))
        elif kind == "sanfuku" and len(partners) >= 2:
            result.append(trio(axis, partners[0], partners[1]))
        elif kind.startswith("santan") and len(partners) >= 2:
            position = int(kind[-1])
            for left, right in permutations(partners[:2], 2):
                ordered = (
                    (axis, left, right) if position == 1 else
                    (left, axis, right) if position == 2 else
                    (left, right, axis)
                )
                result.append(">".join(map(str, ordered)))
    return list(dict.fromkeys(result))


def evaluate(
    frame: pd.DataFrame,
    payouts: dict[tuple[str, str, str], float],
    edge_min: float,
    max_axes: int,
    kind: str,
) -> pd.DataFrame:
    values = frame[
        (frame["race_num"] >= 5)
        & (frame["prior_races"] >= 3)
        & ((frame["prior_bias"] <= 0.38) | (frame["prior_bias"] >= 0.52))
    ].copy()
    values["style_match"] = (
        ((values["prior_bias"] <= 0.38) & (values["h_avg_early3"] <= 0.40))
        | ((values["prior_bias"] >= 0.52) & (values["h_avg_early3"] >= 0.60))
    )
    values["edge"] = values["p_struct"] / values["p_market"].clip(lower=1e-9)
    rows = []
    for race_id, group in values.groupby("race_id"):
        pool = group[
            group["style_match"]
            & (group["popularity"] >= 4)
            & group["win_odds"].between(5, 80)
            & (group["edge"] >= edge_min)
        ].sort_values(["edge", "p_struct"], ascending=False)
        axes = pool["umaban"].dropna().astype(int).head(max_axes).tolist()
        if not axes:
            continue
        order = (
            group.sort_values("p_struct", ascending=False)["umaban"]
            .dropna().astype(int).tolist()
        )
        tickets = make_tickets(kind, axes, order)
        payout_type = kind.rstrip("123")
        returned = sum(
            payouts.get((race_id, payout_type, ticket), 0.0) for ticket in tickets
        )
        rows.append(
            {
                "race_id": race_id,
                "date": group["date"].iloc[0],
                "bets": len(tickets),
                "return": returned,
                "bias": (
                    "front" if group["prior_bias"].iloc[0] <= 0.38 else "closer"
                ),
            }
        )
    return pd.DataFrame(rows)


def summary(rows: pd.DataFrame) -> dict:
    if rows.empty:
        return {"races": 0, "bets": 0, "hits": 0, "roi": None}
    bets = int(rows["bets"].sum())
    returned = float(rows["return"].sum())
    return {
        "races": len(rows),
        "bets": bets,
        "hits": int((rows["return"] > 0).sum()),
        "hit_rate": float((rows["return"] > 0).mean() * 100),
        "roi": returned / (bets * 100) * 100 if bets else None,
        "max_payout_share": (
            float(rows["return"].max() / returned) if returned else None
        ),
        "front_races": int((rows["bias"] == "front").sum()),
        "closer_races": int((rows["bias"] == "closer").sum()),
    }


def run(circuit: str) -> dict:
    frame, payouts = load(circuit)
    rules = []
    for edge_min in (1.15, 1.25):
        for max_axes in (1, 2):
            for kind in (
                "tan", "umaren", "wide", "sanfuku",
                "santan1", "santan2", "santan3",
            ):
                rows = evaluate(frame, payouts, edge_min, max_axes, kind)
                periods: dict[str, dict] = {}
                for year in sorted(rows["date"].dt.year.unique()) if not rows.empty else []:
                    periods[str(year)] = summary(rows[rows["date"].dt.year == year])
                if circuit == "jra":
                    periods["2025_H1"] = summary(
                        rows[
                            (rows["date"].dt.year == 2025)
                            & (rows["date"].dt.month <= 6)
                        ]
                    )
                    periods["2025_H2"] = summary(
                        rows[
                            (rows["date"].dt.year == 2025)
                            & (rows["date"].dt.month >= 7)
                        ]
                    )
                rules.append(
                    {
                        "edge_min": edge_min,
                        "max_axes": max_axes,
                        "bet_type": kind,
                        "periods": periods,
                    }
                )
    if circuit == "local":
        stable = [
            rule for rule in rules
            if (rule["periods"].get("2025", {}).get("roi") or 0) >= 100
            and (rule["periods"].get("2026", {}).get("roi") or 0) >= 100
            and rule["periods"].get("2026", {}).get("bets", 0) >= 100
        ]
    else:
        stable = [
            rule for rule in rules
            if (rule["periods"].get("2025_H1", {}).get("roi") or 0) >= 100
            and (rule["periods"].get("2025_H2", {}).get("roi") or 0) >= 100
            and rule["periods"].get("2025_H2", {}).get("bets", 0) >= 50
        ]
    return {
        "version": VERSION,
        "circuit": circuit,
        "rows": len(frame),
        "stable_rules": stable,
        "rules": rules,
    }


def main() -> None:
    result = {circuit: run(circuit) for circuit in ("local", "jra")}
    REPORT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("saved", REPORT)
    for circuit, report in result.items():
        print(circuit, "stable", len(report["stable_rules"]))
        for rule in report["stable_rules"]:
            print(json.dumps(rule, ensure_ascii=False))


if __name__ == "__main__":
    main()
