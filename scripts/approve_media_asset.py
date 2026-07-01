#!/usr/bin/env python3
"""
Approve a media_asset row: sets reviewed=true and optionally asset_type.
Called by the cockpit /media page via server action.

Usage:
  python3 scripts/approve_media_asset.py --asset-id <uuid> [--asset-type <type>] [--alt-text "..."] [--apply]
  python3 scripts/approve_media_asset.py --unapprove --asset-id <uuid> [--apply]

Without --apply: dry-run only (prints what would change, no writes).
"""
import argparse
import os
import sys
import psycopg2

ALLOWED_ASSET_TYPES = {
    "floor_plan", "exterior", "interior", "amenity",
    "master_layout", "location_map", "video", "brochure", "virtual_stage", "other",
}

def get_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set")
    return psycopg2.connect(url)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--asset-id", required=True)
    p.add_argument("--asset-type", default=None)
    p.add_argument("--alt-text", default=None)
    p.add_argument("--unapprove", action="store_true")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    # Validate UUID loosely
    import re
    if not re.match(r'^[0-9a-f-]{36}$', args.asset_id, re.I):
        sys.exit(f"invalid asset_id: {args.asset_id}")

    if args.asset_type and args.asset_type not in ALLOWED_ASSET_TYPES:
        sys.exit(f"invalid asset_type: {args.asset_type}. allowed: {sorted(ALLOWED_ASSET_TYPES)}")

    conn = get_conn()
    cur = conn.cursor()

    # Fetch current state
    cur.execute(
        "SELECT id, file_path, asset_type, reviewed, source FROM media_assets WHERE id = %s",
        (args.asset_id,)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        sys.exit(f"asset not found: {args.asset_id}")

    asset_id, file_path, current_type, current_reviewed, source = row
    new_reviewed = False if args.unapprove else True
    new_type = args.asset_type or current_type
    new_alt = args.alt_text

    print(f"asset_id: {asset_id}")
    print(f"file_path: {file_path}")
    print(f"source: {source}")
    print(f"reviewed: {current_reviewed} → {new_reviewed}")
    print(f"asset_type: {current_type} → {new_type}")
    if new_alt:
        print(f"alt_text: (set)")
    print(f"apply: {args.apply}")

    if not args.apply:
        print("dry_run: true — pass --apply to write")
        conn.close()
        return

    sets = ["reviewed = %s", "asset_type = %s", "updated_at = now()"]
    vals: list = [new_reviewed, new_type]
    if new_alt:
        sets.append("alt_text = %s")
        vals.append(new_alt)
    vals.append(asset_id)

    cur.execute(
        f"UPDATE media_assets SET {', '.join(sets)} WHERE id = %s",
        vals,
    )
    conn.commit()
    conn.close()
    print(f"result: ok")

if __name__ == "__main__":
    main()
