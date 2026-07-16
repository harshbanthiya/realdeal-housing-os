"""Run every daily worker. Scheduled via workers/install_schedule.sh (launchd).

Each worker is independent; one failure never blocks the rest. Everything is
logged to worker_runs and surfaced at /cockpit/inbox.
"""
from __future__ import annotations

import sys

from _lib import log_run

import content_scout
import data_quality
import listing_readiness
import market_watch
import review_inbox
import seo_freshness

WORKERS = [
    ("market_watch", market_watch.run),        # intake first so counts include new files
    ("data_quality", data_quality.run),
    ("listing_readiness", listing_readiness.run),
    ("seo_freshness", seo_freshness.run),
    ("content_scout", content_scout.run),      # SEO drafts + answer queue (migration 064)
    ("review_inbox", review_inbox.run),        # snapshot last so it sees today's findings
]


def main() -> int:
    ok = all([log_run(name, fn) for name, fn in WORKERS])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
