"""Fixed JRA shadow betting rules for live probability snapshots.

This module never purchases tickets. It converts a race snapshot into a
recommendation or NO_BET and keeps the researched rules explicit.

Version: v2026.07.27.1
"""

from __future__ import annotations

from itertools import combinations
from standalone_display import circled, circled_ticket, ev_circled, pace_lines


VERSION = "v2026.07.27.1"
MARKET_BLEND_ALPHA = 0.10
MARKS = ("◎", "〇", "▲", "△", "☆", "注")


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
    lines.append("●＝△以下の内部期待値100超・WP上位3頭")
    return "\n".join(lines)


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
    pure_order = sorted(common, key=lambda num: (-pure[num], num))
    pure_rank = {num: index + 1 for index, num in enumerate(pure_order)}
    favorite_probability = market[market_order[0]]
    private_flags = {
        int(number) for number in (snapshot.get("x") or [])
        if int(number) in common
    }
    context_signal = any(
        pure_rank[number] <= 3 and rank[number] - pure_rank[number] >= 3
        for number in private_flags
    )
    context_axis = pure_order[1] if len(pure_order) >= 2 else None
    axes = [
        num for num in common
        if 4 <= odds[num] < 20 and 2 <= rank[num] <= 10
    ]
    if axes:
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
        if eligible:
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
                "confidence_tier": "A",
                "weight_status": (
                    "取得済み（急変は別途警告対象）"
                    if snapshot.get("w") else
                    "未取得（買い確定不可）"
                ),
            }
    if context_signal and context_axis is not None:
        return {
            "action": "SHADOW_BET",
            "axis": context_axis,
            "axis_name": names.get(context_axis, ""),
            "odds": odds[context_axis],
            "market_rank": rank[context_axis],
            "ai_probability": pure[context_axis],
            "market_probability": market[context_axis],
            "ratio": pure[context_axis] / max(market[context_axis], 1e-9),
            "delta": pure[context_axis] - market[context_axis],
            "partners": [],
            "bet_type": "単勝",
            "tickets": [str(context_axis)],
            "stake_yen": 100,
            "confidence_tier": "C",
            "rule": "市場順位乖離×構造指数2位",
            "weight_status": (
                "取得済み（急変は別途警告対象）"
                if snapshot.get("w") else
                "未取得（買い確定不可）"
            ),
        }
    return {
        "action": "NO_BET",
        "reason": "独立指数の固定ルール非該当",
        "favorite_market_probability": favorite_probability,
    }


def format_discord(race_name: str, snapshot: dict, decision: dict) -> str:
    stamp = snapshot.get("t") or "--:--"
    latest_index = _latest_index_block(snapshot)
    if decision["action"] == "NO_BET":
        return (
            f"👀 JRA shadow {race_name} [{stamp}]\n"
            f"見：{decision['reason']}\n"
            f"{latest_index}\n"
            f"Version {VERSION}"
        )
    axis = decision["axis"]
    name = decision.get("axis_name") or ""
    tier = decision.get("confidence_tier", "A")
    message = (
        f"🧪 JRA shadow {race_name} [{stamp}] 【{tier}ランク】\n"
        f"{decision['bet_type']}："
        f"{' / '.join(circled_ticket(ticket) for ticket in decision['tickets'])}"
        f"（各100円・計{decision['stake_yen']}円）\n"
        f"軸 {circled(axis)} {name} {decision['odds']:.1f}倍 "
        f"{decision['market_rank']}番人気\n"
        f"AI {decision['ai_probability']:.1%} / 市場 "
        f"{decision['market_probability']:.1%} / 比率 "
        f"{decision['ratio']:.2f}\n"
        f"馬体重：{decision['weight_status']}\n"
        f"⚠️ 自動購入なし・shadow検証専用"
    )
    if tier == "C":
        return (
            message
            + f"\n条件：{decision.get('rule', '構造指数候補')}"
            + f"\n{latest_index}"
            + f"\nVersion {VERSION}"
        )
    message += (
        "\n―― 人が判断する参考買い目 ――\n"
        f"【参考・非推奨】単勝 {circled(axis)}"
        "（ライブ計算可能条件の2025年ROI 69.2%）\n"
        f"【参考・非推奨】ワイド "
        f"{' / '.join(circled_ticket(ticket) for ticket in _tickets(axis, decision['partners'], 'ワイド'))}"
        "（ライブ計算可能条件の2025年ROI 99.3%）"
    )
    return message + f"\n{latest_index}\nVersion {VERSION}"


