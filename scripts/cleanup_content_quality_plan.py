#!/usr/bin/env python3
"""Phase 6.3 cleanup of content quality + AI planning rows. Dry-run by default.

Deletes ONLY rows tagged raw_context phase='6.3', source='content_quality_ai_planning'
(created by prepare_content_quality_plan.py) in FK-safe order. It NEVER deletes the
Phase 6.1 SEO plan rows (building_web_profiles, seo_keywords, content_briefs,
content_publishing_queue, ai_agent_tasks) or the Phase 6.2 Wix mapping/review rows.

It refuses to delete if any tagged row recorded external_calls_made=true or
published=true, or if any publishing-queue row is actually 'published'. Deleting
requires --apply AND --real-ok. Counts only; no raw personal values are printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.3"
SOURCE = "content_quality_ai_planning"

# FK-safe delete order: children/referencing rows before referenced rows.
# (ai_task_execution_plans references ai_prompt_templates, so plans go first.)
DELETE_ORDER = [
    ("ai_task_execution_plans", "raw_context"),
    ("content_quality_checks", "raw_context"),
    ("content_source_requirements", "raw_context"),
    ("ai_prompt_templates", "raw_context"),
]
def tag(col: str) -> str:
    return f"{col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}'"

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {tag(col)}"
        for t, col in DELETE_ORDER
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

def guard_sql() -> str:
    """tagged rows with external_calls_made=true | published=true | actually-published queue rows."""
    ext = " + ".join(
        f"(SELECT count(*) FROM {t} WHERE {tag(col)} AND {col}->>'external_calls_made' = 'true')"
        for t, col in DELETE_ORDER
    )
    pub_flag = " + ".join(
        f"(SELECT count(*) FROM {t} WHERE {tag(col)} AND {col}->>'published' = 'true')"
        for t, col in DELETE_ORDER
    )
    return (
        f"SELECT ({ext})::text, "
        f"(({pub_flag}) + (SELECT count(*) FROM content_publishing_queue WHERE publish_status = 'published'))::text;"
    )

def delete_sql() -> str:
    stmts = "\n".join(f"DELETE FROM {t} WHERE {tag(col)};" for t, col in DELETE_ORDER)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup Phase 6.3 content quality / AI planning. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Content quality / AI planning cleanup. phase={PHASE}; source={SOURCE}. Counts only; "
          "only tagged 6.3 rows are deleted; Phase 6.1 and 6.2 rows are never touched.")

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code

    code, guard = run_psql(guard_sql())
    if code != 0:
        print(guard)
        return code
    ext, published = (guard.split("|") + ["0", "0"])[:2]

    if not args.apply or not args.real_ok:
        print("Dry run only. No database writes were made.")
        print("current phase-6.3 rows (would delete):")
        print(current)
        print(f"guard checks -> external_calls_made={ext}  published={published}")
        print("Deleting requires --apply and --real-ok.")
        return 0

    if ext != "0" or published != "0":
        print(f"Refusing: progressed past planning (external_calls_made={ext}, published={published}). Not deleting.")
        return 1

    code, output = run_psql(delete_sql())
    print("Remaining phase-6.3 rows after cleanup (expect all 0):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
