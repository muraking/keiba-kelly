"""Compare the JRA baseline with leakage-safe pedigree/training features.

Training features use only pre-race workout fields. The scraped result field is
never used. Pedigree rates are expanding statistics shifted by one row, so only
results known before each race contribute.

Version: v2026.07.24.4
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import walkforward_market_edge as base


VERSION = "v2026.07.24.4"


def workout_features(training_path: Path) -> pd.DataFrame:
    source = json.loads(training_path.read_text(encoding="utf-8"))
    rows = []
    positive = ("絶好", "抜群", "上々", "良化", "好気配", "好調", "鋭")
    negative = ("良化薄", "平行線", "一息", "重い", "遅れ", "不安")
    for horse_id, races in source.items():
        for race in races:
            works = race.get("works") or []
            last1f = [
                float(work["last1f"]) for work in works
                if work.get("last1f") is not None
                and 8.0 <= float(work["last1f"]) <= 20.0
            ]
            grades = [str(work.get("grade") or "") for work in works]
            courses = [str(work.get("course") or "") for work in works]
            loads = [str(work.get("load") or "") for work in works]
            evals = [str(work.get("eval") or "") for work in works]
            rows.append({
                "race_id": str(race.get("race_id") or ""),
                "horse_id": str(horse_id),
                "tr_available": 1.0,
                "tr_n_works": float(len(works)),
                "tr_last1f_min": min(last1f) if last1f else np.nan,
                "tr_last1f_mean": np.mean(last1f) if last1f else np.nan,
                "tr_last1f_std": np.std(last1f) if len(last1f) > 1 else np.nan,
                "tr_fast_n_max": float(max(
                    (int(work.get("fast_n") or 0) for work in works),
                    default=0,
                )),
                "tr_grade_a_share": (
                    sum(grade == "A" for grade in grades) / len(grades)
                    if grades else 0.0
                ),
                "tr_grade_b_share": (
                    sum(grade == "B" for grade in grades) / len(grades)
                    if grades else 0.0
                ),
                "tr_course_saka_share": (
                    sum("坂" in course for course in courses) / len(courses)
                    if courses else 0.0
                ),
                "tr_course_cw_share": (
                    sum("ＣＷ" in course or "CW" in course for course in courses)
                    / len(courses) if courses else 0.0
                ),
                "tr_hard_share": (
                    sum(any(word in load for word in ("一杯", "強め", "仕掛"))
                        for load in loads) / len(loads)
                    if loads else 0.0
                ),
                "tr_eval_positive_share": (
                    sum(any(word in value for word in positive) for value in evals)
                    / len(evals) if evals else 0.0
                ),
                "tr_eval_negative_share": (
                    sum(any(word in value for word in negative) for value in evals)
                    / len(evals) if evals else 0.0
                ),
                "tr_heisou_share": (
                    sum(bool(str(work.get("heisou") or "")) for work in works)
                    / len(works) if works else 0.0
                ),
            })
    return pd.DataFrame(rows).drop_duplicates(["race_id", "horse_id"], keep="last")


def add_expanding_rate(
    df: pd.DataFrame, group_col: str, prefix: str
) -> pd.DataFrame:
    # Aggregate first so every horse in the same race receives exactly the
    # same prior statistics; no horse can see another runner's current result.
    events = (
        df.assign(_starts=1.0)
        .groupby([group_col, "date", "race_id"], dropna=False, as_index=False)
        .agg(
            _starts=("_starts", "sum"),
            _wins=("is_win", "sum"),
            _places=("is_place", "sum"),
        )
        .sort_values(["date", "race_id"])
    )
    grouped = events.groupby(group_col, dropna=False)
    events[f"{prefix}_prior_n"] = (
        grouped["_starts"].cumsum() - events["_starts"]
    )
    prior_win = grouped["_wins"].cumsum() - events["_wins"]
    prior_place = grouped["_places"].cumsum() - events["_places"]
    prior_n = events[f"{prefix}_prior_n"]
    events[f"{prefix}_winrate"] = (prior_win + 2.0) / (prior_n + 20.0)
    events[f"{prefix}_placerate"] = (prior_place + 6.0) / (prior_n + 20.0)
    columns = [
        group_col, "date", "race_id", f"{prefix}_prior_n",
        f"{prefix}_winrate", f"{prefix}_placerate",
    ]
    return df.merge(
        events[columns],
        on=[group_col, "date", "race_id"],
        how="left",
        validate="many_to_one",
    )


def augment(
    df: pd.DataFrame, pedigree_path: Path, training_path: Path
) -> tuple[pd.DataFrame, dict]:
    pedigree = json.loads(pedigree_path.read_text(encoding="utf-8"))
    father = {
        str(horse_id): str(value.get("father") or "").split(" ")[0]
        for horse_id, value in pedigree.items()
    }
    mother_father = {
        str(horse_id): str(value.get("mother_father") or "").split(" ")[0]
        for horse_id, value in pedigree.items()
    }
    result = df.copy()
    result["ped_father"] = result["horse_id"].astype(str).map(father).fillna("UNKNOWN")
    result["ped_mother_father"] = (
        result["horse_id"].astype(str).map(mother_father).fillna("UNKNOWN")
    )
    result["ped_available"] = (result["ped_father"] != "UNKNOWN").astype(float)
    result = add_expanding_rate(result, "ped_father", "sire")
    result = add_expanding_rate(result, "ped_mother_father", "bms")
    result = result.drop(columns=["ped_father", "ped_mother_father"])

    workouts = workout_features(training_path)
    result["race_id"] = result["race_id"].astype(str)
    result["horse_id"] = result["horse_id"].astype(str)
    result = result.merge(
        workouts, on=["race_id", "horse_id"], how="left", validate="one_to_one"
    )
    result["tr_available"] = result["tr_available"].fillna(0.0)
    info = {
        "rows": int(len(result)),
        "pedigree_coverage": float(result["ped_available"].mean()),
        "training_coverage": float(result["tr_available"].mean()),
        "training_records": int(len(workouts)),
    }
    return result, info


def feature_columns(df: pd.DataFrame) -> list[str]:
    # The structural model must be computable before odds exist. Market odds
    # are used only after prediction to measure the live market difference.
    drop = (
        base.ID_COLS
        | base.LABEL_COLS
        | base.EVAL_COLS
        | base.MARKET_DERIVED_COLS
    )
    return [
        col for col in df.columns
        if col not in drop
        and col not in {"p_market"}
        and pd.api.types.is_numeric_dtype(df[col])
    ]


def evaluate(
    df: pd.DataFrame, features: list[str], years: list[int]
) -> tuple[list[dict], pd.DataFrame]:
    folds, frames = [], []
    for year in years:
        frame, metrics = base.evaluate_fold(df, features, year)
        folds.append(metrics)
        frames.append(frame)
    return folds, pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--pedigree", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--oos-output", type=Path)
    parser.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    args = parser.parse_args()

    base.DATA = args.data_dir.resolve()
    raw = base.load("jra")
    baseline_features = feature_columns(raw)
    enhanced, coverage = augment(raw, args.pedigree, args.training)
    enhanced_features = feature_columns(enhanced)
    added = [col for col in enhanced_features if col not in baseline_features]

    pedigree_features = [
        col for col in enhanced_features
        if col in baseline_features
        or col.startswith(("ped_", "sire_", "bms_"))
    ]
    training_features = [
        col for col in enhanced_features
        if col in baseline_features or col.startswith("tr_")
    ]
    variants = {
        "baseline": (raw, baseline_features),
        "pedigree": (enhanced, pedigree_features),
        "training": (enhanced, training_features),
        "both": (enhanced, enhanced_features),
    }
    evaluated = {}
    oos_frames = {}
    for name, (frame, features) in variants.items():
        folds, oos = evaluate(frame, features, args.years)
        evaluated[name] = {
            "feature_count": len(features),
            "folds": folds,
            "danger": base.danger_report(oos),
            "strategies": base.strategy_report(oos),
        }
        oos_frames[name] = oos
    report = {
        "version": VERSION,
        "coverage": coverage,
        "baseline_feature_count": len(baseline_features),
        "enhanced_feature_count": len(enhanced_features),
        "added_features": added,
        "variants": evaluated,
        "limitations": [
            "training result fields are explicitly excluded",
            "pedigree rates use shifted expanding history only",
            "final odds are for research, not proof of live purchasability",
            "bet-rule discovery still requires untouched confirmation",
        ],
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.oos_output:
        columns = [
            "race_id", "date", "venue", "umaban", "horse_id",
            "popularity", "win_odds", "finish_pos", "is_win",
            "tan_payout", "place_payout", "p_market", "p_struct",
            "p_combo", "delta", "danger", "danger_pct", "ev_combo",
        ]
        oos_frames["both"].loc[:, columns].to_csv(
            args.oos_output, index=False, date_format="%Y-%m-%d"
        )
    print(
        f"version={VERSION} rows={coverage['rows']:,} "
        f"ped={coverage['pedigree_coverage']:.3%} "
        f"training={coverage['training_coverage']:.3%} "
        f"features={len(baseline_features)}->{len(enhanced_features)}"
    )
    for index, year in enumerate(args.years):
        values = " ".join(
            f"{name}={evaluated[name]['folds'][index]['combo_logloss']:.6f}"
            for name in variants
        )
        market = evaluated["baseline"]["folds"][index]["market_logloss"]
        print(f"{year}: market={market:.6f} {values}")


if __name__ == "__main__":
    main()
