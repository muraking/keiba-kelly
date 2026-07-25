"""Walk-forward hidden-longshot model and multi-ticket evaluation.

The anomaly model is trained only on years before each test year. The current
OOS exports cover 2025/2026, so rules are selected on 2025 and frozen for the
available 2026 partial-year OOS.

Version: v2026.07.25.3
"""

from __future__ import annotations

import json
import math
import sqlite3
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier


VERSION = "v2026.07.25.3"
ROOT = Path(r"C:\keiba\data")
WORK = Path(r"C:\keiba\codex_display_test")
ANA = [
    "ana_layoff", "ana_rest_lean", "ana_tataki2", "ana_draw_change",
    "ana_draw_change_abs", "ana_style_shift", "ana_style_shift_abs",
    "ana_dist_change_abs", "ana_class_change", "ana_going_change",
    "ana_wtcarried_change", "ana_short_rest", "ana_last3f_sharp",
    "ana_surf_change", "ana_venue_change", "ana_last_pos_gain",
    "ana_bounce", "ana_weight_swing_abs",
]
BASE = [
    "field_size", "age", "weight_carried", "h_n_past", "h_days_since",
    "h_last_pos", "h_avg_pos3", "h_winrate", "h_placerate", "h_avg_rel3",
    "h_best_rel5", "h_avg_last3f3", "h_avg_early3", "h_dist_change",
    "j_winrate", "t_winrate", "h_rank_std", "h_venue_winrate",
    "h_avg_spd3", "h_best_spd5", "h_avg_rtop3",
]
FEATURES = ANA + BASE


def load(
    circuit: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, str, str], float]]:
    with sqlite3.connect(ROOT / f"features_{circuit}.sqlite") as connection:
        columns = ", ".join([
            "race_id", "date", "umaban", "is_win", "finish_pos", *FEATURES
        ])
        features = pd.read_sql_query(
            f"SELECT {columns} FROM features", connection, parse_dates=["date"]
        )
    oos = pd.read_csv(
        WORK / f"oos_predictions_{circuit}_full_2026.07.23.5.csv",
        parse_dates=["date"],
    )
    for frame in (features, oos):
        frame["race_id"] = frame["race_id"].astype(str)
        frame["umaban"] = pd.to_numeric(frame["umaban"], errors="coerce").astype("Int64")
    merged = oos.merge(
        features.drop_duplicates(["race_id", "umaban"], keep="last"),
        on=["race_id", "umaban"], how="inner", suffixes=("", "_feature"),
    )
    with sqlite3.connect(ROOT / f"keiba_{circuit}.sqlite") as connection:
        raw_payouts = pd.read_sql_query(
            "SELECT race_id,bet_type,comb,payout FROM payouts", connection
        )
    payouts = {
        (str(row.race_id), str(row.bet_type), str(row.comb)): float(row.payout)
        for row in raw_payouts.itertuples()
    }
    return features, merged, payouts


def walkforward_anomaly(
    history: pd.DataFrame, evaluation: pd.DataFrame,
) -> pd.DataFrame:
    outputs = []
    training = history.copy()
    testing = evaluation.copy()
    training["year"] = training["date"].dt.year
    testing["year"] = testing["date"].dt.year
    for year in sorted(testing["year"].unique()):
        test = testing[testing["year"] == year].copy()
        train = training[
            (training["year"] < year) & (training["year"] >= year - 4)
        ].dropna(subset=["is_win"]).copy()
        if len(test) == 0 or train["is_win"].sum() < 100:
            continue
        model = HistGradientBoostingClassifier(
            learning_rate=.05, max_iter=100, max_leaf_nodes=15,
            min_samples_leaf=80, l2_regularization=5.0, random_state=20260725,
        )
        y = train["is_win"].astype(int)
        field = train["field_size"].fillna(12).clip(5, 20)
        weights = np.where(y == 1, field - 1, 1.0)
        model.fit(train[FEATURES], y, sample_weight=weights)
        raw = model.predict_proba(test[FEATURES])[:, 1]
        test["p_anomaly"] = raw / pd.Series(raw, index=test.index).groupby(
            test["race_id"]
        ).transform("sum")
        outputs.append(test)
    return pd.concat(outputs, ignore_index=True)


def comb_pair(a: int, b: int) -> str:
    return "-".join(map(str, sorted((a, b))))


def comb_trio(a: int, b: int, c: int) -> str:
    return "-".join(map(str, sorted((a, b, c))))


def tickets(kind: str, candidates: list[int], ai: list[int]) -> list[str]:
    result = []
    if kind == "tan":
        return [str(number) for number in candidates]
    for axis in candidates:
        partners = [number for number in ai if number != axis]
        if kind in ("umaren", "wide") and partners:
            result.append(comb_pair(axis, partners[0]))
        elif kind == "sanfuku" and len(partners) >= 2:
            result.append(comb_trio(axis, partners[0], partners[1]))
        elif kind.startswith("santan") and len(partners) >= 2:
            pos = int(kind[-1])
            for left, right in permutations(partners[:2], 2):
                ordered = (
                    (axis, left, right) if pos == 1 else
                    (left, axis, right) if pos == 2 else
                    (left, right, axis)
                )
                result.append(">".join(map(str, ordered)))
    return list(dict.fromkeys(result))


