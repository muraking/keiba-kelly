"""Validate LambdaRank, calibrated rank probability, and finish roles.

Version: v2026.07.26.3
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRanker
from scipy.optimize import minimize_scalar
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.metrics import log_loss, mean_absolute_error, roc_auc_score


VERSION = "v2026.07.26.3"
EXCLUDE = {
    "race_id", "date", "venue", "horse_id", "is_win", "is_place",
    "win_odds", "popularity", "tan_payout", "place_payout", "finish_pos",
    "is_iruka", "obstacle_time",
}


def load(path: Path) -> pd.DataFrame:
    with sqlite3.connect(path) as connection:
        frame = pd.read_sql_query("SELECT * FROM features", connection)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in frame.columns:
        if column not in {"race_id", "date", "venue", "horse_id"}:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame[
        frame["date"].notna()
        & frame["finish_pos"].gt(0)
        & frame["field_size"].gt(1)
        & frame["win_odds"].gt(1)
    ].copy()
    frame["race_id"] = frame["race_id"].astype(str)
    frame["relative_finish"] = (
        (frame["finish_pos"] - 1) / (frame["field_size"] - 1)
    ).clip(0, 1)
    frame["is_top2"] = frame["finish_pos"].le(2).astype(int)
    return frame


def matrices(train: pd.DataFrame, test: pd.DataFrame, features: list[str]):
    train_x = train[features].replace([np.inf, -np.inf], np.nan)
    test_x = test[features].replace([np.inf, -np.inf], np.nan)
    medians = train_x.median().fillna(0)
    return (
        train_x.fillna(medians).astype(np.float32),
        test_x.fillna(medians).astype(np.float32),
    )


def classifier() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        learning_rate=0.055, max_iter=180, max_leaf_nodes=31,
        min_samples_leaf=80, l2_regularization=2.0,
        random_state=20260726,
    )


def ranker() -> LGBMRanker:
    return LGBMRanker(
        objective="lambdarank", n_estimators=240, learning_rate=0.04,
        num_leaves=31, min_child_samples=80, reg_lambda=2.0,
        random_state=20260726, verbosity=-1,
    )


def race_softmax(scores: np.ndarray, race_ids: pd.Series, temperature: float):
    scaled = pd.Series(scores / temperature, index=race_ids.index)
    scaled -= scaled.groupby(race_ids).transform("max")
    exponent = np.exp(scaled)
    return (exponent / exponent.groupby(race_ids).transform("sum")).to_numpy()


def fit_temperature(scores: np.ndarray, race_ids: pd.Series, target: np.ndarray):
    result = minimize_scalar(
        lambda value: log_loss(
            target, np.clip(race_softmax(scores, race_ids, value), 1e-8, 1 - 1e-8)
        ),
        bounds=(0.05, 10.0), method="bounded",
    )
    return float(result.x)


def add_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["rank_model"] = output.groupby("race_id")["rank_score"].rank(
        method="first", ascending=False
    )
    output["rank_win"] = output.groupby("race_id")["p_win"].rank(
        method="first", ascending=False
    )
    output["rank_place"] = output.groupby("race_id")["p_place"].rank(
        method="first", ascending=False
    )
    output["rank_market"] = output.groupby("race_id")["win_odds"].rank(
        method="first", ascending=True
    )
    output["uplift_model"] = output["rank_market"] - output["rank_model"]
    output["uplift_win"] = output["rank_market"] - output["rank_win"]
    output["uplift_place"] = output["rank_market"] - output["rank_place"]
    return output


def summary(frame: pd.DataFrame, mask: pd.Series, bet_type: str) -> dict:
    selected = frame[mask]
    if selected.empty:
        return {"bets": 0, "hits": 0, "roi": 0.0, "lcb90": -999.0}
    if bet_type == "win":
        hit = selected["is_win"].astype(int).to_numpy()
        payout = selected["tan_payout"].fillna(0).to_numpy()
    else:
        hit = selected["is_place"].astype(int).to_numpy()
        payout = selected["place_payout"].fillna(0).to_numpy()
    returns = np.where(hit == 1, payout, 0.0)
    units = returns / 100
    se = float(units.std(ddof=1) / np.sqrt(len(units))) if len(units) > 1 else 999
    total = float(returns.sum())
    return {
        "bets": len(selected),
        "hits": int(hit.sum()),
        "hit_rate": float(hit.mean() * 100),
        "roi": float(total / (len(selected) * 100) * 100),
        "lcb90": float(units.mean() - 1.2816 * se),
        "max_payout_share": float(returns.max() / total) if total else None,
        "avg_popularity": float(selected["popularity"].mean()),
        "avg_odds": float(selected["win_odds"].mean()),
    }


def make_rules() -> list[dict]:
    rules = []
    for role, rank_column, uplift_column, bet_type in (
        ("rank", "rank_model", "uplift_model", "win"),
        ("win", "rank_win", "uplift_win", "win"),
        ("place", "rank_place", "uplift_place", "place"),
    ):
        for rank_max in (1, 2, 3):
            for uplift_min in (2, 3, 4, 5):
                for odds_low, odds_high in ((4, 10), (6, 15), (10, 30), (15, 80), (4, 80)):
                    rules.append({
                        "role": role, "rank_column": rank_column,
                        "uplift_column": uplift_column, "bet_type": bet_type,
                        "rank_max": rank_max, "uplift_min": uplift_min,
                        "odds_low": odds_low, "odds_high": odds_high,
                    })
    return rules


def mask(frame: pd.DataFrame, rule: dict) -> pd.Series:
    return (
        frame[rule["rank_column"]].le(rule["rank_max"])
        & frame[rule["uplift_column"]].ge(rule["uplift_min"])
        & frame["win_odds"].between(rule["odds_low"], rule["odds_high"])
        & frame["popularity"].ge(3)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-db", type=Path, required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frame = load(args.features_db)
    features = [
        column for column in frame.columns
        if column not in EXCLUDE
        and column not in {"relative_finish", "is_top2"}
        and pd.api.types.is_numeric_dtype(frame[column])
    ]
    predictions = []
    folds = []
    for year in (2024, 2025, 2026):
        train = frame[frame["date"].dt.year < year].sort_values(
            ["race_id", "umaban"]
        ).copy()
        test = frame[frame["date"].dt.year == year].sort_values(
            ["race_id", "umaban"]
        ).copy()
        if train.empty or test.empty:
            continue
        train_x, test_x = matrices(train, test, features)
        rank_model = ranker()
        win_model = classifier()
        place_model = classifier()
        relevance = (
            train["field_size"] - train["finish_pos"]
        ).clip(lower=0).astype(int)
        groups = train.groupby("race_id", sort=False).size().to_numpy()
        rank_model.fit(train_x, relevance, group=groups)
        win_model.fit(train_x, train["is_win"].astype(int))
        place_model.fit(train_x, train["is_place"].astype(int))
        test["rank_score"] = rank_model.predict(test_x)
        calibration_year = int(train["date"].dt.year.max())
        calibration = train["date"].dt.year.eq(calibration_year)
        calibration_train = ~calibration
        if not calibration_train.any():
            cutoff = train["date"].quantile(0.80)
            calibration = train["date"].ge(cutoff)
            calibration_train = ~calibration
        calibration_model = ranker()
        calibration_groups = train.loc[calibration_train].groupby(
            "race_id", sort=False
        ).size().to_numpy()
        calibration_model.fit(
            train_x[calibration_train],
            relevance[calibration_train],
            group=calibration_groups,
        )
        calibration_scores = calibration_model.predict(train_x[calibration])
        temperature = fit_temperature(
            calibration_scores,
            train.loc[calibration, "race_id"],
            train.loc[calibration, "is_win"].astype(int).to_numpy(),
        )
        test["rank_to_win_probability"] = race_softmax(
            test["rank_score"].to_numpy(), test["race_id"], temperature
        )
        test["p_win"] = win_model.predict_proba(test_x)[:, 1]
        test["p_place"] = place_model.predict_proba(test_x)[:, 1]
        test = add_ranks(test)
        folds.append({
            "year": year,
            "rows": len(test),
            "mean_absolute_rank_error": float(mean_absolute_error(
                test["finish_pos"], test["rank_model"]
            )),
            "win_auc": float(roc_auc_score(test["is_win"], test["p_win"])),
            "place_auc": float(roc_auc_score(test["is_place"], test["p_place"])),
            "win_logloss": float(log_loss(test["is_win"], test["p_win"])),
            "place_logloss": float(log_loss(test["is_place"], test["p_place"])),
            "rank_temperature": temperature,
            "rank_probability_logloss": float(log_loss(
                test["is_win"], test["rank_to_win_probability"]
            )),
            "model_top1_win_rate": float(
                test.loc[test["rank_model"].eq(1), "is_win"].mean() * 100
            ),
            "market_top1_win_rate": float(
                test.loc[test["rank_market"].eq(1), "is_win"].mean() * 100
            ),
        })
        predictions.append(test)
    oos = pd.concat(predictions, ignore_index=True)
    evaluated = []
    for rule in make_rules():
        periods = {
            str(year): summary(
                subset := oos[oos["date"].dt.year.eq(year)],
                mask(subset, rule), rule["bet_type"],
            )
            for year in (2024, 2025, 2026)
        }
        evaluated.append({**rule, "periods": periods})
    discovery = sorted(
        [rule for rule in evaluated if rule["periods"]["2024"]["bets"] >= 100],
        key=lambda rule: (
            rule["periods"]["2024"]["lcb90"],
            rule["periods"]["2024"]["roi"],
        ),
        reverse=True,
    )
    confirmed = [
        rule for rule in discovery
        if all(rule["periods"][str(year)]["roi"] >= 100 for year in (2024, 2025, 2026))
        and rule["periods"]["2025"]["bets"] >= 100
        and rule["periods"]["2026"]["bets"] >= 50
        and rule["periods"]["2025"]["max_payout_share"] is not None
        and rule["periods"]["2025"]["max_payout_share"] <= 0.20
    ]
    report = {
        "version": VERSION, "market": args.market, "rows": len(frame),
        "features": features, "folds": folds, "rules_tested": len(evaluated),
        "confirmed_rules": confirmed, "top_2024_discovery": discovery[:30],
        "limitations": [
            "place payout represents show/place return, not wide tickets",
            "2024 ranks rules; 2025 and 2026 are frozen checks",
            "2026 is partial",
        ],
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(args.market, "rows", len(frame), "rules", len(evaluated), "confirmed", len(confirmed))


if __name__ == "__main__":
    main()
