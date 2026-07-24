"""Fixed JRA shadow betting rules for live probability snapshots.

This module never purchases tickets. It converts a race snapshot into a
recommendation or NO_BET and keeps the researched rules explicit.

Version: v2026.07.24.2
"""

from __future__ import annotations

from itertools import combinations


VERSION = "v2026.07.24.2"
MARKET_BLEND_ALPHA = 0.10


def _market_probabilities(odds: dict[int, float]) -> dict[int, float]:
    inverse = {num: 1.0 / value for num, value in odds.items() if value > 1.0}
    total = sum(inverse.values())
    return {num: value / total for num, value in inverse.items()} if total else {}


def _tickets(axis: int, partners: list[int], bet_type: str) -> list[str]:
    if bet_type == "単勝":
        return [str(axis)]
    if bet_type == "ワイド":
        return [f"{axis}-{num}" for num in partners[:2]]
    return [
        f"{axis}-{left}-{right}"
        for left, right in combinations(partners[:3], 2)
    ]


def evaluate_snapshot(snapshot: dict) -> dict:
    pure = {int(k): float(v) for k, v in (snapshot.get("p") or {}).items()}
    odds = {int(k): float(v) for k, v in (snapshot.get("o") or {}).items()}
    names = {int(k): str(v) for k, v in (snapshot.get("h") or {}).items()}
    market = _market_probabilities(odds)
    common = set(pure) & set(odds) & set(market)
    if len(common) < 6:
        return {"action": "NO_BET", "reason": "オッズまたは指数が不足"}

    raw_combo = {
        num: (
            market[num] ** (1.0 - MARKET_BLEND_ALPHA)
            * pure[num] ** MARKET_BLEND_ALPHA
        )
        for num in common
    }
    combo_total = sum(raw_combo.values())
    combo = {num: value / combo_total for num, value in raw_combo.items()}
    market_order = sorted(common, key=lambda num: (-market[num], num))
    rank = {num: index + 1 for index, num in enumerate(market_order)}
    favorite_probability = market[market_order[0]]
    axes = [
        num for num in common
        if 4 <= odds[num] < 20 and 2 <= rank[num] <= 10
    ]
    if not axes:
        return {"action": "NO_BET", "reason": "中穴軸候補なし"}
    axis = max(
        axes,
        key=lambda num: (
            pure[num] - market[num],
            pure[num],
            -odds[num],
        ),
    )
    partners = sorted(
        (other for other in common if other != axis),
        key=lambda other: (-combo[other], other),
    )
    ratio = pure[axis] / max(market[axis], 1e-9)
    delta = pure[axis] - market[axis]
    partner_sum = sum(combo[other] for other in partners[:2])
    eligible = (
        10 <= odds[axis] < 20
        and 3 <= rank[axis] < 7
        and favorite_probability < 0.35
        and ratio >= 1.00
        and delta >= 0.02
        and partner_sum >= 0.45
        and len(common) >= 12
    )
    if not eligible:
        return {
            "action": "NO_BET",
            "reason": "独立指数の固定三連複ルール非該当",
            "favorite_market_probability": favorite_probability,
        }
    tickets = _tickets(axis, partners, "三連複")
    return {
        "action": "SHADOW_BET",
        "axis": axis,
        "axis_name": names.get(axis, ""),
        "odds": odds[axis],
        "market_rank": rank[axis],
        "ai_probability": pure[axis],
        "market_probability": market[axis],
        "ratio": ratio,
        "delta": delta,
        "partner_sum": partner_sum,
        "partners": partners,
        "bet_type": "三連複",
        "tickets": tickets,
        "stake_yen": 100 * len(tickets),
        "weight_status": (
            "取得済み（急変は別途警告対象）"
            if snapshot.get("w") else
            "未取得（買い確定不可）"
        ),
    }


def format_discord(race_name: str, snapshot: dict, decision: dict) -> str:
    stamp = snapshot.get("t") or "--:--"
    if decision["action"] == "NO_BET":
        return (
            f"👀 JRA shadow {race_name} [{stamp}]\n"
            f"見：{decision['reason']}\n"
            f"Version {VERSION}"
        )
    axis = decision["axis"]
    name = decision.get("axis_name") or ""
    return (
        f"🧪 JRA shadow {race_name} [{stamp}]\n"
        f"{decision['bet_type']}：{' / '.join(decision['tickets'])}"
        f"（各100円・計{decision['stake_yen']}円）\n"
        f"軸 {axis} {name} {decision['odds']:.1f}倍 "
        f"{decision['market_rank']}番人気\n"
        f"AI {decision['ai_probability']:.1%} / 市場 "
        f"{decision['market_probability']:.1%} / 比率 "
        f"{decision['ratio']:.2f}\n"
        f"馬体重：{decision['weight_status']}\n"
        f"⚠️ 自動購入なし・shadow検証専用\nVersion {VERSION}"
    )
