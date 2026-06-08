#!/usr/bin/env python3
"""Phase 5.9 — revert ONE property relationship approval. Dry-run by default.

Reverses exactly the Phase 5.9 approval for one review item, restoring the candidate
to its review state (no rows are deleted):
  property_relationship_review_items.status  approved -> pending
  contact_property_relationships.relationship_status active -> pending_review
  building_units.canonical_status            active   -> needs_review (this candidate's unit)
  building_aliases.status                    approved -> pending_review (this candidate's alias)
and writes a property_relationship_action_log row.

Writing requires BOTH --real-ok and --apply. Refuses if any communication was sent or
if downstream activity is detected (an action_log entry other than this approval).
Never touches canonical contacts or source-aware rows. Counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
EXPECTED_PHASE = "5.8"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


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


def probe_sql(rid: str) -> str:
    r = sql_literal(rid)
    return f"""
WITH pr AS (SELECT * FROM property_relationship_review_items WHERE id = {r})
SELECT
  (SELECT count(*) FROM pr),
  COALESCE((SELECT status = 'approved' FROM pr), false),
  (SELECT count(*) FROM contact_property_relationships cpr JOIN pr ON pr.contact_property_relationship_id = cpr.id
     WHERE cpr.relationship_status = 'active'),
  (SELECT count(*) FROM contact_property_relationships cpr JOIN pr ON pr.contact_property_relationship_id = cpr.id
     WHERE cpr.raw_context->>'communication_sent' = 'true'),
  COALESCE((SELECT bu.canonical_status = 'active' FROM building_units bu JOIN pr ON pr.building_unit_id = bu.id), false),
  COALESCE((SELECT count(*) FROM building_aliases ba
     JOIN contact_property_relationships cpr ON cpr.building_id = ba.building_id AND cpr.raw_context->>'rel_label' = ba.metadata->>'rel_label'
     JOIN pr ON pr.contact_property_relationship_id = cpr.id
     WHERE ba.metadata->>'phase' = '{EXPECTED_PHASE}' AND ba.status = 'approved'), 0),
  (SELECT count(*) FROM property_relationship_action_log pal JOIN pr ON pr.contact_property_relationship_id = pal.contact_property_relationship_id
     WHERE pal.action_type NOT IN ('approve_property_relationship', 'revert_property_relationship'));
"""


def apply_sql(rid: str, reviewed_by: str, decision_notes: str) -> str:
    r = sql_literal(rid)
    rb = sql_literal(reviewed_by)
    dn = sql_literal(decision_notes)
    return f"""
BEGIN;
CREATE TEMP TABLE tmp_rev AS
SELECT pr.id AS review_item_id, cpr.id AS relationship_id, cpr.building_unit_id,
       cpr.building_id, cpr.raw_context->>'rel_label' AS rel_label
FROM property_relationship_review_items pr
JOIN contact_property_relationships cpr ON cpr.id = pr.contact_property_relationship_id
WHERE pr.id = {r} AND pr.status = 'approved' AND cpr.relationship_status = 'active'
  AND pr.raw_context->>'phase' = '{EXPECTED_PHASE}';

DO $$
BEGIN
  IF (SELECT count(*) FROM tmp_rev) <> 1 THEN
    RAISE EXCEPTION 'Expected exactly 1 revertable approval, got %.', (SELECT count(*) FROM tmp_rev);
  END IF;
  IF EXISTS (SELECT 1 FROM contact_property_relationships cpr JOIN tmp_rev t ON t.relationship_id = cpr.id
             WHERE cpr.raw_context->>'communication_sent' = 'true') THEN
    RAISE EXCEPTION 'Refusing: communication_sent=true on this relationship.';
  END IF;
  IF EXISTS (SELECT 1 FROM property_relationship_action_log pal JOIN tmp_rev t ON t.relationship_id = pal.contact_property_relationship_id
             WHERE pal.action_type NOT IN ('approve_property_relationship', 'revert_property_relationship')) THEN
    RAISE EXCEPTION 'Refusing: downstream action-log activity detected for this relationship.';
  END IF;
END $$;

UPDATE property_relationship_review_items pr
  SET status = 'pending', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn}, updated_at = now()
  FROM tmp_rev t WHERE pr.id = t.review_item_id;

UPDATE contact_property_relationships cpr
  SET relationship_status = 'pending_review', updated_at = now()
  FROM tmp_rev t WHERE cpr.id = t.relationship_id;

UPDATE building_units bu
  SET canonical_status = 'needs_review', updated_at = now()
  FROM tmp_rev t WHERE bu.id = t.building_unit_id
    AND bu.canonical_status = 'active' AND bu.metadata->>'phase' = '{EXPECTED_PHASE}';

UPDATE building_aliases ba
  SET status = 'pending_review', updated_at = now()
  FROM tmp_rev t WHERE ba.building_id = t.building_id
    AND ba.metadata->>'rel_label' = t.rel_label AND ba.metadata->>'phase' = '{EXPECTED_PHASE}'
    AND ba.status = 'approved';

INSERT INTO property_relationship_action_log (
  property_relationship_review_item_id, contact_property_relationship_id,
  old_status, new_status, action_type, reviewed_by, decision_notes, raw_context
)
SELECT t.review_item_id, t.relationship_id, 'approved', 'pending',
       'revert_property_relationship', {rb}, {dn},
       jsonb_build_object('phase', '5.9', 'rel_label', t.rel_label)
FROM tmp_rev t;
COMMIT;

SELECT 'review_items_pending' AS item, count(*)::text AS val FROM property_relationship_review_items WHERE id = {r} AND status = 'pending'
UNION ALL SELECT 'relationships_pending_review', count(*)::text FROM contact_property_relationships
  WHERE id = (SELECT contact_property_relationship_id FROM property_relationship_review_items WHERE id = {r}) AND relationship_status = 'pending_review'
UNION ALL SELECT 'action_log_total', count(*)::text FROM property_relationship_action_log
ORDER BY item;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Revert ONE Phase 5.9 property relationship approval. Dry-run by default.")
    parser.add_argument("--review-item-id", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--decision-notes", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Phase 5.9 property relationship approval REVERT. review_item={args.review_item_id}. Counts only.")
    code, probe = run_psql(probe_sql(args.review_item_id))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 7:
        print("Refusing: probe returned no usable result.")
        return 1
    exists = int(f[0] or 0)
    is_approved = f[1].strip() == "t"
    rel_active = int(f[2] or 0)
    comms = int(f[3] or 0)
    unit_active = f[4].strip() == "t"
    alias_approved = int(f[5] or 0)
    downstream = int(f[6] or 0)

    if exists != 1:
        print("Refusing: review item not found.")
        return 1
    if not is_approved or rel_active != 1:
        print("Refusing: nothing to revert (review item not approved or relationship not active).")
        return 1
    if comms > 0:
        print("Refusing: communication_sent=true detected; not reverting.")
        return 1
    if downstream > 0:
        print("Refusing: downstream action-log activity detected for this relationship.")
        return 1

    print("would revert:")
    print("  property_relationship_review_items: approved -> pending (1)")
    print("  contact_property_relationships: active -> pending_review (1)")
    print(f"  building_units: active -> needs_review ({1 if unit_active else 0})")
    print(f"  building_aliases: approved -> pending_review ({alias_approved})")
    print("  property_relationship_action_log: +1 row")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Reverting requires --apply and --real-ok.")
        return 0

    code, output = run_psql(apply_sql(args.review_item_id, args.reviewed_by, args.decision_notes))
    print("Revert applied:")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
