"""IGR job worker — polls igr_registration_search_jobs and dispatches parsers.

States handled:
  captured  → runs parse_igr_results_to_staging.py or parse_igr_index2_pdfs.py
                (detected by presence of .pdf files in snapshot_path → index2,
                 else → results list)
  queued    → logs "needs operator" (capture is interactive/headed, not automated here)
  captcha_required → skips silently (waits for cockpit signal back to queued)
  all others → skips

Usage:
  python scripts/worker.py           # run once (cron/loop friendly)
  python scripts/worker.py --watch   # poll loop (30s sleep between ticks)
  python scripts/worker.py --dry-run # print what would run, touch nothing
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))
from _db import run_psql  # noqa: E402

# ponytail: single SQL statement → atomic claim, safe for one worker process
# upgrade: FOR UPDATE SKIP LOCKED via psycopg2 when running multiple workers
_CLAIM_SQL = """
WITH claimed AS (
  UPDATE igr_registration_search_jobs
  SET job_status = 'running', attempted_at = now(), updated_at = now()
  WHERE id = (
    SELECT id FROM igr_registration_search_jobs
    WHERE job_status = 'captured'
    ORDER BY created_at LIMIT 1
  )
  RETURNING id, snapshot_path, job_status
)
SELECT id, snapshot_path FROM claimed;
"""

_STATUS_SQL = """
UPDATE igr_registration_search_jobs
SET job_status = '{status}', updated_at = now()
WHERE id = '{job_id}';
"""

_QUEUE_COUNT_SQL = """
SELECT job_status, COUNT(*) as n
FROM igr_registration_search_jobs
GROUP BY job_status ORDER BY job_status;
"""


def _set_status(job_id: str, status: str, error: str | None = None) -> None:
    run_psql(_STATUS_SQL.format(status=status, job_id=job_id))


def _dispatch(job_id: str, snapshot_path: str, dry_run: bool) -> None:
    path = Path(snapshot_path)
    if not path.exists():
        print(f"  [ERROR] snapshot_path not found: {snapshot_path}")
        if not dry_run:
            _set_status(job_id, "error", f"snapshot_path missing: {snapshot_path}")
        return

    # Prefer metadata.json capture_type over heuristic PDF check
    meta_path = path / "metadata.json"
    capture_type = None
    if meta_path.exists():
        try:
            import json as _json
            capture_type = _json.loads(meta_path.read_text()).get("capture_type")
        except Exception:  # noqa: BLE001
            pass

    if capture_type == "index2" or (capture_type is None and (any(path.glob("*.pdf")) or any(path.glob("**/*.pdf")))):
        script = "parse_igr_index2_pdfs.py"
        cmd = [sys.executable, str(SCRIPTS / script), "--page-dir", str(path), "--apply", "--real-ok"]
    else:
        script = "parse_igr_results_to_staging.py"
        cmd = [sys.executable, str(SCRIPTS / script), "--snapshot-dir", str(path), "--apply", "--real-ok"]

    print(f"  → {script} {path.name}")
    if dry_run:
        return

    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode == 0:
        _set_status(job_id, "parsed")
        print(f"  ✓ parsed")
    else:
        _set_status(job_id, "error", f"{script} exited {result.returncode}")
        print(f"  ✗ {script} exited {result.returncode}")


def _show_queue() -> None:
    code, out = run_psql(_QUEUE_COUNT_SQL)
    if code != 0 or not out:
        print("  (no rows / DB unavailable)")
        return
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) == 2:
            print(f"  {parts[0]:<22} {parts[1]}")


def run_once(dry_run: bool = False) -> bool:
    """Claim and dispatch one captured job. Returns True if a job was processed."""
    # Report queue state first
    print("Queue:")
    _show_queue()

    if dry_run:
        # In dry-run, show what's captured without claiming
        code, out = run_psql(
            "SELECT id, snapshot_path FROM igr_registration_search_jobs "
            "WHERE job_status='captured' ORDER BY created_at LIMIT 1;"
        )
        if code == 0 and out:
            parts = out.splitlines()[0].split("|")
            if len(parts) >= 2:
                print(f"\nWould dispatch: {parts[0][:8]}… → {parts[1]}")
            else:
                print("\nNo captured jobs to dispatch.")
        else:
            print("\nNo captured jobs to dispatch.")
        return False

    code, out = run_psql(_CLAIM_SQL)
    if code != 0 or not out:
        return False

    parts = out.splitlines()[0].split("|")
    if len(parts) < 2:
        return False

    job_id, snapshot_path = parts[0].strip(), parts[1].strip()
    print(f"\nDispatching {job_id[:8]}…")
    _dispatch(job_id, snapshot_path, dry_run=False)
    return True


def resume_job(job_id: str) -> int:
    """Set a captcha_required job back to queued so the worker picks it up."""
    # Validate UUID-ish to prevent injection (not full RFC 4122, good enough)
    if not all(c in "0123456789abcdef-" for c in job_id.lower()) or len(job_id) != 36:
        print(f"Invalid job_id: {job_id}")
        return 1
    code, out = run_psql(f"""
        UPDATE igr_registration_search_jobs
        SET job_status = 'queued', updated_at = now()
        WHERE id = '{job_id}' AND job_status = 'captcha_required'
        RETURNING id;
    """)
    if code != 0:
        print(f"DB error: {out}")
        return 1
    if out.strip():
        print(f"resumed: {job_id}")
        return 0
    print(f"not_found_or_wrong_status: {job_id}")
    return 1


def list_paused() -> None:
    code, out = run_psql(
        "SELECT id, building_id, village, property_number, attempted_at "
        "FROM igr_registration_search_jobs WHERE job_status='captcha_required' ORDER BY attempted_at;"
    )
    if code != 0 or not out:
        print("No captcha_required jobs.")
        return
    for line in out.splitlines():
        print(" ", line)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Print actions, touch nothing")
    ap.add_argument("--watch", action="store_true", help="Poll loop (Ctrl-C to stop)")
    ap.add_argument("--resume", metavar="JOB_ID", help="Resume a captcha_required job (sets→queued)")
    ap.add_argument("--list-paused", action="store_true", help="List captcha_required jobs")
    args = ap.parse_args()

    if args.resume:
        return resume_job(args.resume)

    if args.list_paused:
        list_paused()
        return 0

    if args.dry_run:
        print("DRY RUN — no DB writes, no script execution\n")
        run_once(dry_run=True)
        return 0

    if args.watch:
        print("Worker started — polling igr_registration_search_jobs (Ctrl-C to stop)")
        while True:
            try:
                run_once()
                time.sleep(30)  # ponytail: 30s poll; upgrade to pg LISTEN/NOTIFY if latency matters
            except KeyboardInterrupt:
                print("\nStopped.")
                return 0
    else:
        run_once()
        return 0


if __name__ == "__main__":
    sys.exit(main())
