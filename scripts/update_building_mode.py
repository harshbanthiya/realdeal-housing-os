#!/usr/bin/env python3
"""Safely update a building's lifecycle mode in launch_projects."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"

ALLOWED_MODES = {"prospecting", "active", "launch", "post_launch"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,80}[a-z0-9]$")


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i",
        "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql",
        "-U", user, "-d", db_name,
        "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.rstrip("\n") or result.stderr.strip()


def fetch_current(slug: str) -> tuple[int, str | None, str | None]:
    """Return (code, current_mode, project_id) for the given slug."""
    sql = f"SELECT mode::text, id::text FROM launch_projects WHERE launch_key = {sql_literal(slug)} LIMIT 1;"
    code, out = run_psql(sql)
    if code != 0:
        return code, None, None
    if not out:
        return 0, None, None  # no row found
    parts = out.split("\t")
    mode = parts[0].strip() if parts else None
    proj_id = parts[1].strip() if len(parts) > 1 else None
    return 0, mode, proj_id


def update_mode(slug: str, new_mode: str) -> tuple[int, str]:
    sql = (
        f"UPDATE launch_projects SET mode = {sql_literal(new_mode)}, updated_at = NOW() "
        f"WHERE launch_key = {sql_literal(slug)} RETURNING launch_key::text, mode::text;"
    )
    return run_psql(sql)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update launch_projects.mode for a building. Dry-run by default."
    )
    parser.add_argument("--slug", required=True, help="building slug (= launch_key)")
    parser.add_argument("--mode", required=True, help="new mode: prospecting|active|launch|post_launch")
    parser.add_argument("--apply", action="store_true", help="commit the write (default: dry-run)")
    args = parser.parse_args()

    if not SLUG_RE.match(args.slug):
        print("Invalid slug format.")
        return 1
    if args.mode not in ALLOWED_MODES:
        print(f"Invalid mode: {args.mode!r}. Allowed: {', '.join(sorted(ALLOWED_MODES))}")
        return 1

    code, current_mode, project_id = fetch_current(args.slug)
    if code != 0:
        print(f"DB error: {current_mode}")
        return code

    if current_mode is None:
        print(f"No launch_project found for slug {args.slug!r} (legacy building — mode is read-only).")
        print(f"slug: {args.slug}")
        print(f"requested_mode: {args.mode}")
        print("rows_updated: 0")
        return 0  # not an error — just a no-op

    print(f"slug: {args.slug}")
    print(f"project_id: {project_id}")
    print(f"old_mode: {current_mode}")
    print(f"new_mode: {args.mode}")

    if current_mode == args.mode:
        print("rows_updated: 0")
        print("note: already set to requested mode — no change needed")
        return 0

    if not args.apply:
        print("rows_updated: 0")
        print("dry_run: true")
        print(f"note: would set mode {current_mode!r} → {args.mode!r} (pass --apply to write)")
        return 0

    code, out = update_mode(args.slug, args.mode)
    if code != 0:
        print(f"Update failed: {out}")
        return code

    print("rows_updated: 1")
    print("dry_run: false")
    print(f"note: mode updated {current_mode!r} → {args.mode!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