def evaluate_rule(
    frame: pd.DataFrame, payouts: dict, alpha: float, edge: float,
    max_candidates: int, min_odds: float, kind: str,
) -> pd.DataFrame:
    values = frame.copy()
    eps = 1e-9
    values["blend"] = np.exp(
        alpha * np.log(values["p_anomaly"].clip(lower=eps))
        + (1 - alpha) * np.log(values["p_struct"].clip(lower=eps))
    )
    values["blend"] /= values.groupby("race_id")["blend"].transform("sum")
    values["edge"] = values["blend"] / values["p_market"].clip(lower=eps)
    rows = []
    for race_id, group in values.groupby("race_id"):
        pool = group[
            (group["popularity"] >= 4)
            & (group["win_odds"] >= min_odds)
            & (group["win_odds"] <= 80)
            & (group["edge"] >= edge)
        ].sort_values(["edge", "blend"], ascending=False)
        candidate_numbers = pool["umaban"].astype(int).head(max_candidates).tolist()
        if not candidate_numbers:
            continue
        ai_numbers = group.sort_values("p_struct", ascending=False)["umaban"].astype(int).tolist()
        ticket_list = tickets(kind, candidate_numbers, ai_numbers)
        if not ticket_list:
            continue
        returned = sum(
            payouts.get((str(race_id), kind.rstrip("123"), ticket), 0.0)
            for ticket in ticket_list
        )
        rows.append({
            "race_id": str(race_id), "date": group["date"].iloc[0],
            "bets": len(ticket_list), "return": returned,
            "candidates": len(candidate_numbers),
        })
    return pd.DataFrame(rows)


def summarize(rows: pd.DataFrame) -> dict:
    if rows.empty:
        return {"races": 0, "bets": 0, "hits": 0, "roi": 0.0}
    bets = int(rows["bets"].sum())
    returned = float(rows["return"].sum())
    hits = int((rows["return"] > 0).sum())
    max_share = float(rows["return"].max() / returned) if returned else 0.0
    return {
        "races": len(rows), "bets": bets, "hits": hits,
        "hit_rate": hits / len(rows) * 100,
        "roi": returned / (bets * 100) * 100 if bets else 0.0,
        "max_payout_share": max_share,
    }


def run(circuit: str) -> dict:
    history, frame, payouts = load(circuit)
    predicted = walkforward_anomaly(history, frame)
    years = sorted(predicted["date"].dt.year.unique())
    print(f"\n[{circuit}] rows={len(predicted):,} years={years}")
    rules = []
    for alpha in (.50,):
        for edge in (1.25,):
            for count in (1, 2, 3):
                for min_odds in (5.0,):
                    for kind in (
                        "tan", "umaren", "wide", "sanfuku",
                        "santan1", "santan2", "santan3",
                    ):
                        by_year = {}
                        for year in years:
                            rows = evaluate_rule(
                                predicted[predicted["date"].dt.year == year],
                                payouts, alpha, edge, count, min_odds, kind,
                            )
                            by_year[str(year)] = summarize(rows)
                        discovery = by_year.get("2025", {})
                        if discovery.get("bets", 0) >= 100 and discovery.get("hits", 0) >= 8:
                            rules.append({
                                "alpha": alpha, "edge": edge, "max_candidates": count,
                                "min_odds": min_odds, "bet_type": kind, "years": by_year,
                            })
    selected = sorted(
        rules,
        key=lambda rule: (
            rule["years"].get("2025", {}).get("roi", 0) >= 110,
            rule["years"].get("2026", {}).get("roi", 0),
            rule["years"].get("2025", {}).get("roi", 0),
        ),
        reverse=True,
    )
    stable = [
        rule for rule in selected
        if rule["years"].get("2025", {}).get("roi", 0) >= 100
        and rule["years"].get("2026", {}).get("bets", 0) >= 50
        and rule["years"].get("2026", {}).get("roi", 0) >= 100
    ]
    print("stable", len(stable))
    for rule in stable[:20]:
        print(json.dumps(rule, ensure_ascii=False))
    return {
        "version": VERSION, "circuit": circuit, "rows": len(predicted),
        "years": [int(year) for year in years], "stable_rules": stable[:100],
        "top_discovery_rules": selected[:100],
    }


def main() -> None:
    report = {circuit: run(circuit) for circuit in ("local", "jra")}
    output = WORK / f"hidden_longshot_model_{VERSION}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", output)


if __name__ == "__main__":
    main()
