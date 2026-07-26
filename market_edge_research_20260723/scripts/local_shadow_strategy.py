"""Fixed local-racing longshot-axis shadow strategy.

The rules are frozen from the 2024-2026 OOS research. They are shadow
recommendations, not automatic wagering rules, because the same period was
used to discover the segments.

Version: v2026.07.26.2
"""

from __future__ import annotations

VERSION = "v2026.07.26.2"

from standalone_display import circled, circled_ticket, ev_circled, pace_lines

MARKS = ("◎", "〇", "▲", "△", "☆", "注")


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


def supplemental_tickets(snapshot: dict, decision: dict) -> list[dict]:
    """Return human-review candidates without changing the primary decision."""
    if decision.get("action") != "SHADOW_BET":
        return []
    pure = {int(float(k)): float(v) for k, v in snapshot.get("p", {}).items()}
    odds = {int(float(k)): float(v) for k, v in snapshot.get("o", {}).items()}
    common = set(pure) & set(odds)
    market = _market_probabilities({n: odds[n] for n in common})
    common &= set(market)
    axis = int(decision["axis"])
    if axis not in common:
        return []
    order = sorted(common, key=lambda n: (-market[n], n))
    rank = {n: i + 1 for i, n in enumerate(order)}
    partners = [int(n) for n in decision.get("partners", [])]
    quality = decision.get("quality", {})
    field = int(quality.get("field_size", len(common)))
    favorite = float(quality.get("favorite_probability", market[order[0]]))
    coverage = float(quality.get("coverage3", 0.0))
    average_past = float(quality.get("average_past", 0.0))
    ratio = pure[axis] / max(market[axis], 1e-9)
    delta = pure[axis] - market[axis]
    partner_sum = sum(pure.get(n, 0.0) for n in partners[:2])
    result = []
    if (
        len(partners) >= 1 and field >= 12 and favorite < 0.55
        and coverage >= 0.8 and average_past >= 5.0
        and ratio >= 1.1 and pure[axis] >= 0.05 and delta >= 0.01
        and 5.0 <= odds[axis] < 20.0 and rank[axis] >= 4
        and partner_sum >= 0.55
    ):
        result.append({
            "rank": "C", "bet_type": "馬連",
            "tickets": [_pair(axis, partners[0])],
            "evidence": "過去ROI 106.9% / LCB90 94.7%",
        })
    if (
        len(partners) >= 2 and field >= 12 and favorite < 0.55
        and coverage >= 0.8 and average_past >= 3.0
        and ratio >= 1.25 and pure[axis] >= 0.08 and delta >= 0.02
        and 5.0 <= odds[axis] < 30.0 and rank[axis] >= 4
        and partner_sum >= 0.45
    ):
        result.append({
            "rank": "C", "bet_type": "ワイド",
            "tickets": [_pair(axis, n) for n in partners[:2]],
            "evidence": "過去ROI 106.4% / LCB90 98.7%",
        })
    result.append({
        "rank": "参考・非推奨", "bet_type": "単勝",
        "tickets": [str(axis)], "evidence": "同系統の過去ROI 91.3%",
    })
    return result


def _latest_index_block(snapshot: dict) -> str:
    """Format the seven-minute board without displaying EV values."""
    pure = {int(key): float(value) for key, value in (snapshot.get("p") or {}).items()}
    odds = {int(key): float(value) for key, value in (snapshot.get("o") or {}).items()}
    names = {int(key): str(value) for key, value in (snapshot.get("h") or {}).items()}
    styles = {int(key): str(value) for key, value in (snapshot.get("s") or {}).items()}
    order = sorted(pure, key=lambda number: (-pure[number], number))
    value_candidates = [
        number for number in order[3:]
        if odds.get(number) and pure[number] * odds[number] * 100 > 100
    ]
    highlighted = set(value_candidates[:3])
    lines = ["―― 7分前最新指数 ――"]
    lines.extend(pace_lines(snapshot))
    for index, number in enumerate(order):
        price = odds.get(number)
        number_text = (
            ev_circled(number) if number in highlighted else circled(number)
        )
        mark = MARKS[index] if index < len(MARKS) else "　"
        odds_text = f"{price:.1f}倍" if price is not None else "未取得"
        lines.append(
            f"{mark} {number_text} {names.get(number, '')} "
            f"{styles.get(number, '？')} WP{pure[number]:.1%} / {odds_text}"
        )
    lines.append("❶＝△以下の内部期待値100超・WP上位3頭")
    return "\n".join(lines)


def format_discord(title: str, snapshot: dict, decision: dict) -> str:
    quality = decision.get("quality", {})
    base = (
        f"🏇 地方独立指数 {title}\n"
        f"1番人気市場勝率 {quality.get('favorite_probability', 0):.1%} / "
        f"{quality.get('field_size', 0)}頭 / データ充足 {quality.get('coverage3', 0):.0%}\n"
    )
    latest_index = _latest_index_block(snapshot)
    if decision["action"] == "NO_BET":
        return (
            base + f"👀 見: {decision['reason']}\n"
            + latest_index + f"\nVersion {VERSION}"
        )
    names = snapshot.get("h", {})
    axis = str(decision["axis"])
    tickets = " / ".join(circled_ticket(ticket) for ticket in decision["tickets"])
    tier = decision.get("confidence_tier", "A")
    message = (
        base
        + f"🕳️ 軸 {circled(axis)} {names.get(axis, '')} / {decision['bet_type']}\n"
        + f"買い目 {tickets}（各100円・計{decision['stake_yen']}円）\n"
        + f"固定ルール {decision['rule']} / {tier}ランクshadow検証"
    )
    extras = supplemental_tickets(snapshot, decision)
    if extras:
        lines = ["", "―― 人が判断する参考買い目 ――"]
        for item in extras:
            lines.append(
                f"【{item['rank']}】{item['bet_type']} "
                f"{' / '.join(circled_ticket(ticket) for ticket in item['tickets'])}"
                f"（{item['evidence']}）"
            )
        message += "\n".join(lines)
    return message + f"\n{latest_index}\nVersion {VERSION}"
