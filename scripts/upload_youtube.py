#!/usr/bin/env python3
"""Upload ONE approved social_post_draft to YouTube. Explicit, never scheduled
blindly — run per item after the draft is approved AND rendered.

Free: YouTube Data API (10k units/day; one upload = 1600 units ≈ 6/day).
One-time operator setup (all free):
  1. console.cloud.google.com → new project → enable "YouTube Data API v3"
  2. OAuth consent screen (external, add yourself as test user)
  3. Credentials → OAuth client ID → Desktop app → download JSON
     → save as secrets/youtube_client_secret.json
  4. pip3 install google-api-python-client google-auth-oauthlib
  5. First run opens a browser once; token cached in secrets/youtube_token.json

Usage: python3 scripts/upload_youtube.py --draft-id <uuid> [--privacy unlisted] [--apply]
Dry-run by default. On success records posted_url + status='posted'.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _db import run_psql, sql_literal

ROOT = Path(__file__).resolve().parents[1]
CLIENT_SECRET = ROOT / "secrets" / "youtube_client_secret.json"
TOKEN = ROOT / "secrets" / "youtube_token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit("error: pip3 install google-api-python-client google-auth-oauthlib")
    if not CLIENT_SECRET.exists():
        sys.exit(f"error: {CLIENT_SECRET} missing — see setup steps in this file's header")
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET), SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft-id", required=True)
    ap.add_argument("--privacy", default="public",
                    choices=["public", "unlisted", "private"])
    ap.add_argument("--publish-at", metavar="ISO8601",
                    help="schedule publish time, e.g. 2026-07-18T14:00:00Z "
                         "(= 7:30pm IST). Uploads private now; YouTube flips "
                         "it public at that hour. Human still runs the upload.")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    code, out = run_psql(f"""
        select status || E'\\t' || coalesce(output_path,'') || E'\\t' ||
               replace(title, E'\\t', ' ') || E'\\t' ||
               replace(coalesce(description,''), E'\\t', ' ') || E'\\t' ||
               array_to_string(tags, ',')
        from social_post_drafts where id = {sql_literal(args.draft_id)}""")
    if code != 0 or not out.strip():
        print("error: draft not found")
        return 1
    status, path, title, description, tags = out.strip().split("\t", 4)

    print(f"draft_id: {args.draft_id}")
    print(f"status: {status}")
    print(f"file: {path or '(not rendered — run prep_short.sh and set output_path)'}")
    print(f"title: {title}")
    if status not in ("approved", "rendered", "scheduled"):
        print("error: draft must be approved before upload")
        return 1
    if not path or not Path(path).exists():
        print("error: rendered file missing")
        return 1
    if not args.apply:
        print("dry_run: true (pass --apply to upload)")
        return 0

    yt = get_service()
    from googleapiclient.http import MediaFileUpload
    status_body = {"privacyStatus": args.privacy,
                   "selfDeclaredMadeForKids": False}
    if args.publish_at:
        # YouTube requires private + publishAt for scheduled publishing
        status_body["privacyStatus"] = "private"
        status_body["publishAt"] = args.publish_at
    body = {"snippet": {"title": title[:100], "description": description,
                        "tags": [t for t in tags.split(",") if t][:15],
                        "categoryId": "26"},
            "status": status_body}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(path, resumable=True))
    resp = req.execute()
    url = f"https://www.youtube.com/watch?v={resp['id']}"
    sched = (f", scheduled_for={sql_literal(args.publish_at)}"
             if args.publish_at else "")
    run_psql(f"""
        UPDATE social_post_drafts
        SET status='posted', posted_url={sql_literal(url)},
            updated_at=now(){sched}
        WHERE id = {sql_literal(args.draft_id)};
        INSERT INTO review_action_log (old_status, new_status, action_type,
                                       reviewed_by, raw_context)
        VALUES ({sql_literal(status)}, 'posted', 'upload_youtube', 'operator',
                jsonb_build_object('script','upload_youtube.py','draft_id',
                                   {sql_literal(args.draft_id)},'url',{sql_literal(url)}))""")
    print(f"posted: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
