#!/usr/bin/env python3
"""Phase 6.6 revert of internal-evidence acceptance changes. Dry-run by default.

Reverts ONLY the changes made by review_internal_source_evidence.py — rows whose
raw_context carries the `evidence_review_phase=6.6` marker:
  * internal_source_evidence accepted/rejected/needs_review -> candidate
  * the linked source_gap_review_items (internal_evidence_review) approved/rejected/
    needs_more_info -> pending (reviewer/notes cleared)
and strips the Phase 6.6 markers from raw_context. It does NOT touch source gaps,
resolution tasks, content, contacts, or relationships, and makes no external/web/AI
calls. It refuses if any source gap was resolved or any brief became ready_for_ai_draft.
Reverting requires --apply AND --real-ok. Counts only; no raw personal values printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.6"
MARK = "raw_context->>'evidence_review_phase' = '6.6'"
STRIP = "- 'evidence_review_phase' - 'evidence_review_source' - 'evidence_review_prev_status' - 'evidence_reviewed_by'"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
def evidence_scope(slug: str, evidence_ids: list[str]) -> str:
    scope = (
        "e.content_source_gap_item_id IN ("
        "  SELECT g.id FROM content_source_gap_items g"
        "  JOIN content_briefs cb ON cb.id = g.content_brief_id"
        "  JOIN building_web_profiles p ON p.id = cb.building_web_profile_id"
        f"  WHERE p.profile_slug = {sql_literal(slug)})"
    )
    if evidence_ids:
        ids = ",".join(sql_literal(i) for i in evidence_ids)
        scope += f" AND e.id IN ({ids})"
    return scope

def counts_sql(slug: str, evidence_ids: list[str]) -> str:
    scope = evidence_scope(slug, evidence_ids)
    return f"""
SELECT 'evidence_marked_6.6' k, count(*)::text v FROM internal_source_evidence e WHERE {MARK} AND {scope}
UNION ALL SELECT 'reviews_marked_6.6', count(*)::text FROM source_gap_review_items r
   WHERE r.raw_context->>'evidence_review_phase' = '6.6' AND r.content_source_gap_item_id IN (
     SELECT e.content_source_gap_item_id FROM internal_source_evidence e WHERE {MARK} AND {scope})
ORDER BY k;"""

def guard_sql(slug: str) -> str:
    return f"""
SELECT 'gaps_resolved' k, count(*)::text v FROM content_source_gap_items WHERE status <> 'open'
UNION ALL SELECT 'briefs_ready_for_ai_draft', count(*)::text
   FROM vw_imperial_heights_source_gap_status WHERE ready_for_ai_draft
ORDER BY k;"""

def revert_sql(slug: str, evidence_ids: list[str], reviewer: str, notes: str) -> str:
    scope = evidence_scope(slug, evidence_ids)
    return f"""BEGIN;
WITH ev AS (
  SELECT e.id, e.content_source_gap_item_id FROM internal_source_evidence e WHERE {MARK} AND {scope}
),
rev_ev AS (
  UPDATE internal_source_evidence e
     SET evidence_status = COALESCE(e.raw_context->>'evidence_review_prev_status', 'candidate'),
         raw_context = e.raw_context {STRIP}
   WHERE e.id IN (SELECT id FROM ev)
   RETURNING e.id
),
rev_rv AS (
  UPDATE source_gap_review_items r
     SET status = COALESCE(r.raw_context->>'evidence_review_prev_status', 'pending'),
         reviewed_by = NULL, reviewed_at = NULL, decision_notes = NULL,
         raw_context = r.raw_context {STRIP}
   WHERE r.raw_context->>'evidence_review_phase' = '6.6'
     AND r.content_source_gap_item_id IN (SELECT content_source_gap_item_id FROM ev)
   RETURNING r.id
)
SELECT 'evidence_reverted' k, count(*)::text v FROM rev_ev
UNION ALL SELECT 'reviews_reverted', count(*)::text FROM rev_rv
ORDER BY k;
COMMIT;
{counts_sql(slug, evidence_ids)}"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Revert Phase 6.6 internal-evidence review changes. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--evidence-id", default="", help="comma-separated evidence UUIDs (optional)")
    parser.add_argument("--reviewed-by", default="phase_6_6_reverter")
    parser.add_argument("--decision-notes", default="Phase 6.6 internal evidence review revert.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()
    evidence_ids = [s.strip() for s in args.evidence_id.split(",") if s.strip()]
    for i in evidence_ids:
        if not UUID_RE.match(i):
            print(f"Refusing: '{i}' is not a valid UUID.")
            return 1

    print(f"Internal evidence review REVERT. phase={PHASE}; profile_slug={args.profile_slug}. Counts only; "
          "only 6.6-marked rows are reverted; gaps/tasks/content/contacts/relationships untouched.")

    code, current = run_psql(counts_sql(args.profile_slug, evidence_ids))
    if code != 0:
        print(current)
        return code

    code, guard = run_psql(guard_sql(args.profile_slug))
    if code != 0:
        print(guard)
        return code
    g = dict(line.split("|", 1) for line in guard.splitlines() if "|" in line)
    blocked = g.get("gaps_resolved", "0") != "0" or g.get("briefs_ready_for_ai_draft", "0") != "0"

    if not args.apply or not args.real_ok:
        print("Dry run only. No database writes were made.")
        print("current 6.6-marked rows (would revert):")
        print(current)
        print(f"guard -> gaps_resolved={g.get('gaps_resolved','0')}, "
              f"briefs_ready_for_ai_draft={g.get('briefs_ready_for_ai_draft','0')}")
        print("Reverting requires --apply and --real-ok.")
        return 0

    if blocked:
        print("Refusing: a source gap was resolved or a brief became ready_for_ai_draft. Not reverting.")
        return 1

    code, output = run_psql(revert_sql(args.profile_slug, evidence_ids, args.reviewed_by, args.decision_notes))
    print("Reverted; remaining 6.6-marked rows after (expect 0):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
