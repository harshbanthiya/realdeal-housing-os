#!/usr/bin/env python3
"""WhatsApp Business Cloud API sender — heavily gated.

Sends APPROVED TEMPLATE messages via the Meta WhatsApp Cloud API. Reads
credentials from the git-ignored env (never from the prompt, never committed,
never printed):
  WHATSAPP_TOKEN            - System User / app access token (in docker/.env)
  WHATSAPP_PHONE_NUMBER_ID  - the sending number's phone_number_id
  WHATSAPP_API_VERSION      - optional, defaults to v21.0

Safety rails (deliberate friction — outbound messaging is irreversible):
  - DRY RUN by default: builds + shows the payload (token redacted), sends nothing.
  - --send --to <e164> : sends ONE message (use your own number to test first).
  - --send --from-csv <file> : batch from a whatsapp_recipients CSV, but ONLY with
    --confirm-batch AND --max N. Skips rows whose consent_status is not 'allowed'
    unless --include-unconsented is passed explicitly.
  - Every attempt is appended to exports/whatsapp_send_log.jsonl (git-ignored).
This script never mass-sends on its own and never runs from automation by default.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
LOG_FILE = PROJECT_ROOT / "exports" / "whatsapp_send_log.jsonl"


def env(key: str, default: str = "") -> str:
    # web/.env.local first (operator may keep WA creds with the app), then docker/.env.
    for f in (PROJECT_ROOT / "web" / ".env.local", ENV_FILE):
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    return default


def redact(token: str) -> str:
    return f"{token[:4]}…{token[-3:]}" if len(token) > 8 else "set"


def to_digits(e164: str) -> str:
    return re.sub(r"\D", "", e164 or "")


def is_valid_recipient(e164: str) -> bool:
    digits = to_digits(e164)
    return 8 <= len(digits) <= 15


def build_payload(to_e164: str, template: str, lang: str) -> dict:
    return {
        "messaging_product": "whatsapp",
        "to": to_digits(to_e164),
        "type": "template",
        "template": {"name": template, "language": {"code": lang}},
    }


def payload_summary(to_e164: str, template: str, lang: str) -> dict:
    return {
        "messaging_product": "whatsapp",
        "to_digits_len": len(to_digits(to_e164)),
        "type": "template",
        "template": {"name": template, "language": {"code": lang}},
    }


def send_one(to_e164: str, template: str, lang: str, token: str, phone_id: str, version: str) -> tuple[bool, str]:
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = json.dumps(build_payload(to_e164, template, lang)).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        mid = (data.get("messages") or [{}])[0].get("id", "")
        return True, mid or "sent"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


def log(entry: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description="WhatsApp Cloud API sender (gated; template messages only).")
    p.add_argument("--to", help="single recipient in E.164 (e.g. +9198...)")
    p.add_argument("--from-csv", help="whatsapp_recipients CSV for batch send")
    p.add_argument("--template", default="hello_world")
    p.add_argument("--lang", default="en_US")
    p.add_argument("--send", action="store_true", help="actually send (default is dry-run)")
    p.add_argument("--confirm-batch", action="store_true")
    p.add_argument("--max", type=int, default=1)
    p.add_argument("--include-unconsented", action="store_true")
    args = p.parse_args()

    token, phone_id = env("WHATSAPP_TOKEN"), env("WHATSAPP_PHONE_NUMBER_ID")
    version = env("WHATSAPP_API_VERSION", "v21.0")
    creds_ok = bool(token and phone_id)
    print(f"WhatsApp Cloud API — creds: token={'set('+redact(token)+')' if token else 'MISSING'}, "
          f"phone_number_id={'set' if phone_id else 'MISSING'}, version={version}")
    if not creds_ok:
        print("  Add WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID to docker/.env (git-ignored). "
              "Until then this stays a dry run.")

    # Build recipient list.
    recipients: list[dict] = []
    if args.to:
        recipients = [{"name": "(manual)", "phone_e164": args.to, "consent_status": "manual"}]
    elif args.from_csv:
        path = Path(args.from_csv)
        if not path.exists():
            print(f"CSV not found: {path}")
            return 1
        recipients = list(csv.DictReader(path.open(encoding="utf-8")))
    else:
        print("Provide --to <e164> or --from-csv <file>.")
        return 1

    if args.from_csv and not args.include_unconsented:
        before = len(recipients)
        recipients = [r for r in recipients if (r.get("consent_status") or "") == "allowed"]
        print(f"  consent filter: {len(recipients)}/{before} have consent_status='allowed' "
              f"(pass --include-unconsented to override — not recommended).")

    send_blocked_by_missing_creds = args.send and not creds_ok
    will_send = args.send and creds_ok
    is_batch = bool(args.from_csv)
    if is_batch:
        if will_send and not args.confirm_batch:
            print("  Refusing batch send without --confirm-batch.")
            return 1
        before_valid = len(recipients)
        recipients = [r for r in recipients if is_valid_recipient(r.get("phone_e164", ""))]
        print(f"  phone validation: {len(recipients)}/{before_valid} recipient(s) have a plausible WhatsApp number.")
        recipients = recipients[: args.max]
        print(f"  batch capped at --max {args.max} -> {len(recipients)} recipient(s).")
    elif recipients and not is_valid_recipient(recipients[0].get("phone_e164", "")):
        print("  Refusing: --to is not a plausible WhatsApp recipient number.")
        return 1

    mode = "SEND" if will_send else "SEND REQUESTED BUT BLOCKED (missing creds)" if send_blocked_by_missing_creds else "DRY RUN (no send)"
    print(f"  template: {args.template} ({args.lang}) · mode: {mode}")
    if not recipients:
        print("  No eligible recipients.")
        return 0

    sample = recipients[0]
    print(f"  sample payload summary: {json.dumps(payload_summary(sample.get('phone_e164',''), args.template, args.lang))}")

    if send_blocked_by_missing_creds:
        print("  Send requested but credentials are missing — nothing sent.")
        return 1

    if not will_send:
        print("  Dry run complete — nothing sent. Add --send (with creds) to deliver.")
        return 0

    sent = failed = 0
    for r in recipients:
        ok, info = send_one(r.get("phone_e164", ""), args.template, args.lang, token, phone_id, version)
        log({"to_digits_len": len(to_digits(r.get("phone_e164", ""))), "template": args.template,
             "ok": ok, "info": info if ok else info[:120], "consent": r.get("consent_status")})
        sent += ok
        failed += not ok
    print(f"  done: {sent} sent, {failed} failed. Log: {LOG_FILE.relative_to(PROJECT_ROOT)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
