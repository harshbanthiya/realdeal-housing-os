#!/usr/bin/env python3
"""Phase 5.9 — approve ONE property relationship candidate. Dry-run by default.

Approves exactly one pending Phase 5.8 property_relationship_review_item and
activates its single owner/unit relationship chain:
  property_relationship_review_items.status  pending       -> approved
  contact_property_relationships.relationship_status pending_review -> active
  building_units.canonical_status            needs_review  -> active   (this candidate's unit)
  building_aliases.status                    pending_review -> approved (this candidate's alias)
and writes a property_relationship_action_log row.

Writing requires BOTH --real-ok and --apply. Never updates contacts, contact_methods,
or source-aware audit rows. Counts only; no raw personal values; no communications.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
# Identify a genuine review-gated relationship candidate by its source marker rather
# than a specific phase value, so the script works for any phase (5.8, 5.11, ...).
CANDIDATE_SOURCE = "real_property_relationship_candidate"


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
  COALESCE((SELECT status = 'pending' FROM pr), false),
  COALESCE((SELECT raw_context->>'source' = '{CANDIDATE_SOURCE}' FROM pr), false),
  (SELECT count(*) FROM contact_property_relationships cpr JOIN pr ON pr.contact_property_relationship_id = cpr.id
     WHERE cpr.relationship_status = 'pending_review'),
  (SELECT count(*) FROM contact_property_relationships cpr JOIN pr ON pr.contact_property_relationship_id = cpr.id
     WHERE cpr.relationship_status IN ('active', 'approved')),
  (SELECT count(*) FROM contact_property_relationships cpr JOIN pr ON pr.contact_property_relationship_id = cpr.id
     JOIN contacts c ON c.id = cpr.contact_id WHERE c.is_test = false AND c.canonical_status = 'active'),
  (SELECT count(*) FROM contact_property_relationships cpr JOIN pr ON pr.contact_property_relationship_id = cpr.id
     WHERE cpr.raw_context->>'communication_sent' = 'true'),
  COALESCE((SELECT bu.canonical_status = 'needs_review' FROM building_units bu JOIN pr ON pr.building_unit_id = bu.id), false),
  COALESCE((SELECT count(*) FROM building_aliases ba JOIN pr ON true
     JOIN contact_property_relationships cpr ON cpr.id = pr.contact_property_relationship_id
     WHERE ba.building_id = cpr.building_id AND ba.metadata->>'rel_label' = cpr.raw_context->>'rel_label'
       AND ba.metadata->>'source' = '{CANDIDATE_SOURCE}' AND ba.status = 'pending_review'), 0);
"""


