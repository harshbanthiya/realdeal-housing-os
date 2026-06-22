#!/usr/bin/env python3
"""Phase 8.1 — Create custom contact groups and add/remove members. Dry-run by default.

Backs the cockpit's "build your own outreach group by picking contacts" flow.
Exactly one action per call:

  --create --name "VIP owners"        Create a custom group (slug derived from name).
  --add    --group-slug X --contact-ids "uuid,uuid,..."     Add picked contacts.
  --remove --group-slug X --contact-ids "uuid,..."          Remove members.

Groups are NOT tied to buildings. This never sends, never enrolls, and never flips
send_enabled — it only edits group membership. Writing requires BOTH --real-ok and
--apply. Membership inserts are idempotent (ON CONFLICT DO NOTHING).
"""

from __future__ import annotations
from _db import lit, read_env_value, run_psql

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
def slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return s or "group"
def main() -> int:
    parser = argparse.ArgumentParser(description="Create/edit custom contact groups. Dry-run by default.")
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--add", action="store_true")
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--name", default=None, help="Group name (for --create).")
    parser.add_argument("--group-slug", default=None)
    parser.add_argument("--contact-ids", default="", help="Comma-separated contact UUIDs.")
    parser.add_argument("--created-by", default="cockpit")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    actions = [a for a, on in [("create", args.create), ("add", args.add), ("remove", args.remove)] if on]
    if len(actions) != 1:
        print("Refusing: pass exactly one of --create / --add / --remove.")
        return 2
    action = actions[0]
    ids = [x.strip() for x in args.contact_ids.split(",") if x.strip()]
    if action in ("add", "remove"):
        if not args.group_slug:
            print("Refusing: --group-slug is required.")
            return 2
        bad = [i for i in ids if not UUID_RE.match(i)]
        if not ids or bad:
            print(f"Refusing: need valid contact UUIDs (bad: {bad[:3]}).")
            return 2

    if action == "create":
        if not args.name:
            print("Refusing: --name is required for --create.")
            return 2
        slug = args.group_slug or slugify(args.name)
        sql = f"""
BEGIN;
INSERT INTO contact_groups (name, slug, group_type, created_by)
VALUES ({lit(args.name)}, {lit(slug)}, 'custom', {lit(args.created_by)})
ON CONFLICT (slug) DO NOTHING;
COMMIT;
SELECT 'group_slug='||slug||' members='||(SELECT count(*) FROM contact_group_members WHERE group_id=g.id)
FROM contact_groups g WHERE slug={lit(slug)};
"""
        desc = f"create group name={args.name!r} slug={slug}"
    else:
        values = ", ".join(f"('{i}'::uuid)" for i in ids)
        if action == "add":
            sql = f"""
BEGIN;
INSERT INTO contact_group_members (group_id, contact_id, added_by)
SELECT g.id, x.cid, {lit(args.created_by)}
FROM contact_groups g, (VALUES {values}) AS x(cid)
WHERE g.slug={lit(args.group_slug)}
ON CONFLICT (group_id, contact_id) DO NOTHING;
COMMIT;
SELECT 'group='||{lit(args.group_slug)}||' members='||(SELECT count(*) FROM contact_group_members m JOIN contact_groups g ON g.id=m.group_id WHERE g.slug={lit(args.group_slug)});
"""
        else:
            sql = f"""
BEGIN;
DELETE FROM contact_group_members m USING contact_groups g
WHERE m.group_id=g.id AND g.slug={lit(args.group_slug)} AND m.contact_id IN (
  SELECT cid FROM (VALUES {values}) AS x(cid));
COMMIT;
SELECT 'group='||{lit(args.group_slug)}||' members='||(SELECT count(*) FROM contact_group_members m JOIN contact_groups g ON g.id=m.group_id WHERE g.slug={lit(args.group_slug)});
"""
        desc = f"{action} {len(ids)} contact(s) {'to' if action=='add' else 'from'} group {args.group_slug}"

    print(desc)
    if not (args.apply and args.real_ok):
        print("\nDry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, out = run_psql(sql)
    print("\nGroup updated:" if code == 0 else "Group update FAILED (rolled back):")
    print(out)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
