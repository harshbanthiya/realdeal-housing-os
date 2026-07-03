#!/usr/bin/env python3
"""Ramped daily scheduler for the DLF email drip — warms up domain reputation.

New sending domains get spam-filtered if you blast full volume on day one.
This ramps the daily cap up gradually and only sends what's left of *today's*
allowance, so it's safe to call this multiple times a day (e.g. from launchd
at 10:30 and 19:00) without exceeding the ramp or the Resend 100/day limit.

Usage:
  python3 scripts/ramp_send_dlf.py --template dlf-westpark                # dry run: show today's plan
  python3 scripts/ramp_send_dlf.py --template dlf-westpark --apply        # send today's remaining batch

Ramp: day 0=30, day 1=50, day 2=75, day 3+=90/day (holds there).
"Day" = number of distinct calendar dates this template has already sent on
(so the ramp tracks actual send history, not wall-clock days since launch).
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from _db import run_psql

RAMP = [30, 50, 75, 90]   # day index -> cap; holds at last value once exhausted


def ramp_cap(day_index: int) -> int:
    return RAMP[min(day_index, len(RAMP) - 1)]


def days_active(template: str) -> int:
    _, out = run_psql(f"""
        SELECT count(DISTINCT sent_at::date) FROM email_drip_state
        WHERE template_key = '{template}' AND sent_at IS NOT NULL
    """)
    line = out.strip().splitlines()[-1] if out.strip() else "0"
    return int(line.strip() or 0)


def sent_today(template: str) -> int:
    _, out = run_psql(f"""
        SELECT count(*) FROM email_drip_state
        WHERE template_key = '{template}' AND sent_at::date = CURRENT_DATE
    """)
    line = out.strip().splitlines()[-1] if out.strip() else "0"
    return int(line.strip() or 0)


def _evaluate_health(complained: int, bounced: int, sent: int) -> tuple[bool, str]:
    """Any complaint today, or bounce rate over 5% (once sample is big enough), halts the ramp."""
    if complained > 0:
        return False, f"halted: {complained} spam complaint(s) today"
    if sent >= 10 and bounced / sent > 0.05:
        return False, f"halted: bounce rate {bounced}/{sent} ({bounced/sent:.0%}) over 5%"
    return True, "ok"


def health_check(template: str) -> tuple[bool, str]:
    _, out = run_psql(f"""
        SELECT count(*) FILTER (WHERE complained_at::date = CURRENT_DATE),
               count(*) FILTER (WHERE bounced_at::date = CURRENT_DATE),
               count(*) FILTER (WHERE sent_at::date = CURRENT_DATE)
        FROM email_drip_state WHERE template_key = '{template}'
    """)
    line = out.strip().splitlines()[-1] if out.strip() else "0|0|0"
    complained, bounced, sent = (int(x.strip() or 0) for x in line.split("|"))
    return _evaluate_health(complained, bounced, sent)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--segment", default="all")
    ap.add_argument("--apply", action="store_true", help="actually send (default: dry run)")
    args = ap.parse_args()

    healthy, health_msg = health_check(args.template)
    if not healthy:
        print(f"Health check failed — {health_msg}")
        return 1

    day = days_active(args.template)
    already = sent_today(args.template)
    cap = ramp_cap(day)
    remaining = max(0, cap - already)

    print(f"Ramp day {day} (cap {cap}/day) — sent today: {already}, remaining: {remaining} — health: {health_msg}")
    if remaining == 0:
        print("Today's ramp cap already reached. Nothing to do.")
        return 0

    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "email_drip_queue.py"),
           "--template", args.template, "--segment", args.segment,
           "--limit", str(remaining)]
    if args.apply:
        cmd.append("--apply")
    return subprocess.run(cmd, check=False).returncode


def _demo() -> None:
    assert ramp_cap(0) == 30
    assert ramp_cap(1) == 50
    assert ramp_cap(3) == 90
    assert ramp_cap(50) == 90   # holds at last value, doesn't index-error
    assert _evaluate_health(0, 0, 0) == (True, "ok")
    assert _evaluate_health(1, 0, 100)[0] is False       # any complaint halts
    assert _evaluate_health(0, 6, 100)[0] is False        # 6% bounce halts
    assert _evaluate_health(0, 4, 100)[0] is True         # 4% bounce ok
    assert _evaluate_health(0, 5, 5)[0] is True           # too small a sample to judge
    print("ramp_cap + health self-check OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        raise SystemExit(main())
