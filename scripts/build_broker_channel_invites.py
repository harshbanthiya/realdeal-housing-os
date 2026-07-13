#!/usr/bin/env python3
"""Shortlist broker contacts and emit a WhatsApp Channel invite send-list.

WhatsApp Channels cannot be populated programmatically -- there is no bulk-add
and no posting API. Followers must tap an invite link. So this script does the
only part that CAN be automated: pick the brokers, clean the numbers, and mint
a per-broker tracked join URL that redirects to the channel invite.

    python3 scripts/build_broker_channel_invites.py \
        --input ~/Downloads/contacts_tagged.csv \
        --outdir exports/broker_channel

Outputs ready.csv (send these), review.csv (look at these), and prints a summary.
"""

import argparse
import csv
import hashlib
import pathlib
import re
import sys

BROKER_TAGS = {"WhatsApp Brokers", "Brokers"}

# ponytail: join tokens are truncated sha256, not signed. They only gate a
# redirect and leak nothing. Sign them if the redirect ever grants access.
TOKEN_SECRET = "rdh-broker-channel-v1"


def normalize_in(raw: str) -> tuple[str | None, str]:
    """Return (e164, reason). e164 is None when the number needs a human."""
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None, "empty"
    # Strip an Indian country code or trunk prefix down to the bare subscriber number.
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        if digits[0] in "6789":
            return "+91" + digits, "in_mobile"
        return None, "in_landline"
    if 8 <= len(digits) <= 15:
        return None, "foreign_or_unknown"
    return None, "malformed"


def token_for(e164: str) -> str:
    return hashlib.sha256((TOKEN_SECRET + e164).encode()).hexdigest()[:10]


def build(rows, join_base):
    """Filter to brokers, normalize, dedupe by number. Returns (ready, review)."""
    ready, review, seen = [], [], {}
    for row in rows:
        if (row.get("Tag") or "").strip() not in BROKER_TAGS:
            continue
        name = (row.get("Name") or "").strip()
        e164, reason = normalize_in(row.get("Phone") or "")
        if not e164:
            review.append({"name": name, "phone": row.get("Phone", ""), "reason": reason})
            continue
        if e164 in seen:
            # Keep the longest name; exports repeat a broker under several spellings.
            if len(name) > len(seen[e164]["name"]):
                seen[e164]["name"] = name
            continue
        entry = {"name": name, "e164": e164, "join_url": f"{join_base}?b={token_for(e164)}"}
        seen[e164] = entry
        ready.append(entry)
    return ready, review


def demo():
    assert normalize_in("9820990025")[0] == "+919820990025"
    assert normalize_in("+91 98209 90025")[0] == "+919820990025"
    assert normalize_in("09820990025")[0] == "+919820990025"
    assert normalize_in("226308309") == (None, "foreign_or_unknown")  # Mumbai landline
    assert normalize_in("2226308309") == (None, "in_landline")  # 10-digit, not 6-9
    assert normalize_in("971506117425") == (None, "foreign_or_unknown")
    assert normalize_in("") == (None, "empty")
    rows = [
        {"Name": "A", "Phone": "9820990025", "Tag": "Brokers"},
        {"Name": "A Longer", "Phone": "+919820990025", "Tag": "WhatsApp Brokers"},
        {"Name": "Not a broker", "Phone": "9820990026", "Tag": "IMHO Residents"},
    ]
    ready, _ = build(rows, "https://x/j")
    assert len(ready) == 1 and ready[0]["name"] == "A Longer", ready
    assert token_for("+919820990025") == token_for("+919820990025")
    print("ok")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=pathlib.Path)
    p.add_argument("--outdir", required=True, type=pathlib.Path)
    p.add_argument("--join-base", default="https://realdealhousing.com/j/brokers")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    if a.demo:
        return demo()

    with a.input.open(newline="", encoding="utf-8-sig") as f:
        ready, review = build(csv.DictReader(f), a.join_base)

    a.outdir.mkdir(parents=True, exist_ok=True)
    for name, rowset, cols in [
        ("ready.csv", ready, ["name", "e164", "join_url"]),
        ("review.csv", review, ["name", "phone", "reason"]),
    ]:
        with (a.outdir / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rowset)

    reasons = {}
    for r in review:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    print(f"ready:  {len(ready)}  -> {a.outdir/'ready.csv'}")
    print(f"review: {len(review)} -> {a.outdir/'review.csv'}")
    for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"          {v:>5}  {k}")


if __name__ == "__main__":
    sys.exit(main())
