#!/usr/bin/env python3
"""Orchestrate the contact-import pipeline for one uploaded file, tracking an
import_jobs row as it progresses.

Chain (reuses the existing guarded scripts; no logic duplicated):
  normalize -> clean -> dedupe (report) -> plan (dry-run) -> stage into the
  source-aware audit/review tables.

It STOPS at the review queue: it does NOT create canonical contacts, merge,
or send anything. Canonical merge stays a separate human-reviewed step.

  fake mode  -> apply_fake_source_aware_import.py  (.example inputs only)
  real mode  -> apply_real_source_aware_import.py  (real cleaned files)

Usage:
  python3 scripts/run_import_pipeline.py --job-id <uuid> --source-file <path> \
    --batch-label <LABEL> --mode {fake,real} --output-dir <dir> --apply
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
SCRIPTS = PROJECT_ROOT / "scripts"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_* in docker/.env."
    cmd = ["docker", "exec", "-i", "-e", f"PGPASSWORD={password}", "realdeal-postgres",
           "psql", "-U", user, "-d", db_name, "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1"]
    res = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    return res.returncode, (res.stdout.rstrip("\n") or res.stderr.strip())


def job_update(job_id: str, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = {sql_literal(v)}" for k, v in fields.items())
    run_psql(f"UPDATE import_jobs SET {sets}, updated_at = now() WHERE id = {sql_literal(job_id)};")


def run_step(argv: list[str]) -> tuple[int, str]:
    res = subprocess.run(["python3", *argv], cwd=str(PROJECT_ROOT), text=True, capture_output=True, check=False)
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def grep1(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else default


def main() -> int:
    p = argparse.ArgumentParser(description="Run the contact-import pipeline for one uploaded file.")
    p.add_argument("--job-id", required=True)
    p.add_argument("--source-file", required=True)
    p.add_argument("--batch-label", required=True)
    p.add_argument("--mode", choices=["fake", "real"], default="fake")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--apply", action="store_true", help="Write staging rows; without it, stops after dedupe (dry-run).")
    args = p.parse_args()

    job, src = args.job_id, Path(args.source_file)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        job_update(job, status="failed", stage="error", error_summary="Source file not found.")
        print("Source file not found.")
        return 1

    job_update(job, status="running", stage="normalizing", batch_label=args.batch_label)

    try:
        # 1) normalize
        code, out = run_step(["scripts/normalize_contact_file.py", str(src), "--output-dir", str(outdir)])
        normalized = grep1(r"Normalized output:\s*(.+)", out)
        rows_norm = int(grep1(r"Normalized rows written:\s*(\d+)", out, "0") or "0")
        if code != 0 or not normalized:
            raise RuntimeError(out.strip().splitlines()[-1] if out.strip() else "normalize failed")
        job_update(job, rows_normalized=rows_norm, stage="cleaning")

        # 2) clean
        code, out = run_step(["scripts/clean_contacts.py", normalized, "--output-dir", str(outdir)])
        cleaned = grep1(r"Cleaned output:\s*(.+)", out)
        rows_clean = int(grep1(r"Cleaned rows written:\s*(\d+)", out, "0") or "0")
        if code != 0 or not cleaned:
            raise RuntimeError(out.strip().splitlines()[-1] if out.strip() else "clean failed")
        job_update(job, rows_cleaned=rows_clean, stage="deduping")

        # 3) dedupe report (informational)
        code, out = run_step(["scripts/contact_dedupe_report.py", cleaned, "--output-dir", str(outdir)])
        dup_pairs = sum(int(grep1(rf"Reported pairs {k}:\s*(\d+)", out, "0") or "0") for k in ("strong", "medium", "weak"))
        job_update(job, duplicate_pairs=dup_pairs, stage="planning")

        # 4) plan (dry-run, informational)
        run_step(["scripts/plan_source_aware_import.py", cleaned, "--output-dir", str(outdir)])

        if not args.apply:
            job_update(job, status="staged", stage="done", error_summary="Dry run — no staging written.")
            print("Dry run complete (no staging).")
            return 0

        # 5) stage into source-aware review tables (audited; stops at review queue)
        job_update(job, stage="staging")
        applier = "apply_fake_source_aware_import.py" if args.mode == "fake" else "apply_real_source_aware_import.py"
        ok_flag = "--fake-ok" if args.mode == "fake" else "--real-ok"
        code, out = run_step(["scripts/" + applier, cleaned, "--apply", ok_flag, "--batch-label", args.batch_label])
        if code != 0:
            raise RuntimeError(out.strip().splitlines()[-1] if out.strip() else "staging failed")

        # Count review items actually created for this batch (source of truth = DB)
        rc, cnt = run_psql(
            "SELECT count(*) FROM import_review_items iri JOIN import_batches ib ON ib.id = iri.import_batch_id "
            f"WHERE ib.metadata->>'batch_label' = {sql_literal(args.batch_label)};")
        review_items = int(cnt) if rc == 0 and cnt.isdigit() else 0

        job_update(job, status="staged", stage="done", review_items_created=review_items)
        print(f"Staged batch {args.batch_label}: {rows_clean} cleaned rows, {review_items} review items.")
        return 0

    except Exception as exc:  # noqa: BLE001 - we record any failure on the job row
        job_update(job, status="failed", stage="error", error_summary=str(exc)[:500])
        print(f"Pipeline failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
