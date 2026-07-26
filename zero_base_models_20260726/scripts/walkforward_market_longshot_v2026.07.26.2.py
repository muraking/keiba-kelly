"""Walk-forward structural and market-residual models.

The structural model never sees odds, popularity, payouts or result columns.
The longshot model may use market probability because it represents the
pre-race gap between structural evidence and the market.

Version: v2026.07.26.2
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score


VERSION = "v2026.07.26.2"
EXCLUDE = {
    "race_id", "date", "venue", "horse_id", "is_win", "is_place",
    "win_odds", "popularity", "tan_payout", "place_payout", "finish_pos",
    "is_iruka", "obstacle_time",
}


def load(path: Path) -> pd.DataFrame:
    with sqlite3.connect(path) as con:
        frame = pd.read_sql_query("SELECT * FROM features", con)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in frame.columns:
        if column not in {"race_id", "date", "venue", "horse_id"}:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame[
        frame["date"].notna()
        & frame["is_win"].notna()
        & frame["win_odds"].gt(1.0)
    ].copy()
    frame["race_id"] = frame["race_id"].astype(str)
    return frame


def normalize_race(values: np.ndarray, race_ids: pd.Series) -> np.ndarray:
    series = pd.Series(np.clip(values, 1e-7, None), index=race_ids.index)
    denominator = series.groupby(race_ids).transform("sum").clip(lower=1e-9)
    return (series / denominator).to_numpy()


def market_probability(frame: pd.DataFrame) -> np.ndarray:
    raw = 1.0 / frame["win_odds"].clip(lower=1.01)
    return normalize_race(raw.to_numpy(), frame["race_id"])


def matrix(frame: pd.DataFrame, features: list[str], medians=None):
    values = frame[features].replace([np.inf, -np.inf], np.nan)
    if medians is None:
        medians = values.median().fillna(0.0)
    return values.fillna(medians).astype(np.float32), medians


def model() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=180,
        max_leaf_nodes=31,
        min_samples_leaf=80,
        l2_regularization=2.0,
        random_state=20260726,
    )


def metrics(y: np.ndarray, probability: np.ndarray) -> dict:
    p = np.clip(probability, 1e-7, 1 - 1e-7)
    return {
        "logloss": float(log_loss(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
    }


def bet_summary(frame: pd.DataFrame, mask: np.ndarray) -> dict:
    selected = frame.loc[mask]
    bets = len(selected)
    if not bets:
        return {"bets": 0, "hits": 0, "roi": 0.0, "lcb90": -999.0}
    returns = np.where(
        selected["is_win"].to_numpy() == 1,
        selected["tan_payout"].fillna(0).to_numpy(),
        0.0,
    )
    profit_units = returns / 100.0
    standard_error = (
        float(profit_units.std(ddof=1) / np.sqrt(bets)) if bets > 1 else 999.0
    )
    total = float(returns.sum())
    return {
        "bets": bets,
        "hits": int(selected["is_win"].sum()),
        "hit_rate": float(selected["is_win"].mean() * 100),
        "roi": float(total / (bets * 100) * 100),
        "lcb90": float(profit_units.mean() - 1.2816 * standard_error),
        "max_payout_share": (
            float(returns.max() / total) if total > 0 else None
        ),
        "avg_odds": float(selected["win_odds"].mean()),
    }


def rules() -> list[dict]:
    output = []
    for source in ("struct", "residual"):
        for edge in (1.05, 1.10, 1.15, 1.20, 1.30, 1.40):
            for minimum_probability in (0.03, 0.05, 0.08, 0.10):
                for odds_low, odds_high in (
                    (4, 10), (6, 15), (10, 30), (15, 80), (4, 80),
                ):
                    output.append({
                        "source": source,
                        "edge": edge,
                        "minimum_probability": minimum_probability,
                        "odds_low": odds_low,
                        "odds_high": odds_high,
                    })
    return output


def rule_mask(frame: pd.DataFrame, rule: dict) -> np.ndarray:
    probability = (
        frame["p_struct"].to_numpy()
        if rule["source"] == "struct"
        else frame["p_residual"].to_numpy()
    )
    edge = probability / np.clip(frame["p_market"].to_numpy(), 1e-9, None)
    return (
        (probability >= rule["minimum_probability"])
        & (edge >= rule["edge"])
        & frame["win_odds"].between(
            rule["odds_low"], rule["odds_high"], inclusive="both"
        ).to_numpy()
        & (frame["popularity"].to_numpy() >= 2)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-db", type=Path, required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args()

    frame = load(args.features_db)
    structural_features = [
        column for column in frame.columns
        if column not in EXCLUDE
        and column not in {"p_market", "p_struct", "p_residual"}
        and pd.api.types.is_numeric_dtype(frame[column])
    ]
    predictions = []
    fold_reports = []
    for year in (2024, 2025, 2026):
        train = frame[frame["date"].dt.year < year].copy()
        test = frame[frame["date"].dt.year == year].copy()
        if train.empty or test.empty:
            continue
        x_train, medians = matrix(train, structural_features)
        x_test, _ = matrix(test, structural_features, medians)
        structural = model()
        structural.fit(x_train, train["is_win"].astype(int))
        train["p_market"] = market_probability(train)
        test["p_market"] = market_probability(test)
        train["p_struct_raw"] = structural.predict_proba(x_train)[:, 1]
        test["p_struct_raw"] = structural.predict_proba(x_test)[:, 1]
        train["p_struct"] = normalize_race(
            train["p_struct_raw"].to_numpy(), train["race_id"]
        )
        test["p_struct"] = normalize_race(
            test["p_struct_raw"].to_numpy(), test["race_id"]
        )

        residual_features = structural_features + [
            "p_market", "p_struct", "win_odds", "popularity"
        ]
        xr_train, residual_medians = matrix(train, residual_features)
        xr_test, _ = matrix(test, residual_features, residual_medians)
        residual = model()
        residual.fit(xr_train, train["is_win"].astype(int))
        test["p_residual_raw"] = residual.predict_proba(xr_test)[:, 1]
        test["p_residual"] = normalize_race(
            test["p_residual_raw"].to_numpy(), test["race_id"]
        )
        y = test["is_win"].astype(int).to_numpy()
        fold_reports.append({
            "year": year,
            "train_rows": len(train),
            "test_rows": len(test),
            "market": metrics(y, test["p_market"].to_numpy()),
            "structural": metrics(y, test["p_struct"].to_numpy()),
            "residual": metrics(y, test["p_residual"].to_numpy()),
        })
        predictions.append(test[[
            "race_id", "date", "venue", "umaban", "is_win", "is_place",
            "win_odds", "popularity", "tan_payout", "place_payout",
            "p_market", "p_struct", "p_residual",
        ]])

    oos = pd.concat(predictions, ignore_index=True)
    evaluated = []
    for rule in rules():
        periods = {}
        for year in (2024, 2025, 2026):
            subset = oos[oos["date"].dt.year == year]
            periods[str(year)] = bet_summary(subset, rule_mask(subset, rule))
        evaluated.append({**rule, "periods": periods})
    discovery = sorted(
        [
            rule for rule in evaluated
            if rule["periods"]["2024"]["bets"] >= 100
        ],
        key=lambda item: (
            item["periods"]["2024"]["lcb90"],
            item["periods"]["2024"]["roi"],
        ),
        reverse=True,
    )
    confirmed = [
        rule for rule in discovery
        if all(
            rule["periods"][str(year)]["roi"] >= 100
            for year in (2024, 2025, 2026)
        )
        and rule["periods"]["2025"]["bets"] >= 100
        and rule["periods"]["2026"]["bets"] >= 50
        and rule["periods"]["2025"]["max_payout_share"] is not None
        and rule["periods"]["2025"]["max_payout_share"] <= 0.20
    ]
    report = {
        "version": VERSION,
        "market": args.market,
        "rows": len(frame),
        "date_min": str(frame["date"].min().date()),
        "date_max": str(frame["date"].max().date()),
        "structural_features": structural_features,
        "folds": fold_reports,
        "rules_tested": len(evaluated),
        "confirmed_rules": confirmed,
        "top_2024_discovery": discovery[:30],
        "limitations": [
            "2024 ranks thresholds; 2025 and 2026 are frozen checks",
            "2026 is a partial year",
            "final odds do not prove seven-minute execution prices",
            "pedigree and training enrichment is evaluated separately",
        ],
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    oos.to_csv(args.predictions, index=False)
    print(
        args.market, "rows", len(frame), "features", len(structural_features),
        "confirmed", len(confirmed), "saved", args.output,
    )


if __name__ == "__main__":
    main()
