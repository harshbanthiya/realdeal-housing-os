#!/usr/bin/env python3
"""Phase 6.13 cleanup: remove ONLY the parser staging rows (tagged phase=6.13/source).

Deletes rows this phase's parser created in the staging tables (rera_snapshot_review_items,
rera_snapshot_compare_results, rera_parsed_fact_candidates, rera_snapshot_captures) that are
tagged raw_context phase='6.13' AND source='rera_snapshot_parser'. It NEVER touches the Phase 6.9
manual RERA rows, never deletes snapshot files, and never updates canonical RERA/building/content
rows.

Dry-run by default; requires BOTH --apply and --real-ok to delete. Refuses if any parsed fact is
already marked safe_for_public_use=true or any review item is already approved (i.e. a human has
started accepting parser output). Prints counts only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "6.13"
SOURCE = "rera_snapshot_parser"
TAG_WHERE = f"raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}'"
# Child-first delete order to respect FKs.
PHASE_TABLES = (
    "rera_snapshot_review_items",
    "rera_snapshot_compare_results",
    "rera_parsed_fact_candidates",
    "rera_snapshot_captures",
)


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
    return "'" + str(value).replace("'", "''") + "'"


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
    return result.returncode, (result.stdout.strip() or result.stderr.strip())


def scalar(sql: str) -> int:
    code, out = run_psql(sql)
    if code != 0 or not out:
        return 0
    try:
        return int(out.splitlines()[0])
    except ValueError:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Cleanup Phase 6.13 RERA snapshot parser staging rows.")
    ap.add_argument("--snapshot-capture-id", default="")
    ap.add_argument("--profile-slug", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    args = ap.parse_args()

    # Optional scoping predicate (always combined with the phase/source tag).
    scope = ""
    if args.snapshot_capture_id:
        cid = sql_literal(args.snapshot_capture_id)
        scope = cid  # used per-table below
    profile_id = None
    if args.profile_slug:
        code, out = run_psql(
            "SELECT p.id FROM rera_project_profiles p "
            "JOIN building_web_profiles wp ON wp.id = p.building_web_profile_id "
            f"WHERE wp.profile_slug = {sql_literal(args.profile_slug)};")
        if code != 0 or not out:
            print(f"Refusing: profile slug not found: {args.profile_slug}")
            return 1
        profile_id = out.splitlines()[0]

    def table_where(table: str) -> str:
        w = TAG_WHERE
        if args.snapshot_capture_id:
            col = "id" if table == "rera_snapshot_captures" else "rera_snapshot_capture_id"
            w += f" AND {col} = {sql_literal(args.snapshot_capture_id)}"
        if profile_id and table in ("rera_parsed_fact_candidates", "rera_snapshot_compare_results"):
            w += f" AND rera_project_profile_id = {sql_literal(profile_id)}"
        return w

    # ----- safety refusals -----
    promoted = scalar(
        f"SELECT count(*) FROM rera_parsed_fact_candidates WHERE {TAG_WHERE} "
        "AND safe_for_public_use = true;")
    approved = scalar(
        f"SELECT count(*) FROM rera_snapshot_review_items WHERE {TAG_WHERE} "
        "AND status = 'approved';")
    if promoted > 0:
        print(f"Refusing: {promoted} parsed fact(s) are marked safe_for_public_use=true "
              "(human has begun accepting parser output). Not deleting.")
        return 1
    if approved > 0:
        print(f"Refusing: {approved} review item(s) already approved. Not deleting.")
        return 1

    # ----- counts of what WOULD be deleted (tagged 6.13 rows only) -----
    print(f"=== Phase 6.13 parser-staging cleanup [{'APPLY' if (args.apply and args.real_ok) else 'DRY-RUN'}] ===")
    print(f"scope: capture_id={args.snapshot_capture_id or '(all)'}  profile_slug={args.profile_slug or '(all)'}")
    print("(only rows tagged phase=6.13/source=rera_snapshot_parser; Phase 6.9 manual rows untouched)")
    total = 0
    for t in PHASE_TABLES:
        n = scalar(f"SELECT count(*) FROM {t} WHERE {table_where(t)};")
        total += n
        print(f"  {t}: {n}")
    print(f"total_rows_in_scope={total}")

    if not (args.apply and args.real_ok):
        print("DRY-RUN only: nothing deleted. Re-run with --apply --real-ok to delete. "
              "Snapshot files are never deleted.")
        return 0

    sql = ["BEGIN;"]
    for t in PHASE_TABLES:
        sql.append(f"DELETE FROM {t} WHERE {table_where(t)};")
    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"Delete FAILED (rolled back): {out[:300]}")
        return 2
    print(f"DELETED {total} tagged Phase 6.13 staging row(s). No manual rows / snapshot files touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
