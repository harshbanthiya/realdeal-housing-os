"""Seed igr_registration_search_jobs with Index II fetch jobs.

Finds unit_registration_records that have a doc_number but no index2_file_path
(not yet fetched), then creates a queued igr_registration_search_jobs row for each.
The worker surfaces these in /cockpit/jobs so the operator can fetch them one by one.

Idempotent: skips rows where a job already exists (matched by building_id + doc_number).

Usage:
  python scripts/seed_index2_fetch_queue.py          # dry run — shows what would be queued
  python scripts/seed_index2_fetch_queue.py --apply  # write jobs to DB
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import run_psql  # noqa: E402

_COUNT_SQL = """
SELECT COUNT(*) FROM unit_registration_records urr
WHERE urr.doc_number IS NOT NULL
  AND urr.index2_file_path IS NULL
  AND urr.verification_status = 'unparsed'
  AND NOT EXISTS (
    SELECT 1 FROM igr_registration_search_jobs j
    WHERE j.building_id = urr.building_id
      AND j.raw_context->>'doc_number' = urr.doc_number
      AND j.raw_context->>'job_type' = 'index2_fetch'
  );
"""

_PREVIEW_SQL = """
SELECT urr.doc_number, urr.registration_year, b.name AS building_name
FROM unit_registration_records urr
JOIN buildings b ON b.id = urr.building_id
WHERE urr.doc_number IS NOT NULL
  AND urr.index2_file_path IS NULL
  AND urr.verification_status = 'unparsed'
  AND NOT EXISTS (
    SELECT 1 FROM igr_registration_search_jobs j
    WHERE j.building_id = urr.building_id
      AND j.raw_context->>'doc_number' = urr.doc_number
      AND j.raw_context->>'job_type' = 'index2_fetch'
  )
ORDER BY urr.registration_year DESC, urr.doc_number
LIMIT 50;
"""

_INSERT_SQL = """
INSERT INTO igr_registration_search_jobs (
  building_id, search_year, job_status, captcha_required, raw_context
)
SELECT DISTINCT
  urr.building_id,
  urr.registration_year,
  'queued',
  true,
  jsonb_build_object(
    'job_type',  'index2_fetch',
    'doc_number', urr.doc_number,
    'source',    'unit_registration_records'
  )
FROM unit_registration_records urr
WHERE urr.doc_number IS NOT NULL
  AND urr.index2_file_path IS NULL
  AND urr.verification_status = 'unparsed'
  AND NOT EXISTS (
    SELECT 1 FROM igr_registration_search_jobs j
    WHERE j.building_id = urr.building_id
      AND j.raw_context->>'doc_number' = urr.doc_number
      AND j.raw_context->>'job_type' = 'index2_fetch'
  );
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write jobs to DB (default: dry run)")
    args = ap.parse_args()

    code, out = run_psql(_COUNT_SQL)
    if code != 0:
        print(f"DB error: {out}")
        return 1

    pending = int(out.strip() or "0")
    print(f"Pending Index II fetch jobs to create: {pending}")

    if pending == 0:
        print("Nothing to do.")
        return 0

    # Preview first few
    _, preview = run_psql(_PREVIEW_SQL)
    if preview:
        print("\nSample (up to 50):")
        for line in preview.splitlines():
            print(" ", line)

    if not args.apply:
        print(f"\nDry run — {pending} job(s) would be queued. Re-run with --apply to write.")
        return 0

    code, out = run_psql(_INSERT_SQL)
    if code != 0:
        print(f"Insert failed: {out}")
        return 1

    print(f"\nQueued {pending} Index II fetch job(s).")
    print("rows_queued:", pending)
    return 0


if __name__ == "__main__":
    sys.exit(main())
