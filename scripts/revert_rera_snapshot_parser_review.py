#!/usr/bin/env python3
"""Phase 6.14 revert: undo ONLY the Phase 6.14 parser-review changes (staging only).

Reverts exactly the rows stamped raw_context.review_phase='6.14' by
review_rera_snapshot_parser_candidates.py:
  * rera_snapshot_review_items  status (approved/needs_more_info/rejected) -> pending
  * rera_parsed_fact_candidates parse_status (matched_manual/needs_human_review/rejected) -> candidate

It NEVER touches the canonical/manual RERA tables (rera_project_profiles /
rera_building_match_candidates / rera_carpet_area_records / rera_project_status_checks /
rera_verification_review_items), buildings, content, or source gaps. It REFUSES if a canonical
RERA profile has since been verified or any RERA match accepted (i.e. downstream work already
depends on this review). Dry-run by default; requires BOTH --apply and --real-ok. Prints counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
REVIEW_PHASE = "6.14"
PHASE_WHERE = f"raw_context->>'review_phase' = '{REVIEW_PHASE}'"


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


def resolve_profile_id(slug: str) -> str | None:
    code, out = run_psql(
        "SELECT p.id FROM rera_project_profiles p "
        "JOIN building_web_profiles wp ON wp.id = p.building_web_profile_id "
        f"WHERE wp.profile_slug = {sql_literal(slug)};")
    if code != 0 or not out:
        return None
    return out.splitlines()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Revert Phase 6.14 parser-review changes (staging only).")
    ap.add_argument("--profile-slug", required=True)
    ap.add_argument("--review-item-id", action="append", default=[])
    ap.add_argument("--reviewed-by", default="operator")
    ap.add_argument("--decision-notes", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    args = ap.parse_args()

    profile_id = resolve_profile_id(args.profile_slug)
    if not profile_id:
        print(f"Refusing: profile slug not found: {args.profile_slug}")
        return 1

    # Safety refusal: do not revert if downstream canonical work already depends on this review.
    verified = scalar("SELECT count(*) FROM rera_project_profiles "
                      f"WHERE id = {sql_literal(profile_id)} AND verification_status = 'verified';")
    accepted = scalar("SELECT count(*) FROM rera_building_match_candidates "
                      "WHERE match_status = 'accepted';")
    if verified > 0:
        print("Refusing: RERA profile is now 'verified' — downstream depends on this review. Not reverting.")
        return 1
    if accepted > 0:
        print(f"Refusing: {accepted} RERA match(es) accepted — downstream depends on this review. Not reverting.")
        return 1

    # Optional id scoping (combined with the phase stamp).
    item_filter = ""
    if args.review_item_id:
        ids = ", ".join(sql_literal(x) for x in args.review_item_id)
        item_filter = f" AND id IN ({ids})"

    review_n = scalar(
        "SELECT count(*) FROM rera_snapshot_review_items "
        f"WHERE {PHASE_WHERE} AND status <> 'pending'{item_filter};")
    fact_n = scalar(
        "SELECT count(*) FROM rera_parsed_fact_candidates "
        f"WHERE {PHASE_WHERE} AND parse_status <> 'candidate';")

    mode = "APPLY" if (args.apply and args.real_ok) else "DRY-RUN"
    print(f"=== Phase 6.14 parser-review revert [{mode}] ===")
    print(f"profile_slug={args.profile_slug}")
    print("(reverts only rows stamped review_phase=6.14; canonical/manual RERA tables untouched)")
    print(f"review_items_to_revert_to_pending={review_n}")
    print(f"parsed_facts_to_revert_to_candidate={fact_n}")

    if not (args.apply and args.real_ok):
        print("DRY-RUN only: nothing changed. Re-run with --apply --real-ok to revert.")
        return 0

    notes = args.decision_notes or f"Phase {REVIEW_PHASE} review reverted"
    sql = ["BEGIN;",
           "UPDATE rera_snapshot_review_items SET status = 'pending', reviewed_at = NULL, "
           f"reviewed_by = {sql_literal(args.reviewed_by)}, decision_notes = {sql_literal(notes)}, "
           "raw_context = raw_context - 'review_phase' "
           f"WHERE {PHASE_WHERE} AND status <> 'pending'{item_filter};",
           "UPDATE rera_parsed_fact_candidates SET parse_status = 'candidate', "
           "raw_context = raw_context - 'review_phase' "
           f"WHERE {PHASE_WHERE} AND parse_status <> 'candidate';",
           "COMMIT;"]
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"Revert FAILED (rolled back): {out[:300]}")
        return 2
    print(f"REVERTED {review_n} review item(s) -> pending and {fact_n} parsed fact(s) -> candidate.")
    print("No canonical/manual RERA, building, content, or gap rows touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
