"""Audit exact live-cache consensus: normal index, Taichi index, and lap theory."""
from __future__ import annotations

import json
import math
import sqlite3
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

VERSION = "v2026.08.28.1"
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from keiba_ai import live_probs as lp
from keiba_ai.taichi_index_notify import score_entry

JRA_VENUES = {"札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"}


def metrics(x: pd.DataFrame) -> dict:
    if x.empty:
        return {"bets": 0, "races": 0}
    tan, plc = x.tan_payout.fillna(0), x.place_payout.fillna(0)
    return {
        "bets": int(len(x)), "races": int(x.race_id.nunique()),
        "win_rate": float(x.finish_pos.eq(1).mean()),
        "place_rate": float(x.finish_pos.le(3).mean()),
        "win_roi": float(tan.sum() / (100 * len(x))),
        "place_roi": float(plc.sum() / (100 * len(x))),
        "win_roi_trim_largest": float((tan.sum() - tan.max()) / (100 * len(x))),
        "place_roi_trim_largest": float((plc.sum() - plc.max()) / (100 * len(x))),
        "avg_odds": float(x.win_odds.mean()),
    }


def outcomes(race_ids: list[str]) -> pd.DataFrame:
    frames = []
    for tag in ("local", "jra"):
        path = BASE / "data" / f"keiba_{tag}.sqlite"
        with sqlite3.connect(path) as con:
            have = {r[1] for r in con.execute("pragma table_info(runs)")}
            wanted = ["race_id", "umaban", "finish_pos", "win_odds", "tan_payout", "place_payout"]
            cols = [c for c in wanted if c in have]
            for i in range(0, len(race_ids), 700):
                part = race_ids[i:i + 700]
                marks = ",".join("?" for _ in part)
                q = pd.read_sql_query(
                    f"select {','.join(cols)} from runs where cast(race_id as text) in ({marks})", con,
                    params=part)
                for c in wanted:
                    if c not in q:
                        q[c] = np.nan
                frames.append(q[wanted])
    d = pd.concat(frames, ignore_index=True)
    d["race_id"] = d.race_id.astype(str)
    d["umaban"] = pd.to_numeric(d.umaban, errors="coerce")
    for c in ("finish_pos", "win_odds", "tan_payout", "place_payout"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.drop_duplicates(["race_id", "umaban"], keep="last")


def main():
    rows = []
    for path in sorted((BASE / "data").glob("live_index_cache_202608*.joblib")):
        date = path.stem.rsplit("_", 1)[-1]
        if not ("20260822" <= date <= "20260827"):
            continue
        pkg = joblib.load(path)
        entries = pkg.get("entries") or {}
        races = (pkg.get("meta") or {}).get("races") or {}
        for rid, ce in entries.items():
            venue, race_no, n = races.get(rid, ("", 0, 0))
            normal = sorted((ce.get("sol_wp") or ce.get("pm") or {}),
                            key=lambda u: -float((ce.get("sol_wp") or ce.get("pm") or {})[u]))[:3]
            taichi = [r["u"] for r in score_entry(ce)[:3]]
            mt = {"venue": str(venue), "race_num": int(race_no),
                  "jra": str(venue) in JRA_VENUES, "banei": str(venue) == "帯広",
                  "distance": ce.get("distance"), "surface": ce.get("surface")}
            lap = lp._lap9_score(mt, ce)
            lap3 = [int(h["umaban"]) for h in (lap or {}).get("horses", [])[:3]]
            sets = [set(map(int, normal)), set(map(int, taichi)), set(lap3)]
            common3 = sets[0] & sets[1] & sets[2]
            common2 = {u for u in set.union(*sets) if sum(u in s for s in sets) >= 2}
            for u in sorted(common2):
                rows.append({"date": pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:]}") ,
                             "race_id": str(rid), "venue": str(venue), "race_no": int(race_no),
                             "umaban": int(u), "agree": 3 if u in common3 else 2})
    picks = pd.DataFrame(rows)
    if picks.empty:
        raise RuntimeError("consensus picks not found")
    result_rows = picks.merge(outcomes(picks.race_id.unique().tolist()),
                              on=["race_id", "umaban"], how="left")
    completed = result_rows[result_rows.finish_pos.notna()].copy()
    result = {
        "version": VERSION, "mode": "exact current live-cache replay",
        "period": [str(completed.date.min().date()), str(completed.date.max().date())],
        "all_three_top3": metrics(completed[completed.agree.eq(3)]),
        "at_least_two_top3": metrics(completed),
        "by_market_all_three": {
            "jra": metrics(completed[completed.agree.eq(3) & completed.venue.isin(JRA_VENUES)]),
            "local": metrics(completed[completed.agree.eq(3) & ~completed.venue.isin(JRA_VENUES)]),
        },
        "by_day_all_three": {
            str(k.date()): metrics(v) for k, v in completed[completed.agree.eq(3)].groupby("date")
        },
    }
    outdir = Path(__file__).resolve().parent / "reports"
    outdir.mkdir(exist_ok=True)
    (outdir / "archive_consensus_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    completed.to_csv(outdir / "archive_consensus_picks.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
