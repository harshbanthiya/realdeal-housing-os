#!/usr/bin/env python3
"""Phase 8.0 — Record a human-in-loop outreach activity against a queued contact. Dry-run by default.

After the director sends (or gets a reply) in WhatsApp Web, the operator records the outcome
here. Exactly one action per call, keyed by --queue-id:

  --mark-sent       Human confirms they SENT step N in WhatsApp Web. Refuses if today's
                    sent count already reached the daily cap (anti-spam radar guard). Logs a
                    'sent' event and advances the sequence enrollment to the next step's due date.
  --mark-replied    Contact replied. Logs a 'replied' (inbound) event; warms the lead score.
  --mark-enquired   Contact asked about a property. Logs an 'enquired' (inbound) event.
  --mark-opted-in   Contact agreed to receive updates. Logs 'opted_in' AND grants a real
                    channel_permissions row (whatsapp / opted_in) — the legitimate, human-
                    confirmed consent capture that makes them eligible for future campaigns.
  --mark-opted-out  Contact asked to stop. Logs 'opted_out', records channel_permissions
                    opted_out, adds them to outreach_suppression_list, and ends the enrollment.

This NEVER sends a message and never flips send_enabled. Writing requires BOTH --real-ok and
--apply; an in-transaction guard rolls back if send_enabled would become true.
"""

from __future__ import annotations
from _db import lit, read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUARD = ("DO $$ DECLARE se text; BEGIN SELECT setting_value INTO se FROM outreach_settings "
         "WHERE setting_key='send_enabled'; IF se='true' THEN "
         "RAISE EXCEPTION 'Refusing: send_enabled must stay false.'; END IF; END $$;")

def probe(qid: str) -> str:
    return (f"SELECT (q.id IS NOT NULL), q.status, q.sequence_step, mask_name(c.full_name) "
            f"FROM whatsapp_assisted_queue q LEFT JOIN contacts c ON c.id=q.contact_id "
            f"WHERE q.id={lit(qid)};")

