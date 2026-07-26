"""Shared display helpers for the independent local/JRA services.

Version: v2026.07.26.2
"""

from __future__ import annotations

import re
from datetime import timedelta


VERSION = "v2026.07.26.2"
_CIRCLED = {
    **{number: chr(0x2460 + number - 1) for number in range(1, 21)},
    0: "⓪",
}
_EV_CIRCLED = {
    **{number: chr(0x2776 + number - 1) for number in range(1, 11)},
    **{number: chr(0x24EB + number - 11) for number in range(11, 21)},
}


def circled(number: int | str) -> str:
    """Return a Unicode circled horse number, falling back safely above 20."""
    try:
        value = int(number)
    except (TypeError, ValueError):
        return str(number)
    return _CIRCLED.get(value, f"㊀{value}")


def ev_circled(number: int | str) -> str:
    """Return a filled circle number used only for internal EV above 100."""
    try:
        value = int(number)
    except (TypeError, ValueError):
        return str(number)
    return _EV_CIRCLED.get(value, f"●{value}")


def circled_ticket(ticket: str) -> str:
    """Convert every horse number in a ticket while retaining separators."""
    return re.sub(r"\d+", lambda match: circled(match.group()), str(ticket))


def notification_due(now, post, lead_minutes: int) -> bool:
    """Return true only inside the pre-post notification window."""
    return post - timedelta(minutes=lead_minutes) <= now < post


def relative_styles(early: dict[str, float | None]) -> dict[str, str]:
    """Classify leakage-safe historical early position within today's field."""
    valid = []
    for number, value in early.items():
        try:
            valid.append((str(number), float(value)))
        except (TypeError, ValueError):
            pass
    styles = {str(number): "？" for number in early}
    count = len(valid)
    if not count:
        return styles
    for index, (number, _value) in enumerate(sorted(valid, key=lambda item: item[1])):
        percentile = (index + 0.5) / count
        styles[number] = (
            "逃" if percentile < 0.18 else
            "先" if percentile < 0.38 else
            "差" if percentile < 0.62 else "追"
        )
    return styles


def pace_lines(snapshot: dict) -> list[str]:
    """Build a compact projected running-style line and a cautious pace label."""
    styles = snapshot.get("s") or {}
    groups = {
        style: [circled(number) for number, value in styles.items() if value == style]
        for style in ("逃", "先", "差", "追", "？")
    }
    lineup = " / ".join(
        f"{style}{''.join(numbers) or '―'}" for style, numbers in groups.items()
    )
    front = len(groups["逃"]) + len(groups["先"])
    known = sum(len(groups[style]) for style in ("逃", "先", "差", "追"))
    if not known:
        outlook = "判定保留（脚質データ不足）"
    elif len(groups["逃"]) >= 3 or front / known >= 0.50:
        outlook = "前が多い流れ（差し・追込の浮上に注意）"
    elif len(groups["逃"]) <= 1 and front / known <= 0.30:
        outlook = "前が少ない流れ（前残りに注意）"
    else:
        outlook = "平均的な構成"
    return [f"展開 {lineup}", f"想定 {outlook}"]
