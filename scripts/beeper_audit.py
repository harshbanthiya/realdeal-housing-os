#!/usr/bin/env python3
"""Beeper Desktop API setup audit (read-only).

Verifies: API reachable, token valid, which networks are linked,
chat/contact visibility, and a sample of recent messages.
Token: secrets/beeper_access_token (create in Beeper Desktop ->
Settings -> Desktop API -> create access token).

Usage: python3 scripts/beeper_audit.py
"""
import json
import sys
import urllib.request
from pathlib import Path

BASE = "http://localhost:23373"
ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / "secrets" / "beeper_access_token"


def get(path, params=""):
    req = urllib.request.Request(
        f"{BASE}{path}{params}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


if not TOKEN_FILE.exists():
    sys.exit(
        f"NO TOKEN: create one in Beeper Desktop -> Settings -> Desktop API,\n"
        f"then: echo '<token>' > '{TOKEN_FILE}' && chmod 600 '{TOKEN_FILE}'"
    )
TOKEN = TOKEN_FILE.read_text().strip()

print("== /v1/info ==")
try:
    info = get("/v1/info")
except Exception as e:
    sys.exit(f"FAIL: API not reachable or token rejected: {e}")
print(json.dumps(info, indent=2)[:600])

print("\n== accounts (linked networks) ==")
accounts = get("/v1/accounts")
items = accounts if isinstance(accounts, list) else accounts.get("items", [])
for a in items:
    print(f"  - {a.get('accountID', a)}  network={a.get('network', '?')}  user={a.get('user', {}).get('fullName', '?')}")
wa = [a for a in items if "whatsapp" in str(a).lower()]
print(f"WhatsApp linked: {'YES' if wa else 'NO — link it: Beeper Desktop -> + -> WhatsApp -> QR scan'}")

print("\n== recent chats (sample 10) ==")
chats = get("/v1/chats/search", "?limit=10")
for c in chats.get("items", []):
    print(f"  - [{c.get('network', c.get('accountID', '?'))}] {c.get('title', '?')}  type={c.get('type', '?')}  unread={c.get('unreadCount', 0)}")

print("\n== recent messages (sample 5) ==")
msgs = get("/v1/messages/search", "?limit=5")
for m in msgs.get("items", []):
    print(f"  - {m.get('timestamp', '?')} {m.get('senderName', m.get('senderID', '?'))}: {str(m.get('text', ''))[:80]}")

print("\nAUDIT OK — ingest-ready." if items else "\nAUDIT PARTIAL — no accounts visible.")
