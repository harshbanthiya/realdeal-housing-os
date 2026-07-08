"""Data Quality worker: daily structural health checks on canonical data."""
from __future__ import annotations

from _lib import finding, log_run, one

CHECKS = [
    ("units_without_building",
     "SELECT count(*) FROM building_units WHERE building_id IS NULL",
     "building_units rows with no building link", "warn"),
    ("units_without_source",
     "SELECT count(*) FROM building_units WHERE source_file_id IS NULL AND source_import_row_id IS NULL",
     "building_units rows with no source provenance", "info"),
    ("media_unreviewed",
     "SELECT count(*) FROM media_assets WHERE reviewed IS NOT TRUE",
     "media assets awaiting review", "info"),
    ("source_files_unprocessed",
     "SELECT count(*) FROM source_files WHERE processing_status IN ('pending','error')",
     "source files pending or failed processing", "warn"),
    ("inventory_no_price",
     "SELECT count(*) FROM inventory WHERE asking_price IS NULL AND monthly_rent IS NULL",
     "inventory rows with neither price nor rent", "info"),
    ("contacts_unattached",
     "SELECT count(*) FROM contacts c WHERE canonical_status='canonical' AND NOT EXISTS "
     "(SELECT 1 FROM contact_property_relationships r WHERE r.contact_id=c.id)",
     "canonical contacts with no property relationship", "info"),
]


def run() -> tuple[str, int, dict]:
    detail: dict[str, int] = {}
    issues = 0
    for key, sql, label, severity in CHECKS:
        try:
            n = int(one(sql) or 0)
        except RuntimeError:
            continue  # table/column drift — skip check, don't kill the run
        detail[key] = n
        if n > 0:
            issues += 1
            finding("data_quality", key, f"dq:{key}", f"{n} {label}",
                    {"count": n}, severity=severity)
    return (f"{issues} of {len(CHECKS)} checks flagged", issues, detail)


if __name__ == "__main__":
    log_run("data_quality", run)
