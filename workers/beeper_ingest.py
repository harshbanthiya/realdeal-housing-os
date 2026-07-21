"""Beeper WhatsApp read-only ingest (docs/BEEPER-ASSISTANT-PLAN.md, migration 066).

READ-ONLY against WhatsApp: pulls messages/rosters from the local Beeper
Desktop API and writes ONLY wa_* tables + interactions (message-grain facts).
Never writes contacts/buildings; unknown numbers go to wa_number_queue for
operator review. Sending never happens here (wa.me deep links in cockpit).

Batched: contact matching is one in-memory map; inserts are multi-row VALUES
(one docker-exec psql per page/roster, not per row).
Skips gracefully when Beeper Desktop isn't running or no token exists.
"""
from __future__ import annotations

import html as htmllib
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from _lib import q, one

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import sql_literal as lit, jsonb_lit  # noqa: E402

BASE = "http://127.0.0.1:23373"
TOKEN_FILE = Path(__file__).resolve().parents[1] / "secrets" / "beeper_access_token"
MAX_PAGES_PER_CHAT = 25          # ~500 msgs/chat/run; cursor resumes next run
CODE_RE = re.compile(r"^⌂([VFNL])\s*(.*)$", re.M)
BR_RE = re.compile(r"<br\s*/?>", re.I)


