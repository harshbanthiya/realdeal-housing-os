#!/usr/bin/env python3
"""Phase 6.4 export of INTERNAL content draft artifacts to ignored exports/content/.

Dry-run by default; --apply writes files. Exports each phase-6.4 draft artifact for
the profile as a Markdown file under exports/content/ (git-ignored). File names use
only the artifact type, brief content type, and artifact UUID — never any contact
data. Each file is prefixed with 'INTERNAL DRAFT — NOT FOR PUBLISHING'. The artifact
bodies themselves contain no private contact data (only outlines / [SOURCE NEEDED]
placeholders). Prints counts only; never prints artifact bodies to stdout.
"""

from __future__ import annotations

import argparse
import base64
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
EXPORT_DIR = PROJECT_ROOT / "exports" / "content"
PHASE = "6.4"
SOURCE = "local_content_draft_workspace"
HEADER = "INTERNAL DRAFT — NOT FOR PUBLISHING\n"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


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


def fetch_sql(slug: str) -> str:
    # body base64-encoded (newlines stripped) so each row stays on one line.
    return (
        "SELECT a.id || '|' || a.artifact_type || '|' || COALESCE(cb.content_type, 'na') || '|' || "
        "replace(encode(convert_to(COALESCE(a.artifact_body, ''), 'UTF8'), 'base64'), chr(10), '') "
        "FROM content_draft_artifacts a "
        "LEFT JOIN content_briefs cb ON cb.id = a.content_brief_id "
        f"WHERE a.raw_context->>'phase' = '{PHASE}' AND a.raw_context->>'source' = '{SOURCE}' "
        "AND a.content_brief_id IN (SELECT id FROM content_briefs WHERE building_web_profile_id = "
        f"(SELECT id FROM building_web_profiles WHERE profile_slug = '" + slug.replace("'", "''") + "')) "
        "ORDER BY a.created_at;"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export internal content draft artifacts. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Export internal content draft artifacts. phase={PHASE}; target={EXPORT_DIR}. "
          "Counts only; internal drafts only; no contact data in filenames or bodies.")

    code, out = run_psql(fetch_sql(args.profile_slug))
    if code != 0:
        print(out)
        return code
    rows = [r for r in out.splitlines() if r.count("|") >= 3]
    print(f"draft artifacts to export: {len(rows)}")

    if not args.apply:
        print(f"Dry run only. No files were written. They would be written under {EXPORT_DIR} (git-ignored).")
        print("Run with --apply to write files.")
        return 0

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for r in rows:
        artifact_id, artifact_type, content_type, b64 = r.split("|", 3)
        body = base64.b64decode(b64).decode("utf-8") if b64 else ""
        fname = f"{artifact_type}__{content_type}__{artifact_id}.md"
        text = HEADER + body if not body.startswith("INTERNAL DRAFT") else body
        (EXPORT_DIR / fname).write_text(text, encoding="utf-8")
        written += 1
    print(f"files written: {written} under {EXPORT_DIR}")
    print("Reminder: exports/content/ is git-ignored; do not commit exported drafts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
