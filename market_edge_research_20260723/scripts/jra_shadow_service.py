"""Wait for JRA live snapshots and send fixed-rule shadow picks to Discord.

The service is deliberately separate from keiba_ai.live_probs. It can launch
the existing JRA monitor, watches its forward archive, and sends one shadow
decision per newly archived JRA race. It never purchases tickets.

Version: v2026.07.24.2
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from jra_shadow_strategy import VERSION as STRATEGY_VERSION
from jra_shadow_strategy import evaluate_snapshot, format_discord


VERSION = "v2026.07.24.2"
JST = timezone(timedelta(hours=9))
JRA_VENUES = {
    "札幌", "函館", "福島", "新潟", "東京",
    "中山", "中京", "京都", "阪神", "小倉",
}


def archive_path(data_dir: Path, date_iso: str) -> Path:
    return data_dir / f"ai_live_archive_{date_iso[:7].replace('-', '_')}.json"


def load_day(path: Path, date_iso: str) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get(date_iso, {})
    except (OSError, json.JSONDecodeError):
        return {}


def is_jra_race(name: str) -> bool:
    return any(name.startswith(venue) for venue in JRA_VENUES)


def send(webhook: str, message: str, dry_run: bool) -> None:
    print(message, flush=True)
    if dry_run:
        return
    if not webhook:
        raise RuntimeError(
            "DISCORD_WEBHOOK_JRA_SHADOW（またはDISCORD_WEBHOOK7）が未設定"
        )
    response = requests.post(webhook, json={"content": message[:1990]}, timeout=15)
    response.raise_for_status()


def run_preday(python: str, workdir: Path, target: str, dry_run: bool) -> int:
    command = [
        python, "-X", "utf8", "-m", "keiba_ai.live_probs",
        "--preday", target, "--jra",
    ]
    if dry_run:
        command.append("--dry")
    return subprocess.run(command, cwd=workdir, check=False).returncode


def watch(
    data_dir: Path,
    date_iso: str,
    webhook: str,
    state_path: Path,
    interval: int,
    dry_run: bool,
    stop_after: str | None,
    once: bool,
) -> None:
    sent = set()
    if state_path.exists():
        try:
            sent = set(json.loads(state_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            sent = set()
    stop = None
    if stop_after:
        hour, minute = map(int, stop_after.split(":"))
        stop = datetime.now(JST).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
    print(
        f"[jra_shadow_service {VERSION}] {date_iso} "
        f"strategy={STRATEGY_VERSION} poll={interval}s",
        flush=True,
    )
    while stop is None or datetime.now(JST) <= stop:
        day = load_day(archive_path(data_dir, date_iso), date_iso)
        changed = False
        for race_name, snapshot in sorted(day.items()):
            key = f"{date_iso}:{race_name}:{snapshot.get('t', '')}"
            if key in sent or not is_jra_race(race_name):
                continue
            decision = evaluate_snapshot(snapshot)
            send(webhook, format_discord(race_name, snapshot, decision), dry_run)
            sent.add(key)
            changed = True
        if changed and not dry_run:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(sorted(sent), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if once:
            break
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preday", "watch"), required=True)
    parser.add_argument("--date")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--state", type=Path, default=Path("data/jra_shadow_state.json"))
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--stop-after", default="17:30")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    today = datetime.now(JST)
    target = args.date or (
        (today + timedelta(days=1)).strftime("%Y-%m-%d")
        if args.mode == "preday" else today.strftime("%Y-%m-%d")
    )
    if args.mode == "preday":
        raise SystemExit(
            run_preday(args.python, args.workdir, target, args.dry_run)
        )
    webhook = (
        os.getenv("DISCORD_WEBHOOK_JRA_SHADOW")
        or os.getenv("DISCORD_WEBHOOK7")
        or os.getenv("DISCORD_WEBHOOK_PREDAY")
        or ""
    )
    watch(
        args.data_dir,
        target,
        webhook,
        args.state,
        max(5, args.interval),
        args.dry_run,
        args.stop_after,
        args.once,
    )


if __name__ == "__main__":
    main()
