"""Review Inbox worker: one snapshot of every human review queue.

Discovers all *_review_items tables (plus known candidate queues) dynamically,
counts pending rows, and flags queues whose oldest pending item is stale.
The cockpit /cockpit/inbox page renders the latest snapshot.
"""
from __future__ import annotations

from _lib import finding, log_run, q

PENDING = "('pending','pending_review','open','queued','needs_review','draft','flagged')"
EXTRA_QUEUES = [
    ("contact_duplicate_candidates", "status"),
    ("building_duplicate_candidates", "status"),
    ("whatsapp_assisted_queue", "status"),
    ("content_publishing_queue", "status"),
    ("source_gap_resolution_tasks", "status"),
]
STALE_DAYS = 14


def _status_col(table: str) -> str | None:
    rows = q(f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='{table}'
          AND column_name IN ('status','review_status','item_status')
        ORDER BY 1 LIMIT 1
    """)
    return rows[0][0] if rows else None


def run() -> tuple[str, int, dict]:
    tables = [r[0] for r in q("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name LIKE '%review_items'
        ORDER BY 1
    """)] + [t for t, _ in EXTRA_QUEUES]

    snapshot: dict[str, dict] = {}
    total = 0
    for table in tables:
        col = _status_col(table)
        if not col:
            continue
        rows = q(f"""
            SELECT count(*), coalesce(min(created_at)::date::text, '')
            FROM {table} WHERE {col} IN {PENDING}
        """)
        count = int(rows[0][0]) if rows else 0
        oldest = rows[0][1] if rows and len(rows[0]) > 1 else ""
        if count == 0:
            continue
        total += count
        snapshot[table] = {"pending": count, "oldest": oldest}
        stale = q(f"""
            SELECT count(*) FROM {table}
            WHERE {col} IN {PENDING} AND created_at < now() - interval '{STALE_DAYS} days'
        """)
        if int(stale[0][0]) > 0:
            finding(
                "review_inbox", "stale_queue", f"stale_queue:{table}",
                f"{table}: {stale[0][0]} pending items older than {STALE_DAYS} days (oldest {oldest})",
                {"table": table, "stale": int(stale[0][0]), "pending": count},
                severity="warn",
            )
    return (f"{total} pending items across {len(snapshot)} queues", total, {"queues": snapshot})


if __name__ == "__main__":
    log_run("review_inbox", run)
