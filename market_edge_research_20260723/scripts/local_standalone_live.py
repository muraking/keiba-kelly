"""Standalone local-racing index and Discord shadow service.

This service does not import or launch keiba_ai.live_probs. It directly uses
the low-level local card parser and structural feature builder.

Version: v2026.07.26.4
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import joblib

sys.path.insert(0, str(Path.cwd()))

from keiba_ai.features import build
from keiba_ai.predict import SHUTUBA_LOCAL, fill_weights_from_history, parse_shutuba
from keiba_ai.scrape_local import (
    JST,
    LIST_URL_LOCAL,
    RID_VENUE,
    get_html,
    make_session,
    race_ids_for,
)

import walkforward_market_edge as research
from local_shadow_strategy import evaluate_snapshot, format_discord
from standalone_display import (
    circled, notification_due, pace_lines, relative_styles,
)


VERSION = "v2026.07.26.4"
MAX_TRAIN_ROWS = 350_000
MAX_RUN_ROWS = 200_000
MODEL_CACHE_VERSION = 1
CHECK_SECONDS = 30
MARKS = ("◎", "○", "▲", "△", "☆", "注")


def discord_send(webhook: str, message: str, dry_run: bool) -> None:
    print(message, flush=True)
    if dry_run:
        return
    if not webhook:
        raise RuntimeError("LOCAL_STANDALONE_WEBHOOK または DISCORD_WEBHOOK7 が未設定")
    response = requests.post(webhook, json={"content": message[:1990]}, timeout=15)
    response.raise_for_status()


def discord_send_7(
    webhook: str, webhook4: str, message: str, dry_run: bool
) -> None:
    """Send only the seven-minute notification to primary and WEBHOOK4."""
    targets = list(dict.fromkeys(target for target in (webhook, webhook4) if target))
    if dry_run:
        discord_send(webhook, message, True)
        return
    if not targets:
        discord_send("", message, False)
        return
    for target in targets:
        discord_send(target, message, False)


def read_env_value(path: Path, *names: str) -> str:
    """Read selected values from a simple .env file without logging secrets."""
    if not path.exists():
        return ""
    wanted = set(names)
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in wanted:
            return value.strip().strip("\"'")
    return ""


def fetch_card(session, race_id: str) -> tuple[dict, list[dict]]:
    html = get_html(session, SHUTUBA_LOCAL.format(rid=race_id))
    return parse_shutuba(html, race_id) if html else ({}, [])


def build_schedule(session, date_iso: str) -> dict[str, dict]:
    ids = race_ids_for(session, date_iso.replace("-", ""), LIST_URL_LOCAL)
    schedule = {}
    for race_id in ids:
        venue = RID_VENUE.get(race_id[4:6])
        if not venue or venue == "帯広":
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


def load_recent_runs(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "keiba_local.sqlite"
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    runs = pd.read_sql_query(
        "SELECT * FROM (SELECT * FROM runs ORDER BY date DESC "
        f"LIMIT {MAX_RUN_ROWS})",
        connection,
        parse_dates=["date"],
    )
    connection.close()
    return runs


def train_model(data_dir: Path) -> dict:
    feature_path = data_dir / "features_local.sqlite"
    signature = {
        "size": feature_path.stat().st_size,
        "mtime_ns": feature_path.stat().st_mtime_ns,
    }
    cache_path = data_dir / "local_standalone_model.joblib"
    if cache_path.exists():
        try:
            cached = joblib.load(cache_path)
            if (
                cached.get("signature") == signature
                and cached.get("model_cache_version", 1) == MODEL_CACHE_VERSION
            ):
                print(
                    f"[local standalone {VERSION}] model cache loaded "
                    f"features={len(cached['features'])}",
                    flush=True,
                )
                runs = load_recent_runs(data_dir)
                return {
                    "model": cached["model"],
                    "features": cached["features"],
                    "runs": runs,
                    "last_weight": (
                        runs.dropna(subset=["horse_weight"]).sort_values("date")
                        .groupby("horse_id")["horse_weight"].last().to_dict()
                    ),
                    "live_features": {},
                }
        except Exception as error:
            print(f"[local standalone] cache ignored: {error}", flush=True)
    print(f"[local standalone {VERSION}] loading training data", flush=True)
    drop = research.ID_COLS | research.LABEL_COLS | research.EVAL_COLS
    connection = sqlite3.connect(
        f"file:{feature_path.as_posix()}?mode=ro", uri=True
    )
    schema = connection.execute("PRAGMA table_info(features)").fetchall()
    features = [
        str(row[1]) for row in schema
        if str(row[2]).upper() in {"REAL", "INTEGER"}
        and str(row[1]) not in drop
        and str(row[1]) not in research.MARKET_DERIVED_COLS
    ]
    select_columns = ", ".join(f'"{column}"' for column in features + ["is_win"])
    frame = pd.read_sql_query(
        f"SELECT {select_columns} FROM features "
        "WHERE win_odds > 0 AND is_win IS NOT NULL "
        "AND race_id IN (SELECT race_id FROM features WHERE tan_payout IS NOT NULL) "
        f"ORDER BY date DESC LIMIT {MAX_TRAIN_ROWS}",
        connection,
        dtype={column: "float32" for column in features + ["is_win"]},
    )
    connection.close()
    model = research.make_model()
    print(
        f"[local standalone {VERSION}] fitting rows={len(frame):,} "
        f"features={len(features)}",
        flush=True,
    )
    model.fit(frame[features], frame["is_win"].astype(int))
    joblib.dump(
        {
            "service_version": VERSION,
            "model_cache_version": MODEL_CACHE_VERSION,
            "signature": signature,
            "model": model,
            "features": features,
        },
        cache_path,
    )
    print(
        f"[local standalone {VERSION}] trained rows={len(frame):,} "
        f"features={len(features)} market_columns=excluded",
        flush=True,
    )
    runs = load_recent_runs(data_dir)
    return {
        "model": model,
        "features": features,
        "runs": runs,
        "last_weight": (
            runs.dropna(subset=["horse_weight"]).sort_values("date")
            .groupby("horse_id")["horse_weight"].last().to_dict()
        ),
        "live_features": {},
    }


def _rows_from_card(
    race_id: str, meta: dict, date_iso: str, info: dict,
    horses: list[dict], columns,
) -> list[dict]:
    rows = []
    for horse in horses:
        row = {column: None for column in columns}
        row.update({
            "race_id": race_id, "date": date_iso, "venue": meta["venue"],
            "race_num": meta["race_num"], "distance": info.get("distance"),
            "surface": info.get("surface"), "going": info.get("going"),
            "direction": info.get("direction"), "race_class": info.get("race_class"),
        })
        for key in (
            "horse_id", "sex", "age", "draw", "umaban", "weight_carried",
            "horse_weight", "horse_weight_diff", "jockey_id", "trainer_id",
        ):
            row[key] = horse.get(key)
        rows.append(row)
    return rows


def _snapshots_from_target(
    target: pd.DataFrame, cards: dict[str, dict], bundle: dict,
) -> dict[str, dict]:
    for column in bundle["features"]:
        if column not in target:
            target[column] = np.nan
    target["_raw"] = bundle["model"].predict_proba(target[bundle["features"]])[:, 1]
    target["_probability"] = target["_raw"] / target.groupby("race_id")[
        "_raw"
    ].transform("sum")
    snapshots = {}
    for race_id, group in target.groupby("race_id"):
        card = cards[str(race_id)]
        bundle["live_features"][str(race_id)] = group[
            ["horse_id", "umaban", *bundle["features"]]
        ].copy()
        snapshots[str(race_id)] = {
            "p": {
                str(int(row["umaban"])): round(float(row["_probability"]), 7)
                for _, row in group.iterrows()
            },
            "h": {str(key): value for key, value in card["names"].items()},
            "ages": {str(key): value for key, value in card["ages"].items()},
            "past": {
                str(int(row["umaban"])): int(max(0, row["h_n_past"]))
                if pd.notna(row["h_n_past"]) else 0
                for _, row in group.iterrows()
            },
            "s": relative_styles({
                str(int(row["umaban"])): (
                    float(row["h_avg_early3"])
                    if "h_avg_early3" in group and pd.notna(row["h_avg_early3"])
                    else None
                )
                for _, row in group.iterrows()
            }),
            "w": card["weight_ok"],
            "t": datetime.now(JST).strftime("%H:%M"),
            "version": VERSION,
        }
    return snapshots


def calculate_all_indices(
    session, schedule: dict, date_iso: str, bundle: dict,
) -> dict[str, dict]:
    rows, cards = [], {}
    for race_id, meta in schedule.items():
        info, horses = fetch_card(session, race_id)
        time.sleep(0.6)
        if len(horses) < 5:
            continue
        cards[race_id] = {
            "names": {int(h["umaban"]): str(h.get("horse_name") or "") for h in horses},
            "ages": {int(h["umaban"]): h.get("age") for h in horses},
            "weight_ok": all(h.get("horse_weight") is not None for h in horses),
        }
        rows.extend(_rows_from_card(
            race_id, meta, date_iso, info, horses, bundle["runs"].columns
        ))
    if not rows:
        return {}
    fill_weights_from_history(rows, bundle["runs"])
    combined = pd.concat([bundle["runs"], pd.DataFrame(rows)], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    features, _ = build(combined)
    target = features[features["race_id"].isin(cards)].copy()
    return _snapshots_from_target(target, cards, bundle)


def recalculate_cached_index(
    session, race_id: str, base: dict, bundle: dict,
) -> dict | None:
    features = bundle["live_features"].get(race_id)
    if features is None:
        return None
    _info, horses = fetch_card(session, race_id)
    if len(horses) < 5:
        return None
    by_number = {int(horse["umaban"]): horse for horse in horses}
    current = features.copy()
    actual_weight = all(
        horse.get("horse_weight") is not None for horse in horses
    )
    for index, row in current.iterrows():
        horse = by_number.get(int(row["umaban"]), {})
        weight = horse.get("horse_weight")
        difference = horse.get("horse_weight_diff")
        if weight is None:
            continue
        current.at[index, "horse_weight"] = float(weight)
        current.at[index, "horse_weight_diff"] = (
            float(difference) if difference is not None else np.nan
        )
        previous = bundle["last_weight"].get(row["horse_id"])
        current.at[index, "h_weight_change"] = (
            float(weight) - float(previous) if previous is not None else np.nan
        )
    raw = bundle["model"].predict_proba(current[bundle["features"]])[:, 1]
    probability = raw / raw.sum()
    result = dict(base)
    result["p"] = {
        str(int(row["umaban"])): round(float(value), 7)
        for (_, row), value in zip(current.iterrows(), probability)
    }
    result["w"] = actual_weight
    result["t"] = datetime.now(JST).strftime("%H:%M")
    result["version"] = VERSION
    return result


def calculate_index(
    session, race_id: str, meta: dict, date_iso: str, bundle: dict,
) -> dict | None:
    result = calculate_all_indices(session, {race_id: meta}, date_iso, bundle)
    return result.get(race_id)


def fetch_local_odds(session, race_id: str) -> dict[int, float]:
    _info, horses = fetch_card(session, race_id)
    return {
        int(horse["umaban"]): float(horse["win_odds"])
        for horse in horses
        if horse.get("umaban") and horse.get("win_odds") and horse["win_odds"] > 1.0
    }


def format_index(meta: dict, snapshot: dict, phase: str) -> str:
    order = sorted(snapshot["p"], key=lambda number: -snapshot["p"][number])
    lines = [
        f"{MARKS[index] if index < len(MARKS) else '　'}"
        f"{circled(number)} {snapshot['h'].get(number, '')} {snapshot['p'][number]:.1%}"
        for index, number in enumerate(order)
    ]
    title = f"{meta['venue']}{meta['race_num']}R {meta.get('race_name', '')}".strip()
    weight = "実測馬体重取得済み" if snapshot.get("w") else "過去馬体重で補完"
    return (
        f"🏇 地方独立指数 {phase} {title}\n構造指数 / {weight}\n"
        + "\n".join(pace_lines(snapshot))
        + "\n"
        + "\n".join(lines)
        + f"\nVersion {VERSION}"
    )


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


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
        print(f"{date_iso}: local preday notifications already complete", flush=True)
        return
    snapshots = calculate_all_indices(session, pending, date_iso, bundle)
    for race_id, meta in sorted(
        pending.items(), key=lambda item: item[1]["post"] or datetime.max.replace(tzinfo=JST)
    ):
        snapshot = snapshots.get(race_id)
        if not snapshot:
            continue
        state["races"][race_id] = {
            "meta": {
                **meta, "post": meta["post"].isoformat() if meta["post"] else None,
            },
            "preday": snapshot,
        }
        discord_send(webhook, format_index(meta, snapshot, "前日"), dry_run)
        save_state(state_path, state)
        time.sleep(0.6)


def live_run(
    session, schedule: dict, date_iso: str, bundle: dict,
    webhook: str, webhook4: str, state_path: Path, dry_run: bool, once: bool,
) -> None:
    state = load_state(state_path, date_iso)
    notified_30 = {
        race_id for race_id, race in state["races"].items() if "t30" in race
    }
    notified_7 = {
        race_id for race_id, race in state["races"].items() if "t7" in race
    }
    morning_snapshots = calculate_all_indices(session, schedule, date_iso, bundle)
    while len(notified_7) < len(schedule):
        now = datetime.now(JST)
        due_30 = {
            race_id: meta for race_id, meta in schedule.items()
            if race_id not in notified_30
            and meta["post"]
            and (
                (once and now < meta["post"])
                or notification_due(now, meta["post"], 30)
            )
        }
        due_30_snapshots = {
            race_id: recalculate_cached_index(
                session, race_id, morning_snapshots[race_id], bundle
            )
            for race_id in due_30 if race_id in morning_snapshots
        }
        for race_id, meta in sorted(schedule.items(), key=lambda item: item[1]["post"] or now):
            post = meta["post"]
            if not post:
                continue
            if now >= post:
                race_state = state["races"].setdefault(race_id, {})
                if race_id not in notified_30:
                    race_state["t30"] = {"skipped": "post_started"}
                    notified_30.add(race_id)
                if race_id not in notified_7:
                    race_state["t7"] = {"skipped": "post_started"}
                    notified_7.add(race_id)
                continue
            if race_id not in notified_30 and (
                once or notification_due(now, post, 30)
            ):
                snapshot = (
                    due_30_snapshots.get(race_id)
                )
                if snapshot:
                    state["races"].setdefault(race_id, {})["t30"] = snapshot
                    discord_send(webhook, format_index(meta, snapshot, "発走30分前"), dry_run)
                    notified_30.add(race_id)
                    save_state(state_path, state)
            if race_id not in notified_7 and (
                once or notification_due(now, post, 7)
            ):
                snapshot = state["races"].get(race_id, {}).get("t30")
                if not snapshot:
                    snapshot = calculate_index(session, race_id, meta, date_iso, bundle)
                odds = fetch_local_odds(session, race_id)
                if snapshot and odds:
                    snapshot = dict(snapshot)
                    snapshot["o"] = {str(number): value for number, value in odds.items()}
                    snapshot["t"] = datetime.now(JST).strftime("%H:%M")
                    decision = evaluate_snapshot(snapshot)
                    title = f"{meta['venue']}{meta['race_num']}R"
                    discord_send_7(
                        webhook, webhook4,
                        format_discord(title, snapshot, decision), dry_run,
                    )
                    state["races"].setdefault(race_id, {})["t7"] = {
                        "snapshot": snapshot, "decision": decision,
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
    parser.add_argument("--state", type=Path, default=Path("data/local_standalone_state.json"))
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
        os.getenv("LOCAL_STANDALONE_WEBHOOK")
        or os.getenv("DISCORD_WEBHOOK7")
        or os.getenv("DISCORD_WEBHOOK_PREDAY")
        or ""
    )
    if not webhook and args.webhook_file and args.webhook_file.exists():
        webhook = args.webhook_file.read_text(encoding="utf-8").strip()
    webhook4 = (
        os.getenv("WEBHOOK4")
        or os.getenv("DISCORD_WEBHOOK4")
        or read_env_value(args.data_dir.parent / ".env", "WEBHOOK4", "DISCORD_WEBHOOK4")
    )
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
        print(f"{date_iso}: 地方対象レースなし", flush=True)
        return
    if args.mode == "preday":
        existing = load_state(args.state, date_iso)
        if all("preday" in existing["races"].get(race_id, {}) for race_id in schedule):
            print(f"{date_iso}: local preday notifications already complete", flush=True)
            return
    bundle = train_model(args.data_dir)
    if args.mode == "preday":
        preday(session, schedule, date_iso, bundle, webhook, args.state, args.dry_run)
    else:
        live_run(
            session, schedule, date_iso, bundle, webhook, webhook4,
            args.state, args.dry_run, args.once,
        )


if __name__ == "__main__":
    main()
