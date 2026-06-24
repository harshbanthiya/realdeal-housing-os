"""Promote stale duplicate_doc_number records to parsed_candidate.

Pre-consolidation, the parser flagged records as duplicate_doc_number when the
same doc_number appeared across multiple building rows. After consolidation to 1
Kalpataru building, 153 of these appear only once — they are valid unique records.
The remaining 8 pairs are multi-property IGR docs (same deed, multiple units) or
will be caught in downstream review as parsed_candidate.

Usage:
  python scripts/promote_duplicate_doc_records.py          # dry run
  python scripts/promote_duplicate_doc_records.py --apply  # write
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql, scalar

BUILDING_ID = 'f63d75ab-2ef9-48a9-afe2-cab3c4283283'

COUNT_SQL = f"""
SELECT COUNT(*) FROM unit_registration_records
WHERE building_id='{BUILDING_ID}' AND verification_status='duplicate_doc_number'
"""

PROMOTE_SQL = f"""
UPDATE unit_registration_records
SET verification_status = 'parsed_candidate'
WHERE building_id='{BUILDING_ID}' AND verification_status = 'duplicate_doc_number'
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    count = scalar(COUNT_SQL)
    print(f"Records to promote: {count}")
    if count == 0:
        print("Nothing to do.")
        return 0

    if not args.apply:
        print("Dry run — pass --apply to write.")
        return 0

    rc, out = run_psql(PROMOTE_SQL)
    if rc != 0:
        print(f"ERROR: {out}", file=sys.stderr)
        return rc
    print(f"Promoted {count} records → parsed_candidate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
