#!/usr/bin/env python3
"""Guarded writer for WhatsApp-ingest operator actions (migration 066).

Dry-run by default; --apply to write. Labeled "key: value" output for the
cockpit server-action parser. Ops:

  classify-chat   --chat-id <beeper_chat_id> --kind <kind> [--ingest on|off]
                  [--building-id <uuid>] [--contact-id <uuid>]
  confirm-number  --phone <+E164> --action attach --contact-id <uuid>
  confirm-number  --phone <+E164> --action create   (new contact from wa_name)
  confirm-number  --phone <+E164> --action ignore
  complete-task   --task-id <uuid>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql, sql_literal as lit  # noqa: E402

KINDS = {"unclassified", "client", "broker", "broker_group", "tenant_group",
         "community_ours", "personal", "other"}
UUID_RE = re.compile(r"^[0-9a-f-]{36}$", re.I)
PHONE_RE = re.compile(r"^\+?[\d]{8,15}$")


def sql_or_die(sql: str) -> str:
    code, out = run_psql(sql)
    if code != 0:
        print(f"error: {out}")
        sys.exit(1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("op", choices=["classify-chat", "confirm-number", "complete-task"])
    ap.add_argument("--chat-id")
    ap.add_argument("--kind")
    ap.add_argument("--ingest", choices=["on", "off"])
    ap.add_argument("--building-id")
    ap.add_argument("--contact-id")
    ap.add_argument("--phone")
    ap.add_argument("--action", choices=["attach", "create", "ignore"])
    ap.add_argument("--task-id")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    for val, pat, name in ((a.building_id, UUID_RE, "building-id"),
                           (a.contact_id, UUID_RE, "contact-id"),
                           (a.task_id, UUID_RE, "task-id"),
                           (a.phone, PHONE_RE, "phone")):
        if val and not pat.match(val):
            print(f"error: invalid {name}")
            sys.exit(1)

    stmts: list[str] = []
    if a.op == "classify-chat":
        if not a.chat_id:
            sys.exit("error: --chat-id required")
        sets = []
        if a.kind:
            if a.kind not in KINDS:
                sys.exit(f"error: kind must be one of {sorted(KINDS)}")
            sets.append(f"kind = {lit(a.kind)}")
            if a.kind == "personal" and not a.ingest:
                sets.append("ingest_enabled = FALSE")  # personal ⇒ ingest off unless told otherwise
        if a.ingest:
            sets.append(f"ingest_enabled = {a.ingest == 'on'}")
        if a.building_id:
            sets.append(f"building_id = {lit(a.building_id)}")
        if a.contact_id:
            sets.append(f"contact_id = {lit(a.contact_id)}")
        if not sets:
            sys.exit("error: nothing to change")
        stmts.append(f"UPDATE wa_chats SET {', '.join(sets)}, updated_at = NOW() "
                     f"WHERE beeper_chat_id = {lit(a.chat_id)} RETURNING title")
        if a.kind == "personal" or a.ingest == "off":
            # purge already-ingested bodies for privacy (keep nothing readable)
            stmts.append(f"DELETE FROM interactions WHERE beeper_chat_id = {lit(a.chat_id)} "
                         f"AND source = 'beeper' RETURNING id")

    elif a.op == "confirm-number":
        if not a.phone or not a.action:
            sys.exit("error: --phone and --action required")
        if a.action == "attach":
            if not a.contact_id:
                sys.exit("error: attach needs --contact-id")
            stmts += [
                f"UPDATE wa_number_queue SET status='attached', proposed_contact_id={lit(a.contact_id)}, reviewed_at=NOW() WHERE phone={lit(a.phone)} RETURNING wa_name",
                f"UPDATE wa_chat_members SET contact_id={lit(a.contact_id)} WHERE phone={lit(a.phone)} AND contact_id IS NULL RETURNING beeper_chat_id",
                f"UPDATE interactions SET contact_id={lit(a.contact_id)} WHERE sender_phone={lit(a.phone)} AND contact_id IS NULL RETURNING id",
                f"UPDATE wa_chats w SET contact_id={lit(a.contact_id)} FROM wa_chat_members m WHERE m.beeper_chat_id=w.beeper_chat_id AND w.chat_type='single' AND w.contact_id IS NULL AND m.phone={lit(a.phone)} RETURNING w.beeper_chat_id",
            ]
        elif a.action == "create":
            stmts += [
                f"""INSERT INTO contacts (full_name, contact_type, whatsapp_number, source, status)
                    SELECT COALESCE(NULLIF(wa_name,''), phone), 'lead', phone, 'whatsapp_ingest', 'active'
                    FROM wa_number_queue WHERE phone={lit(a.phone)} AND status='pending' RETURNING id""",
                f"UPDATE wa_number_queue SET status='created', reviewed_at=NOW() WHERE phone={lit(a.phone)} RETURNING phone",
                # link the new contact everywhere (matches by phone)
                f"""UPDATE wa_chat_members m SET contact_id = c.id FROM contacts c
                    WHERE m.phone={lit(a.phone)} AND m.contact_id IS NULL
                      AND c.whatsapp_number={lit(a.phone)} AND c.source='whatsapp_ingest' RETURNING m.beeper_chat_id""",
                f"""UPDATE interactions i SET contact_id = c.id FROM contacts c
                    WHERE i.sender_phone={lit(a.phone)} AND i.contact_id IS NULL
                      AND c.whatsapp_number={lit(a.phone)} AND c.source='whatsapp_ingest' RETURNING i.id""",
            ]
        else:
            stmts.append(f"UPDATE wa_number_queue SET status='ignored', reviewed_at=NOW() WHERE phone={lit(a.phone)} RETURNING phone")

    elif a.op == "complete-task":
        if not a.task_id:
            sys.exit("error: --task-id required")
        stmts.append(f"UPDATE tasks SET status='done', completed_at=NOW() WHERE id={lit(a.task_id)} RETURNING title")

    if not a.apply:
        print("dry_run: true")
        for s in stmts:
            print(f"would_run: {s[:160]}")
        return
    affected = 0
    for s in stmts:
        out = sql_or_die(s)
        affected += len([ln for ln in out.splitlines() if ln])
    print("dry_run: false")
    print(f"rows_affected: {affected}")
    print("status: ok")


if __name__ == "__main__":
    main()
