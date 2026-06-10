#!/usr/bin/env python3
"""Phase 6.14: human review of RERA snapshot parser candidates (staging only, reversible).

Updates ONLY the Phase 6.13 parser staging review queue (rera_snapshot_review_items) and the
linked rera_parsed_fact_candidates.parse_status. It NEVER touches canonical/manual RERA tables
(rera_project_profiles / rera_building_match_candidates / rera_carpet_area_records /
rera_project_status_checks / rera_verification_review_items), buildings, content, or source gaps,
and never verifies a profile, accepts a match, merges, publishes, or sends.

Safe batch helpers:
  --approve-safe-matched   approve pending parser_manual_match_review items whose linked compare
                           is 'matched' (non-personal), and promote the mapped parsed fact to
                           matched_manual. REFUSES to touch risk/legal-count items.
  --approve-privacy-safety approve pending privacy_safety_review items ONLY when the linked fact
                           has personal_data_excluded=true AND safe_for_public_use=false. The
                           legal-count fact's parse_status stays needs_human_review (a privacy
                           confirmation is NOT a verification of the count).

Every change is stamped raw_context.review_phase='6.14' so revert_rera_snapshot_parser_review.py
can undo exactly this phase. Dry-run by default; --real-ok required; --apply to write. Prints
counts only (never personal names / page text).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
REVIEW_PHASE = "6.14"

# Map a matched compare (by its safe_summary) to the parsed fact_key it corroborates.
COMPARE_SUMMARY_TO_FACT_KEY = {
    "registration_number": "rera_registration_number",
    "project_status": "project_status",
    "registration_date": "registration_date",
    "carpet_area_record_count": "carpet_area_row_count",
    "apartment_total": "apartment_total_count",
    # 'section_presence_overlap' intentionally maps to nothing (leave facts as candidate).
}
RISK_COMPARE_TYPES = {"risk_count_compare"}
LEGAL_FACT_GROUP = "legal_risk_count"


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


def resolve_profile_id(slug: str) -> str | None:
    code, out = run_psql(
        "SELECT p.id FROM rera_project_profiles p "
        "JOIN building_web_profiles wp ON wp.id = p.building_web_profile_id "
        f"WHERE wp.profile_slug = {sql_literal(slug)};")
    if code != 0 or not out:
        return None
    return out.splitlines()[0]


def fetch_queue(profile_id: str) -> list[dict]:
    """Return review items for this profile with safe linkage fields (no personal data)."""
    sql = (
        "SELECT i.id, i.review_type, i.status, "
        "coalesce(f.id::text,''), coalesce(f.fact_group,''), coalesce(f.fact_key,''), "
        "coalesce(f.personal_data_excluded::text,''), coalesce(f.safe_for_public_use::text,''), "
        "coalesce(r.id::text,''), coalesce(r.compare_type,''), coalesce(r.compare_status,''), "
        "coalesce(r.safe_summary,''), coalesce(f.rera_snapshot_capture_id::text, r.rera_snapshot_capture_id::text, i.rera_snapshot_capture_id::text,''), "
        "coalesce(f.rera_project_profile_id::text, r.rera_project_profile_id::text,'') "
        "FROM rera_snapshot_review_items i "
        "LEFT JOIN rera_parsed_fact_candidates f ON f.id = i.rera_parsed_fact_candidate_id "
        "LEFT JOIN rera_snapshot_compare_results r ON r.id = i.rera_snapshot_compare_result_id "
        f"WHERE coalesce(f.rera_project_profile_id, r.rera_project_profile_id) = {sql_literal(profile_id)} "
        f"   OR i.rera_snapshot_capture_id IN (SELECT rera_snapshot_capture_id FROM rera_parsed_fact_candidates WHERE rera_project_profile_id = {sql_literal(profile_id)}) "
        "ORDER BY i.review_type;"
    )
    code, out = run_psql(sql)
    if code != 0 or not out:
        return []
    rows = []
    for line in out.splitlines():
        p = line.split("|")
        if len(p) < 14:
            continue
        rows.append({
            "id": p[0], "review_type": p[1], "status": p[2],
            "fact_id": p[3] or None, "fact_group": p[4], "fact_key": p[5],
            "pde": p[6] in ("t", "true"), "sfpu": p[7] in ("t", "true"),
            "compare_id": p[8] or None, "compare_type": p[9], "compare_status": p[10],
            "compare_summary": p[11], "capture_id": p[12] or None, "profile_id": p[13] or None,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Review RERA snapshot parser candidates (staging only).")
    ap.add_argument("--profile-slug", required=True)
    ap.add_argument("--review-item-id", action="append", default=[])
    ap.add_argument("--status", choices=["approved", "needs_more_info", "rejected", "pending"])
    ap.add_argument("--reviewed-by", default="operator")
    ap.add_argument("--decision-notes", default="")
    ap.add_argument("--approve-safe-matched", action="store_true")
    ap.add_argument("--approve-privacy-safety", action="store_true")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--allow-existing", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not args.real_ok:
        print("Refusing: --real-ok is required (even for the dry-run plan).")
        return 1

    profile_id = resolve_profile_id(args.profile_slug)
    if not profile_id:
        print(f"Refusing: profile slug not found: {args.profile_slug}")
        return 1

    queue = fetch_queue(profile_id)
    if not queue:
        print("No parser review items found for this profile.")
        return 0
    by_id = {r["id"]: r for r in queue}

    # ----- build selection -----
    selected: list[tuple[dict, str, str]] = []  # (row, target_status, source)

    if args.review_item_id:
        if not args.status:
            print("Refusing: --status is required when using --review-item-id.")
            return 1
        for rid in args.review_item_id:
            # allow short id prefix match
            match = [r for r in queue if r["id"] == rid or r["id"].startswith(rid)]
            if not match:
                print(f"Refusing: review item not in this profile's queue: {rid}")
                return 1
            selected.append((match[0], args.status, "manual"))

    if args.approve_safe_matched:
        for r in queue:
            if r["review_type"] == "parser_manual_match_review" and r["compare_status"] == "matched":
                selected.append((r, "approved", "safe_matched"))

    if args.approve_privacy_safety:
        for r in queue:
            if r["review_type"] == "privacy_safety_review" and r["pde"] and not r["sfpu"]:
                selected.append((r, "approved", "privacy_safety"))

    if not selected:
        print("No review items selected. Use --approve-safe-matched / --approve-privacy-safety / "
              "--review-item-id + --status.")
        return 0

    # de-dup (an item could be selected twice)
    seen = set()
    dedup = []
    for r, st, src in selected:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        dedup.append((r, st, src))
    selected = dedup

    # ----- refusals -----
    # The safe-matched path must never touch risk/legal-count items (privacy_safety items, which
    # ARE legal-count facts, are allowed here because we only confirm name exclusion, not counts).
    bad = [r for r, st, src in selected
           if src == "safe_matched"
           and (r["compare_type"] in RISK_COMPARE_TYPES or r["fact_group"] == LEGAL_FACT_GROUP)]
    if bad:
        print(f"Refusing: --approve-safe-matched must not touch risk/legal-count items "
              f"({len(bad)} found). Review those manually.")
        return 1
    if len(selected) > args.limit:
        print(f"Refusing: selection ({len(selected)}) exceeds --limit ({args.limit}).")
        return 1
    if not args.allow_existing:
        existing = [r for r, st, src in selected if r["status"] != "pending"]
        if existing:
            print(f"Refusing: {len(existing)} selected item(s) are already non-pending. "
                  "Re-run with --allow-existing to update them.")
            return 1

    # ----- plan parsed-fact promotions -----
    fact_updates: list[tuple[str, str]] = []  # (fact_id-or-capture+key marker, new_status) computed in SQL below
    promote_keys: list[tuple[str, str]] = []  # (capture_id, fact_key) -> matched_manual
    direct_fact_status: list[tuple[str, str]] = []  # (fact_id, new_status)
    for r, st, src in selected:
        if st == "approved" and r["review_type"] == "parser_manual_match_review":
            key = COMPARE_SUMMARY_TO_FACT_KEY.get(r["compare_summary"])
            if key and r["capture_id"]:
                promote_keys.append((r["capture_id"], key))
        elif st == "approved" and r["review_type"] == "privacy_safety_review":
            pass  # privacy confirmation only; legal-count fact parse_status unchanged
        elif r["fact_id"]:
            if st == "needs_more_info":
                direct_fact_status.append((r["fact_id"], "needs_human_review"))
            elif st == "rejected":
                direct_fact_status.append((r["fact_id"], "rejected"))
            elif st == "approved":
                direct_fact_status.append((r["fact_id"], "matched_manual"))

    # ----- counts -----
    plan_by_type: dict[str, int] = {}
    for r, st, src in selected:
        k = f"{r['review_type']}->{st}"
        plan_by_type[k] = plan_by_type.get(k, 0) + 1

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Phase 6.14 parser review [{mode}] ===")
    print(f"profile_slug={args.profile_slug}  reviewed_by={args.reviewed_by}")
    print(f"review_items_selected={len(selected)} (limit={args.limit})")
    for k in sorted(plan_by_type):
        print(f"  {k}: {plan_by_type[k]}")
    print(f"parsed_fact_promotions_matched_manual={len(promote_keys)}")
    print(f"parsed_fact_direct_status_changes={len(direct_fact_status)}")
    print("canonical RERA tables: untouched (no profile verify / match accept / merge / publish)")

    if not args.apply:
        print("DRY-RUN only: no DB writes. Re-run with --apply to write.")
        return 0

    # ----- emit transaction -----
    notes = args.decision_notes or f"Phase {REVIEW_PHASE} parser review"
    stamp = f"jsonb_build_object('review_phase','{REVIEW_PHASE}','reviewed_by',{sql_literal(args.reviewed_by)})"
    sql = ["BEGIN;"]
    for r, st, src in selected:
        sql.append(
            "UPDATE rera_snapshot_review_items SET "
            f"status = {sql_literal(st)}, reviewed_by = {sql_literal(args.reviewed_by)}, "
            f"reviewed_at = now(), decision_notes = {sql_literal(notes)}, "
            f"raw_context = coalesce(raw_context,'{{}}'::jsonb) || {stamp} "
            f"WHERE id = {sql_literal(r['id'])};")
    for capture_id, key in promote_keys:
        sql.append(
            "UPDATE rera_parsed_fact_candidates SET parse_status = 'matched_manual', "
            f"raw_context = coalesce(raw_context,'{{}}'::jsonb) || {stamp} "
            f"WHERE rera_snapshot_capture_id = {sql_literal(capture_id)} "
            f"AND fact_key = {sql_literal(key)} AND parse_status = 'candidate';")
    for fact_id, new_status in direct_fact_status:
        sql.append(
            f"UPDATE rera_parsed_fact_candidates SET parse_status = {sql_literal(new_status)}, "
            f"raw_context = coalesce(raw_context,'{{}}'::jsonb) || {stamp} "
            f"WHERE id = {sql_literal(fact_id)};")
    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"DB write FAILED (rolled back): {out[:300]}")
        return 2
    print("APPLIED: review items + linked parsed-fact statuses updated (stamped review_phase=6.14).")
    print("No canonical RERA/building/content/gap rows changed. ready_* flags remain false.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