def _get(path: str, query: str = "") -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}{query}",
        headers={"Authorization": f"Bearer {TOKEN_FILE.read_text().strip()}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _strip(html_text: str | None) -> str:
    if not html_text:
        return ""
    t = BR_RE.sub("\n", html_text)
    t = re.sub(r"<[^>]+>", "", t)
    return htmllib.unescape(t).strip()


def _last10(phone: str | None) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else ""


def _load_phone_map() -> dict[str, str]:
    """last-10-digits -> contact uuid, from contacts + contact_methods. One pass."""
    m: dict[str, str] = {}
    for row in q("""
        SELECT contact_id::text, val FROM (
          SELECT id AS contact_id, UNNEST(ARRAY[whatsapp_number, phone_primary, phone_secondary]) AS val FROM contacts
          UNION ALL
          SELECT contact_id, COALESCE(normalized_value, raw_value) FROM contact_methods
            WHERE method_type IN ('mobile','phone') AND contact_id IS NOT NULL
        ) s WHERE val IS NOT NULL AND val <> ''"""):
        if len(row) < 2:
            continue
        key = _last10(row[1])
        if key and key not in m:
            m[key] = row[0]
    return m


def _parse_due(text: str) -> str | None:
    """Crude dd/mm [hh[:mm][am|pm]] | today | tomorrow -> ISO or None."""
    now = datetime.now()
    t = text.lower()
    base, m = None, re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if m:
        y = int(m.group(3) or now.year)
        y = y + 2000 if y < 100 else y
        try:
            base = now.replace(year=y, month=int(m.group(2)), day=int(m.group(1)))
        except ValueError:
            return None
    elif "tomorrow" in t:
        base = now + timedelta(days=1)
    elif "today" in t:
        base = now
    if base is None:
        return None
    hm = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", t[m.end():] if m else t)
    hour, minute = 10, 0
    if hm and hm.group(1):
        hour = int(hm.group(1)) % 12 + (12 if hm.group(3) == "pm" else 0)
        minute = int(hm.group(2) or 0)
    return base.replace(hour=hour, minute=minute, second=0).isoformat()


def _handle_code(code: str, arg: str, contact_id: str, chat_title: str) -> None:
    if code in ("V", "F"):
        due = _parse_due(arg)
        title = ("Viewing: " if code == "V" else "Follow-up: ") + (arg or chat_title)[:200]
        q(f"""INSERT INTO tasks (title, task_type, due_at, status, contact_id, metadata)
              VALUES ({lit(title)}, {lit('viewing' if code == 'V' else 'follow_up')},
                      {lit(due) if due else 'NULL'}, 'pending',
                      {lit(contact_id) if contact_id else 'NULL'},
                      {jsonb_lit({'source': 'wa_code', 'raw': arg})})""")
    elif code == "N":
        target, note = contact_id, arg
        m = re.match(r"@(\S+(?:\s\S+)?)\s+(.*)", arg)
        if m:
            target = one(f"SELECT id FROM contacts WHERE full_name ILIKE {lit('%' + m.group(1) + '%')} LIMIT 1") or contact_id
            note = m.group(2)
        if target:
            q(f"""INSERT INTO interactions (contact_id, channel, direction, occurred_at, summary, source)
                  VALUES ({lit(target)}, 'note', 'internal', NOW(), {lit(note[:1000])}, 'wa_code')""")


def run() -> tuple[str, int, dict]:
    if not TOKEN_FILE.exists():
        return "skipped: no beeper token", 0, {}
    try:
        _get("/v1/info")
    except Exception as e:
        return f"skipped: beeper not reachable ({e})", 0, {}

    phone_map = _load_phone_map()

    # ── 1. chats ──────────────────────────────────────────────────────────
    chats, cursor, pages = [], "", 0
    while pages < 30:
        d = _get("/v1/chats/search", f"?limit=200{'&cursor=' + cursor if cursor else ''}")
        chats += d.get("items", [])
        if not d.get("hasMore") or not d.get("oldestCursor"):
            break
        cursor, pages = d["oldestCursor"], pages + 1

    wa = [c for c in chats if c.get("network") == "WhatsApp"]
    groups = sum(1 for c in wa if c.get("type") == "group")

    chat_rows, member_rows, queue_rows = [], [], {}
    chat_contact_cache: dict[str, str] = {}
    for c in wa:
        cid = c["id"]
        parts = (c.get("participants") or {}).get("items", [])
        others = [p for p in parts if not p.get("isSelf")]
        chat_contact = ""
        if c.get("type") == "single" and others:
            chat_contact = phone_map.get(_last10(others[0].get("phoneNumber")), "")
        chat_contact_cache[cid] = chat_contact
        chat_rows.append(
            f"({lit(cid)}, {lit(c.get('title') or '')}, {lit(c.get('type', 'single'))},"
            f" {int((c.get('participants') or {}).get('total') or len(parts))},"
            f" {lit(c.get('lastActivity')) if c.get('lastActivity') else 'NULL'},"
            f" {lit(chat_contact) if chat_contact else 'NULL'})")
        for p in others:
            phone = p.get("phoneNumber") or ""
            contact = phone_map.get(_last10(phone), "")
            name = p.get("fullName") or ""
            member_rows.append(
                f"({lit(cid)}, {lit(p['id'])}, {lit(phone) if phone else 'NULL'},"
                f" {lit(name)}, {bool(p.get('isAdmin'))},"
                f" {lit(contact) if contact else 'NULL'})")
            if phone and not contact and name and not re.fullmatch(r"\+?[\d\s]+", name):
                if phone not in queue_rows:
                    queue_rows[phone] = (name, c.get("title") or cid)

    for i in range(0, len(chat_rows), 500):
        q(f"""INSERT INTO wa_chats (beeper_chat_id, title, chat_type, member_count, last_activity, contact_id)
              VALUES {','.join(chat_rows[i:i + 500])}
              ON CONFLICT (beeper_chat_id) DO UPDATE SET
                title = EXCLUDED.title, member_count = EXCLUDED.member_count,
                last_activity = EXCLUDED.last_activity, updated_at = NOW(),
                contact_id = COALESCE(wa_chats.contact_id, EXCLUDED.contact_id)""")
    for i in range(0, len(member_rows), 500):
        q(f"""INSERT INTO wa_chat_members (beeper_chat_id, member_id, phone, display_name, is_admin, contact_id)
              VALUES {','.join(member_rows[i:i + 500])}
              ON CONFLICT (beeper_chat_id, member_id) DO UPDATE SET
                phone = COALESCE(EXCLUDED.phone, wa_chat_members.phone),
                display_name = EXCLUDED.display_name,
                contact_id = COALESCE(wa_chat_members.contact_id, EXCLUDED.contact_id),
                last_seen_at = NOW()""")
    if queue_rows:
        vals = [f"({lit(ph)}, {lit(nm)}, {lit(ch)})" for ph, (nm, ch) in queue_rows.items()]
        for i in range(0, len(vals), 500):
            q(f"""INSERT INTO wa_number_queue (phone, wa_name, first_seen_chat)
                  VALUES {','.join(vals[i:i + 500])}
                  ON CONFLICT (phone) DO UPDATE SET
                    seen_count = wa_number_queue.seen_count + 1,
                    wa_name = COALESCE(NULLIF(wa_number_queue.wa_name,''), EXCLUDED.wa_name)""")

    # LID -> (phone, contact) from all rosters, for group sender resolution
    lid_map = {r[0]: (r[1], r[2]) for r in q(
        "SELECT member_id, COALESCE(phone,''), COALESCE(contact_id::text,'') FROM wa_chat_members WHERE phone <> ''") if len(r) >= 3}

    # ── 2. messages (cursor-resumed, ingest_enabled only) ────────────────
    enabled = {r[0] for r in q("SELECT beeper_chat_id FROM wa_chats WHERE ingest_enabled")}
    known_keys = {r[0]: r[1] for r in q(
        "SELECT beeper_chat_id, COALESCE(last_sort_key,'') FROM wa_ingest_state") if len(r) >= 2}
    new_msgs, code_hits, state_rows = 0, [], []
    for c in wa:
        cid = c["id"]
        if cid not in enabled:
            continue
        last_key = known_keys.get(cid, "")
        chat_contact = chat_contact_cache.get(cid, "")
        is_group = c.get("type") == "group"
        enc = urllib.parse.quote(cid, safe="")
        others = [p for p in (c.get("participants") or {}).get("items", []) if not p.get("isSelf")]
        single_phone = (others[0].get("phoneNumber") or "") if (not is_group and others) else ""
        cursor, page, newest, done = "", 0, "", False
        msg_rows = []
        while not done and page < MAX_PAGES_PER_CHAT:
            d = _get(f"/v1/chats/{enc}/messages", f"?cursor={cursor}" if cursor else "")
            items = d.get("items", [])
            if not items:
                break
            newest = newest or items[0].get("sortKey", "")
            for msg in items:
                sk = msg.get("sortKey", "")
                if last_key and sk and sk.isdigit() and last_key.isdigit() and int(sk) <= int(last_key):
                    done = True
                    break
                if msg.get("isDeleted"):
                    continue
                sender_lid = msg.get("senderID", "")
                sname = msg.get("senderName") or ""
                phone, contact = "", ""
                if not msg.get("isSender"):
                    if is_group:
                        phone, contact = lid_map.get(sender_lid, ("", ""))
                        if not phone and re.fullmatch(r"\+?[\d\s]+", sname):
                            phone = re.sub(r"\s", "", sname)
                            contact = phone_map.get(_last10(phone), "")
                    else:
                        phone = single_phone
                        contact = chat_contact or phone_map.get(_last10(phone), "")
                body = _strip(msg.get("text"))
                codes = CODE_RE.findall(body)
                media = msg.get("attachments")
                msg_rows.append(
                    f"({lit(msg['id'])}, {lit(cid)}, 'whatsapp',"
                    f" {lit('outbound' if msg.get('isSender') else 'inbound')},"
                    f" {lit(msg.get('timestamp'))},"
                    f" {lit(contact) if contact else 'NULL'},"
                    f" {lit(phone) if phone else 'NULL'}, {lit(sender_lid)},"
                    f" {lit(sname)}, {is_group}, {lit(msg.get('type', 'TEXT'))},"
                    f" {lit(body[:8000])}, {lit((msg.get('text') or '')[:8000])},"
                    f" {jsonb_lit(media) if media else 'NULL'},"
                    f" {lit(codes[0][0] + ' ' + codes[0][1]) if codes else 'NULL'},"
                    f" 'beeper', {lit(body[:200])})")
                for code, arg in codes:
                    code_hits.append((code, arg.strip(), contact or chat_contact, c.get("title") or ""))
            if done or not d.get("hasMore"):
                break
            cursor, page = d.get("oldestCursor", ""), page + 1
        for i in range(0, len(msg_rows), 200):
            q(f"""INSERT INTO interactions (beeper_message_id, beeper_chat_id, channel,
                    direction, occurred_at, contact_id, sender_phone, sender_lid,
                    sender_display_name, is_group_msg, message_type, body_text,
                    body_html, media, rdh_code, source, summary)
                  VALUES {','.join(msg_rows[i:i + 200])}
                  ON CONFLICT (beeper_message_id) DO NOTHING""")
        new_msgs += len(msg_rows)
        if newest:
            state_rows.append(f"({lit(cid)}, {lit(newest)}, NOW(), {len(msg_rows)})")
        if page >= MAX_PAGES_PER_CHAT:
            print(f"[cap] {c.get('title')}: backfill truncated at {MAX_PAGES_PER_CHAT} pages, resumes next run")

    if state_rows:
        q(f"""INSERT INTO wa_ingest_state (beeper_chat_id, last_sort_key, last_run_at, msg_count)
              VALUES {','.join(state_rows)}
              ON CONFLICT (beeper_chat_id) DO UPDATE SET
                last_sort_key = EXCLUDED.last_sort_key, last_run_at = NOW(),
                msg_count = wa_ingest_state.msg_count + EXCLUDED.msg_count""")
    for code, arg, contact, title in code_hits:
        _handle_code(code, arg, contact, title)

    summary = f"{len(wa)} chats ({groups} groups), {new_msgs} new msgs, {len(queue_rows)} numbers queued"
    return summary, new_msgs, {"chats": len(wa), "groups": groups, "queued": len(queue_rows)}


if __name__ == "__main__":
    from _lib import log_run
    log_run("beeper_ingest", run)
