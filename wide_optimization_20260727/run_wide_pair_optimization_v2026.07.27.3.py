"""Build and evaluate OOS wide-pair probability strategies.

Existing horse-level p_win/p_place OOS predictions are inputs. Pair models are
trained only on earlier years and calibrated inside the training period.
Purchase-time wide odds are unavailable, so no payout-derived EV selects bets.
Version: v2026.07.27.3
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


VERSION = "v2026.07.27.3"
FEATURES = [
    "a_p_win", "b_p_win", "a_p_place", "b_p_place",
    "place_product", "place_sum", "place_min", "place_max", "place_gap",
    "win_product", "win_sum", "win_gap", "rank_gap", "pop_sum", "pop_gap",
    "field_size", "race_top1_place", "race_top2_place", "race_place_gap",
    "race_place_std", "race_win_entropy", "hole_rank", "axis_rank",
]


def normalized_entropy(values: pd.Series) -> float:
    probabilities = values.clip(lower=1e-12).to_numpy(dtype=float).copy()
    probabilities /= probabilities.sum()
    value = -float(np.sum(probabilities * np.log(probabilities)))
    return value / np.log(len(probabilities)) if len(probabilities) > 1 else 0.0


def load_payouts(db: Path) -> dict[tuple[str, str], float]:
    with sqlite3.connect(db) as connection:
        payout = pd.read_sql_query(
            "SELECT race_id, comb, payout FROM payouts WHERE bet_type='wide'",
            connection,
        )
    return {
        (str(row.race_id), str(row.comb)): float(row.payout)
        for row in payout.itertuples()
    }


def pair_key(a: int, b: int) -> str:
    return "-".join(map(str, sorted((int(a), int(b)))))


def build_pairs(oos: Path, db: Path, market: str) -> pd.DataFrame:
    horses = pd.read_csv(oos, parse_dates=["date"])
    horses["race_id"] = horses["race_id"].astype(str)
    payouts = load_payouts(db)
    covered = {race_id for race_id, _comb in payouts}
    rows = []
    for race_id, race in horses.groupby("race_id", sort=False):
        race_id = str(race_id)
        if race_id not in covered:
            continue
        race = race.copy()
        race["win_axis_rank"] = race["p_win"].rank(
            method="first", ascending=False
        )
        race["place_axis_rank"] = race["p_place"].rank(
            method="first", ascending=False
        )
        holes = race[race["win_odds"].ge(10)].sort_values(
            ["p_place", "umaban"], ascending=[False, True]
        ).head(3).copy()
        holes["hole_rank"] = np.arange(1, len(holes) + 1)
        win_axes = race[race["win_axis_rank"].le(2)].copy()
        place_axes = race[race["place_axis_rank"].le(2)].copy()
        top_place = race.sort_values(
            ["p_place", "umaban"], ascending=[False, True]
        ).head(2)
        race_top1_place = float(top_place.iloc[0]["p_place"])
        race_top2_place = float(top_place.iloc[-1]["p_place"])
        race_context = {
            "field_size": int(race.iloc[0]["field_size"]),
            "race_top1_place": race_top1_place,
            "race_top2_place": race_top2_place,
            "race_place_gap": race_top1_place - race_top2_place,
            "race_place_std": float(race["p_place"].std(ddof=0)),
            "race_win_entropy": normalized_entropy(race["p_win"]),
        }
        for axis_source, axes, rank_column in (
            ("win", win_axes, "win_axis_rank"),
            ("place", place_axes, "place_axis_rank"),
        ):
            for axis in axes.itertuples():
                for hole in holes.itertuples():
                    if int(axis.umaban) == int(hole.umaban):
                        continue
                    a, b = sorted((int(axis.umaban), int(hole.umaban)))
                    first = race.loc[race["umaban"].eq(a)].iloc[0]
                    second = race.loc[race["umaban"].eq(b)].iloc[0]
                    comb = pair_key(a, b)
                    returned = payouts.get((race_id, comb), 0.0)
                    rows.append({
                        "market": market, "race_id": race_id,
                        "date": axis.date, "year": int(axis.date.year),
                        "venue": axis.venue, "axis_source": axis_source,
                        "axis_rank": int(getattr(axis, rank_column)),
                        "hole_rank": int(hole.hole_rank),
                        "horse_a": a, "horse_b": b, "comb": comb,
                        "a_p_win": float(first.p_win),
                        "b_p_win": float(second.p_win),
                        "a_p_place": float(first.p_place),
                        "b_p_place": float(second.p_place),
                        "place_product": float(first.p_place * second.p_place),
                        "place_sum": float(first.p_place + second.p_place),
                        "place_min": float(min(first.p_place, second.p_place)),
                        "place_max": float(max(first.p_place, second.p_place)),
                        "place_gap": float(abs(first.p_place - second.p_place)),
                        "win_product": float(first.p_win * second.p_win),
                        "win_sum": float(first.p_win + second.p_win),
                        "win_gap": float(abs(first.p_win - second.p_win)),
                        "rank_gap": float(abs(
                            first.place_axis_rank - second.place_axis_rank
                        )),
                        "pop_sum": float(first.popularity + second.popularity),
                        "pop_gap": float(abs(first.popularity - second.popularity)),
                        **race_context,
                        "target_wide_hit": int(returned > 0),
                        "return": returned,
                        "purchase_wide_odds": np.nan,
                        "wide_ev": np.nan,
                    })
    return pd.DataFrame(rows).drop_duplicates(
        ["race_id", "axis_source", "axis_rank", "hole_rank", "comb"]
    )


def ece(y: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    frame = pd.DataFrame({"y": y, "p": probability})
    frame["bin"] = pd.cut(frame["p"], np.linspace(0, 1, bins + 1),
                          include_lowest=True)
    total = len(frame)
    return float(sum(
        len(group) / total * abs(group["y"].mean() - group["p"].mean())
        for _key, group in frame.groupby("bin", observed=True)
    ))


def probability_metrics(y: np.ndarray, probability: np.ndarray) -> dict:
    clipped = np.clip(probability, 1e-6, 1 - 1e-6)
    return {
        "rows": int(len(y)),
        "hits": int(y.sum()),
        "logloss": float(log_loss(y, clipped)),
        "brier": float(brier_score_loss(y, clipped)),
        "auc": float(roc_auc_score(y, clipped)) if len(np.unique(y)) > 1 else None,
        "ece10": ece(y, clipped),
    }


def betting_metrics(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"bets": 0, "races": 0, "hits": 0, "roi": 0.0}
    returns = frame["return"].to_numpy(dtype=float)
    total = float(returns.sum())
    dates = frame.sort_values(["date", "race_id"]).copy()
    dates["profit"] = dates["return"] - 100.0
    cumulative = dates["profit"].cumsum()
    drawdown = cumulative.cummax() - cumulative
    return {
        "bets": int(len(frame)),
        "races": int(frame["race_id"].nunique()),
        "bets_per_race": float(len(frame) / frame["race_id"].nunique()),
        "hits": int((returns > 0).sum()),
        "hit_rate": float((returns > 0).mean() * 100),
        "investment": float(len(frame) * 100),
        "return_total": total,
        "profit": float(total - len(frame) * 100),
        "roi": float(total / len(frame)),
        "median_hit_payout": float(
            np.median(returns[returns > 0]) if (returns > 0).any() else 0
        ),
        "max_payout": float(returns.max()),
        "roi_without_max": float((total - returns.max()) / len(frame)),
        "max_payout_share": float(returns.max() / total) if total else None,
        "max_drawdown": float(drawdown.max()) if len(drawdown) else 0.0,
    }


def fit_predict(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    ordered = train.sort_values(["date", "race_id"])
    cutoff = ordered["date"].quantile(.80)
    fit = ordered[ordered["date"].lt(cutoff)]
    calibration = ordered[ordered["date"].ge(cutoff)]
    if fit["target_wide_hit"].nunique() < 2 or calibration.empty:
        raise RuntimeError("Insufficient pair calibration data")
    x_fit = fit[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    x_cal = calibration[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    x_test = test[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    y_fit = fit["target_wide_hit"].to_numpy(dtype=int)
    y_cal = calibration["target_wide_hit"].to_numpy(dtype=int)
    y_test = test["target_wide_hit"].to_numpy(dtype=int)
    models = {
        "logistic": make_pipeline(
            StandardScaler(),
            LogisticRegression(C=.5, max_iter=500, class_weight=None),
        ),
        "hist_gb": HistGradientBoostingClassifier(
            max_iter=160, learning_rate=.04, max_leaf_nodes=15,
            min_samples_leaf=100, l2_regularization=3, random_state=20260727,
        ),
    }
    output = test.copy()
    diagnostics = {}
    independent_calibrator = IsotonicRegression(
        out_of_bounds="clip", y_min=.001, y_max=.999
    ).fit(calibration["place_product"], y_cal)
    output["prob_independent"] = independent_calibrator.predict(
        test["place_product"]
    )
    diagnostics["independent"] = probability_metrics(
        y_test, output["prob_independent"].to_numpy()
    )
    calibration_scores = {}
    for name, model in models.items():
        model.fit(x_fit, y_fit)
        raw_cal = model.predict_proba(x_cal)[:, 1]
        calibrator = IsotonicRegression(
            out_of_bounds="clip", y_min=.001, y_max=.999
        ).fit(raw_cal, y_cal)
        raw_test = model.predict_proba(x_test)[:, 1]
        output[f"prob_{name}"] = calibrator.predict(raw_test)
        diagnostics[name] = probability_metrics(
            y_test, output[f"prob_{name}"].to_numpy()
        )
        calibration_scores[name] = brier_score_loss(
            y_cal, calibrator.predict(raw_cal)
        )
    winner = min(calibration_scores, key=calibration_scores.get)
    output["pred_wide_hit_probability"] = output[f"prob_{winner}"]
    diagnostics["selected_model"] = winner
    diagnostics["purchase_wide_odds_available"] = False
    return output, diagnostics


def top_k(frame: pd.DataFrame, k: int) -> pd.DataFrame:
    return (
        frame.sort_values(
            ["race_id", "pred_wide_hit_probability", "comb"],
            ascending=[True, False, True],
        )
        .groupby("race_id", sort=False)
        .head(k)
    )


def pattern_report(frame: pd.DataFrame) -> list[dict]:
    rows = []
    current = frame[frame["axis_source"].eq("win")]
    for (axis_rank, hole_rank), group in current.groupby(
        ["axis_rank", "hole_rank"], sort=True
    ):
        metric = betting_metrics(group)
        rows.append({
            "axis_rank": int(axis_rank), "hole_rank": int(hole_rank), **metric
        })
    return rows


def strategy_report(test: pd.DataFrame) -> dict:
    current = test[test["axis_source"].eq("win")]
    place = test[test["axis_source"].eq("place")]
    strategies = {
        "current_win_axis_max6": current,
        "place_axis1_max3": place[place["axis_rank"].eq(1)],
        "place_pair_probability_top1": top_k(place, 1),
        "place_pair_probability_top2": top_k(place, 2),
        "place_pair_probability_top3": top_k(place, 3),
    }
    return {name: betting_metrics(group) for name, group in strategies.items()}


def process_market(
    market: str, oos: Path, db: Path, output: Path
) -> dict:
    pairs = build_pairs(oos, db, market)
    pair_predictions = []
    fold_reports = []
    test_years = sorted(pairs["year"].unique())
    for year in test_years:
        train = pairs[pairs["year"].lt(year)]
        test = pairs[pairs["year"].eq(year)]
        if train.empty or test.empty:
            continue
        predicted, probability = fit_predict(train, test)
        pair_predictions.append(predicted)
        fold_reports.append({
            "year": int(year),
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "probability": probability,
            "six_patterns": pattern_report(predicted),
            "strategies": strategy_report(predicted),
        })
    predictions = (
        pd.concat(pair_predictions, ignore_index=True)
        if pair_predictions else pairs.iloc[0:0].copy()
    )
    output.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(output / f"{market}_wide_pair_dataset.csv.gz", index=False)
    predictions.to_csv(
        output / f"{market}_wide_pair_oos_predictions.csv.gz", index=False
    )
    excluded = []
    for year, fold in predictions.groupby("year"):
        place = fold[fold["axis_source"].eq("place")]
        selected = set(
            zip(
                top_k(place, 3)["race_id"],
                top_k(place, 3)["comb"],
            )
        )
        current = fold[fold["axis_source"].eq("win")]
        rejected = current[
            ~current.apply(lambda row: (row.race_id, row.comb) in selected, axis=1)
        ].copy()
        rejected["current_strategy_bet"] = True
        rejected["exclude_reason"] = "outside calibrated pair-probability top3"
        rejected["result"] = rejected["target_wide_hit"]
        rejected["payout"] = rejected["return"]
        excluded.append(rejected)
    if excluded:
        pd.concat(excluded, ignore_index=True).to_csv(
            output / f"{market}_excluded_bets.csv.gz", index=False
        )
    return {
        "market": market,
        "pair_rows": int(len(pairs)),
        "folds": fold_reports,
        "limitations": [
            "Historical purchase-time wide odds are unavailable.",
            "EV threshold strategies are not reported as executable backtests.",
            "Candidate longshots reproduce the current final-win-odds>=10 baseline.",
            "Pair-model OOS begins one year after horse-level OOS predictions.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jra-oos", type=Path, required=True)
    parser.add_argument("--jra-db", type=Path, required=True)
    parser.add_argument("--local-oos", type=Path, required=True)
    parser.add_argument("--local-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--markets", nargs="+", choices=("jra", "local"),
        default=("jra", "local"),
    )
    args = parser.parse_args()
    market_arguments = {
        "jra": (args.jra_oos, args.jra_db),
        "local": (args.local_oos, args.local_db),
    }
    report = {
        "version": VERSION,
        "wide_ev_status": "UNAVAILABLE_NO_PURCHASE_TIME_WIDE_ODDS",
        "markets": [
            process_market(market, *market_arguments[market], args.output)
            for market in args.markets
        ],
    }
    suffix = "_".join(args.markets)
    (args.output / f"strategy_comparison_{suffix}_v2026.07.27.3.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
