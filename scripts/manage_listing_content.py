#!/usr/bin/env python3
"""Attach media_assets to site listings and track their social lifecycle.

Guarded writer for listing_content (migration 063). Dry-run by default;
pass --apply to write. Called by the cockpit /cockpit/content server actions
and usable directly from the CLI.
"""

from __future__ import annotations
from _db import run_psql, sql_literal

import argparse
import re

ROLES = {"reel", "story", "tour", "photo_set", "ambient_loop", "thumbnail"}
STATUSES = {"draft", "scheduled", "posted", "retired"}
PLATFORMS = {"instagram", "youtube", "facebook", "site"}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,80}$")


def cmd_attach(args: argparse.Namespace) -> int:
    if not UUID_RE.match(args.media_asset_id):
        print("Invalid media_asset_id.")
        return 1
    if not SLUG_RE.match(args.listing_slug):
        print("Invalid listing_slug.")
        return 1
    if args.role not in ROLES:
        print("Allowed roles: " + ", ".join(sorted(ROLES)))
        return 1

    code, asset = run_psql(
        f"SELECT id, COALESCE(title,''), building_id FROM media_assets WHERE id = {sql_literal(args.media_asset_id)};"
    )
    if code != 0:
        print(asset)
        return code
    if not asset:
        print("Media asset not found.")
        return 1
    building_id = asset.split("|")[2] if len(asset.split("|")) > 2 else ""

    if not args.apply:
        print("Dry run only. No database rows were inserted.")
        print(f"media_asset_id: {args.media_asset_id}")
        print(f"asset_title: {asset.split('|')[1]}")
        print(f"listing_slug: {args.listing_slug}")
        print(f"role: {args.role}")
        return 0

    code, out = run_psql(f"""
INSERT INTO listing_content (media_asset_id, listing_slug, building_id, role, notes)
VALUES ({sql_literal(args.media_asset_id)}, {sql_literal(args.listing_slug)},
        {sql_literal(building_id) if building_id else 'NULL'},
        {sql_literal(args.role)}, {sql_literal(args.notes)})
ON CONFLICT (media_asset_id, listing_slug, role) DO NOTHING
RETURNING id;
""")
    if code != 0:
        print(out)
        return code
    if not out:
        print("Already attached (no new row).")
        return 0
    print("Attached.")
    print(f"listing_content_id: {out}")
    return 0


def cmd_set_status(args: argparse.Namespace) -> int:
    if not UUID_RE.match(args.id):
        print("Invalid listing_content id.")
        return 1
    if args.status not in STATUSES:
        print("Allowed statuses: " + ", ".join(sorted(STATUSES)))
        return 1
    if args.platform and args.platform not in PLATFORMS:
        print("Allowed platforms: " + ", ".join(sorted(PLATFORMS)))
        return 1

    code, row = run_psql(
        f"SELECT id, status FROM listing_content WHERE id = {sql_literal(args.id)};"
    )
    if code != 0:
        print(row)
        return code
    if not row:
        print("listing_content row not found.")
        return 1
    old_status = row.split("|")[1]

    if not args.apply:
        print("Dry run only. No database rows were updated.")
        print(f"listing_content_id: {args.id}")
        print(f"old_status: {old_status}")
        print(f"new_status: {args.status}")
        return 0

    sets = [
        f"status = {sql_literal(args.status)}",
        "updated_at = NOW()",
    ]
    if args.platform:
        sets.append(f"platform = {sql_literal(args.platform)}")
    if args.post_url:
        sets.append(f"post_url = {sql_literal(args.post_url)}")
    if args.status == "posted":
        sets.append("posted_at = COALESCE(posted_at, NOW())")

    code, out = run_psql(f"""
UPDATE listing_content SET {', '.join(sets)}
WHERE id = {sql_literal(args.id)}
RETURNING id, status;
""")
    if code != 0:
        print(out)
        return code
    print("Updated.")
    print(f"listing_content_id: {args.id}")
    print(f"old_status: {old_status}")
    print(f"new_status: {args.status}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage listing_content rows. Dry-run by default.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("attach", help="Attach a media asset to a listing slug")
    a.add_argument("--media-asset-id", required=True)
    a.add_argument("--listing-slug", required=True)
    a.add_argument("--role", required=True)
    a.add_argument("--notes", default="")
    a.add_argument("--apply", action="store_true")
    a.set_defaults(fn=cmd_attach)

    s = sub.add_parser("set-status", help="Move a listing_content row through its lifecycle")
    s.add_argument("--id", required=True)
    s.add_argument("--status", required=True)
    s.add_argument("--platform", default="")
    s.add_argument("--post-url", default="")
    s.add_argument("--apply", action="store_true")
    s.set_defaults(fn=cmd_set_status)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
