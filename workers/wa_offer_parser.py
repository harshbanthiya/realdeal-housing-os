"""Parse ingested WhatsApp group texts into structured market offers (068).

Deterministic regex — no LLM. Runs after beeper_ingest in the roster; scans
interactions not yet parsed, emits wa_market_offers rows. English + Hinglish +
Devanagari keywords. Our-building mentions (Ekta Tripolis / Imperial Heights /
Kalpataru Radiance) are flagged with building_id for the operator box.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from _lib import q

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import sql_literal as lit  # noqa: E402

BHK_RE = re.compile(r"\b(\d(?:\.\d)?)\s*(?:bhk|b\.h\.k)\b|\b(\d)\s*rk\b", re.I)
RENT_RE = re.compile(r"rent|rental|lease|leave\s*(?:and|&)\s*licen|\bl\s*&\s*l\b|किरा[एय]|भाड", re.I)
SALE_RE = re.compile(r"\bsale\b|\bsell\b|outright|resale|\bbuy\b|बिक्री|विक|खरीद", re.I)
PG_RE = re.compile(r"\bpg\b|sharing\s+(?:avail|basis)|paying\s*guest", re.I)
PRICE_RE = re.compile(
    r"(?:₹|rs\.?|inr)\s*[\d.,]+\s*(?:cr|crore|lakh|lacs?|lac|k)?|"
    r"[\d.]+\s*(?:cr|crore|lakh|lacs?|lac)\b|\b\d{2,3}\s*k\b", re.I)
AREA_RE = re.compile(r"\d{3,5}\s*(?:sq\.?\s*ft|sqft|sq\s*feet|carpet)", re.I)
FURN_RE = re.compile(r"(fully|semi|un)\s*[- ]?\s*furnished|\bfurnished\b", re.I)
LOCALITY_RE = re.compile(
    r"andheri(?:\s*(?:west|east|w|e))?|bandra(?:\s*(?:west|east|w|e))?|juhu|"
    r"goregaon|malad|borivali|kandivali|santacruz|khar|vile\s*parle|"
    r"jogeshwari|oshiwara|lokhandwala|versova|powai|dahisar|mira\s*road", re.I)

# our buildings: alias regex -> canonical name (id resolved at runtime)
BUILDING_ALIASES = [
    (re.compile(r"tripolis|एकता\s*ट्रिपोलिस", re.I), "Ekta Tripolis"),
    (re.compile(r"imperial\s*(?:heights?|hts)|इ[मं]्?पीरियल", re.I), "Imperial Heights"),
    (re.compile(r"kalpataru\s*radiance|\bradiance\b|कल्पतर[ुू]", re.I), "Kalpataru Radiance"),
]


def run() -> tuple[str, int, dict]:
    bmap = {r[1]: r[0] for r in q(
        "SELECT id, name FROM buildings WHERE name IN ('Ekta Tripolis','Imperial Heights','Kalpataru Radiance')")}
    # ponytail: IH has a known duplicate anchor; first row per name wins (0e72db71 sorts via name query order)

    rows = q("""
        SELECT i.id, i.beeper_chat_id, i.occurred_at, COALESCE(i.sender_display_name,''),
               COALESCE(i.sender_phone,''), REPLACE(COALESCE(i.body_text,''), '|', ' ')
        FROM interactions i
        LEFT JOIN wa_market_offers o ON o.interaction_id = i.id
        WHERE i.source = 'beeper' AND o.id IS NULL AND i.message_type = 'TEXT'
          AND LENGTH(COALESCE(i.body_text,'')) > 15
        ORDER BY i.occurred_at DESC LIMIT 20000""")

    inserts, hits_building = [], 0
    for r in rows:
        if len(r) < 6:
            continue
        iid, chat_id, occurred, sname, sphone, body = r
        bhk_m = BHK_RE.search(body)
        bhk = None
        if bhk_m:
            bhk = bhk_m.group(1) or bhk_m.group(2)
            if bhk_m.group(2):  # RK ≈ 0.5
                bhk = "0.5"
        building_id, building_hit = "", ""
        for rx, name in BUILDING_ALIASES:
            m = rx.search(body)
            if m and name in bmap:
                building_id, building_hit = bmap[name], m.group(0)
                break
        is_pg = bool(PG_RE.search(body))
        is_rent = bool(RENT_RE.search(body))
        is_sale = bool(SALE_RE.search(body))
        price = PRICE_RE.search(body)
        # qualifies: (BHK + transaction-or-price signal) OR our-building mention
        if not building_id and not (bhk and (is_rent or is_sale or is_pg or price)):
            continue
        txn = "pg" if is_pg else ("rent" if is_rent and not is_sale else
                                  "sale" if is_sale and not is_rent else "unknown")
        area = AREA_RE.search(body)
        furn = FURN_RE.search(body)
        loc = LOCALITY_RE.search(body)
        if building_id:
            hits_building += 1
        inserts.append(
            f"({lit(iid)}, {lit(chat_id)}, {lit(occurred)}, {lit(sname)}, {lit(sphone)},"
            f" {lit(txn)}, {bhk or 'NULL'},"
            f" {lit(building_id) if building_id else 'NULL'},"
            f" {lit(building_hit) if building_hit else 'NULL'},"
            f" {lit(price.group(0)) if price else 'NULL'},"
            f" {lit(area.group(0)) if area else 'NULL'},"
            f" {lit(furn.group(0).lower()) if furn else 'NULL'},"
            f" {lit(loc.group(0).title()) if loc else 'NULL'})")

    for i in range(0, len(inserts), 300):
        q(f"""INSERT INTO wa_market_offers (interaction_id, beeper_chat_id, occurred_at,
                sender_name, sender_phone, transaction, bhk, building_id, building_hit,
                price_text, area_text, furnished, locality)
              VALUES {','.join(inserts[i:i + 300])}
              ON CONFLICT (interaction_id) DO NOTHING""")

    summary = f"{len(inserts)} offers parsed from {len(rows)} texts, {hits_building} our-building mentions"
    return summary, len(inserts), {"scanned": len(rows), "our_buildings": hits_building}


if __name__ == "__main__":
    from _lib import log_run
    log_run("wa_offer_parser", run)
