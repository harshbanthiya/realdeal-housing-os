"""SEO Freshness worker: flags stale/stuck content so something ships daily."""
from __future__ import annotations

from _lib import finding, log_run, one

STALE_DAYS = 60


def run() -> tuple[str, int, dict]:
    stale_published = int(one(f"""
        SELECT count(*) FROM content_items
        WHERE status = 'published'
          AND coalesce(updated_at, published_at) < now() - interval '{STALE_DAYS} days'
    """) or 0)
    approved_unscheduled = int(one("""
        SELECT count(*) FROM content_items
        WHERE approval_status = 'approved' AND published_at IS NULL AND scheduled_for IS NULL
    """) or 0)
    drafts_stuck = int(one("""
        SELECT count(*) FROM content_items
        WHERE status = 'draft' AND created_at < now() - interval '21 days'
    """) or 0)
    buildings_without_content = int(one("""
        SELECT count(*) FROM buildings b
        WHERE NOT EXISTS (SELECT 1 FROM content_items c WHERE c.building_id = b.id)
    """) or 0)

    if stale_published:
        finding("seo_freshness", "stale_published", "seo:stale_published",
                f"{stale_published} published content items older than {STALE_DAYS} days — refresh queue",
                {"count": stale_published}, severity="warn")
    if approved_unscheduled:
        finding("seo_freshness", "approved_unscheduled", "seo:approved_unscheduled",
                f"{approved_unscheduled} approved content items never scheduled/published",
                {"count": approved_unscheduled}, severity="action")
    if drafts_stuck:
        finding("seo_freshness", "drafts_stuck", "seo:drafts_stuck",
                f"{drafts_stuck} drafts idle for 21+ days — finish or kill",
                {"count": drafts_stuck}, severity="info")
    if buildings_without_content:
        finding("seo_freshness", "buildings_uncovered", "seo:buildings_uncovered",
                f"{buildings_without_content} buildings have zero content items — SEO gap",
                {"count": buildings_without_content}, severity="info")

    total = stale_published + approved_unscheduled + drafts_stuck
    return (f"{total} content items need attention; {buildings_without_content} buildings uncovered",
            total,
            {"stale_published": stale_published, "approved_unscheduled": approved_unscheduled,
             "drafts_stuck": drafts_stuck, "buildings_without_content": buildings_without_content})


if __name__ == "__main__":
    log_run("seo_freshness", run)
