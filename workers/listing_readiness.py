"""Listing Readiness worker: scores inventory rows on completeness.

A listing is sellable when it has area, floor, price/rent, description, and
approved media. Near-ready units become action findings so the operator's
smallest daily step (one phone call, one photo) unlocks a publishable listing.
"""
from __future__ import annotations

from _lib import finding, log_run, q

SCORE_SQL = """
SELECT i.id, coalesce(b.name, i.building_id::text, 'unknown') AS building,
       coalesce(i.unit_number,'?') AS unit_number, i.listing_type,
       (CASE WHEN i.carpet_area_sq_ft IS NOT NULL OR i.built_up_area_sq_ft IS NOT NULL THEN 1 ELSE 0 END) +
       (CASE WHEN i.floor_number IS NOT NULL THEN 1 ELSE 0 END) +
       (CASE WHEN i.asking_price IS NOT NULL OR i.monthly_rent IS NOT NULL THEN 1 ELSE 0 END) +
       (CASE WHEN coalesce(i.public_description,'') <> '' THEN 1 ELSE 0 END) +
       (CASE WHEN EXISTS (SELECT 1 FROM media_assets m
                          WHERE m.inventory_id = i.id AND m.reviewed IS TRUE) THEN 1 ELSE 0 END)
       AS score
FROM inventory i
LEFT JOIN buildings b ON b.id = i.building_id
WHERE coalesce(i.availability_status,'') NOT IN ('sold','rented','withdrawn','inactive')
"""


def run() -> tuple[str, int, dict]:
    rows = q(f"SELECT * FROM ({SCORE_SQL}) s ORDER BY score DESC")
    buckets = {"ready_5": 0, "near_4": 0, "partial": 0}
    near_ready = 0
    for inv_id, building, unit, listing_type, score in rows:
        score = int(score)
        if score >= 5:
            buckets["ready_5"] += 1
            finding("listing_readiness", "listing_ready", f"ready:{inv_id}",
                    f"READY to draft listing: {building} {unit} ({listing_type or 'sale/rent'})",
                    {"inventory_id": inv_id, "score": score}, severity="action")
        elif score == 4:
            buckets["near_4"] += 1
            near_ready += 1
            finding("listing_readiness", "listing_near", f"near:{inv_id}",
                    f"1 field from listing-ready: {building} {unit}",
                    {"inventory_id": inv_id, "score": score}, severity="info")
        else:
            buckets["partial"] += 1
    return (f"{buckets['ready_5']} ready, {buckets['near_4']} near-ready of {len(rows)} active",
            buckets["ready_5"] + buckets["near_4"], buckets)


if __name__ == "__main__":
    log_run("listing_readiness", run)
