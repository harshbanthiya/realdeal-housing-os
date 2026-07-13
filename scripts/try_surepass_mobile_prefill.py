#!/usr/bin/env python3
"""Try Surepass Mobile To Prefill in sandbox without persisting credentials.

The bearer token can come from SUREPASS_BEARER_TOKEN / SUREPASS_SANDBOX_BEARER_TOKEN
or directly from the sandbox-access .eml. Output intentionally prints only status
and response shape, not returned personal values.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from email import policy
from email.parser import BytesParser
from pathlib import Path

DEFAULT_EMAIL = Path(
    "/Volumes/RDH 5TB/Youtube Channel Downloaded /Downloaded /API Access Granted - Sandbox Environment.eml"
)
DEFAULT_BASE_URL = "https://sandbox.surepass.app"
DEFAULT_ENDPOINT = "/api/v1/pan/mobile-to-prefill-v3"


def extract_token_from_email(path: Path) -> str:
    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if msg.is_multipart():
        body = "\n".join(
            part.get_content()
            for part in msg.walk()
            if part.get_content_type() in ("text/plain", "text/html")
        )
    else:
        body = msg.get_content()
    body = html.unescape(body)
    match = re.search(
        r"Sandbox API Bearer Token:\s*</strong>\s*<code[^>]*>\s*([^<\s]+)",
        body,
        re.I,
    )
    if not match:
        match = re.search(r"Bearer\s+([A-Za-z0-9._~+/=-]{80,})", body, re.I)
    return match.group(1).strip() if match else ""


def get_token(token_email: Path | None) -> str:
    token = os.environ.get("SUREPASS_BEARER_TOKEN") or os.environ.get("SUREPASS_SANDBOX_BEARER_TOKEN")
    if token:
        return token.strip()
    if token_email and token_email.exists():
        return extract_token_from_email(token_email)
    return ""


def response_shape(value):
    if isinstance(value, dict):
        return {k: response_shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [response_shape(value[0])] if value else []
    if value is None:
        return None
    return f"<{type(value).__name__}>"


def fetch_kalpataru_rows(limit: int) -> list[dict[str, str]]:
    from _db import run_psql

    sql = f"""
        SELECT coalesce(cleaned_display_name, raw_name) AS name, phone_normalized AS phone
        FROM contact_import_rows
        WHERE source_file = 'Kalptaru Radiance new.xlsx'
          AND phone_normalized IS NOT NULL
          AND coalesce(cleaned_display_name, raw_name) IS NOT NULL
        ORDER BY id
        LIMIT {int(limit)}
    """
    code, out = run_psql(sql)
    if code != 0:
        raise RuntimeError(out)
    rows = []
    for line in out.splitlines():
        name, _, phone = line.partition("|")
        if name and phone:
            rows.append({"name": name, "phone": phone})
    return rows


def call_surepass(url: str, token: str, payload: dict) -> tuple[int, dict | str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode(errors="replace"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, re.sub(r"\s+", " ", raw[:500])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-email", type=Path, default=DEFAULT_EMAIL)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--mobile", default="7827234123", help="Sandbox/sample mobile number.")
    ap.add_argument("--name", default="", help="Optional name for older Mobile To Prefill variants.")
    ap.add_argument("--mobile-key", default="mobile_number", choices=("mobile_no", "mobile_number"))
    ap.add_argument("--include-name", action="store_true", help="Send name as well as mobile number.")
    ap.add_argument("--kalpataru-batch", type=int, default=0, help="Test N Kalpataru phone/name rows.")
    args = ap.parse_args()

    token = get_token(args.token_email)
    if not token:
        print("ERROR: Surepass bearer token not found in env or token email.", file=sys.stderr)
        return 1

    url = args.base_url.rstrip("/") + "/" + args.endpoint.lstrip("/")

    if args.kalpataru_batch:
        rows = fetch_kalpataru_rows(args.kalpataru_batch)
        print(f"batch_rows={len(rows)} endpoint={args.endpoint} base_url={args.base_url}")
        for i, row in enumerate(rows, 1):
            payload = {args.mobile_key: row["phone"]}
            if args.include_name:
                payload["name"] = row["name"].split()[0]
            status, data = call_surepass(url, token, payload)
            if isinstance(data, dict):
                print(
                    f"row={i} HTTP={status} success={data.get('success')} "
                    f"message_code={data.get('message_code')} message={data.get('message')}"
                )
            else:
                print(f"row={i} HTTP={status} non_json")
            if status in (401, 403, 405):
                print("stopped_after_global_access_failure=true")
                break
        return 0

    payload = {args.mobile_key: args.mobile}
    if args.include_name and args.name:
        payload["name"] = args.name

    status, data = call_surepass(url, token, payload)
    if isinstance(data, dict):
        if 200 <= status < 300:
            print(f"HTTP {status}")
            print(
                "success={success} status_code={status_code} message_code={message_code}".format(
                    success=data.get("success"),
                    status_code=data.get("status_code"),
                    message_code=data.get("message_code"),
                )
            )
            print(json.dumps(response_shape(data), indent=2, sort_keys=True))
            return 0
        print(f"HTTP {status}")
        print(
            "success={success} status_code={status_code} message_code={message_code}".format(
                success=data.get("success"),
                status_code=data.get("status_code"),
                message_code=data.get("message_code"),
            )
        )
        if data.get("message"):
            print(f"message={data.get('message')}")
        print(json.dumps(response_shape(data), indent=2, sort_keys=True))
        return 2
    print(f"HTTP {status}")
    print(data)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