def _compact_selection(snapshot: dict) -> tuple[list[int], list[int]]:
    win = {int(k): float(v) for k, v in (snapshot.get("p") or {}).items()}
    place = {int(k): float(v) for k, v in (snapshot.get("q") or {}).items()}
    odds = {int(k): float(v) for k, v in (snapshot.get("o") or {}).items()}
    winners = sorted(win, key=lambda n: (-win[n], n))[:2]
    holes = sorted(
        (n for n in place if odds.get(n, 0) >= 10.0),
        key=lambda n: (-place[n], n),
    )[:3]
    return winners, holes


def _entropy(values: dict[int, float]) -> float:
    import math

    positive = [value for value in values.values() if value > 0]
    total = sum(positive)
    if len(positive) < 2 or total <= 0:
        return 0.0
    return -sum(
        (value / total) * math.log(value / total) for value in positive
    ) / math.log(len(positive))


def _additional_tickets(snapshot: dict, winners: list[int], holes: list[int]) -> list[str]:
    win = {int(k): float(v) for k, v in (snapshot.get("p") or {}).items()}
    place = {int(k): float(v) for k, v in (snapshot.get("q") or {}).items()}
    odds = {int(k): float(v) for k, v in (snapshot.get("o") or {}).items()}
    race_num = int(snapshot.get("r") or 0)
    lines, used = [], set()

    def add(label: str, bet_type: str, left: int, right: int, note: str) -> None:
        pair = tuple(sorted((left, right)))
        key = (bet_type, pair)
        if left != right and key not in used:
            used.add(key)
            lines.append(
                f"{label} {bet_type} {circled(left)}-{circled(right)} "
                f"（{note}）"
            )

    if winners and holes:
        product = odds.get(winners[0], 0) * odds.get(holes[0], 0)
        if 1 <= race_num <= 3 and 100 <= product < 200:
            add("【A・検証】", "ワイド", winners[0], holes[0], "勝1－穴1・1点")
    if winners and len(holes) >= 3:
        product = odds.get(winners[0], 0) * odds.get(holes[2], 0)
        if 0.15 <= win.get(winners[0], 0) < 0.25 and 100 <= product < 200:
            add("【A・検証】", "馬連", winners[0], holes[2], "勝1－穴3・1点")
    place_order = sorted(place, key=lambda n: (-place[n], n))
    if (
        race_num >= 7 and len(place_order) >= 2 and holes
        and place[place_order[0]] - place[place_order[1]] < 0.05
        and _entropy(win) >= 0.85
    ):
        pairs = sorted(
            {
                tuple(sorted((a, b)))
                for a in place_order[:2] for b in holes if a != b
            },
            key=lambda pair: -(place[pair[0]] * place[pair[1]]),
        )[:2]
        for left, right in pairs:
            add("【B・検証】", "ワイド", left, right, "後半・均衡")
    return lines


# Seven-minute notification format. This intentionally overrides the legacy
# full-board formatter above while the old evaluator remains available.
def format_discord(race_name: str, snapshot: dict, decision: dict) -> str:
    del decision
    stamp = snapshot.get("t") or "--:--"
    names = {int(k): str(v) for k, v in (snapshot.get("h") or {}).items()}
    winners, holes = _compact_selection(snapshot)
    lines = [f"🏇 JRA 7分前 {race_name} [{stamp}]"]
    for rank, number in enumerate(winners, 1):
        lines.append(f"勝{rank} {circled(number)} {names.get(number, '')}")
    lines.append("")
    if not snapshot.get("o"):
        lines.append("穴馬 未確定（オッズ未取得）")
    elif not snapshot.get("q"):
        lines.append("穴馬 未確定（3着内確率未取得）")
    elif not holes:
        lines.append("穴馬 該当なし（単勝10倍以上なし）")
    else:
        for rank, number in enumerate(holes, 1):
            lines.append(f"穴{rank} {circled(number)} {names.get(number, '')}")
    lines.extend(["", "【追加買い目】"])
    lines.extend(_additional_tickets(snapshot, winners, holes) or ["追加候補なし"])
    lines.append(f"Version {VERSION}")
    return "\n".join(lines)
