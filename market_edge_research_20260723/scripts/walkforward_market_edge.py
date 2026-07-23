#!/usr/bin/env python3
"""
市場オッズを基準に、構造化特徴量が追加情報を持つかを年次walk-forwardで検証する。

Version: v2026.07.23.5

重要:
- win_odds は最終オッズの可能性があるため、本検証のROIは「実購入可能性」ではなく
  市場残差の発見可能性を測る研究指標として扱う。
- 評価年のデータでモデル重みや閾値を選ばない。
- サーバーDBは使わず、PCへコピーした読み取り専用スナップショットだけを使う。
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


VERSION = "v2026.07.23.5"
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

ID_COLS = {"race_id", "date", "venue", "umaban", "horse_id"}
LABEL_COLS = {"is_win", "is_place"}
EVAL_COLS = {
    "win_odds",
    "popularity",
    "tan_payout",
    "place_payout",
    "finish_pos",
}
MARKET_DERIVED_COLS = {
    "overround",
    "log_p_market",
    "market_rank",
    "market_gap",
}


def load(tag: str) -> pd.DataFrame:
    path = DATA / f"features_{tag}.sqlite"
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    df = pd.read_sql_query("SELECT * FROM features", con, parse_dates=["date"])
    con.close()

    for col in df.columns:
        if col not in {"race_id", "date", "venue", "horse_id"}:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[
        (df["win_odds"] > 0)
        & df["is_win"].notna()
        & df["tan_payout"].notna().groupby(df["race_id"]).transform("max")
    ].copy()

    inv = 1.0 / df["win_odds"].clip(lower=1.001)
    df["overround"] = inv.groupby(df["race_id"]).transform("sum")
    df["p_market"] = inv / df["overround"]
    df["log_p_market"] = np.log(df["p_market"].clip(1e-6))
    df["market_rank"] = df.groupby("race_id")["p_market"].rank(
        method="first", ascending=False
    )
    fav = df.groupby("race_id")["p_market"].transform("max")
    df["market_gap"] = fav - df["p_market"]
    return df.reset_index(drop=True)


def normalize_by_race(raw: np.ndarray, race_id: pd.Series) -> np.ndarray:
    s = pd.Series(np.clip(raw, 1e-8, 1.0), index=race_id.index)
    den = s.groupby(race_id).transform("sum")
    return (s / den).to_numpy()


def combine(
    p_market: np.ndarray, p_model: np.ndarray, race_id: pd.Series, alpha: float
) -> np.ndarray:
    score = np.exp(
        (1.0 - alpha) * np.log(np.clip(p_market, 1e-8, 1.0))
        + alpha * np.log(np.clip(p_model, 1e-8, 1.0))
    )
    return normalize_by_race(score, race_id)


def make_model() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=220,
        max_leaf_nodes=31,
        min_samples_leaf=150,
        l2_regularization=5.0,
        random_state=20260723,
    )


def choose_alpha(
    train: pd.DataFrame, feature_cols: list[str]
) -> tuple[float, dict[str, float]]:
    dates = np.sort(train["date"].unique())
    cut = dates[max(1, int(len(dates) * 0.8))]
    fit = train[train["date"] < cut]
    val = train[train["date"] >= cut]

    model = make_model()
    model.fit(fit[feature_cols], fit["is_win"].astype(int))
    p_raw = model.predict_proba(val[feature_cols])[:, 1]
    p_model = normalize_by_race(p_raw, val["race_id"])
    y = val["is_win"].astype(int).to_numpy()

    losses: dict[str, float] = {}
    for alpha in np.linspace(0.0, 1.0, 11):
        p = combine(
            val["p_market"].to_numpy(), p_model, val["race_id"], float(alpha)
        )
        losses[f"{alpha:.1f}"] = float(log_loss(y, p, labels=[0, 1]))

    best = min(losses, key=losses.get)
    return float(best), losses


def top_pick_metrics(df: pd.DataFrame, prob_col: str) -> dict[str, float]:
    idx = df.groupby("race_id")[prob_col].idxmax()
    picks = df.loc[idx]
    returns = np.where(
        picks["is_win"].to_numpy() == 1,
        picks["tan_payout"].fillna(0).to_numpy(),
        0.0,
    )
    return {
        "bets": int(len(picks)),
        "hit_rate": float(picks["is_win"].mean()),
        "roi": float(returns.mean()),
    }


def ev_metrics(df: pd.DataFrame, threshold: float) -> dict[str, float]:
    bets = df[df["ev_combo"] >= threshold]
    if bets.empty:
        return {"bets": 0, "hit_rate": 0.0, "roi": 0.0}
    returns = np.where(
        bets["is_win"].to_numpy() == 1,
        bets["tan_payout"].fillna(0).to_numpy(),
        0.0,
    )
    return {
        "bets": int(len(bets)),
        "hit_rate": float(bets["is_win"].mean()),
        "roi": float(returns.mean()),
    }


def evaluate_fold(
    df: pd.DataFrame, feature_cols: list[str], test_year: int
) -> tuple[pd.DataFrame, dict]:
    train = df[df["date"].dt.year < test_year].copy()
    test = df[df["date"].dt.year == test_year].copy()
    if train.empty or test.empty:
        raise ValueError(f"{test_year}: train/test が不足")

    alpha, alpha_losses = choose_alpha(train, feature_cols)
    model = make_model()
    model.fit(train[feature_cols], train["is_win"].astype(int))
    p_raw = model.predict_proba(test[feature_cols])[:, 1]
    test["p_struct"] = normalize_by_race(p_raw, test["race_id"])
    test["p_combo"] = combine(
        test["p_market"].to_numpy(),
        test["p_struct"].to_numpy(),
        test["race_id"],
        alpha,
    )
    test["delta"] = test["p_combo"] - test["p_market"]
    test["danger"] = test["p_market"] - test["p_combo"]
    test["ev_combo"] = test["p_combo"] * test["win_odds"]

    # 危険度はfold内の1番人気だけで百分位化。閾値の絶対値を未来へ持ち込まない。
    fav_mask = test["popularity"] == 1
    test["danger_pct"] = np.nan
    if fav_mask.any():
        test.loc[fav_mask, "danger_pct"] = test.loc[fav_mask, "danger"].rank(
            pct=True, method="average"
        )

    y = test["is_win"].astype(int).to_numpy()
    result = {
        "year": test_year,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "alpha": alpha,
        "alpha_losses": alpha_losses,
        "market_logloss": float(log_loss(y, test["p_market"], labels=[0, 1])),
        "combo_logloss": float(log_loss(y, test["p_combo"], labels=[0, 1])),
        "market_brier": float(brier_score_loss(y, test["p_market"])),
        "combo_brier": float(brier_score_loss(y, test["p_combo"])),
        "market_auc": float(roc_auc_score(y, test["p_market"])),
        "combo_auc": float(roc_auc_score(y, test["p_combo"])),
        "top_market": top_pick_metrics(test, "p_market"),
        "top_combo": top_pick_metrics(test, "p_combo"),
        "ev": {
            f"{thr:.2f}": ev_metrics(test, thr)
            for thr in (1.00, 1.05, 1.10, 1.20)
        },
    }
    return test, result


def danger_report(oos: pd.DataFrame) -> list[dict]:
    fav = oos[oos["popularity"] == 1].copy()
    fav["bucket"] = pd.cut(
        fav["danger_pct"],
        bins=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        labels=["safe_1", "safe_2", "middle", "danger_2", "danger_1"],
        include_lowest=True,
    )
    rows = []
    for bucket, group in fav.groupby("bucket", observed=True):
        returns = np.where(
            group["is_win"].to_numpy() == 1,
            group["tan_payout"].fillna(0).to_numpy(),
            0.0,
        )
        rows.append(
            {
                "bucket": str(bucket),
                "bets": int(len(group)),
                "hit_rate": float(group["is_win"].mean()),
                "market_expected": float(group["p_market"].mean()),
                "residual": float(
                    group["is_win"].mean() - group["p_market"].mean()
                ),
                "roi": float(returns.mean()),
                "avg_odds": float(group["win_odds"].mean()),
            }
        )
    return rows


def flat_bet_stats(group: pd.DataFrame, bet_type: str = "win") -> dict[str, float]:
    if group.empty:
        return {
            "bets": 0,
            "hit_rate": 0.0,
            "roi": 0.0,
            "max_payout_share": 0.0,
            "max_drawdown_yen": 0.0,
        }
    if bet_type == "place":
        hit = group["is_place"].fillna(0).to_numpy() == 1
        payout = group["place_payout"].fillna(0).to_numpy()
    else:
        hit = group["is_win"].fillna(0).to_numpy() == 1
        payout = group["tan_payout"].fillna(0).to_numpy()
    returns = np.where(hit, payout, 0.0)
    ordered = group.assign(_return=returns).sort_values(["date", "race_id"])
    pnl = ordered["_return"].to_numpy() - 100.0
    equity = np.cumsum(pnl)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])[:-1]
    drawdown = peaks - equity
    total_return = float(returns.sum())
    return {
        "bets": int(len(group)),
        "hit_rate": float(hit.mean()),
        "roi": float(returns.mean()),
        "max_payout_share": (
            float(returns.max() / total_return) if total_return > 0 else 0.0
        ),
        "max_drawdown_yen": float(drawdown.max(initial=0.0)),
    }


def strategy_report(oos: pd.DataFrame) -> dict:
    fav = oos[oos["popularity"] == 1].copy()
    result: dict[str, dict] = {}

    for threshold in (0.2, 0.4, 0.6, 0.8):
        safe = fav[fav["danger_pct"] <= threshold]
        result[f"safe_favorite_pct_le_{threshold:.1f}"] = {
            "win": flat_bet_stats(safe, "win"),
            "place": flat_bet_stats(safe, "place"),
        }

    danger_fav = fav[fav["danger_pct"] >= 0.8]
    danger_races = set(danger_fav["race_id"])
    candidates = oos[
        oos["race_id"].isin(danger_races) & (oos["popularity"] != 1)
    ].copy()
    if not candidates.empty:
        selections = {
            "danger_race_market_second": candidates.loc[
                candidates.groupby("race_id")["p_market"].idxmax()
            ],
            "danger_race_combo_alt": candidates.loc[
                candidates.groupby("race_id")["p_combo"].idxmax()
            ],
            "danger_race_struct_alt": candidates.loc[
                candidates.groupby("race_id")["p_struct"].idxmax()
            ],
        }
        for name, picks in selections.items():
            result[name] = {
                "win": flat_bet_stats(picks, "win"),
                "place": flat_bet_stats(picks, "place"),
            }

    result["danger_favorite_pct_ge_0.8"] = {
        "win": flat_bet_stats(danger_fav, "win"),
        "place": flat_bet_stats(danger_fav, "place"),
    }
    return result


def _rule_candidates():
    rules = []
    for bet_type in ("win", "place"):
        for danger_max in (0.1, 0.2, 0.3, 0.4):
            for odds_min, odds_max, odds_name in (
                (1.0, 1000.0, "all"),
                (1.0, 1.8, "lt1.8"),
                (1.8, 2.5, "1.8-2.5"),
                (2.5, 1000.0, "ge2.5"),
            ):
                name = (
                    f"safe_fav_{bet_type}_d{danger_max:.1f}_odds_{odds_name}"
                )

                def selector(
                    df,
                    dm=danger_max,
                    omin=odds_min,
                    omax=odds_max,
                ):
                    return df[
                        (df["popularity"] == 1)
                        & (df["danger_pct"] <= dm)
                        & (df["win_odds"] >= omin)
                        & (df["win_odds"] < omax)
                    ]

                rules.append((name, bet_type, selector))

    for threshold in (1.00, 1.05, 1.10, 1.15, 1.20):
        for odds_max, odds_name in (
            (10.0, "lt10"),
            (20.0, "lt20"),
            (50.0, "lt50"),
            (1000.0, "all"),
        ):
            name = f"combo_ev_{threshold:.2f}_odds_{odds_name}"

            def selector(df, th=threshold, omax=odds_max):
                return df[
                    (df["ev_combo"] >= th)
                    & (df["win_odds"] < omax)
                ]

            rules.append((name, "win", selector))
    return rules


def _rule_score(group: pd.DataFrame, bet_type: str) -> dict[str, float]:
    if group.empty:
        return {"bets": 0, "roi": 0.0, "lcb90": -999.0}
    if bet_type == "place":
        returns = np.where(
            group["is_place"].fillna(0).to_numpy() == 1,
            group["place_payout"].fillna(0).to_numpy(),
            0.0,
        )
    else:
        returns = np.where(
            group["is_win"].fillna(0).to_numpy() == 1,
            group["tan_payout"].fillna(0).to_numpy(),
            0.0,
        )
    n = len(returns)
    roi = float(returns.mean())
    se = float(returns.std(ddof=1) / np.sqrt(n)) if n > 1 else 999.0
    return {"bets": int(n), "roi": roi, "lcb90": roi - 1.2816 * se}


def meta_strategy_walkforward(oos: pd.DataFrame) -> list[dict]:
    """過去年だけでルールを選び、翌年へ固定適用する。"""
    years = sorted(int(y) for y in oos["date"].dt.year.unique())
    rules = _rule_candidates()
    results = []
    for year in years[1:]:
        prior = oos[oos["date"].dt.year < year]
        test = oos[oos["date"].dt.year == year]
        ranked = []
        for name, bet_type, selector in rules:
            score = _rule_score(selector(prior), bet_type)
            if score["bets"] >= 300:
                ranked.append((score["lcb90"], name, bet_type, selector, score))
        if not ranked:
            continue
        ranked.sort(key=lambda x: x[0], reverse=True)
        _, name, bet_type, selector, train_score = ranked[0]
        test_group = selector(test)
        test_score = _rule_score(test_group, bet_type)
        results.append(
            {
                "test_year": year,
                "selected_rule": name,
                "bet_type": bet_type,
                "train": train_score,
                "decision": (
                    "BET" if train_score["lcb90"] > 100.0 else "NO_BET"
                ),
                "test": test_score,
            }
        )
    return results


def monthly_report(oos: pd.DataFrame) -> list[dict]:
    rows = []
    oos = oos.copy()
    oos["ym"] = oos["date"].dt.strftime("%Y-%m")
    for ym, group in oos.groupby("ym"):
        row = {"ym": ym}
        for threshold in (1.00, 1.05, 1.10):
            stats = ev_metrics(group, threshold)
            row[f"ev{threshold:.2f}_bets"] = stats["bets"]
            row[f"ev{threshold:.2f}_roi"] = stats["roi"]
        rows.append(row)
    return rows


def main() -> None:
    global DATA, REPORTS
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", choices=["local", "jra"], required=True)
    parser.add_argument("--years", nargs="+", type=int, default=[2024, 2025, 2026])
    parser.add_argument(
        "--variant",
        choices=["full", "struct", "market"],
        default="full",
        help="full=市場派生+競馬特徴、struct=競馬特徴のみ、market=市場派生のみ",
    )
    parser.add_argument(
        "--export-oos",
        action="store_true",
        help="完全OOSの馬単位予測をCSVへ保存する",
    )
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    args = parser.parse_args()

    DATA = args.data_dir.resolve()
    REPORTS = args.reports_dir.resolve()
    REPORTS.mkdir(exist_ok=True)
    df = load(args.tag)
    drop = ID_COLS | LABEL_COLS | EVAL_COLS
    all_numeric = [
        col
        for col in df.columns
        if col not in drop
        and col not in {"p_market"}
        and pd.api.types.is_numeric_dtype(df[col])
    ]
    if args.variant == "struct":
        feature_cols = [col for col in all_numeric if col not in MARKET_DERIVED_COLS]
    elif args.variant == "market":
        feature_cols = [col for col in all_numeric if col in MARKET_DERIVED_COLS]
    else:
        feature_cols = all_numeric

    fold_frames = []
    folds = []
    for year in args.years:
        print(f"[{args.tag}] fold {year} ...", flush=True)
        frame, result = evaluate_fold(df, feature_cols, year)
        fold_frames.append(frame)
        folds.append(result)
        print(
            f"  alpha={result['alpha']:.1f} "
            f"logloss market={result['market_logloss']:.6f} "
            f"combo={result['combo_logloss']:.6f}",
            flush=True,
        )

    oos = pd.concat(fold_frames, ignore_index=True)
    report = {
        "version": VERSION,
        "tag": args.tag,
        "variant": args.variant,
        "feature_count": len(feature_cols),
        "feature_columns": feature_cols,
        "folds": folds,
        "danger_favorite": danger_report(oos),
        "bet_strategies": strategy_report(oos),
        "meta_strategy_walkforward": meta_strategy_walkforward(oos),
        "monthly_ev": monthly_report(oos),
        "limitations": [
            "win_oddsが最終オッズの場合、ROIは購入可能性ではなく市場残差の研究指標",
            "調教・血統はこのbaselineには未統合",
            "EV閾値は事前固定で、評価結果を見て最適化していない",
        ],
    }
    out = REPORTS / (
        f"walkforward_market_edge_{args.tag}_{args.variant}_{VERSION[1:]}.json"
    )
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {out}")
    if args.export_oos:
        oos_columns = [
            "race_id",
            "date",
            "venue",
            "umaban",
            "horse_id",
            "popularity",
            "win_odds",
            "finish_pos",
            "is_win",
            "tan_payout",
            "place_payout",
            "p_market",
            "p_struct",
            "p_combo",
            "delta",
            "danger",
            "danger_pct",
            "ev_combo",
        ]
        oos_out = REPORTS / (
            f"oos_predictions_{args.tag}_{args.variant}_{VERSION[1:]}.csv"
        )
        oos.loc[:, oos_columns].to_csv(
            oos_out, index=False, date_format="%Y-%m-%d"
        )
        print(f"saved: {oos_out} ({len(oos):,} rows)")


if __name__ == "__main__":
    main()
