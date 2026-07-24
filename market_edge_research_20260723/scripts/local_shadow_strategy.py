"""Fixed local-racing longshot-axis shadow strategy.

The rules are frozen from the 2024-2026 OOS research. They are shadow
recommendations, not automatic wagering rules, because the same period was
used to discover the segments.

Version: v2026.07.25.7
"""

from __future__ import annotations

VERSION = "v2026.07.25.7"


def _market_probabilities(odds: dict[int, float]) -> dict[int, float]:
    inverse = {number: 1.0 / value for number, value in odds.items() if value > 1.0}
    total = sum(inverse.values())
    return {number: value / total for number, value in inverse.items()} if total else {}


def _pair(a: int, b: int) -> str:
    return f"{min(a, b)}-{max(a, b)}"


def _trio(a: int, b: int, c: int) -> str:
    return "-".join(map(str, sorted((a, b, c))))


def _trifecta(axis: int, partners: list[int], position: int) -> list[str]:
    a, b = partners[:2]
    if position == 1:
        return [f"{axis}>{a}>{b}", f"{axis}>{b}>{a}"]
    if position == 2:
        return [f"{a}>{axis}>{b}", f"{b}>{axis}>{a}"]
    return [f"{a}>{b}>{axis}", f"{b}>{a}>{axis}"]


def _axis(
    pure: dict[int, float],
    market: dict[int, float],
    odds: dict[int, float],
    rank: dict[int, int],
    *,
    ratio: float,
    probability: float,
    delta: float,
    odds_min: float,
    odds_max: float,
    rank_min: int,
) -> int | None:
    eligible = [
        number for number in pure
        if number in market
        and number in odds
        and pure[number] / max(market[number], 1e-9) >= ratio
        and pure[number] >= probability
        and pure[number] - market[number] >= delta
        and odds_min <= odds[number] < odds_max
        and rank[number] >= rank_min
    ]
    return max(
        eligible,
        key=lambda number: (pure[number] - market[number], pure[number], -odds[number]),
        default=None,
    )


def _matches(
    number: int | None,
    pure: dict[int, float],
    market: dict[int, float],
    odds: dict[int, float],
    rank: dict[int, int],
    *,
    ratio: float,
    probability: float,
    delta: float,
    odds_min: float,
    odds_max: float,
    rank_min: int,
) -> bool:
    return bool(
        number is not None
        and pure[number] / max(market[number], 1e-9) >= ratio
        and pure[number] >= probability
        and pure[number] - market[number] >= delta
        and odds_min <= odds[number] < odds_max
        and rank[number] >= rank_min
    )


