#!/usr/bin/env python3
"""Phase 6.6 internal-evidence acceptance review. Dry-run by default.

Reviews `internal_source_evidence` candidates created in Phase 6.5 and records a human
decision (accepted / rejected / needs_review) for a chosen, tiny set of rows — so the
system knows which purely-internal, non-personal facts can be trusted for future
content drafting. When evidence is accepted/rejected/needs_review, the linked
`source_gap_review_items` of type `internal_evidence_review` is moved accordingly
(pending -> approved / rejected / needs_more_info).

It does NOT resolve source gaps, change resolution-task status, mark content
ready_for_ai_draft/public_ready, publish, or send anything; it makes no AI/external/web
calls. Every change is tagged in raw_context with an `evidence_review_phase=6.6` marker
(plus the previous status) so Phase 6.6 changes are reversible. Writing requires
--real-ok AND --apply. Counts only; no raw personal values are printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.6"
SOURCE = "internal_evidence_acceptance"

# Count-based / structural evidence considered safe for the auto-select "safe batch".
SAFE_BATCH_TYPES = ("source_batch_count", "unit_count", "building_alias")

# Evidence status -> target status for a linked internal_evidence_review (from pending).
STATUS_TO_REVIEW = {
    "accepted": "approved",
    "rejected": "rejected",
    "needs_review": "needs_more_info",
}

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
# Evidence belonging to the profile: evidence -> gap -> brief -> building_web_profile.
def profile_scope(slug: str) -> str:
    return (
        "e.content_source_gap_item_id IN ("
        "  SELECT g.id FROM content_source_gap_items g"
        "  JOIN content_briefs cb ON cb.id = g.content_brief_id"
        "  JOIN building_web_profiles p ON p.id = cb.building_web_profile_id"
        f"  WHERE p.profile_slug = {sql_literal(slug)})"
    )

# Phone-/email-like patterns in a safe summary are a hard stop.
PII_PREDICATE = (
    "(e.safe_summary ~* '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}' "
    "OR e.safe_summary ~ '[0-9][0-9 ()+.-]{7,}[0-9]')"
)

def target_cte(slug: str, args) -> str:
    """CTE `tgt(id)` listing the evidence rows this run targets."""
    scope = profile_scope(slug)
    status_filter = "" if args.allow_existing else "AND e.evidence_status = 'candidate'"
    if args.accept_safe_batch:
        types = ",".join(sql_literal(t) for t in SAFE_BATCH_TYPES)
        return (
            "WITH tgt AS (\n"
            "  SELECT e.id FROM internal_source_evidence e\n"
            f"  WHERE {scope} {status_filter}\n"
            f"    AND e.evidence_type IN ({types})\n"
            "  ORDER BY array_position(ARRAY['source_batch_count','unit_count','building_alias']::text[], e.evidence_type), e.created_at\n"
            f"  LIMIT {int(args.limit)}\n)"
        )
    ids = ",".join(sql_literal(i) for i in args.evidence_ids)
    return (
        "WITH tgt AS (\n"
        "  SELECT e.id FROM internal_source_evidence e\n"
        f"  WHERE {scope} {status_filter} AND e.id IN ({ids})\n)"
    )

def precheck_sql(slug: str, args) -> str:
    """One query returning labelled validation counts."""
    cte = target_cte(slug, args)
    requested = "NULL" if args.accept_safe_batch else str(len(args.evidence_ids))
    return f"""{cte}
SELECT 'profile_found' k, count(*)::text v FROM building_web_profiles WHERE profile_slug = {sql_literal(slug)}
UNION ALL SELECT 'target_count', count(*)::text FROM tgt
UNION ALL SELECT 'requested_count', {sql_literal('') if args.accept_safe_batch else "'" + requested + "'"}::text
UNION ALL SELECT 'non_candidate_in_targets', count(*)::text FROM internal_source_evidence e
   WHERE e.id IN (SELECT id FROM tgt) AND e.evidence_status <> 'candidate'
UNION ALL SELECT 'pii_in_targets', count(*)::text FROM internal_source_evidence e
   WHERE e.id IN (SELECT id FROM tgt) AND {PII_PREDICATE}
UNION ALL SELECT 'outside_profile', count(*)::text FROM internal_source_evidence e
   WHERE e.id IN (SELECT id FROM tgt) AND NOT ({profile_scope(slug)})
ORDER BY k;"""

def target_list_sql(slug: str, args) -> str:
    cte = target_cte(slug, args)
    return f"""{cte}
SELECT e.id::text, e.evidence_type, e.evidence_status
FROM internal_source_evidence e WHERE e.id IN (SELECT id FROM tgt)
ORDER BY e.evidence_type, e.id;"""

def apply_sql(slug: str, args) -> str:
    cte = target_cte(slug, args)
    review_target = STATUS_TO_REVIEW[args.status]
    marker_ev = (
        "jsonb_build_object('evidence_review_phase', '%s', 'evidence_review_source', '%s', "
        "'evidence_review_prev_status', e.evidence_status, 'evidence_reviewed_by', %s)"
        % (PHASE, SOURCE, sql_literal(args.reviewed_by))
    )
    marker_rv = (
        "jsonb_build_object('evidence_review_phase', '%s', 'evidence_review_source', '%s', "
        "'evidence_review_prev_status', r.status)" % (PHASE, SOURCE)
    )
    notes = sql_literal(args.decision_notes)
    reviewer = sql_literal(args.reviewed_by)
    return f"""{cte},
