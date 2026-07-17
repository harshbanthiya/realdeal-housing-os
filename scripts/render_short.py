#!/usr/bin/env python3
"""Render ONE approved social_post_draft with the Remotion Short template.

The draft's edit_spec jsonb IS the Remotion props object (see
video/props/*.json for the shape). Review gate: only status='approved'
drafts render — copy approval and render are the same human decision.

Usage: python3 scripts/render_short.py --draft-id <uuid> [--apply]
Dry-run by default. On success sets output_path + status='rendered'.
Then: python3 scripts/upload_youtube.py --draft-id <uuid> --apply
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from _db import run_psql, sql_literal

ROOT = Path(__file__).resolve().parents[1]
RENDERS = ROOT / "exports" / "renders"

# same rule the template enforces — fail fast before spending a render
UNIT_NUMBER = re.compile(
    r"(\b(flat|unit|apt|apartment)\s*(no\.?|number)?\s*#?\s*[a-z]?-?\s*\d{2,4}\b)"
    r"|(\b[a-z]\s*-\s*\d{3,4}\b)|(#\s*\d{3,4}\b)", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft-id", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    code, out = run_psql(f"""
        select status || E'\\t' || replace(title, E'\\t', ' ') || E'\\t' ||
               coalesce(edit_spec::text, '')
        from social_post_drafts where id = {sql_literal(args.draft_id)}""")
    if code != 0 or not out.strip():
        print("error: draft not found")
        return 1
    status, title, spec_json = out.strip().split("\t", 2)
    print(f"draft_id: {args.draft_id}\nstatus: {status}\ntitle: {title}")

    if status != "approved":
        print("error: draft must be status='approved' to render "
              "(approve it in /cockpit/seo first)")
        return 1
    if not spec_json:
        print("error: edit_spec is empty — no Remotion props to render")
        return 1
    props = json.loads(spec_json)

    leaks = [m.group(0) for m in (
        UNIT_NUMBER.search(str(v)) for v in _strings(props)) if m]
    if leaks:
        print(f"error: edit_spec exposes a flat number: {leaks[0]!r}")
        return 1

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    out_path = RENDERS / f"{slug}.mp4"
    print(f"render_to: {out_path}")
    if not args.apply:
        print("dry_run: true (pass --apply to render)")
        return 0

    RENDERS.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(props, f)
        props_file = f.name
    r = subprocess.run(
        ["npx", "remotion", "render", "Short", str(out_path),
         f"--props={props_file}"],
        cwd=ROOT / "video", capture_output=True, text=True)
    if r.returncode != 0 or not out_path.exists():
        print(r.stdout[-2000:], r.stderr[-2000:], sep="\n")
        print("error: render failed")
        return 1

    run_psql(f"""
        UPDATE social_post_drafts
        SET output_path={sql_literal(str(out_path))}, status='rendered',
            updated_at=now()
        WHERE id = {sql_literal(args.draft_id)};
        INSERT INTO review_action_log (old_status, new_status, action_type,
                                       reviewed_by, raw_context)
        VALUES ('approved', 'rendered', 'render_short', 'operator',
                jsonb_build_object('script','render_short.py','draft_id',
                                   {sql_literal(args.draft_id)},
                                   'output_path',{sql_literal(str(out_path))}))""")
    print(f"rendered: {out_path}")
    return 0


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)


if __name__ == "__main__":
    sys.exit(main())
