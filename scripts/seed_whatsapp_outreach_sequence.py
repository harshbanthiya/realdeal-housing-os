#!/usr/bin/env python3
"""Phase 8.0 — Seed the "Warm Owner Greeting" assisted WhatsApp sequence. Dry-run by default.

Creates ONE owner-only sequence with two human-sent steps (warm greeting + opt-in ask, then a
gentle follow-up). Templates contain compliant opt-in/opt-out language and {{placeholders}}
({{first_name}}, {{building}}, {{director}}, {{link}}) that the queue builder resolves later.

This NEVER sends anything, never enrolls contacts, never builds a queue, and never flips
send_enabled. It only defines a sequence + steps and ensures the director-name / link-base
settings exist. Writing requires BOTH --real-ok and --apply. Idempotent on sequence name.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEQUENCE_NAME = "Warm Owner Greeting"

STEP_1 = (
    "Hi {{first_name}}, this is {{director}} from Real Deal Housing. "
    "It was a pleasure working with you at {{building}}. We occasionally share a few "
    "hand-picked property opportunities for owners in your area — would it be okay if I "
    "send you the relevant ones now and then? Just reply YES and I'll keep them useful. "
    "Reply STOP anytime and I won't message again."
)
STEP_2 = (
    "Hi {{first_name}}, just a gentle follow-up. If you'd like occasional curated updates for "
    "{{building}}-style homes, reply YES. If not, no problem at all — reply STOP and I won't "
    "reach out again. {{link}}"
)
def build_sql(director: str, link_base: str, activate: bool, created_by: str) -> str:
    name = sql_literal(SEQUENCE_NAME)
    status = sql_literal("active" if activate else "draft")
    cb = sql_literal(created_by)
    return f"""
BEGIN;
-- ensure supporting settings exist (never overwrite existing values)
INSERT INTO outreach_settings (setting_key, setting_value, notes) VALUES
  ('director_display_name', {sql_literal(director)}, 'Resolves {{{{director}}}} in assisted message templates.'),
  ('tracked_link_base_url', {sql_literal(link_base)}, 'Base URL for per-contact tracked links: base || token.')
ON CONFLICT (setting_key) DO NOTHING;

WITH up_seq AS (
  INSERT INTO outreach_sequences (name, description, channel, owner_only, status, created_by)
  VALUES ({name}, 'Warm re-introduction + opt-in ask for past owners (assisted, human-sent).',
          'whatsapp_personal', true, {status}, {cb})
  ON CONFLICT DO NOTHING
  RETURNING id
), seq AS (
  SELECT id FROM up_seq
  UNION ALL
  SELECT id FROM outreach_sequences WHERE name = {name} AND NOT EXISTS (SELECT 1 FROM up_seq)
  LIMIT 1
)
INSERT INTO outreach_sequence_steps (sequence_id, step_number, delay_days, channel, message_template, link_target, goal)
SELECT seq.id, v.step_number, v.delay_days, 'whatsapp_personal', v.tpl, v.link_target, v.goal
FROM seq, (VALUES
  (1, 0, {sql_literal(STEP_1)}, NULL::text, 'opt_in'),
  (2, 4, {sql_literal(STEP_2)}, '/', 're_engage')
) AS v(step_number, delay_days, tpl, link_target, goal)
ON CONFLICT (sequence_id, step_number) DO NOTHING;

-- guard: this script must not enable sending or create any queue/enrollment
DO $$
DECLARE se text; q int; e int;
BEGIN
  SELECT setting_value INTO se FROM outreach_settings WHERE setting_key = 'send_enabled';
  SELECT count(*) INTO q FROM whatsapp_assisted_queue;
  SELECT count(*) INTO e FROM contact_sequence_enrollments;
  IF se = 'true' THEN RAISE EXCEPTION 'Refusing: send_enabled must stay false.'; END IF;
  IF q > 0 THEN RAISE EXCEPTION 'Refusing: seed must not create queue rows (found %).', q; END IF;
  IF e > 0 THEN RAISE EXCEPTION 'Refusing: seed must not enroll contacts (found %).', e; END IF;
END $$;
COMMIT;

SELECT 'sequence='||s.status||' steps='||count(st.id)
FROM outreach_sequences s LEFT JOIN outreach_sequence_steps st ON st.sequence_id=s.id
WHERE s.name = {name} GROUP BY s.status;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the Warm Owner Greeting assisted sequence. Dry-run by default.")
    parser.add_argument("--director", default="[DIRECTOR_NAME]",
                        help="Resolves {{director}} in templates. Leave as placeholder until confirmed.")
    parser.add_argument("--link-base", default="http://localhost:3000/r/",
                        help="Base URL for tracked links (base || token).")
    parser.add_argument("--activate", action="store_true", help="Create the sequence as 'active' instead of 'draft'.")
    parser.add_argument("--created-by", default="cockpit")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Seed assisted sequence '{SEQUENCE_NAME}'. director={args.director!r} "
          f"status={'active' if args.activate else 'draft'} link_base={args.link_base!r}")
    print("Step 1 (opt-in ask) and Step 2 (follow-up, +4 days) — compliant YES/STOP language, masked in views.")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, out = run_psql(build_sql(args.director, args.link_base, args.activate, args.created_by))
    print("\nSequence seeded:" if code == 0 else "Seed FAILED (rolled back):")
    print(out)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
