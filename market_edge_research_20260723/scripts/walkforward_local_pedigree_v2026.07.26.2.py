"""Compare the local baseline with leakage-safe pedigree suitability features.

Every pedigree statistic is an expanding aggregate shifted at race granularity,
so a runner sees only results known before its own race.

Version: v2026.07.26.2
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import walkforward_market_edge as base


VERSION = "v2026.07.26.2"


def load_local(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "features_local.sqlite"
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
        available = pd.read_sql_query(
            "PRAGMA table_info(features)", connection
        )["name"].tolist()
        columns = [column for column in available if column != "venue"]
        chunks = []
        for chunk in pd.read_sql_query(
            f"SELECT {','.join(columns)} FROM features",
            connection,
            parse_dates=["date"],
            chunksize=75_000,
        ):
            for column in chunk.columns:
                if column not in {"race_id", "date", "horse_id"}:
                    chunk[column] = pd.to_numeric(
                        chunk[column], errors="coerce", downcast="float"
                    )
            chunks.append(chunk)
    frame = pd.concat(chunks, ignore_index=True)
    del chunks
    frame = frame[
        (frame["win_odds"] > 0)
        & frame["is_win"].notna()
        & frame["tan_payout"].notna().groupby(frame["race_id"]).transform("max")
    ].copy()
    inverse = 1.0 / frame["win_odds"].clip(lower=1.001)
    frame["overround"] = inverse.groupby(frame["race_id"]).transform("sum")
    frame["p_market"] = inverse / frame["overround"]
    frame["log_p_market"] = np.log(frame["p_market"].clip(1e-6))
    frame["market_rank"] = frame.groupby("race_id")["p_market"].rank(
        method="first", ascending=False
    )
    favorite = frame.groupby("race_id")["p_market"].transform("max")
    frame["market_gap"] = favorite - frame["p_market"]
    return frame.reset_index(drop=True)


def add_prior_year_rate(
    frame: pd.DataFrame, group_col: str, prefix: str,
) -> pd.DataFrame:
    years = frame["date"].dt.year
    prior_n = np.zeros(len(frame), dtype=np.float32)
    prior_wins = np.zeros(len(frame), dtype=np.float32)
    prior_places = np.zeros(len(frame), dtype=np.float32)
    for year in sorted(years.unique()):
        train = frame[years < year]
        mask = years == year
        if train.empty:
            continue
        aggregate = train.groupby(group_col, dropna=False).agg(
            n=("is_win", "size"),
            wins=("is_win", "sum"),
            places=("is_place", "sum"),
        )
        keys = frame.loc[mask, group_col]
        prior_n[mask] = keys.map(aggregate["n"]).fillna(0).to_numpy()
        prior_wins[mask] = keys.map(aggregate["wins"]).fillna(0).to_numpy()
        prior_places[mask] = keys.map(aggregate["places"]).fillna(0).to_numpy()
    frame[f"{prefix}_prior_n"] = prior_n
    frame[f"{prefix}_winrate"] = (prior_wins + 2.0) / (prior_n + 20.0)
    frame[f"{prefix}_placerate"] = (prior_places + 6.0) / (prior_n + 20.0)
    return frame


def pedigree_augment(frame: pd.DataFrame, pedigree_path: Path) -> tuple[pd.DataFrame, dict]:
    source = json.loads(pedigree_path.read_text(encoding="utf-8"))
    fields = {
        field: {
            str(horse_id): str(values.get(field) or "").split(" ")[0]
            for horse_id, values in source.items()
        }
        for field in ("father", "mother_father", "father_father")
    }
    result = frame.copy()
    horse_ids = result["horse_id"].astype(str)
    for field, mapping in fields.items():
        result[f"ped_{field}"] = horse_ids.map(mapping).fillna("UNKNOWN")
    result["ped_available"] = (
        result["ped_father"] != "UNKNOWN"
    ).astype(float)
    result["_dist_band"] = (
        pd.to_numeric(result["distance"], errors="coerce")
        .floordiv(200).mul(200).fillna(-1).astype(int).astype(str)
    )
    result["_surface"] = np.where(result["is_dirt"] == 1, "D", "T")
    result["_going"] = result["going_code"].fillna(-1).astype(str)
    result["_venue"] = result["venue_code"].fillna(-1).astype(str)
    result["ped_sire_venue"] = result["ped_father"] + "|" + result["_venue"]
    result["ped_sire_dist"] = result["ped_father"] + "|" + result["_dist_band"]
    result["ped_sire_surface"] = result["ped_father"] + "|" + result["_surface"]
    result["ped_sire_going"] = result["ped_father"] + "|" + result["_going"]
    groups = (
        ("ped_father", "sire"),
        ("ped_mother_father", "bms"),
        ("ped_father_father", "sireline"),
        ("ped_sire_venue", "sire_venue"),
        ("ped_sire_dist", "sire_dist"),
        ("ped_sire_surface", "sire_surface"),
        ("ped_sire_going", "sire_going"),
    )
    for group_col, prefix in groups:
        result = add_prior_year_rate(result, group_col, prefix)
    result = result.drop(
        columns=[
            "ped_father", "ped_mother_father", "ped_father_father",
            "ped_sire_venue", "ped_sire_dist", "ped_sire_surface",
            "ped_sire_going", "_dist_band", "_surface", "_going", "_venue",
        ]
    )
    return result, {
        "records": len(source),
        "coverage": float(result["ped_available"].mean()),
        "rate_groups": [prefix for _group, prefix in groups],
    }


def feature_columns(frame: pd.DataFrame) -> list[str]:
    drop = (
        base.ID_COLS | base.LABEL_COLS | base.EVAL_COLS
        | base.MARKET_DERIVED_COLS
    )
    return [
        column for column in frame.columns
        if column not in drop
        and column != "p_market"
        and pd.api.types.is_numeric_dtype(frame[column])
    ]


def structural_metrics(frame: pd.DataFrame) -> dict:
    y = frame["is_win"].astype(int).to_numpy()
    return {
        "logloss": float(log_loss(y, frame["p_struct"], labels=[0, 1])),
        "brier": float(brier_score_loss(y, frame["p_struct"])),
        "auc": float(roc_auc_score(y, frame["p_struct"])),
        "top": base.top_pick_metrics(frame, "p_struct"),
    }


def segment_metrics(
    baseline: pd.DataFrame, pedigree: pd.DataFrame,
) -> list[dict]:
    definitions = {
        "all": lambda values: pd.Series(True, index=values.index),
        "age_le_3": lambda values: values["age"] <= 3,
        "past_lt_3": lambda values: values["h_n_past"] < 3,
        "pop_1_3": lambda values: values["popularity"].between(1, 3),
        "pop_4_6": lambda values: values["popularity"].between(4, 6),
        "pop_7_plus": lambda values: values["popularity"] >= 7,
        "heavy_going": lambda values: values["going_code"] >= 2,
    }
    output = []
    for year in sorted(baseline["date"].dt.year.unique()):
        left_year = baseline[baseline["date"].dt.year == year]
        right_year = pedigree[pedigree["date"].dt.year == year]
        for name, selector in definitions.items():
            left = left_year[selector(left_year)]
            right = right_year[selector(right_year)]
            if len(left) < 100 or len(right) != len(left):
                continue
            left_metric = structural_metrics(left)
            right_metric = structural_metrics(right)
            output.append({
                "year": int(year),
                "segment": name,
                "rows": len(left),
                "baseline": left_metric,
                "pedigree": right_metric,
                "logloss_change_pct": (
                    (right_metric["logloss"] / left_metric["logloss"] - 1) * 100
                ),
                "brier_change_pct": (
                    (right_metric["brier"] / left_metric["brier"] - 1) * 100
                ),
            })
    return output


def evaluate(
    frame: pd.DataFrame, columns: list[str], years: list[int],
) -> tuple[list[dict], pd.DataFrame]:
    folds, outputs = [], []
    for year in years:
        prediction, metrics = base.evaluate_fold(frame, columns, year)
        metrics["structural"] = structural_metrics(prediction)
        folds.append(metrics)
        outputs.append(prediction)
    return folds, pd.concat(outputs, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--pedigree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--oos-output", type=Path)
    parser.add_argument("--years", nargs="+", type=int, default=[2024, 2025, 2026])
    args = parser.parse_args()
    base.DATA = args.data_dir.resolve()
    raw = load_local(args.data_dir.resolve())
    enhanced, coverage = pedigree_augment(raw, args.pedigree)
    baseline_columns = feature_columns(raw)
    pedigree_columns = feature_columns(enhanced)
    baseline_folds, baseline_oos = evaluate(raw, baseline_columns, args.years)
    pedigree_folds, pedigree_oos = evaluate(
        enhanced, pedigree_columns, args.years
    )
    report = {
        "version": VERSION,
        "coverage": coverage,
        "baseline_feature_count": len(baseline_columns),
        "pedigree_feature_count": len(pedigree_columns),
        "added_features": [
            column for column in pedigree_columns if column not in baseline_columns
        ],
        "baseline": {
            "folds": baseline_folds,
            "danger": base.danger_report(baseline_oos),
            "strategies": base.strategy_report(baseline_oos),
            "meta_strategy": base.meta_strategy_walkforward(baseline_oos),
        },
        "pedigree": {
            "folds": pedigree_folds,
            "danger": base.danger_report(pedigree_oos),
            "strategies": base.strategy_report(pedigree_oos),
            "meta_strategy": base.meta_strategy_walkforward(pedigree_oos),
        },
        "segments": segment_metrics(baseline_oos, pedigree_oos),
        "limitations": [
            "pedigree rates use prior calendar years only",
            "2026 is partial-year OOS",
            "final odds are research inputs, not live purchasability proof",
            "production model remains unchanged",
        ],
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.oos_output:
        export = pedigree_oos.copy()
        export.to_csv(args.oos_output, index=False)
    print(json.dumps({
        "version": VERSION,
        "coverage": coverage,
        "baseline_features": len(baseline_columns),
        "pedigree_features": len(pedigree_columns),
        "folds": {
            str(fold["year"]): fold["structural"] for fold in pedigree_folds
        },
    }, ensure_ascii=False, indent=2))
    print("saved", args.output)


if __name__ == "__main__":
    main()