def evaluate_snapshot(snapshot: dict) -> dict:
    pure = {int(float(key)): float(value) for key, value in snapshot.get("p", {}).items()}
    odds = {int(float(key)): float(value) for key, value in snapshot.get("o", {}).items()}
    common = set(pure) & set(odds)
    if len(common) < 5:
        return {"action": "NO_BET", "reason": "オッズまたは指数が不足", "version": VERSION}
    pure = {number: pure[number] for number in common}
    odds = {number: odds[number] for number in common}
    market = _market_probabilities(odds)
    common &= set(market)
    if len(common) < 5:
        return {"action": "NO_BET", "reason": "有効オッズが不足", "version": VERSION}
    pure = {number: pure[number] for number in common}
    odds = {number: odds[number] for number in common}
    market_order = sorted(common, key=lambda number: (-market[number], number))
    rank = {number: index + 1 for index, number in enumerate(market_order)}
    favorite = market[market_order[0]]
    context = snapshot.get("context", {})
    field = int(context.get("field_size", len(common)))
    ages = [int(value) for value in snapshot.get("ages", {}).values() if value is not None]
    past = [float(value) for value in snapshot.get("past", {}).values() if value is not None]
    all_two = bool(
        context.get(
            "all_two_year",
            bool(ages) and len(ages) == field and all(age == 2 for age in ages),
        )
    )
    coverage = float(context.get(
        "cover3",
        sum(value >= 3 for value in past) / field if len(past) == field else 0.0,
    ))
    average_past = float(context.get(
        "avg_past",
        sum(past) / field if len(past) == field else 0.0,
    ))
    quality = {
        "favorite_probability": favorite,
        "field_size": field,
        "all_two_year_old": all_two,
        "coverage3": coverage,
        "average_past": average_past,
    }
    # Match the research pipeline: choose one broad longshot first, then test
    # that same horse against each stricter profile. Never reselect the axis.
    axis = _axis(
        pure, market, odds, rank, ratio=1.1, probability=0.03,
        delta=0.0, odds_min=5.0, odds_max=50.0, rank_min=2,
    )

    # Weak-favorite first-place rule. The former normal-favorite second-place
    # candidate is deliberately excluded: exact replay returned 0% in 2025/26.
    favorite_number = market_order[0]
    favorite_danger = market[favorite_number] - pure.get(favorite_number, 0.0)
    if field >= 10 and favorite < 0.45 and not all_two:
        spec = dict(
            ratio=1.1, probability=0.05, delta=0.01,
            odds_min=5.0, odds_max=20.0, rank_min=4,
        )
        position, rule = 1, "LONGSHOT_FIRST_WEAK_FAVORITE"
        if _matches(axis, pure, market, odds, rank, **spec) and favorite_danger >= 0.02:
            partners = [
                number for number in sorted(common, key=lambda n: (-pure[n], n))
                if number != axis
            ][:2]
            if len(partners) == 2 and sum(pure[number] for number in partners) >= 0.55:
                return {
                    "action": "SHADOW_BET", "rule": rule, "bet_type": "三連単",
                    "axis": axis, "partners": partners,
                    "tickets": _trifecta(axis, partners, position),
                    "stake_yen": 200, "quality": quality, "version": VERSION,
                }

    # Weak-favorite small fields: independently track the third-place pattern.
    if favorite < 0.45 and field < 10 and coverage >= 0.8 and not all_two:
        if _matches(
            axis, pure, market, odds, rank, ratio=1.1, probability=0.05,
            delta=0.01, odds_min=5.0, odds_max=20.0, rank_min=4,
        ):
            partners = [
                number for number in sorted(common, key=lambda n: (-pure[n], n))
                if number != axis
            ][:2]
            if len(partners) == 2 and sum(pure[number] for number in partners) >= 0.55:
                return {
                    "action": "SHADOW_BET", "rule": "LONGSHOT_THIRD_SMALL_FIELD",
                    "bet_type": "三連単", "axis": axis, "partners": partners,
                    "tickets": _trifecta(axis, partners, 3),
                    "stake_yen": 200, "quality": quality, "version": VERSION,
                }

    # Large/high-coverage races: the only combination rule with LCB90 > 100.
    if field >= 12 and coverage >= 0.8 and not all_two:
        if _matches(
            axis, pure, market, odds, rank, ratio=1.25, probability=0.08,
            delta=0.02, odds_min=5.0, odds_max=30.0, rank_min=4,
        ):
            partners = [
                number for number in sorted(common, key=lambda n: (-pure[n], n))
                if number != axis
            ][:2]
            if len(partners) == 2 and sum(pure[number] for number in partners) >= 0.45:
                return {
                    "action": "SHADOW_BET", "rule": "QUALITY_LARGE_FIELD_SANFUKU",
                    "confidence_tier": "A",
                    "bet_type": "三連複", "axis": axis, "partners": partners,
                    "tickets": [_trio(axis, *partners)], "stake_yen": 100,
                    "quality": quality, "version": VERSION,
                }

    # B tier increases participation without relaxing the A-tier decisions.
    # It is kept separate because its standalone LCB90 remains below 100%.
    if (
        favorite < 0.55 and field >= 10 and coverage >= 0.8
        and average_past >= 5.0 and not all_two
    ):
        if _matches(
            axis, pure, market, odds, rank, ratio=1.25, probability=0.08,
            delta=0.02, odds_min=5.0, odds_max=30.0, rank_min=4,
        ):
            partners = [
                number for number in sorted(common, key=lambda n: (-pure[n], n))
                if number != axis
            ][:2]
            if len(partners) == 2 and sum(pure[number] for number in partners) >= 0.45:
                return {
                    "action": "SHADOW_BET", "rule": "B_QUALITY_SANFUKU",
                    "confidence_tier": "B",
                    "bet_type": "三連複", "axis": axis, "partners": partners,
                    "tickets": [_trio(axis, *partners)], "stake_yen": 100,
                    "quality": quality, "version": VERSION,
                }

    return {
        "action": "NO_BET",
        "reason": "固定済み地方穴軸ルール非該当（単勝・馬連・ワイドも見）",
        "quality": quality,
        "version": VERSION,
    }


def format_discord(title: str, snapshot: dict, decision: dict) -> str:
    quality = decision.get("quality", {})
    base = (
        f"🏇 地方独立指数 {title}\n"
        f"1番人気市場勝率 {quality.get('favorite_probability', 0):.1%} / "
        f"{quality.get('field_size', 0)}頭 / データ充足 {quality.get('coverage3', 0):.0%}\n"
    )
    if decision["action"] == "NO_BET":
        return base + f"👀 見: {decision['reason']}\nVersion {VERSION}"
    names = snapshot.get("h", {})
    axis = str(decision["axis"])
    tickets = " / ".join(decision["tickets"])
    tier = decision.get("confidence_tier", "A")
    return (
        base
        + f"🕳️ 軸 {axis} {names.get(axis, '')} / {decision['bet_type']}\n"
        + f"買い目 {tickets}（各100円・計{decision['stake_yen']}円）\n"
        + f"固定ルール {decision['rule']} / {tier}ランクshadow検証\nVersion {VERSION}"
    )
