#!/usr/bin/env python3
"""Build and run the email drip queue.

Usage:
  python3 scripts/email_drip_queue.py --template dlf-westpark              # dry run: show queue
  python3 scripts/email_drip_queue.py --template dlf-westpark --limit 50   # cap at 50
  python3 scripts/email_drip_queue.py --template dlf-westpark --apply      # send (100/day Resend limit)

Segments (--segment):
  all            all contacts with a sendable email (default)
  owners         contacts linked as owner-party to any unit_registration_record
  tenants        contacts linked as tenant/lessee
  kalpataru      contacts linked to Kalpataru building
  imperial       contacts linked to Imperial Heights building

Guards:
  - skips contacts already sent or unsubscribed (email_drip_state)
  - skips emails with validation_status not in (valid, unverified)
  - --apply sends one at a time with 1-sec gap; aborts on first hard error
  - default daily cap: 90 (stays safely under Resend free 100/day limit)
"""
from __future__ import annotations
import argparse, subprocess, sys, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from _db import run_psql

DAILY_CAP = 90   # ponytail: Resend free = 100/day, stay 10 under


_SEGMENT_WHERE = {
    "all": "1=1",
    "owners": """c.id IN (
        SELECT DISTINCT p.party_contact_id FROM unit_registration_parties p
        WHERE p.party_contact_id IS NOT NULL AND p.party_role IN ('seller','lessor','owner')
    )""",
    "tenants": """c.id IN (
        SELECT DISTINCT p.party_contact_id FROM unit_registration_parties p
        WHERE p.party_contact_id IS NOT NULL AND p.party_role IN ('buyer','lessee','tenant')
    )""",
    "kalpataru": """c.id IN (
        SELECT DISTINCT p.party_contact_id FROM unit_registration_parties p
        JOIN unit_registration_records r ON r.id = p.unit_registration_record_id
        JOIN buildings b ON b.id = r.building_id
        WHERE p.party_contact_id IS NOT NULL AND b.name ILIKE '%kalpataru%'
    )""",
    "imperial": """c.id IN (
        SELECT DISTINCT p.party_contact_id FROM unit_registration_parties p
        JOIN unit_registration_records r ON r.id = p.unit_registration_record_id
        WHERE p.party_contact_id IS NOT NULL
          AND r.building_id = '0e72db71-8b93-4ecd-879c-17d8d8f2b206'
    )""",
}


def build_queue(template: str, segment: str, limit: int) -> list[dict]:
    seg_where = _SEGMENT_WHERE.get(segment, _SEGMENT_WHERE["all"])
    _, out = run_psql(f"""
        SELECT c.id, c.full_name, cm.normalized_value AS email
        FROM contacts c
        JOIN contact_methods cm ON cm.contact_id = c.id
          AND cm.method_type = 'email'
          AND cm.validation_status IN ('valid','unverified')
        WHERE {seg_where}
          AND NOT EXISTS (
            SELECT 1 FROM email_drip_state ds
            WHERE ds.contact_id = c.id
              AND ds.template_key = '{template}'
              AND (ds.sent_at IS NOT NULL OR ds.unsubscribed_at IS NOT NULL)
          )
        ORDER BY (cm.validation_status <> 'valid'), c.full_name
        LIMIT {limit}
    """)
    rows = []
    for line in out.strip().splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        rows.append({"id": parts[0].strip(), "name": parts[1].strip(), "email": parts[2].strip()})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template",  required=True)
    ap.add_argument("--segment",   default="all", choices=list(_SEGMENT_WHERE))
    ap.add_argument("--limit",     type=int, default=DAILY_CAP)
    ap.add_argument("--apply",     action="store_true", help="actually send")
    ap.add_argument("--delay",     type=float, default=1.2,
                    help="seconds between sends (default 1.2)")
    args = ap.parse_args()

    queue = build_queue(args.template, args.segment, args.limit)

    print(f"Template : {args.template}")
    print(f"Segment  : {args.segment}")
    print(f"Queue    : {len(queue)} contacts")
    print()

    if not queue:
        print("Nothing to send.")
        return 0

    for i, contact in enumerate(queue, 1):
        print(f"  [{i:3}/{len(queue)}] {contact['name'][:30]:<30}  {contact['email']}")

    if not args.apply:
        print(f"\n[DRY RUN] — re-run with --apply to send {len(queue)} emails.")
        return 0

    print(f"\nSending {len(queue)} emails ({args.delay}s gap) …\n")
    sent = failed = 0
    for i, contact in enumerate(queue, 1):
        print(f"  [{i:3}/{len(queue)}] {contact['name'][:28]:<28}  ", end="", flush=True)
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "send_email_drip.py"),
             "--contact-id", contact["id"],
             "--template",   args.template,
             "--apply"],
            capture_output=True, text=True,
        )
        last_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        if result.returncode == 0 and "OK" in last_line:
            print(f"✓  {last_line}")
            sent += 1
        elif "Skipped" in result.stdout:
            print("skipped (already sent or suppressed)")
        else:
            err = (result.stdout + result.stderr).strip().splitlines()[-1] if result.stdout + result.stderr else "unknown"
            print(f"✗  {err[:80]}")
            failed += 1
            if failed >= 3:
                print("\nToo many consecutive failures — aborting. Check RESEND_API_KEY.")
                break

        if i < len(queue):
            time.sleep(args.delay)

    print(f"\nDone: {sent} sent, {failed} failed, {len(queue)-sent-failed} skipped.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
