"""Standalone pedigree/training JRA index and Discord shadow service.

This process does not import or launch keiba_ai.live_probs.  It directly uses
the low-level scraper, feature builder and odds client, then applies the
leakage-safe research model and fixed shadow strategy.

Version: v2026.07.25.6
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path.cwd()))

from keiba_ai.features import build, load_runs
from keiba_ai.predict import (
    SHUTUBA_JRA,
    fetch_jra_odds,
    fill_weights_from_history,
    parse_shutuba,
)
from keiba_ai.scrape_local import (
    JST,
    LIST_URL_JRA,
    RID_VENUE,
    get_html,
    make_session,
    race_ids_for,
)

import walkforward_jra_pedigree_training as enhanced
import walkforward_market_edge as research
from jra_shadow_strategy import evaluate_snapshot, format_discord


VERSION = "v2026.07.25.6"
MARKS = ("◎", "○", "▲", "△", "☆", "注")
CHECK_SECONDS = 30


def discord_send(webhook: str, message: str, dry_run: bool) -> None:
    print(message, flush=True)
    if dry_run:
        return
    if not webhook:
        raise RuntimeError("JRA_STANDALONE_WEBHOOK または DISCORD_WEBHOOK7 が未設定")
    response = requests.post(webhook, json={"content": message[:1990]}, timeout=15)
    response.raise_for_status()


def fetch_card(session, race_id: str) -> tuple[dict, list[dict]]:
    html = get_html(session, SHUTUBA_JRA.format(rid=race_id))
    if not html:
        return {}, []
    return parse_shutuba(html, race_id)


def build_schedule(session, date_iso: str) -> dict[str, dict]:
    ids = race_ids_for(session, date_iso.replace("-", ""), LIST_URL_JRA)
    schedule = {}
    for race_id in ids:
        venue = RID_VENUE.get(race_id[4:6])
        if not venue:
            continue
        info, horses = fetch_card(session, race_id)
        time.sleep(0.6)
        if len(horses) < 5:
            continue
        post = None
        if info.get("post_time"):
            hour, minute = map(int, info["post_time"].split(":"))
            post = datetime.strptime(date_iso, "%Y-%m-%d").replace(
                hour=hour, minute=minute, tzinfo=JST
            )
        schedule[race_id] = {
            "venue": info.get("venue") or venue,
            "race_num": info.get("race_num") or int(race_id[-2:]),
            "race_name": info.get("race_name") or "",
            "post": post,
        }
    return schedule


def pedigree_maps(raw: pd.DataFrame, pedigree_path: Path) -> tuple[dict, dict, dict]:
    pedigree = json.loads(pedigree_path.read_text(encoding="utf-8"))
    father = {
        str(horse_id): str(value.get("father") or "").split(" ")[0]
        for horse_id, value in pedigree.items()
    }
    bms = {
        str(horse_id): str(value.get("mother_father") or "").split(" ")[0]
        for horse_id, value in pedigree.items()
    }
    history = raw.loc[:, ["horse_id", "is_win", "is_place"]].copy()
    history["sire"] = history["horse_id"].astype(str).map(father).fillna("UNKNOWN")
    history["bms"] = history["horse_id"].astype(str).map(bms).fillna("UNKNOWN")

    def rates(column: str) -> dict:
        grouped = history.groupby(column).agg(
            n=("is_win", "count"), wins=("is_win", "sum"), places=("is_place", "sum")
        )
        return {
            str(key): {
                "n": float(row.n),
                "winrate": float((row.wins + 2.0) / (row.n + 20.0)),
                "placerate": float((row.places + 6.0) / (row.n + 20.0)),
            }
            for key, row in grouped.iterrows()
        }

    return father, bms, {"sire": rates("sire"), "bms": rates("bms")}


def train_model(
    data_dir: Path, pedigree_path: Path, training_path: Path
) -> dict:
    research.DATA = data_dir.resolve()
    raw = research.load("jra")
    frame, coverage = enhanced.augment(raw, pedigree_path, training_path)
    features = enhanced.feature_columns(frame)
    model = research.make_model()
    model.fit(frame[features], frame["is_win"].astype(int))
    alpha, losses = research.choose_alpha(frame, features)
    father, bms, rates = pedigree_maps(raw, pedigree_path)
    workouts = enhanced.workout_features(training_path).set_index(
        ["race_id", "horse_id"]
    )
    print(
        f"[standalone {VERSION}] trained rows={len(frame):,} features={len(features)} "
        f"alpha={alpha:.1f} ped={coverage['pedigree_coverage']:.1%} "
        f"training={coverage['training_coverage']:.1%}",
        flush=True,
    )
    return {
        "model": model,
        "features": features,
        "alpha": alpha,
        "alpha_losses": losses,
        "father": father,
        "bms": bms,
        "rates": rates,
        "workouts": workouts,
        "runs": load_runs(str(data_dir / "keiba_jra.sqlite")),
    }


def add_live_enhancements(target: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    result = target.copy()
    horse_ids = result["horse_id"].astype(str)
    result["ped_father"] = horse_ids.map(bundle["father"]).fillna("UNKNOWN")
    result["ped_mother_father"] = horse_ids.map(bundle["bms"]).fillna("UNKNOWN")
    result["ped_available"] = (result["ped_father"] != "UNKNOWN").astype(float)
    for source, name in (("ped_father", "sire"), ("ped_mother_father", "bms")):
        mapped = result[source].map(bundle["rates"][name])
        result[f"{name}_prior_n"] = mapped.map(
            lambda value: value["n"] if isinstance(value, dict) else 0.0
        )
        result[f"{name}_winrate"] = mapped.map(
            lambda value: value["winrate"] if isinstance(value, dict) else 0.1
        )
        result[f"{name}_placerate"] = mapped.map(
            lambda value: value["placerate"] if isinstance(value, dict) else 0.3
        )
    result = result.drop(columns=["ped_father", "ped_mother_father"])
    workout_rows = []
    for row in result.itertuples():
        key = (str(row.race_id), str(row.horse_id))
        if key in bundle["workouts"].index:
            value = bundle["workouts"].loc[key]
            workout_rows.append(value.to_dict())
        else:
            workout_rows.append({"tr_available": 0.0})
    workout = pd.DataFrame(workout_rows, index=result.index)
    for column in workout:
        result[column] = workout[column]
    result["tr_available"] = result["tr_available"].fillna(0.0)
    for column in bundle["features"]:
        if column not in result:
            result[column] = np.nan
    return result


def calculate_index(
    session, race_id: str, meta: dict, date_iso: str, bundle: dict
) -> dict | None:
    info, horses = fetch_card(session, race_id)
    if len(horses) < 5:
        return None
    names = {int(h["umaban"]): str(h.get("horse_name") or "") for h in horses}
    actual_weight = all(h.get("horse_weight") is not None for h in horses)
    rows = []
    columns = bundle["runs"].columns
    for horse in horses:
        row = {column: None for column in columns}
        row.update({
            "race_id": race_id,
            "date": date_iso,
            "venue": meta["venue"],
            "race_num": meta["race_num"],
            "distance": info.get("distance"),
            "surface": info.get("surface"),
            "going": info.get("going"),
            "direction": info.get("direction"),
            "race_class": info.get("race_class"),
        })
        for key in (
            "horse_id", "sex", "age", "draw", "umaban", "weight_carried",
            "horse_weight", "horse_weight_diff", "jockey_id", "trainer_id",
        ):
            row[key] = horse.get(key)
        rows.append(row)
    fill_weights_from_history(rows, bundle["runs"])
    combined = pd.concat(
        [bundle["runs"], pd.DataFrame(rows)], ignore_index=True
    )
    combined["date"] = pd.to_datetime(combined["date"])
    base_features, _ = build(combined)
    target = base_features[base_features["race_id"] == race_id].copy()
    target = add_live_enhancements(target, bundle)
    raw_probability = bundle["model"].predict_proba(
        target[bundle["features"]]
    )[:, 1]
    probability = raw_probability / raw_probability.sum()
    pure = {
        int(row.umaban): float(value)
        for row, value in zip(target.itertuples(), probability)
    }
    return {
        "p": {str(key): round(value, 7) for key, value in pure.items()},
        "h": {str(key): value for key, value in names.items()},
        "w": actual_weight,
        "t": datetime.now(JST).strftime("%H:%M"),
        "version": VERSION,
    }


def calculate_all_indices(
    session, schedule: dict, date_iso: str, bundle: dict
) -> dict[str, dict]:
    """Calculate every race in one feature-build pass for practical preday use."""
    rows, cards = [], {}
    columns = bundle["runs"].columns
    for race_id, meta in schedule.items():
        info, horses = fetch_card(session, race_id)
        time.sleep(0.6)
        if len(horses) < 5:
            continue
        cards[race_id] = {
            "names": {
                int(horse["umaban"]): str(horse.get("horse_name") or "")
                for horse in horses
            },
            "weight_ok": all(
                horse.get("horse_weight") is not None for horse in horses
            ),
        }
        for horse in horses:
            row = {column: None for column in columns}
            row.update({
                "race_id": race_id,
                "date": date_iso,
                "venue": meta["venue"],
                "race_num": meta["race_num"],
                "distance": info.get("distance"),
                "surface": info.get("surface"),
                "going": info.get("going"),
                "direction": info.get("direction"),
                "race_class": info.get("race_class"),
            })
            for key in (
                "horse_id", "sex", "age", "draw", "umaban", "weight_carried",
                "horse_weight", "horse_weight_diff", "jockey_id", "trainer_id",
            ):
                row[key] = horse.get(key)
            rows.append(row)
    if not rows:
        return {}
    fill_weights_from_history(rows, bundle["runs"])
    combined = pd.concat(
        [bundle["runs"], pd.DataFrame(rows)], ignore_index=True
    )
    combined["date"] = pd.to_datetime(combined["date"])
    base_features, _ = build(combined)
    target = base_features[base_features["race_id"].isin(cards)].copy()
    target = add_live_enhancements(target, bundle)
    raw = bundle["model"].predict_proba(target[bundle["features"]])[:, 1]
    target["_raw_probability"] = raw
    target["_probability"] = target["_raw_probability"] / target.groupby(
        "race_id"
    )["_raw_probability"].transform("sum")
    snapshots = {}
    for race_id, group in target.groupby("race_id"):
        probability = {
            str(int(row["umaban"])): round(float(row["_probability"]), 7)
            for _, row in group.iterrows()
        }
        card = cards[str(race_id)]
        snapshots[str(race_id)] = {
            "p": probability,
            "h": {
                str(key): value for key, value in card["names"].items()
            },
            "w": card["weight_ok"],
            "t": datetime.now(JST).strftime("%H:%M"),
            "version": VERSION,
        }
    return snapshots


def format_index(meta: dict, snapshot: dict, phase: str) -> str:
    order = sorted(snapshot["p"], key=lambda key: -snapshot["p"][key])
    title = f"{meta['venue']}{meta['race_num']}R {meta.get('race_name', '')}".strip()
    lines = [
        f"{MARKS[index] if index < len(MARKS) else '　'}"
        f"{number} {snapshot['h'].get(number, '')} "
        f"{snapshot['p'][number]:.1%}"
        for index, number in enumerate(order)
    ]
    weight = "実測馬体重取得済み" if snapshot.get("w") else "馬体重なし（過去体重補完）"
    return (
        f"📊 JRA独立指数 {phase} {title}\n"
        f"血統・調教込み / {weight}\n"
        + "\n".join(lines)
        + f"\nVersion {VERSION}"
    )


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_state(path: Path, date_iso: str) -> dict:
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            if state.get("date") == date_iso and isinstance(state.get("races"), dict):
                state["version"] = VERSION
                return state
        except (OSError, json.JSONDecodeError):
            pass
    return {"date": date_iso, "version": VERSION, "races": {}}


def preday(
    session, schedule: dict, date_iso: str, bundle: dict,
    webhook: str, state_path: Path, dry_run: bool,
) -> None:
    state = load_state(state_path, date_iso)
    pending = {
        race_id: meta for race_id, meta in schedule.items()
        if "preday" not in state["races"].get(race_id, {})
    }
    if not pending:
        print(f"{date_iso}: preday notifications already complete", flush=True)
        return
    snapshots = calculate_all_indices(session, pending, date_iso, bundle)
    for race_id, meta in sorted(
        pending.items(), key=lambda item: item[1]["post"] or datetime.max.replace(tzinfo=JST)
    ):
        snapshot = snapshots.get(race_id)
        if not snapshot:
            continue
        state["races"][race_id] = {"meta": {
            **meta, "post": meta["post"].isoformat() if meta["post"] else None
        }, "preday": snapshot}
        discord_send(webhook, format_index(meta, snapshot, "前日"), dry_run)
        save_state(state_path, state)
        time.sleep(0.6)


def live_run(
    session, schedule: dict, date_iso: str, bundle: dict,
    webhook: str, state_path: Path, dry_run: bool, once: bool,
) -> None:
    state = load_state(state_path, date_iso)
    notified_30 = {
        race_id for race_id, race in state["races"].items() if "t30" in race
    }
    notified_7 = {
        race_id for race_id, race in state["races"].items() if "t7" in race
    }
    once_snapshots = (
        calculate_all_indices(session, schedule, date_iso, bundle)
        if once else {}
    )
    while len(notified_7) < len(schedule):
        now = datetime.now(JST)
        for race_id, meta in sorted(
            schedule.items(), key=lambda item: item[1]["post"] or now
        ):
            post = meta["post"]
            if not post:
                continue
            if race_id not in notified_30 and (once or now >= post - timedelta(minutes=30)):
                snapshot = (
                    once_snapshots.get(race_id)
                    if once else
                    calculate_index(session, race_id, meta, date_iso, bundle)
                )
                if snapshot:
                    state["races"].setdefault(race_id, {})["t30"] = snapshot
                    discord_send(webhook, format_index(meta, snapshot, "発走30分前"), dry_run)
                    notified_30.add(race_id)
                    save_state(state_path, state)
            if race_id not in notified_7 and (once or now >= post - timedelta(minutes=7)):
                snapshot = state["races"].get(race_id, {}).get("t30")
                if not snapshot:
                    snapshot = calculate_index(session, race_id, meta, date_iso, bundle)
                odds = fetch_jra_odds(session, race_id)
                if snapshot and odds:
                    snapshot = dict(snapshot)
                    snapshot["o"] = {
                        str(number): float(values[0])
                        for number, values in odds.items()
                    }
                    snapshot["t"] = datetime.now(JST).strftime("%H:%M")
                    decision = evaluate_snapshot(snapshot)
                    title = f"{meta['venue']}{meta['race_num']}R"
                    discord_send(
                        webhook, format_discord(title, snapshot, decision), dry_run
                    )
                    state["races"].setdefault(race_id, {})["t7"] = {
                        "snapshot": snapshot, "decision": decision
                    }
                    notified_7.add(race_id)
                    save_state(state_path, state)
                elif not once and now >= post + timedelta(minutes=3):
                    title = f"{meta['venue']}{meta['race_num']}R"
                    reason = "index unavailable" if not snapshot else "odds unavailable"
                    decision = {"action": "NO_BET", "reason": reason}
                    discord_send(
                        webhook,
                        f"JRA standalone {title}\nNO_BET: {reason}\nVersion {VERSION}",
                        dry_run,
                    )
                    state["races"].setdefault(race_id, {})["t7"] = {
                        "snapshot": snapshot, "decision": decision
                    }
                    notified_7.add(race_id)
                    save_state(state_path, state)
        save_state(state_path, state)
        if once:
            break
        time.sleep(CHECK_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preday", "live"), required=True)
    parser.add_argument("--date")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--pedigree", type=Path, default=Path("data/pedigree_jra.json"))
    parser.add_argument("--training", type=Path, default=Path("data/training_jra.json"))
    parser.add_argument("--state", type=Path, default=Path("data/jra_standalone_state.json"))
    parser.add_argument("--webhook-file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    now = datetime.now(JST)
    date_iso = args.date or (
        (now + timedelta(days=1)).strftime("%Y-%m-%d")
        if args.mode == "preday" else now.strftime("%Y-%m-%d")
    )
    webhook = (
        os.getenv("JRA_STANDALONE_WEBHOOK")
        or os.getenv("DISCORD_WEBHOOK7")
        or os.getenv("DISCORD_WEBHOOK_PREDAY")
        or ""
    )
    if not webhook and args.webhook_file and args.webhook_file.exists():
        webhook = args.webhook_file.read_text(encoding="utf-8").strip()
    session = make_session()
    schedule = build_schedule(session, date_iso)
    if args.limit > 0:
        ordered = sorted(
            schedule,
            key=lambda race_id: schedule[race_id]["post"]
            or datetime.max.replace(tzinfo=JST),
        )
        schedule = {race_id: schedule[race_id] for race_id in ordered[:args.limit]}
    if not schedule:
        print(f"{date_iso}: JRA対象レースなし", flush=True)
        return
    if args.mode == "preday":
        existing = load_state(args.state, date_iso)
        if all(
            "preday" in existing["races"].get(race_id, {})
            for race_id in schedule
        ):
            print(f"{date_iso}: preday notifications already complete", flush=True)
            return
    bundle = train_model(args.data_dir, args.pedigree, args.training)
    if args.mode == "preday":
        preday(session, schedule, date_iso, bundle, webhook, args.state, args.dry_run)
    else:
        live_run(
            session, schedule, date_iso, bundle, webhook,
            args.state, args.dry_run, args.once,
        )


if __name__ == "__main__":
    main()
