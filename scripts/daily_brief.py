#!/usr/bin/env python3
"""Print today's real state in one shot — the first thing to run each session.

Exists so the daily prompt can stay short and never rely on memory: the numbers
come from the DB, not from what a doc claimed last week.

  python3 scripts/daily_brief.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql  # noqa: E402


def rows(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        return [["(query failed)", out.splitlines()[0][:80] if out else ""]]
    return [ln.split("|") for ln in out.splitlines() if ln]


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def table(headers: list[str], data: list[list[str]], limit: int = 12) -> None:
    if not data:
        print("  (nothing)")
        return
    widths = [len(h) for h in headers]
    for r in data[:limit]:
        for i, c in enumerate(r[:len(headers)]):
            widths[i] = max(widths[i], len(str(c)))
    print("  " + "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    for r in data[:limit]:
        print("  " + "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r[:len(headers)])))
    if len(data) > limit:
        print(f"  … +{len(data) - limit} more")


def main() -> None:
    print("\033[1m=== RDH daily brief ===\033[0m")

    section("Review backlog (the throttle — /cockpit/review)")
    table(["queue", "cohorts", "pending"], rows("""
        SELECT q, count(*)::text, sum(n)::text FROM (
          SELECT 'contact_import' q, count(*) n FROM import_review_items WHERE status='pending'
            GROUP BY review_type, import_batch_id
          UNION ALL SELECT 'unit_registration', count(*) FROM unit_registration_review_items
            WHERE status='pending' GROUP BY review_type, building_id
          UNION ALL SELECT 'media', count(*) FROM media_assets WHERE reviewed IS FALSE
            GROUP BY source, asset_type
          UNION ALL SELECT 'property_rels', count(*) FROM contact_property_relationships
            WHERE relationship_status='pending_review' GROUP BY relationship_type, building_id
          UNION ALL SELECT 'drive_contacts', count(*) FROM contact_sheet_rows
            WHERE review_status='pending' GROUP BY sheet_file_id
          UNION ALL SELECT 'contact_dupes', count(*) FROM contact_duplicate_candidates
            WHERE status='pending_review' GROUP BY candidate_type
          UNION ALL SELECT 'party_matches', count(*) FROM registration_party_contact_matches
            WHERE match_status='needs_review' GROUP BY building_id
        ) x GROUP BY q ORDER BY 3::int DESC"""))

    section("Contact reconciliation (every drive contact accounted for?)")
    table(["sheets_done/total", "rows_seen", "matched", "created", "in_review", "unresolved"], rows("""
        SELECT sheets_done || '/' || sheets_total, rows_seen::text, rows_matched::text,
               rows_created::text, rows_in_review::text, rows_unresolved::text
          FROM vw_contact_reconcile_progress"""))

    section("Content shelf (Loop 2 — be found)")
    table(["status", "platform", "count"], rows("""
        SELECT status, platform, count(*)::text FROM social_post_drafts
         GROUP BY 1,2 ORDER BY 3::int DESC"""))
    table(["blog status", "count"], rows("""
        SELECT status, count(*)::text FROM seo_content_drafts GROUP BY 1 ORDER BY 2::int DESC"""))

    section("Scheduled / posted next")
    table(["title", "status", "scheduled"], rows("""
        SELECT left(title, 52), status, coalesce(scheduled_for::text, '—')
          FROM social_post_drafts WHERE status IN ('posted','rendered','approved')
         ORDER BY scheduled_for DESC NULLS LAST LIMIT 6"""))

    section("Worker health (last run per worker)")
    table(["worker", "when", "status", "summary"], rows("""
        SELECT DISTINCT ON (worker) worker,
               to_char(started_at, 'MM-DD HH24:MI'), status, left(coalesce(summary,''), 60)
          FROM worker_runs ORDER BY worker, started_at DESC"""))

    section("Open findings (action first)")
    table(["sev", "worker", "title"], rows("""
        SELECT severity, worker, left(title, 70) FROM worker_findings
         WHERE status='pending'
         ORDER BY CASE severity WHEN 'action' THEN 0 WHEN 'warn' THEN 1 ELSE 2 END,
                  last_seen_at DESC"""))

    section("Building coverage (Loop 1 — know)")
    table(["building", "drive files", "units", "registrations", "media reviewed"], rows("""
        SELECT b.name,
               coalesce((SELECT count(*) FROM drive_files d
                          WHERE d.building_id=b.id AND NOT d.is_noise),0)::text,
               (SELECT count(*) FROM building_units u WHERE u.building_id=b.id)::text,
               (SELECT count(*) FROM unit_registration_records r WHERE r.building_id=b.id)::text,
               (SELECT count(*) FROM media_assets m WHERE m.building_id=b.id AND m.reviewed)::text
          FROM buildings b ORDER BY 3::int DESC"""))

    section("Known blockers")
    for line in [
        "PostHog: key is in web/.env.local — production needs it in Vercel env + redeploy.",
        "WhatsApp: set building on tenant/community groups (/cockpit/whatsapp) to unblock roster match.",
        "Brokers: contacts table holds 0 brokers; ~16k rows sit in drive sheets (see NORTH-STAR §7).",
    ]:
        print(f"  • {line}")

    print("\nRead docs/NORTH-STAR.md before proposing work. "
          "State detail: docs/NEXT-SESSION.md\n")


if __name__ == "__main__":
    main()
