"""Queue igr_registration_search_jobs for tenancy years missing Index II coverage.

For each year that has tenancy records without rent data AND no existing queued/planned
capture job, inserts a 'planned' job for the operator to run headed Playwright capture.

Usage:
  python scripts/queue_tenancy_index2_jobs.py          # dry run — shows what would be queued
  python scripts/queue_tenancy_index2_jobs.py --apply  # write jobs to DB
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql, scalar

BUILDING_ID = 'f63d75ab-2ef9-48a9-afe2-cab3c4283283'

# Standard Kalpataru Radiance search params (CTS 260/5A, Pahadi Goregaon)
DISTRICT = 'Mumbai Suburban'
VILLAGE  = 'pahadi goregaon'
CTS      = '260/5A'


def missing_years() -> list[int]:
    """Years with tenancy records that still lack rent data and have no active job."""
    _, rows = run_psql(f"""
        SELECT DISTINCT r.registration_year
        FROM unit_registration_records r
        WHERE r.building_id = '{BUILDING_ID}'
          AND r.transaction_category = 'tenancy'
          AND r.tenancy_monthly_rent IS NULL
          AND NOT EXISTS (
            SELECT 1 FROM igr_registration_search_jobs j
            WHERE j.building_id = '{BUILDING_ID}'
              AND j.search_year = r.registration_year
              AND j.job_status NOT IN ('error')
          )
        ORDER BY 1;
    """)
    return [int(line.strip()) for line in rows.splitlines() if line.strip().isdigit()]


def queue_year(year: int, dry_run: bool) -> None:
    sql = f"""
        INSERT INTO igr_registration_search_jobs
          (building_id, search_year, district, village, property_number, job_status,
           captcha_required, external_call_made, raw_context)
        VALUES (
          '{BUILDING_ID}', {year}, '{DISTRICT}', '{VILLAGE}', '{CTS}',
          'planned', true, false,
          '{{"queued_by":"queue_tenancy_index2_jobs","purpose":"tenancy_index2"}}'::jsonb
        );
    """
    if dry_run:
        print(f"  would queue: year={year} village={VILLAGE} cts={CTS}")
    else:
        rc, out = run_psql(sql)
        if rc != 0:
            print(f"  ERROR year={year}: {out}", file=sys.stderr)
        else:
            print(f"  queued: year={year}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    years = missing_years()
    if not years:
        print("All tenancy years already have capture jobs or rent data. Nothing to queue.")
        return 0

    print(f"{'DRY RUN — ' if not args.apply else ''}Years needing capture jobs: {years}")
    for y in years:
        queue_year(y, dry_run=not args.apply)

    if not args.apply:
        print("\nPass --apply to create the jobs.")
        print("\nAfter applying, run operator capture for each year:")
        for y in years:
            print(f"  python scripts/fetch_igr_esearch_playwright.py \\")
            print(f"    --output-label kalpataru-{CTS.replace('/','_')}-{y} \\")
            print(f"    --year {y} --district '{DISTRICT}' --village '{VILLAGE}' \\")
            print(f"    --cts '{CTS}' --building-label 'Kalpataru Radiance' \\")
            print(f"    --save-html --save-visible-text --max-captures 20 --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
