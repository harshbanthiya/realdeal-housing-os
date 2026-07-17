#!/usr/bin/env python3
"""Google Search Console report — building-name queries + top pages.

Reuses secrets/youtube_client_secret.json (same Cloud project). One-time:
  1. console.cloud.google.com → same project → enable "Google Search Console API"
  2. realdealhousing.com must be a verified property in search.google.com/search-console
  3. First run opens a browser once; token cached as secrets/gsc_token.json
     (separate from the YouTube token — different scope).

Usage: python3 scripts/gsc_report.py [--days 28] [--site sc-domain:realdealhousing.com]
Read-only; no DB writes. ~0 quota concerns (API is free).
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT_SECRET = ROOT / "secrets" / "youtube_client_secret.json"
TOKEN = ROOT / "secrets" / "gsc_token.json"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# the low-competition names the whole strategy targets
BUILDINGS = ["ekta tripolis", "imperial heights", "kalpataru radiance",
             "dlf westpark", "oberoi esquire"]


def get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
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
    return build("searchconsole", "v1", credentials=creds)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--site", default=None)
    args = ap.parse_args()

    svc = get_service()
    sites = svc.sites().list().execute().get("siteEntry", [])
    if not sites:
        print("no verified properties — verify realdealhousing.com in "
              "search.google.com/search-console first")
        return 1
    site = args.site or next(
        (s["siteUrl"] for s in sites if "realdealhousing" in s["siteUrl"]),
        sites[0]["siteUrl"])
    end = dt.date.today()
    start = end - dt.timedelta(days=args.days)
    print(f"site: {site}   window: {start} → {end}\n")

    def query(dims, flt=None, limit=25):
        body = {"startDate": str(start), "endDate": str(end),
                "dimensions": dims, "rowLimit": limit}
        if flt:
            body["dimensionFilterGroups"] = [{"filters": flt}]
        return svc.searchanalytics().query(
            siteUrl=site, body=body).execute().get("rows", [])

    print("== building-name queries (the strategy scorecard) ==")
    for b in BUILDINGS:
        rows = query(["query"], [{"dimension": "query",
                                  "operator": "contains", "expression": b}], 5)
        if not rows:
            print(f"  {b:<22} — no impressions yet")
            continue
        for r in rows:
            print(f"  {r['keys'][0]:<40} pos {r['position']:5.1f}  "
                  f"imp {int(r['impressions']):5d}  clicks {int(r['clicks'])}")

    print("\n== top queries overall ==")
    for r in query(["query"], limit=15):
        print(f"  {r['keys'][0]:<45} pos {r['position']:5.1f}  "
              f"imp {int(r['impressions']):5d}  clicks {int(r['clicks'])}")

    print("\n== top pages ==")
    for r in query(["page"], limit=10):
        print(f"  {r['keys'][0]:<60} imp {int(r['impressions']):5d}  "
              f"clicks {int(r['clicks'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
