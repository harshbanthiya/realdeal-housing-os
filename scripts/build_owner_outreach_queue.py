#!/usr/bin/env python3
"""Phase 8.0 — Build today's owners-only assisted WhatsApp queue. Dry-run by default.

Picks eligible owners (owner relationship, reachable number, NOT suppressed / opted-out /
in cooldown / already enrolled), up to the remaining daily cap, and for each:
  * enrolls them in the active "Warm Owner Greeting" sequence (current_step=0, status active),
  * mints a per-contact tracked link (first-party web-read attribution, NOT Meta Pixel),
  * resolves the step-1 template into the real message (truth; masked in views),
  * inserts a 'pending' whatsapp_assisted_queue row with a wa.me click-to-chat deep link.

It NEVER sends, never sets status='sent_by_human', never flips send_enabled, and an
in-transaction guard rolls everything back if the day's queue would exceed the cap or any
'sent' row would appear. Writing requires BOTH --real-ok and --apply.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


# Shared candidate selection (used by both dry-run probe and apply).
CAND_CTE = """
seq AS (
  SELECT s.id AS sequence_id FROM outreach_sequences s
  WHERE s.status='active' AND s.owner_only=true ORDER BY s.created_at LIMIT 1
),
step1 AS (
  SELECT st.message_template, st.link_target
  FROM outreach_sequence_steps st JOIN seq ON st.sequence_id=seq.sequence_id WHERE st.step_number=1
),
cfg AS (
  SELECT
    (SELECT setting_value FROM outreach_settings WHERE setting_key='director_display_name') AS director,
    (SELECT setting_value FROM outreach_settings WHERE setting_key='tracked_link_base_url') AS link_base,
    (SELECT setting_value::int FROM outreach_settings WHERE setting_key='daily_send_cap') AS cap
),
remaining AS (
  SELECT greatest((SELECT cap FROM cfg) - (
     SELECT count(*) FROM whatsapp_assisted_queue
     WHERE queued_for_date=CURRENT_DATE AND status IN ('pending','sent_by_human')), 0) AS slots
),
cand AS (
  SELECT c.id AS contact_id,
         split_part(c.full_name,' ',1) AS first_name,
         (SELECT b.name FROM contact_property_relationships r JOIN buildings b ON b.id=r.building_id
            WHERE r.contact_id=c.id AND r.relationship_type='owner'
              AND r.relationship_status IN ('active','approved') ORDER BY r.created_at LIMIT 1) AS building_name,
         (SELECT m.normalized_value FROM contact_methods m
            WHERE m.contact_id=c.id AND m.method_type IN ('mobile','phone','whatsapp')
            ORDER BY m.is_primary DESC NULLS LAST, m.created_at LIMIT 1) AS raw_number
  FROM contacts c
  WHERE c.status NOT IN ('do_not_contact','duplicate','archived')
    AND __SOURCE_PREDICATE__
    AND NOT EXISTS (SELECT 1 FROM outreach_suppression_list s WHERE s.contact_id=c.id AND s.status='active')
    AND NOT EXISTS (SELECT 1 FROM channel_permissions p WHERE p.contact_id=c.id AND p.channel='whatsapp'
                      AND p.permission_status IN ('opted_out','do_not_contact'))
    AND NOT EXISTS (SELECT 1 FROM contact_activity_events e WHERE e.contact_id=c.id AND e.direction='outbound'
                      AND e.occurred_at > now() - make_interval(days =>
                          (SELECT setting_value::int FROM outreach_settings WHERE setting_key='cooldown_days')))
    AND NOT EXISTS (SELECT 1 FROM contact_sequence_enrollments en JOIN seq ON en.sequence_id=seq.sequence_id
                      WHERE en.contact_id=c.id)
    AND EXISTS (SELECT 1 FROM contact_methods m WHERE m.contact_id=c.id AND m.method_type IN ('mobile','phone','whatsapp'))
),
pick AS (
  SELECT contact_id, first_name, building_name,
         regexp_replace(coalesce(raw_number,''),'[^0-9]','','g') AS digits
  FROM cand WHERE coalesce(raw_number,'') <> ''
  ORDER BY contact_id
  LIMIT least((SELECT slots FROM remaining), __LIMIT__)
),
norm AS (
  SELECT contact_id, first_name, building_name,
    CASE WHEN length(digits)=10 THEN '91'||digits
         WHEN length(digits)=12 AND left(digits,2)='91' THEN digits
         WHEN length(digits)=11 AND left(digits,1)='0' THEN '91'||right(digits,10)
         ELSE digits END AS e164
  FROM pick
)
"""


OWNER_PREDICATE = (
    "EXISTS (SELECT 1 FROM contact_property_relationships r WHERE r.contact_id=c.id "
    "AND r.relationship_type='owner' AND r.relationship_status IN ('active','approved'))"
)


def group_predicate(slug: str) -> str:
    lit = "'" + slug.replace("'", "''") + "'"
    return (f"EXISTS (SELECT 1 FROM contact_group_members m JOIN contact_groups g ON g.id=m.group_id "
            f"WHERE m.contact_id=c.id AND g.slug={lit})")


UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def contact_predicate(contact_id: str) -> str:
    return f"c.id = '{contact_id}'::uuid"


def probe_sql(limit: int, predicate: str) -> str:
    cte = CAND_CTE.replace("__LIMIT__", str(limit)).replace("__SOURCE_PREDICATE__", predicate)
    return f"""
WITH {cte}
SELECT
  (SELECT count(*) FROM seq)                                AS active_sequences,
  (SELECT slots FROM remaining)                            AS remaining_slots_today,
  (SELECT count(*) FROM cand WHERE coalesce(raw_number,'')<>'') AS ready_candidates,
  (SELECT count(*) FROM norm)                              AS would_queue,
  (SELECT string_agg(mask_name(c.full_name), ', ')
     FROM norm n JOIN contacts c ON c.id=n.contact_id)     AS sample_masked;
