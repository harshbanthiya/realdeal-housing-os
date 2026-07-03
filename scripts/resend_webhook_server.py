#!/usr/bin/env python3
"""Receives Resend webhook events (bounce/complaint/delivery) and records them.

Why this exists: the ramp scheduler (ramp_send_dlf.py) needs to know about
bounces/complaints to slow down or stop — without this, the ramp is blind
and only tracks reputation by elapsed days, not actual delivery health.

Run:
  python3 scripts/resend_webhook_server.py --port 8787 --secret <token>

Expose it publicly (Resend needs to reach it) with a tunnel, e.g.:
  cloudflared tunnel --url http://localhost:8787

Then add the tunnel URL + "?secret=<token>" as the webhook endpoint in the
Resend dashboard (Webhooks tab), subscribed to: email.delivered,
email.bounced, email.complained, email.opened, email.clicked.

ponytail: auth is a shared-secret query param, not full Svix signature
verification — fine for "someone could mark a fake bounce" (low blast
radius, worst case the ramp pauses a day early). Upgrade to real Svix
signature checks if this ever touches something higher-stakes.
"""
from __future__ import annotations
import argparse, json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from _db import run_psql, sql_literal

EVENT_COLUMN = {
    "email.delivered":  "delivered_at",
    "email.bounced":    "bounced_at",
    "email.complained": "complained_at",
    "email.opened":     "opened_at",
    "email.clicked":    "clicked_at",
}

SECRET: str = ""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *a) -> None:
        print(f"[webhook] {self.address_string()} " + fmt % a)

    def do_POST(self) -> None:
        qs = parse_qs(urlparse(self.path).query)
        if qs.get("secret", [""])[0] != SECRET:
            self.send_response(401)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        event_type = payload.get("type", "")
        resend_id = (payload.get("data") or {}).get("email_id", "")
        column = EVENT_COLUMN.get(event_type)

        if column and resend_id:
            code, out = run_psql(f"""
                UPDATE email_drip_state SET {column} = NOW()
                WHERE resend_id = {sql_literal(resend_id)}
            """)
            print(f"  {event_type} resend_id={resend_id} -> {column} (db exit {code})")
        else:
            print(f"  ignored event: {event_type}")

        self.send_response(200)
        self.end_headers()


def main() -> int:
    global SECRET
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--secret", required=True)
    args = ap.parse_args()
    SECRET = args.secret

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Listening on 127.0.0.1:{args.port} (secret required in ?secret=)")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