upd_ev AS (
  UPDATE internal_source_evidence e
     SET evidence_status = {sql_literal(args.status)},
         raw_context = e.raw_context || {marker_ev}
   WHERE e.id IN (SELECT id FROM tgt)
   RETURNING e.id, e.content_source_gap_item_id
),
upd_rv AS (
  UPDATE source_gap_review_items r
     SET status = {sql_literal(review_target)},
         reviewed_by = {reviewer},
         reviewed_at = now(),
         decision_notes = {notes},
         raw_context = r.raw_context || {marker_rv}
   WHERE r.review_type = 'internal_evidence_review'
     AND r.status = 'pending'
     AND r.content_source_gap_item_id IN (SELECT content_source_gap_item_id FROM upd_ev)
   RETURNING r.id
)
SELECT 'evidence_updated' k, count(*)::text v FROM upd_ev
UNION ALL SELECT 'reviews_updated', count(*)::text FROM upd_rv
ORDER BY k;"""

def status_counts_sql() -> str:
    return (
        "SELECT 'evidence:'||evidence_status k, count(*)::text v FROM internal_source_evidence GROUP BY 1\n"
        "UNION ALL SELECT 'ievreview:'||status, count(*)::text FROM source_gap_review_items "
        "WHERE review_type='internal_evidence_review' GROUP BY 1\n"
        "ORDER BY k;"
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Review/accept internal source evidence. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--evidence-id", default="", help="comma-separated evidence UUIDs")
    parser.add_argument("--status", default="accepted", choices=["accepted", "rejected", "needs_review"])
    parser.add_argument("--reviewed-by", default="phase_6_6_reviewer")
    parser.add_argument("--decision-notes", default="Phase 6.6 internal evidence review.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--accept-safe-batch", action="store_true",
                        help="auto-select safe count-based evidence up to --limit (forces status=accepted)")
    parser.add_argument("--allow-existing", action="store_true",
                        help="permit updating evidence that is not currently 'candidate'")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.accept_safe_batch:
        args.status = "accepted"
    args.evidence_ids = [s.strip() for s in args.evidence_id.split(",") if s.strip()]

    print(f"Internal evidence review. phase={PHASE}; profile_slug={args.profile_slug}; status={args.status}; "
          f"limit={args.limit}; mode={'safe-batch' if args.accept_safe_batch else 'explicit-ids'}. "
          "Counts only; gaps stay open; tasks stay pending; no AI/external calls; nothing published or sent.")

    if not args.real_ok:
        print("Refusing: --real-ok is required to operate on real evidence.")
        return 1
    if not args.accept_safe_batch and not args.evidence_ids:
        print("Refusing: provide --evidence-id <uuid[,uuid...]> or --accept-safe-batch.")
        return 1
    for i in args.evidence_ids:
        if not UUID_RE.match(i):
            print(f"Refusing: '{i}' is not a valid UUID.")
            return 1

    code, found = run_psql(precheck_sql(args.profile_slug, args))
    if code != 0:
        print(found)
        return code
    checks = dict(line.split("|", 1) for line in found.splitlines() if "|" in line)

    if checks.get("profile_found", "0") != "1":
        print(f"Refusing: profile_slug {args.profile_slug} not found.")
        return 1
    target_count = int(checks.get("target_count", "0"))
    if target_count == 0:
        print("Refusing: no matching evidence rows to review (already reviewed, or IDs/filter matched nothing).")
        print(found)
        return 1
    if not args.accept_safe_batch and target_count != len(args.evidence_ids):
        print(f"Refusing: {len(args.evidence_ids)} evidence id(s) requested but {target_count} matched in-profile "
              "and candidate (use --allow-existing for non-candidate rows; check IDs/profile).")
        print(found)
        return 1
    if int(checks.get("outside_profile", "0")) != 0:
        print("Refusing: some target evidence is outside the profile slug.")
        return 1
    if int(checks.get("pii_in_targets", "0")) != 0:
        print("Refusing: a target evidence safe_summary matches a phone/email-like pattern. Not touching it.")
        return 1
    if not args.allow_existing and int(checks.get("non_candidate_in_targets", "0")) != 0:
        print("Refusing: some target evidence is not 'candidate' (use --allow-existing to override).")
        return 1
    if target_count > args.limit:
        print(f"Refusing: {target_count} rows would change but --limit is {args.limit}.")
        return 1

    code, targets = run_psql(target_list_sql(args.profile_slug, args))
    if code != 0:
        print(targets)
        return code

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print(f"target evidence rows ({target_count}; would set evidence_status={args.status}, "
              f"linked internal_evidence_review pending -> {STATUS_TO_REVIEW[args.status]}):")
        print(targets)
        print("gaps stay open; resolution tasks stay pending; ready_for_ai_draft/ready_for_publish unchanged; "
              "no publishing; no outreach.")
        print("Writing requires --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.profile_slug, args))
    if code != 0:
        print(output)
        return code
    print("Applied (counts):")
    print(output)
    code, after = run_psql(status_counts_sql())
    print("evidence + internal_evidence_review status after:")
    print(after)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
