"""Validate change-horse signals matched to same-day track bias and style.

The track-bias value for a race uses only the latest three completed races at
the same date, venue and surface. Strategy ranking uses 2024 only; 2025 and
2026 are frozen out-of-sample confirmation periods.

Version: v2026.07.26.1
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd


VERSION = "v2026.07.26.1"
ANA = [
    "ana_layoff", "ana_rest_lean", "ana_tataki2", "ana_draw_change",
    "ana_draw_change_abs", "ana_style_shift", "ana_style_shift_abs",
    "ana_dist_change_abs", "ana_class_change", "ana_going_change",
    "ana_wtcarried_change", "ana_short_rest", "ana_last3f_sharp",
    "ana_surf_change", "ana_venue_change", "ana_last_pos_gain",
    "ana_bounce", "ana_weight_swing_abs",
]


def last_corner(value: object) -> float:
    numbers = re.findall(r"\d+", str(value))
    return float(numbers[-1]) if numbers else np.nan


def load(data_dir: Path, oos_path: Path) -> tuple[pd.DataFrame, dict]:
    oos = pd.read_csv(oos_path, parse_dates=["date"])
    columns = ",".join(
        ["race_id", "umaban", "h_avg_early3", *ANA]
    )
    with sqlite3.connect(data_dir / "features_local.sqlite") as connection:
        features = pd.read_sql_query(
            f"SELECT {columns} FROM features", connection
        )
    with sqlite3.connect(data_dir / "keiba_local.sqlite") as connection:
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
        frame["umaban"] = pd.to_numeric(
            frame["umaban"], errors="coerce"
        ).astype("Int64")

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
    keys = ["date", "venue", "surface"]
    race_bias["prior_bias"] = race_bias.groupby(keys)["corner_rel"].transform(
        lambda values: values.rolling(3, min_periods=3).mean().shift(1)
    )
    race_bias["prior_races"] = race_bias.groupby(keys).cumcount()
    metadata = runs[
        ["race_id", "date", "venue", "surface", "race_num"]
    ].drop_duplicates("race_id", keep="last")
    metadata = metadata.merge(
        race_bias[["race_id", "prior_bias", "prior_races"]],
        on="race_id", how="left",
    )
    frame = (
        oos.merge(metadata, on="race_id", how="inner", suffixes=("", "_run"))
        .merge(
            features.drop_duplicates(["race_id", "umaban"], keep="last"),
            on=["race_id", "umaban"], how="left",
        )
    )
    numeric = frame[ANA].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    # Every anomaly field is pre-race and centered at no change. Count material
    # deviations without assigning a result-derived direction.
    frame["change_score"] = (
        numeric.abs().gt(1e-9).sum(axis=1).astype(np.int8)
    )
    frame["edge"] = frame["p_struct"] / frame["p_market"].clip(lower=1e-9)
    frame["bias_side"] = np.where(
        frame["prior_bias"] <= 0.38, "front",
        np.where(frame["prior_bias"] >= 0.48, "closer", "neutral"),
    )
    frame["style_match"] = (
        ((frame["bias_side"] == "front") & (frame["h_avg_early3"] <= 0.40))
        | ((frame["bias_side"] == "closer") & (frame["h_avg_early3"] >= 0.60))
    )
    payouts = {
        (row.race_id, str(row.bet_type), str(row.comb)): float(row.payout)
        for row in payout_rows.itertuples()
    }
    return frame, payouts


def pair(a: int, b: int) -> str:
    return "-".join(map(str, sorted((a, b))))


def trio(a: int, b: int, c: int) -> str:
    return "-".join(map(str, sorted((a, b, c))))


def tickets(kind: str, axes: list[int], order: list[int]) -> list[str]:
    if kind == "tan":
        return [str(axis) for axis in axes]
    output = []
    for axis in axes:
        partners = [number for number in order if number != axis]
        if kind in ("umaren", "wide") and partners:
            output.append(pair(axis, partners[0]))
        elif kind == "sanfuku" and len(partners) >= 2:
            output.append(trio(axis, partners[0], partners[1]))
        elif kind.startswith("santan") and len(partners) >= 2:
            position = int(kind[-1])
            for left, right in permutations(partners[:2], 2):
                ordered = (
                    (axis, left, right) if position == 1 else
                    (left, axis, right) if position == 2 else
                    (left, right, axis)
                )
                output.append(">".join(map(str, ordered)))
    return list(dict.fromkeys(output))


def candidate_mask(
    frame: pd.DataFrame, variant: str, change_min: int, edge_min: float,
) -> pd.Series:
    mask = (
        (frame["race_num"] >= 5)
        & (frame["popularity"] >= 4)
        & frame["win_odds"].between(5, 80)
    )
    if variant in {"change", "change_bias", "change_bias_edge"}:
        mask &= frame["change_score"] >= change_min
    if variant in {"bias", "change_bias", "change_bias_edge"}:
        mask &= (
            (frame["prior_races"] >= 3)
            & frame["style_match"]
            & (frame["bias_side"] != "neutral")
        )
    if variant == "change_bias_edge":
        mask &= frame["edge"] >= edge_min
    return mask


def evaluate(
    frame: pd.DataFrame, payouts: dict, variant: str, change_min: int,
    edge_min: float, max_axes: int, kind: str,
) -> pd.DataFrame:
    eligible = candidate_mask(frame, variant, change_min, edge_min)
    rows = []
    for race_id, group in frame.groupby("race_id", sort=False):
        pool = group[eligible.loc[group.index]].sort_values(
            ["edge", "p_struct"], ascending=False
        )
        axes = pool["umaban"].dropna().astype(int).head(max_axes).tolist()
        if not axes:
            continue
        order = (
            group.sort_values("p_struct", ascending=False)["umaban"]
            .dropna().astype(int).tolist()
        )
        bet_list = tickets(kind, axes, order)
        payout_type = kind.rstrip("123")
        returned = sum(
            payouts.get((race_id, payout_type, ticket), 0.0)
            for ticket in bet_list
        )
        rows.append({
            "race_id": race_id,
            "date": group["date"].iloc[0],
            "bets": len(bet_list),
            "return": returned,
            "bias_side": group["bias_side"].iloc[0],
        })
    return pd.DataFrame(rows)


def summarize(rows: pd.DataFrame) -> dict:
    if rows.empty:
        return {"races": 0, "bets": 0, "hits": 0, "roi": 0.0, "lcb90": -999}
    bets = int(rows["bets"].sum())
    # Split a race return over its tickets for a conservative ticket-level SE.
    per_ticket = rows["return"].to_numpy() / rows["bets"].to_numpy()
    roi = float(rows["return"].sum() / (bets * 100) * 100)
    se = (
        float(per_ticket.std(ddof=1) / np.sqrt(len(per_ticket)))
        if len(per_ticket) > 1 else 999
    )
    returned = float(rows["return"].sum())
    return {
        "races": len(rows),
        "bets": bets,
        "hits": int((rows["return"] > 0).sum()),
        "hit_rate": float((rows["return"] > 0).mean() * 100),
        "roi": roi,
        "lcb90": float(per_ticket.mean() - 1.2816 * se),
        "max_payout_share": (
            float(rows["return"].max() / returned) if returned else None
        ),
        "front_races": int((rows["bias_side"] == "front").sum()),
        "closer_races": int((rows["bias_side"] == "closer").sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frame, payouts = load(args.data_dir, args.oos)
    rules = []
    variants = ("change", "bias", "change_bias", "change_bias_edge")
    kinds = ("tan", "umaren", "wide", "sanfuku", "santan1", "santan2", "santan3")
    for variant in variants:
        change_values = (1, 2, 3) if "change" in variant else (1,)
        edge_values = (1.15, 1.25) if variant == "change_bias_edge" else (1.0,)
        for change_min in change_values:
            for edge_min in edge_values:
                for max_axes in (1, 2):
                    for kind in kinds:
                        rows = evaluate(
                            frame, payouts, variant, change_min,
                            edge_min, max_axes, kind,
                        )
                        periods = {
                            str(year): summarize(
                                rows[rows["date"].dt.year == year]
                            )
                            for year in (2024, 2025, 2026)
                        }
                        rules.append({
                            "variant": variant,
                            "change_min": change_min,
                            "edge_min": edge_min,
                            "max_axes": max_axes,
                            "bet_type": kind,
                            "periods": periods,
                        })
    discovery = sorted(
        [
            rule for rule in rules
            if rule["periods"]["2024"]["bets"] >= 200
            and rule["periods"]["2024"]["hits"] >= 10
        ],
        key=lambda rule: (
            rule["periods"]["2024"]["lcb90"],
            rule["periods"]["2024"]["roi"],
        ),
        reverse=True,
    )
    confirmed = [
        rule for rule in discovery
        if rule["periods"]["2024"]["roi"] >= 100
        and rule["periods"]["2025"]["roi"] >= 100
        and rule["periods"]["2026"]["roi"] >= 100
        and rule["periods"]["2025"]["bets"] >= 100
        and rule["periods"]["2026"]["bets"] >= 50
    ]
    report = {
        "version": VERSION,
        "rows": len(frame),
        "change_score_distribution": {
            str(key): int(value)
            for key, value in frame["change_score"].value_counts().sort_index().items()
        },
        "bias_distribution": {
            str(key): int(value)
            for key, value in frame.drop_duplicates("race_id")[
                "bias_side"
            ].value_counts().items()
        },
        "confirmed_rules": confirmed,
        "top_2024_discovery": discovery[:30],
        "all_rules": rules,
        "limitations": [
            "2024 ranks candidate rules; 2025/2026 are frozen confirmation",
            "2026 is partial year",
            "final odds measure research value, not live execution slippage",
        ],
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("rows", len(frame), "rules", len(rules), "confirmed", len(confirmed))
    for rule in confirmed[:20]:
        print(json.dumps(rule, ensure_ascii=False))
    print("saved", args.output)


if __name__ == "__main__":
    main()
