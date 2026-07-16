#!/usr/bin/env python3
"""Safely update one SEO worker item (seo_content_drafts / answer_opportunities).

Dry-run by default; --apply to write. Logs to review_action_log.
Usage:
  python3 scripts/update_seo_item.py --table seo_content_drafts --id <uuid> \
      --status approved --reviewed-by operator [--notes "..."] [--apply]
"""
from __future__ import annotations

import argparse
import re
import sys

from _db import run_psql, sql_literal

TABLES = {
    "seo_content_drafts": {"draft", "approved", "rejected", "published"},
    "answer_opportunities": {"found", "drafted", "approved", "rejected", "posted", "stale"},
    "social_post_drafts": {"draft", "approved", "rendered", "scheduled", "posted", "rejected"},
    "video_research": {"found", "analyzed", "used", "ignored"},
}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True, choices=sorted(TABLES))
    ap.add_argument("--id", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--reviewed-by", required=True)
    ap.add_argument("--notes", default="")
    ap.add_argument("--posted-url", default="", help="answer_opportunities only")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not UUID_RE.match(args.id):
        print("error: invalid uuid")
        return 1
    if args.status not in TABLES[args.table]:
        print(f"error: status must be one of {sorted(TABLES[args.table])}")
        return 1

    code, out = run_psql(
        f"SELECT status FROM {args.table} WHERE id = {sql_literal(args.id)}")
    if code != 0 or not out.strip():
        print("error: item not found")
        return 1
    old_status = out.strip()

    print(f"table: {args.table}")
    print(f"item_id: {args.id}")
    print(f"old_status: {old_status}")
    print(f"new_status: {args.status}")
    if not args.apply:
        print("dry_run: true (pass --apply to write)")
        return 0

    posted = (f", posted_url = {sql_literal(args.posted_url)}"
              if args.table in ("answer_opportunities", "social_post_drafts")
              and args.posted_url else "")
    # video_research is a research log, not a review item — no reviewer columns
    reviewer_cols = ("" if args.table == "video_research" else f"""
    reviewed_by = {sql_literal(args.reviewed_by)},
    reviewed_at = now(),
    decision_notes = {sql_literal(args.notes)},""")
    code, out = run_psql(f"""
BEGIN;
UPDATE {args.table}
SET status = {sql_literal(args.status)},{reviewer_cols}
    updated_at = now(){posted}
WHERE id = {sql_literal(args.id)};
INSERT INTO review_action_log (old_status, new_status, action_type, reviewed_by,
                               decision_notes, raw_context)
VALUES ({sql_literal(old_status)}, {sql_literal(args.status)}, 'update_seo_item',
        {sql_literal(args.reviewed_by)}, {sql_literal(args.notes)},
        jsonb_build_object('script', 'update_seo_item.py',
                           'table', {sql_literal(args.table)},
                           'item_id', {sql_literal(args.id)}));
COMMIT;""")
    if code != 0:
        print(f"error: {out[-300:]}")
        return 1
    print("applied: true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