def action_sql(action: str, qid: str, by: str, note: str | None) -> str:
    q = lit(qid)
    b = lit(by)
    n = lit(note)

    if action == "mark-sent":
        return f"""
BEGIN;
DO $$ DECLARE cap int; st int; BEGIN
  SELECT setting_value::int INTO cap FROM outreach_settings WHERE setting_key='daily_send_cap';
  SELECT count(*) INTO st FROM whatsapp_assisted_queue WHERE status='sent_by_human' AND sent_at::date=CURRENT_DATE;
  IF st >= cap THEN RAISE EXCEPTION 'Refusing: daily send cap % reached (sent_today=%).', cap, st; END IF;
END $$;
WITH q AS (
  UPDATE whatsapp_assisted_queue SET status='sent_by_human', send_confirmed=true, sent_at=now(),
         sent_by={b}, notes=coalesce({n}, notes), updated_at=now()
  WHERE id={q} AND status='pending'
  RETURNING contact_id, enrollment_id, sequence_id, sequence_step, tracked_link_id
),
ev AS (
  INSERT INTO contact_activity_events
    (contact_id, channel, event_type, direction, source, sequence_id, sequence_step, tracked_link_id, safe_summary, created_by)
  SELECT contact_id,'whatsapp_personal','sent','outbound','cockpit_assisted', sequence_id, sequence_step,
         tracked_link_id, 'assisted step '||sequence_step||' sent by human', {b} FROM q
  RETURNING 1
)
UPDATE contact_sequence_enrollments en
SET current_step = greatest(en.current_step, (SELECT sequence_step FROM q)),
    next_due_at = now() + make_interval(days => coalesce(
        (SELECT delay_days FROM outreach_sequence_steps st
           WHERE st.sequence_id=en.sequence_id AND st.step_number=(SELECT sequence_step FROM q)+1), 0)),
    status = CASE WHEN EXISTS (SELECT 1 FROM outreach_sequence_steps st
                    WHERE st.sequence_id=en.sequence_id AND st.step_number=(SELECT sequence_step FROM q)+1)
                  THEN 'active' ELSE 'completed' END,
    updated_at=now()
FROM q WHERE en.id=q.enrollment_id;
{GUARD}
COMMIT;
SELECT 'queue_status='||status||'  send_confirmed='||send_confirmed FROM whatsapp_assisted_queue WHERE id={q};
"""

    if action in ("mark-replied", "mark-enquired"):
        etype = "replied" if action == "mark-replied" else "enquired"
        return f"""
BEGIN;
WITH q AS (
  UPDATE whatsapp_assisted_queue SET status='replied', notes=coalesce({n}, notes), updated_at=now()
  WHERE id={q} RETURNING contact_id, sequence_id, sequence_step
)
INSERT INTO contact_activity_events
  (contact_id, channel, event_type, direction, source, sequence_id, sequence_step, safe_summary, created_by)
SELECT contact_id,'whatsapp_personal',{lit(etype)},'inbound','manual_mark', sequence_id, sequence_step,
       {lit(etype + ' recorded by human')}, {b} FROM q;
{GUARD}
COMMIT;
SELECT 'recorded {etype} for queue {qid}';
"""

    if action == "mark-opted-in":
        return f"""
BEGIN;
WITH q AS (
  UPDATE whatsapp_assisted_queue SET status='replied', notes=coalesce({n}, notes), updated_at=now()
  WHERE id={q} RETURNING contact_id, sequence_id, sequence_step
),
ev AS (
  INSERT INTO contact_activity_events
    (contact_id, channel, event_type, direction, source, sequence_id, sequence_step, safe_summary, created_by)
  SELECT contact_id,'whatsapp_personal','opted_in','inbound','manual_mark', sequence_id, sequence_step,
         'opt-in confirmed by human', {b} FROM q
  RETURNING contact_id
)
INSERT INTO channel_permissions (contact_id, channel, permission_status, consent_source, consent_timestamp, notes)
SELECT contact_id, 'whatsapp', 'opted_in', 'assisted_whatsapp_reply', now(),
       'Human-confirmed opt-in via director assisted WhatsApp' FROM ev;
{GUARD}
COMMIT;
SELECT 'opted_in recorded; channel_permissions granted (whatsapp/opted_in)';
"""

    if action == "mark-opted-out":
        return f"""
BEGIN;
WITH q AS (
  UPDATE whatsapp_assisted_queue SET status='cancelled', notes=coalesce({n}, notes), updated_at=now()
  WHERE id={q} RETURNING contact_id, enrollment_id, sequence_id, sequence_step
),
ev AS (
  INSERT INTO contact_activity_events
    (contact_id, channel, event_type, direction, source, sequence_id, sequence_step, safe_summary, created_by)
  SELECT contact_id,'whatsapp_personal','opted_out','inbound','manual_mark', sequence_id, sequence_step,
         'opt-out / STOP recorded by human', {b} FROM q
  RETURNING contact_id
),
perm AS (
  INSERT INTO channel_permissions (contact_id, channel, permission_status, consent_source, consent_timestamp, notes)
  SELECT contact_id, 'whatsapp', 'opted_out', 'assisted_whatsapp_reply', now(),
         'Human-recorded opt-out via director assisted WhatsApp' FROM ev
  RETURNING contact_id
),
sup AS (
  INSERT INTO outreach_suppression_list (contact_id, channel, reason, status, created_by)
  SELECT contact_id, 'whatsapp', 'opted_out_via_assisted_whatsapp', 'active', {b} FROM perm
  RETURNING contact_id
)
UPDATE contact_sequence_enrollments en SET status='opted_out', paused_reason='opted_out', updated_at=now()
FROM q WHERE en.id=q.enrollment_id;
{GUARD}
COMMIT;
SELECT 'opted_out recorded; suppression + channel_permissions opted_out written';
"""

    return "SELECT 'unknown action';"

def main() -> int:
    parser = argparse.ArgumentParser(description="Record a human-in-loop outreach activity. Dry-run by default.")
    parser.add_argument("--queue-id", required=True)
    parser.add_argument("--by", default="director")
    parser.add_argument("--note", default=None)
    parser.add_argument("--mark-sent", action="store_true")
    parser.add_argument("--mark-replied", action="store_true")
    parser.add_argument("--mark-enquired", action="store_true")
    parser.add_argument("--mark-opted-in", action="store_true")
    parser.add_argument("--mark-opted-out", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    chosen = [a for a, on in [
        ("mark-sent", args.mark_sent), ("mark-replied", args.mark_replied),
        ("mark-enquired", args.mark_enquired), ("mark-opted-in", args.mark_opted_in),
        ("mark-opted-out", args.mark_opted_out)] if on]
    if len(chosen) != 1:
        print("Refusing: pass exactly one of --mark-sent / --mark-replied / --mark-enquired / "
              "--mark-opted-in / --mark-opted-out.")
        return 2
    action = chosen[0]

    code, out = run_psql(probe(args.queue_id))
    if code != 0:
        print(f"Probe failed: {out}")
        return code
    parts = out.split("|")
    if not out or parts[0] not in ("t", "true"):
        print(f"Refusing: queue id {args.queue_id} not found.")
        return 1
    print(f"Action={action}  queue={args.queue_id}  current_status={parts[1]}  step={parts[2]}  contact={parts[3]}")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, out = run_psql(action_sql(action, args.queue_id, args.by, args.note))
    print("\nActivity recorded:" if code == 0 else "Record FAILED (rolled back):")
    print(out)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