def apply_sql(rid: str, reviewed_by: str, decision_notes: str) -> str:
    r = sql_literal(rid)
    rb = sql_literal(reviewed_by)
    dn = sql_literal(decision_notes)
    return f"""
BEGIN;
CREATE TEMP TABLE tmp_appr AS
SELECT pr.id AS review_item_id, cpr.id AS relationship_id, cpr.building_unit_id,
       cpr.building_id, cpr.raw_context->>'rel_label' AS rel_label, pr.status AS old_review_status
FROM property_relationship_review_items pr
JOIN contact_property_relationships cpr ON cpr.id = pr.contact_property_relationship_id
JOIN contacts c ON c.id = cpr.contact_id AND c.is_test = false AND c.canonical_status = 'active'
WHERE pr.id = {r} AND pr.status = 'pending'
  AND cpr.relationship_status = 'pending_review'
  AND pr.raw_context->>'source' = '{CANDIDATE_SOURCE}';

DO $$
BEGIN
  IF (SELECT count(*) FROM tmp_appr) <> 1 THEN
    RAISE EXCEPTION 'Expected exactly 1 approvable candidate, got %.', (SELECT count(*) FROM tmp_appr);
  END IF;
  IF EXISTS (SELECT 1 FROM contact_property_relationships cpr JOIN tmp_appr t ON t.relationship_id = cpr.id
             WHERE cpr.raw_context->>'communication_sent' = 'true') THEN
    RAISE EXCEPTION 'Refusing: communication_sent=true on this relationship.';
  END IF;
END $$;

UPDATE property_relationship_review_items pr
  SET status = 'approved', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn}, updated_at = now()
  FROM tmp_appr t WHERE pr.id = t.review_item_id;

UPDATE contact_property_relationships cpr
  SET relationship_status = 'active', updated_at = now()
  FROM tmp_appr t WHERE cpr.id = t.relationship_id;

UPDATE building_units bu
  SET canonical_status = 'active', updated_at = now()
  FROM tmp_appr t WHERE bu.id = t.building_unit_id
    AND bu.canonical_status = 'needs_review' AND bu.metadata->>'source' = '{CANDIDATE_SOURCE}';

UPDATE building_aliases ba
  SET status = 'approved', updated_at = now()
  FROM tmp_appr t WHERE ba.building_id = t.building_id
    AND ba.metadata->>'rel_label' = t.rel_label AND ba.metadata->>'source' = '{CANDIDATE_SOURCE}'
    AND ba.status = 'pending_review';

INSERT INTO property_relationship_action_log (
  property_relationship_review_item_id, contact_property_relationship_id,
  old_status, new_status, action_type, reviewed_by, decision_notes, raw_context
)
SELECT t.review_item_id, t.relationship_id, t.old_review_status, 'approved',
       'approve_property_relationship', {rb}, {dn},
       jsonb_build_object('phase', '5.9', 'rel_label', t.rel_label)
FROM tmp_appr t;
COMMIT;

SELECT 'review_items_approved' AS item, count(*)::text AS val FROM property_relationship_review_items pr
  JOIN contact_property_relationships cpr ON cpr.id = pr.contact_property_relationship_id
  WHERE pr.id = {r} AND pr.status = 'approved'
UNION ALL SELECT 'relationships_active', count(*)::text FROM contact_property_relationships
  WHERE id = (SELECT contact_property_relationship_id FROM property_relationship_review_items WHERE id = {r}) AND relationship_status = 'active'
UNION ALL SELECT 'units_active', count(*)::text FROM building_units
  WHERE id = (SELECT building_unit_id FROM property_relationship_review_items WHERE id = {r}) AND canonical_status = 'active'
UNION ALL SELECT 'aliases_approved', count(*)::text FROM building_aliases ba
  JOIN contact_property_relationships cpr ON cpr.building_id = ba.building_id AND cpr.raw_context->>'rel_label' = ba.metadata->>'rel_label'
  WHERE cpr.id = (SELECT contact_property_relationship_id FROM property_relationship_review_items WHERE id = {r}) AND ba.status = 'approved'
UNION ALL SELECT 'action_log_total', count(*)::text FROM property_relationship_action_log
ORDER BY item;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve ONE property relationship candidate (review-gated). Dry-run by default.")
    parser.add_argument("--review-item-id", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--decision-notes", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Property relationship approval. review_item={args.review_item_id}. Counts only.")
    code, probe = run_psql(probe_sql(args.review_item_id))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 9:
        print("Refusing: probe returned no usable result.")
        return 1
    exists = int(f[0] or 0)
    is_pending = f[1].strip() == "t"
    is_candidate = f[2].strip() == "t"
    rel_pending = int(f[3] or 0)
    rel_active = int(f[4] or 0)
    contact_ok = int(f[5] or 0)
    comms = int(f[6] or 0)
    unit_needs_review = f[7].strip() == "t"
    alias_pending = int(f[8] or 0)

    if exists != 1:
        print("Refusing: review item not found.")
        return 1
    if not is_pending:
        print("Refusing: review item status is not 'pending'.")
        return 1
    if not is_candidate:
        print("Refusing: review item is not a real relationship candidate (source marker missing).")
        return 1
    if rel_active > 0:
        print("Refusing: the relationship is already active/approved.")
        return 1
    if rel_pending != 1:
        print("Refusing: expected exactly one pending_review relationship to activate.")
        return 1
    if contact_ok != 1:
        print("Refusing: canonical contact does not exist or is not active.")
        return 1
    if comms > 0:
        print("Refusing: communication_sent=true detected on this relationship.")
        return 1

    print("intended transitions:")
    print("  property_relationship_review_items: pending -> approved (1)")
    print("  contact_property_relationships: pending_review -> active (1)")
    print(f"  building_units: needs_review -> active ({1 if unit_needs_review else 0})")
    print(f"  building_aliases: pending_review -> approved ({alias_pending})")
    print("  property_relationship_action_log: +1 row")
    print("  contacts / contact_methods / source audit rows: untouched")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires --apply and --real-ok.")
        return 0

    code, output = run_psql(apply_sql(args.review_item_id, args.reviewed_by, args.decision_notes))
    print("Approval applied:")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
