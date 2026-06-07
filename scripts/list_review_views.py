#!/usr/bin/env python3
"""List NocoDB review views and local review instructions."""

from __future__ import annotations


REVIEW_VIEWS = [
    ("vw_review_dashboard_summary", "Batch-level review counts and status flags."),
    ("vw_review_batch_sources", "Source files and detected formats in each batch."),
    ("vw_review_business_leads", "Business/portal lead requirements for review."),
    ("vw_review_contact_methods", "Masked phones, emails, websites, and map links."),
    ("vw_review_duplicate_candidates", "Duplicate candidates with masked contact hints."),
    ("vw_review_queue", "Primary review task queue."),
]


REVIEW_TABLES = [
    "import_batches",
    "source_files",
    "contact_import_rows",
    "contact_methods",
    "contact_aliases",
    "contact_property_hints",
    "lead_requirements",
    "inventory_import_rows",
    "contact_duplicate_candidates",
    "import_review_items",
]


def main() -> int:
    print("NocoDB URL: http://localhost:8080")
    print("Filter by batch label: REAL_PHASE_3_5_TEST_001")
    print("Open tables:")
    for table in REVIEW_TABLES:
        print(f"- {table}")
    print("Open review views in this order:")
    for view_name, description in REVIEW_VIEWS:
        print(f"- {view_name}: {description}")
    print("Reviewing does not merge into canonical contacts.")
    print("Do not send messages, WhatsApp, or email from this system yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