"""


def apply_sql(limit: int, created_by: str, predicate: str) -> str:
    cb = "'" + created_by.replace("'", "''") + "'"
    cte = CAND_CTE.replace("__LIMIT__", str(limit)).replace("__SOURCE_PREDICATE__", predicate)
    return f"""
BEGIN;
WITH {cte},
ins_links AS (
  INSERT INTO outreach_tracked_links (contact_id, token, target_url, channel, sequence_id, sequence_step)
  SELECT n.contact_id, substr(md5(gen_random_uuid()::text),1,10),
         coalesce((SELECT link_target FROM step1),'/'), 'whatsapp_personal', (SELECT sequence_id FROM seq), 1
  FROM norm n
  RETURNING id AS link_id, contact_id, token
),
ins_enroll AS (
  INSERT INTO contact_sequence_enrollments (contact_id, sequence_id, current_step, status, next_due_at, enrolled_by)
  SELECT n.contact_id, (SELECT sequence_id FROM seq), 0, 'active', now(), {cb}
  FROM norm n
  RETURNING id AS enrollment_id, contact_id
)
INSERT INTO whatsapp_assisted_queue
  (contact_id, enrollment_id, sequence_id, sequence_step, channel, drafted_message, wa_link, tracked_link_id, queued_for_date, status)
SELECT n.contact_id, e.enrollment_id, (SELECT sequence_id FROM seq), 1, 'whatsapp_personal',
  replace(replace(replace(replace(
     (SELECT message_template FROM step1),
     '{{{{first_name}}}}', coalesce(nullif(n.first_name,''),'there')),
     '{{{{building}}}}', coalesce(n.building_name,'your building')),
     '{{{{director}}}}', coalesce((SELECT director FROM cfg),'[DIRECTOR_NAME]')),
     '{{{{link}}}}', coalesce((SELECT link_base FROM cfg),'') || l.token),
  'https://wa.me/' || n.e164, l.link_id, CURRENT_DATE, 'pending'
FROM norm n
JOIN ins_links l  ON l.contact_id  = n.contact_id
JOIN ins_enroll e ON e.contact_id = n.contact_id;

DO $$
DECLARE se text; cap int; pend int;
BEGIN
  SELECT setting_value INTO se FROM outreach_settings WHERE setting_key='send_enabled';
  SELECT setting_value::int INTO cap FROM outreach_settings WHERE setting_key='daily_send_cap';
  SELECT count(*) INTO pend FROM whatsapp_assisted_queue
    WHERE queued_for_date=CURRENT_DATE AND status IN ('pending','sent_by_human');
  IF se='true' THEN RAISE EXCEPTION 'Refusing: send_enabled must stay false.'; END IF;
  IF pend > cap THEN RAISE EXCEPTION 'Refusing: today queue % exceeds daily cap %.', pend, cap; END IF;
  IF EXISTS (SELECT 1 FROM whatsapp_assisted_queue
               WHERE status='sent_by_human' AND created_at > now() - interval '2 minutes') THEN
     RAISE EXCEPTION 'Refusing: queue builder must only create pending rows.'; END IF;
END $$;
COMMIT;

SELECT 'queued_today='||count(*) FILTER (WHERE status='pending')
     ||'  enrollments='||(SELECT count(*) FROM contact_sequence_enrollments)
     ||'  tracked_links='||(SELECT count(*) FROM outreach_tracked_links)
FROM whatsapp_assisted_queue WHERE queued_for_date=CURRENT_DATE;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build today's owners-only assisted WhatsApp queue. Dry-run by default.")
    parser.add_argument("--limit", type=int, default=10, help="Max rows to queue this run (still capped by remaining daily cap).")
    parser.add_argument("--source", choices=["owners", "group", "contact"], default="owners",
                        help="Audience source: owners (default), a contact group, or a single contact.")
    parser.add_argument("--group-slug", default=None, help="Required when --source group.")
    parser.add_argument("--contact-id", default=None, help="Required when --source contact.")
    parser.add_argument("--created-by", default="cockpit")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    if args.source == "group":
        if not args.group_slug:
            print("Refusing: --source group requires --group-slug.")
            return 2
        predicate = group_predicate(args.group_slug)
        label = f"group '{args.group_slug}'"
    elif args.source == "contact":
        if not args.contact_id or not UUID_RE.match(args.contact_id):
            print("Refusing: --source contact requires a valid --contact-id.")
            return 2
        predicate = contact_predicate(args.contact_id)
        label = "single contact"
    else:
        predicate = OWNER_PREDICATE
        label = "owners"

    print(f"Build outreach queue. source={label} requested_limit={args.limit} (also bounded by remaining daily cap).")
    code, out = run_psql(probe_sql(args.limit, predicate))
    if code != 0:
        print(f"Probe failed: {out}")
        return code
    parts = out.split("|")
    if len(parts) >= 5:
        seqs, slots, ready, would, sample = parts[0], parts[1], parts[2], parts[3], parts[4]
        print(f"  active_sequences={seqs}  remaining_slots_today={slots}  ready_candidates={ready}  would_queue={would}")
        if seqs == "0":
            print("  NOTE: no active owner sequence. Run seed_whatsapp_outreach_sequence.py --activate first.")
        if sample:
            print(f"  sample (masked): {sample}")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, out = run_psql(apply_sql(args.limit, args.created_by, predicate))
    print("\nQueue built (pending only; nothing sent):" if code == 0 else "Queue build FAILED (rolled back):")
    print(out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
