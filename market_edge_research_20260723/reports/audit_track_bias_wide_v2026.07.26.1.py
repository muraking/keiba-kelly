"""Focused robustness audit for the local track-bias wide rule.

Version: v2026.07.26.1
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np


VERSION = "v2026.07.26.1"
WORK = Path(r"C:\keiba\codex_display_test")
SOURCE = WORK / "analyze_same_day_track_bias_v2026.07.25.1.py"
OUTPUT = WORK / f"audit_track_bias_wide_{VERSION}.json"

spec = importlib.util.spec_from_file_location("track_bias", SOURCE)
track_bias = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(track_bias)


def bootstrap_lcb90(returns: np.ndarray, seed: int) -> float | None:
    if len(returns) == 0:
        return None
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(10_000):
        means.append(rng.choice(returns, size=len(returns), replace=True).mean())
    return float(np.quantile(means, 0.05))


frame, payouts = track_bias.load("local")
rows = track_bias.evaluate(frame, payouts, 1.25, 1, "wide")
rows["year"] = rows["date"].dt.year
rows["month"] = rows["date"].dt.to_period("M").astype(str)

years = {}
for year, group in rows.groupby("year"):
    returns = group["return"].to_numpy(dtype=float)
    years[str(year)] = {
        **track_bias.summary(group),
        "bootstrap_lcb90_roi": bootstrap_lcb90(returns, 20260726 + int(year)),
        "profitable_months": int(
            (group.groupby("month")["return"].mean() >= 100).sum()
        ),
        "months": int(group["month"].nunique()),
    }

months = {
    month: {
        "bets": len(group),
        "hits": int((group["return"] > 0).sum()),
        "roi": float(group["return"].mean()),
    }
    for month, group in rows.groupby("month")
}
report = {
    "version": VERSION,
    "rule": {
        "circuit": "local",
        "bet_type": "wide",
        "max_axes": 1,
        "edge_min": 1.25,
        "prior_races_min": 3,
        "later_race_min": 5,
        "front_bias_max": 0.38,
        "closer_bias_min": 0.52,
        "front_style_max": 0.40,
        "closer_style_min": 0.60,
    },
    "years": years,
    "months": months,
}
OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report["years"], ensure_ascii=False, indent=2))
print("saved", OUTPUT)
