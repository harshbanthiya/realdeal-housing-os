#!/usr/bin/env python3
"""Run once each morning: paces today's ramp batches across the day, with
you as the human-in-the-middle approval gate at each slot — nothing sends
without you actively saying yes.

No launchd, no cron, no extra macOS permissions — this is just a normal
process in your logged-in session (started by you), so it can read
everything on the external drive fine. It just needs the Mac to stay
awake and logged in until it finishes for the day.

Usage:
  python3 scripts/schedule_ramp_today.py --template dlf-westpark &

At each slot (10:30, 19:00 local time) it shows you a DRY RUN of exactly
who's in the batch and fires a macOS notification, then blocks waiting for
you to type y/N in the terminal — nothing is sent until you approve. Since
you're checking the laptop twice a day anyway, just answer whenever you
next look at it; the batch waits for you, it doesn't time out or auto-send.

Safe to re-run / interrupt: nothing partial happens on Ctrl+C or the Mac
sleeping — a batch either got your explicit yes and sent, or it didn't
run at all. Re-running tomorrow just picks up where the ramp left off.
"""
from __future__ import annotations
import argparse, subprocess, sys, time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SLOTS = [(10, 30), (19, 0)]   # (hour, minute), 24h local time


def seconds_until(now: datetime, hour: int, minute: int) -> float:
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return (target - now).total_seconds()


def notify(title: str, message: str) -> None:
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], check=False)


def run_batch(template: str, segment: str) -> None:
    base_cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "ramp_send_dlf.py"),
                "--template", template, "--segment", segment]

    print("\n--- DRY RUN: this is what would send ---")
    subprocess.run(base_cmd, check=False)

    notify("DLF ramp batch ready", "A send batch is prepped and waiting for your approval.")
    answer = input("\nSend this batch for real? [y/N]: ").strip().lower()
    if answer != "y":
        print("Skipped — nothing sent for this slot.")
        return

    subprocess.run(base_cmd + ["--apply"], check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--segment", default="all")
    args = ap.parse_args()

    for hour, minute in SLOTS:
        wait = seconds_until(datetime.now(), hour, minute)
        if wait <= 0:
            print(f"[{hour:02d}:{minute:02d}] already passed today — prepping now.")
        else:
            print(f"[{hour:02d}:{minute:02d}] waiting {wait/60:.0f} min...")
            time.sleep(wait)

        run_batch(args.template, args.segment)

    print("Done for today.")
    return 0


def _demo() -> None:
    from datetime import datetime as dt
    assert seconds_until(dt(2026, 1, 1, 9, 0), 10, 30) == 90 * 60
    assert seconds_until(dt(2026, 1, 1, 11, 0), 10, 30) < 0
    assert seconds_until(dt(2026, 1, 1, 10, 30), 10, 30) == 0
    print("seconds_until self-check OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        raise SystemExit(main())
