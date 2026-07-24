"""Evaluate non-overlapping A/B tiers for a higher-frequency local portfolio.

Version: v2026.07.25.1
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from local_shadow_strategy import (
    _axis,
    _market_probabilities,
    _matches,
    _pair,
    _trio,
    evaluate_snapshot,
)
from verify_local_fixed_strategy import contexts, payout_map, races


VERSION = "v2026.07.25.1"


def expanded(snapshot: dict) -> dict:
    """Return a fallback B-tier decision only when the frozen A tier passed."""
    if evaluate_snapshot(snapshot)["action"] == "SHADOW_BET":
        return {"action": "NO_BET", "reason": "Aランクと重複"}
    pure = {int(float(k)): float(v) for k, v in snapshot["p"].items()}
    odds = {int(float(k)): float(v) for k, v in snapshot["o"].items()}
    common = set(pure) & set(odds)
    market = _market_probabilities({n: odds[n] for n in common})
    common &= set(market)
    if len(common) < 6:
        return {"action": "NO_BET", "reason": "データ不足"}
    pure = {n: pure[n] for n in common}
    odds = {n: odds[n] for n in common}
    order = sorted(common, key=lambda n: (-market[n], n))
    rank = {n: i + 1 for i, n in enumerate(order)}
    favorite = market[order[0]]
    context = snapshot["context"]
    field = int(context["field_size"])
    if context["all_two_year"]:
        return {"action": "NO_BET", "reason": "全馬2歳"}
    axis = _axis(
        pure, market, odds, rank, ratio=1.1, probability=0.03,
        delta=0.0, odds_min=5.0, odds_max=50.0, rank_min=2,
    )
    if axis is None:
        return {"action": "NO_BET", "reason": "穴軸なし"}
    partners = [
        n for n in sorted(common, key=lambda n: (-pure[n], n)) if n != axis
    ]

    # First fallback: broader high-quality trifecta population found in the
    # predeclared race-quality analysis (LCB90 97.8%, 1,918 races).
    quality = dict(
        ratio=1.25, probability=0.08, delta=0.02,
        odds_min=5.0, odds_max=30.0, rank_min=4,
    )
    if (
        favorite < 0.55 and field >= 10 and context["cover3"] >= 0.8
        and context["avg_past"] >= 5.0
        and _matches(axis, pure, market, odds, rank, **quality)
        and len(partners) >= 2
        and sum(pure[n] for n in partners[:2]) >= 0.45
    ):
        return {
            "action": "B_BET", "rule": "B_QUALITY_SANFUKU",
            "bet_type": "sanfuku", "tickets": [_trio(axis, *partners[:2])],
        }

    # Second fallback: one-point quinella in deep, stable fields.
    danger = dict(
        ratio=1.1, probability=0.05, delta=0.01,
        odds_min=5.0, odds_max=20.0, rank_min=4,
    )
    if (
        favorite < 0.55 and field >= 12 and context["cover3"] >= 0.8
        and context["avg_past"] >= 5.0
        and _matches(axis, pure, market, odds, rank, **danger)
        and len(partners) >= 2
        and sum(pure[n] for n in partners[:2]) >= 0.55
    ):
        return {
            "action": "B_BET", "rule": "B_DEEP_UMAREN",
            "bet_type": "umaren", "tickets": [_pair(axis, partners[0])],
        }
    return {"action": "NO_BET", "reason": "Bランク非該当"}


def metrics(rows: list[dict]) -> dict:
    stake = sum(r["stake"] for r in rows)
    returned = sum(r["return"] for r in rows)
    race_roi = [100.0 * r["return"] / r["stake"] for r in rows]
    mean = sum(race_roi) / len(race_roi) if race_roi else 0.0
    variance = (
        sum((x - mean) ** 2 for x in race_roi) / (len(race_roi) - 1)
        if len(race_roi) > 1 else math.inf
    )
    balance = peak = max_drawdown = 0
    for row in sorted(rows, key=lambda r: (r["date"], r["race_id"])):
        balance += row["return"] - row["stake"]
        peak = max(peak, balance)
        max_drawdown = max(max_drawdown, peak - balance)
    dates = Counter(r["date"] for r in rows)
    return {
        "races": len(rows),
        "active_days": len(dates),
        "races_per_calendar_day": round(
            len(rows) / max(1, 931), 3  # 2024-01-01 through 2026-07-19
        ),
        "races_per_active_day": round(len(rows) / max(1, len(dates)), 3),
        "median_active_day": sorted(dates.values())[len(dates) // 2] if dates else 0,
        "stake": stake,
        "return": returned,
        "roi": round(100.0 * returned / stake, 3) if stake else 0.0,
        "lcb90": round(
            mean - 1.6448536269514722 * math.sqrt(variance / len(race_roi)), 3
        ) if race_roi else 0.0,
        "max_drawdown_yen": max_drawdown,
        "max_payout_share": round(
            max((r["return"] for r in rows), default=0) / returned, 5
        ) if returned else 0.0,
    }


def run(oos: Path, database: Path, features: Path) -> dict:
    payouts = payout_map(database)
    race_context = contexts(features)
    tiers: dict[str, list[dict]] = defaultdict(list)
    annual: dict[str, dict[int, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for race_id, date, rows in races(oos):
        if race_id not in payouts or race_id not in race_context:
            continue
        snapshot = {
            "p": {row["umaban"]: float(row["p_struct"]) for row in rows},
            "o": {row["umaban"]: float(row["win_odds"]) for row in rows},
            "context": race_context[race_id],
        }
        a = evaluate_snapshot(snapshot)
        if a["action"] == "SHADOW_BET":
            bet_type = {"三連単": "santan", "三連複": "sanfuku"}[a["bet_type"]]
            decision, tier = a, "A"
        else:
            decision = expanded(snapshot)
            if decision["action"] != "B_BET":
                continue
            bet_type, tier = decision["bet_type"], "B"
        table = payouts[race_id].get(bet_type)
        if not table:
            continue
        item = {
            "race_id": race_id, "date": date, "tier": tier,
            "rule": decision["rule"], "stake": 100 * len(decision["tickets"]),
            "return": sum(table.get(ticket, 0) for ticket in decision["tickets"]),
        }
        tiers[tier].append(item)
        tiers["A+B"].append(item)
        annual[tier][int(date[:4])].append(item)
        annual["A+B"][int(date[:4])].append(item)
    return {
        "version": VERSION,
        "method": "frozen A rules plus non-overlapping predeclared B fallbacks",
        "tiers": {name: metrics(items) for name, items in tiers.items()},
        "annual": {
            name: {str(year): metrics(items) for year, items in years.items()}
            for name, years in annual.items()
        },
        "rules": {
            name: metrics([r for r in tiers["A+B"] if r["rule"] == name])
            for name in sorted({r["rule"] for r in tiers["A+B"]})
        },
        "limitations": [
            "B rules were discovered on the same 2024-2026 OOS period",
            "final odds and final payouts are used",
            "shadow validation at T-7 is required before purchase",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("oos", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("features", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = run(args.oos, args.database, args.features)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
