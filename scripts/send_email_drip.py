#!/usr/bin/env python3
"""Send one drip email to one contact via Resend.

Usage:
  python3 scripts/send_email_drip.py --contact-id <uuid> --template dlf-westpark   # dry run
  python3 scripts/send_email_drip.py --contact-id <uuid> --template dlf-westpark --apply

Templates live in web/emails/<template>.tsx.
Reads RESEND_API_KEY from docker/.env (or environment).
Hard guards: dry-run default, suppression check, dedup check, no DB writes without --apply.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, urllib.request, urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR      = PROJECT_ROOT / "web"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from _db import run_psql

FROM_ADDRESS    = os.environ.get("EMAIL_FROM", "Padmini Jain <padmini@realdealhousing.com>")
DIRECTOR_EMAIL  = "PadminiJain1@gmail.com"   # cc + reply-to on every send
DIRECTOR_WA     = "https://wa.me/918291293889"
YOUTUBE_URL     = "https://www.youtube.com/@RealDealHousing"
ASSET_BASE      = os.environ.get("EMAIL_ASSET_BASE", "http://localhost:3000/emails/assets")

SUBJECTS = {
    "dlf-westpark":   "{firstName}, wanted you to see this before it's public",
    "drip-1-variant-a": "An exclusive opportunity — DLF Westpark",
    "drip-1-variant-b": "Private invite — DLF Westpark Phase 2",
}

# ponytail: simple substring check, not a full entity-type classifier — good
# enough to keep "Dear Shree," from firing off a company-name fragment.
ENTITY_MARKERS = ("PVT", "LTD", "LLP", "TRUST", "M/S", "HUF", "BUILDER",
                   "DEVELOPER", "ASSOCIATES", "ENTERPRISE", "COMPANY")


def first_name_or_fallback(full_name: str) -> str:
    name = (full_name or "").strip()
    if not name or any(marker in name.upper() for marker in ENTITY_MARKERS):
        return "there"
    return name.split()[0].capitalize()


def load_env() -> dict:
    env_path = PROJECT_ROOT / "docker" / ".env"
    env: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update(os.environ)
    return env


def get_contact(contact_id: str) -> dict | None:
    _, out = run_psql(f"""
        SELECT c.id, c.full_name, c.unsub_token,
               cm.normalized_value AS email
        FROM contacts c
        JOIN contact_methods cm ON cm.contact_id = c.id
        WHERE c.id = '{contact_id}'
          AND cm.method_type = 'email'
          AND cm.validation_status IN ('valid', 'unverified')
        ORDER BY cm.validation_status, cm.created_at
        LIMIT 1
    """)
    lines = [l for l in out.strip().splitlines() if "|" in l]
    if not lines:
        return None
    parts = lines[0].split("|")
    return {"id": parts[0].strip(), "name": parts[1].strip(),
            "unsub_token": parts[2].strip(), "email": parts[3].strip()}


def is_suppressed(contact_id: str, template_key: str) -> tuple[bool, str]:
    _, out = run_psql(f"""
        SELECT unsubscribed_at IS NOT NULL, sent_at IS NOT NULL
        FROM email_drip_state
        WHERE contact_id = '{contact_id}' AND template_key = '{template_key}'
    """)
    lines = [l for l in out.strip().splitlines() if "|" in l]
    if not lines:
        return False, ""
    unsub, sent = lines[0].split("|")
    if unsub.strip() == "t":
        return True, "unsubscribed"
    if sent.strip() == "t":
        return True, "already_sent"
    return False, ""


def render_template(template: str, props: dict) -> str:
    props_json = json.dumps(props)
    tsx_import = f"./emails/{template}"
    code = (
        f"import Email from '{tsx_import}';"
        f"import {{ render }} from '@react-email/render';"
        f"Promise.resolve(render(Email({props_json}))).then(h => process.stdout.write(h));"
    )
    result = subprocess.run(
        ["npx", "tsx", "-e", code],
        # ponytail: 90s not 30s — cold `npx tsx` start (esbuild/register) can
        # blow past 30s on the first call of the day and crash the whole batch
        cwd=str(WEB_DIR), capture_output=True, text=True, timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tsx render failed:\n{result.stderr[:800]}")
    return result.stdout


def send_via_resend(api_key: str, to: str, subject: str, html: str) -> dict:
    payload = json.dumps({
        "from": FROM_ADDRESS,
        "to": [to],
        "cc": [DIRECTOR_EMAIL],
        "reply_to": DIRECTOR_EMAIL,
        "subject": subject,
        "html": html,
    }).encode()
    req = urllib.request.Request("https://api.resend.com/emails", data=payload)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "RDH-Drip/1.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"error": str(e), "body": body}
    except Exception as e:
        return {"error": str(e)}


def log_send(contact_id: str, template_key: str, resend_id: str | None, error: str | None) -> None:
    if resend_id:
        run_psql(f"""
            INSERT INTO email_drip_state (contact_id, template_key, sent_at, resend_id)
            VALUES ('{contact_id}', '{template_key}', NOW(), '{resend_id}')
            ON CONFLICT (contact_id, template_key) DO UPDATE
              SET sent_at = NOW(), resend_id = EXCLUDED.resend_id, error_msg = NULL;
        """)
    else:
        err_escaped = (error or "unknown").replace("'", "''")[:500]
        run_psql(f"""
            INSERT INTO email_drip_state (contact_id, template_key, error_msg)
            VALUES ('{contact_id}', '{template_key}', '{err_escaped}')
            ON CONFLICT (contact_id, template_key) DO UPDATE
              SET error_msg = EXCLUDED.error_msg;
        """)


def make_unsub_url(contact_id: str, token: str) -> str:
    base = os.environ.get("NEXT_PUBLIC_BASE_URL", "http://localhost:3000")
    return f"{base}/unsubscribe?contact={contact_id}&token={token}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contact-id", required=True)
    ap.add_argument("--template",   required=True, help="e.g. dlf-westpark")
    ap.add_argument("--apply",      action="store_true", help="actually send (default: dry run)")
    args = ap.parse_args()

    contact = get_contact(args.contact_id)
    if not contact:
        print(f"No sendable email for contact {args.contact_id}")
        return 1

    suppressed, reason = is_suppressed(args.contact_id, args.template)
    if suppressed:
        print(f"Skipped ({reason}): {contact['email']}")
        return 0

    first_name = first_name_or_fallback(contact["name"])
    unsub_url  = make_unsub_url(contact["id"], contact["unsub_token"])

    props = {
        "firstName":  first_name,
        "waUrl":      DIRECTOR_WA,
        "youtubeUrl": YOUTUBE_URL,
        "assetBase":  ASSET_BASE,
        "showProofStrip": True,
        "showGardens":    True,
    }

    subject_name = first_name if first_name != "there" else "Hello"
    subject = SUBJECTS.get(args.template, "A private note from Real Deal Housing").format(firstName=subject_name)

    print(f"Contact : {contact['name']} <{contact['email']}>")
    print(f"Template: {args.template}")
    print(f"Subject : {subject}")

    print("Rendering … ", end="", flush=True)
    # inject unsubscribe URL into rendered HTML post-render
    html = render_template(args.template, props)
    html = html.replace("{{unsubscribe}}", unsub_url)
    print(f"{len(html):,} chars")

    if not args.apply:
        out_path = Path(f"/tmp/drip_preview_{args.template}_{args.contact_id[:8]}.html")
        out_path.write_text(html)
        print(f"\n[DRY RUN] HTML → {out_path}")
        print("Re-run with --apply to send.")
        return 0

    env = load_env()
    api_key = env.get("RESEND_API_KEY", "")
    if not api_key or api_key.startswith("re_xxx"):
        print("ERROR: RESEND_API_KEY not set in docker/.env")
        return 1

    print("Sending … ", end="", flush=True)
    resp = send_via_resend(api_key, contact["email"], subject, html)
    resend_id = resp.get("id")
    error     = resp.get("error") or (None if resend_id else str(resp))

    if resend_id:
        log_send(contact["id"], args.template, resend_id, None)
        print(f"OK  resend_id={resend_id}")
    else:
        log_send(contact["id"], args.template, None, error)
        print(f"FAILED: {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
