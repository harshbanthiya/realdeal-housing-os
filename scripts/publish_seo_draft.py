#!/usr/bin/env python3
"""Publish ONE approved seo_content_draft to the website blog fixtures.

Review gate: only status='approved' drafts publish (approve in /cockpit/seo).
Appends a BlogPost entry to web/src/lib/blog-fixtures.ts (CMS posts with the
same slug still override fixtures — see cms.ts), then reminds the operator to
deploy. Sets published_url + status='published' on --apply.

Usage: python3 scripts/publish_seo_draft.py --draft-id <uuid> [--apply]
Then:  cd web && npx vercel --prod
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from _db import run_psql, sql_literal

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "web" / "src" / "lib" / "blog-fixtures.ts"


def md_to_html(md: str) -> str:
    import markdown
    return markdown.markdown(md, extensions=["extra"])


def ts_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft-id", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    code, out = run_psql(f"""
        select row_to_json(t)::text from (
          select status, slug, title, excerpt, body_md, seo_title,
                 seo_description, target_keywords
          from seo_content_drafts where id = {sql_literal(args.draft_id)}) t""")
    if code != 0 or not out.strip():
        print("error: draft not found")
        return 1
    d = json.loads(out.strip())
    print(f"draft_id: {args.draft_id}\nstatus: {d['status']}\nslug: {d['slug']}")
    print(f"title: {d['title']}")

    if d["status"] != "approved":
        print("error: draft must be status='approved' (approve in /cockpit/seo)")
        return 1

    src = FIXTURES.read_text(encoding="utf-8")
    if f'slug: "{d["slug"]}"' in src:
        print(f"error: slug {d['slug']!r} already in blog-fixtures.ts")
        return 1

    body_html = md_to_html(d["body_md"] or "")
    tags = (d.get("target_keywords") or "").strip("{}").split(",")[:3]
    tags = [t.strip().strip('"').title() for t in tags if t.strip()]
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    body_esc = (body_html.replace("\\", "\\\\").replace("`", "\\`")
                .replace("${", "\\${"))
    entry = f"""  {{
    slug: {ts_str(d["slug"])},
    title: {ts_str(d["title"])},
    excerpt: {ts_str(d["excerpt"] or "")},
    body: `
{body_esc}
`,
    heroImageUrl: "/og-default.jpg",
    tags: {json.dumps(tags, ensure_ascii=False)},
    publishedAt: {ts_str(now)},
    seoTitle: {ts_str(d["seo_title"] or d["title"])},
    seoDescription: {ts_str(d["seo_description"] or d["excerpt"] or "")},
  }},
"""
    anchor = src.rstrip().rfind("];")
    if anchor == -1:
        print("error: could not find closing `];` in blog-fixtures.ts")
        return 1
    url = f"https://realdealhousing.com/blog/{d['slug']}"
    print(f"publish_to: {url}")
    if not args.apply:
        print("dry_run: true (pass --apply to write fixture + mark published)")
        return 0

    FIXTURES.write_text(src[:anchor] + entry + src[anchor:], encoding="utf-8")
    run_psql(f"""
        UPDATE seo_content_drafts
        SET status='published', published_url={sql_literal(url)}, updated_at=now()
        WHERE id = {sql_literal(args.draft_id)};
        INSERT INTO review_action_log (old_status, new_status, action_type,
                                       reviewed_by, raw_context)
        VALUES ('approved', 'published', 'publish_seo_draft', 'operator',
                jsonb_build_object('script','publish_seo_draft.py',
                                   'draft_id',{sql_literal(args.draft_id)},
                                   'url',{sql_literal(url)}))""")
    print(f"published: {url}")
    print("NOW DEPLOY: cd web && npx vercel --prod")
    return 0


if __name__ == "__main__":
    sys.exit(main())
