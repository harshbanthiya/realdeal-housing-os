#!/usr/bin/env python3
"""Summarise canonical contacts as counts only. Read-only; no database writes.

Prints, for an optional --merge-label and/or --contact-id scope:
  canonical contact count, method count, lead requirement count, merge links
  count, source trace count, and the rollback dry-run command. Never prints
  names, phone numbers, emails, websites, or addresses.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def summary_sql(merge_label: str | None, contact_id: str | None) -> str:
    conds = []
    if merge_label:
        conds.append(f"cmb.merge_label = {sql_literal(merge_label)}")
    if contact_id:
        conds.append(f"c.id = {sql_literal(contact_id)}")
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    return f"""
WITH scope_contacts AS (
  SELECT c.id
  FROM contacts c
  LEFT JOIN canonical_merge_batches cmb ON cmb.id = c.source_merge_batch_id
  {where}
)
SELECT 'canonical_contacts' AS item, count(*) AS count FROM scope_contacts
UNION ALL SELECT 'contact_methods', count(*) FROM contact_methods WHERE contact_id IN (SELECT id FROM scope_contacts)
UNION ALL SELECT 'lead_requirements', count(*) FROM lead_requirements WHERE contact_id IN (SELECT id FROM scope_contacts)
UNION ALL SELECT 'merge_links', count(*) FROM canonical_merge_links WHERE canonical_contact_id IN (SELECT id FROM scope_contacts)
UNION ALL SELECT 'source_trace_rows', count(*) FROM vw_canonical_source_trace WHERE contact_id IN (SELECT id FROM scope_contacts)
ORDER BY item;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical contact summary. Counts only; no DB writes.")
    parser.add_argument("--merge-label")
    parser.add_argument("--contact-id")
    args = parser.parse_args()

    print("Canonical contact summary. Counts only; no raw contact values are printed.")
    if args.merge_label:
        print(f"merge_label: {args.merge_label}")
    if args.contact_id:
        print(f"contact_id: {args.contact_id}")

    code, output = run_psql(summary_sql(args.merge_label, args.contact_id))
    print(output)

    label = args.merge_label or "<MERGE_LABEL>"
    print("rollback dry-run command (does not run; review only):")
    print(
        f"  python3 scripts/rollback_canonical_merge.py "
        f"--merge-label {label} --real-ok --confirm-real-rollback"
    )
    return code

if __name__ == "__main__":
    raise SystemExit(main())
