#!/usr/bin/env python3
"""Parse IGR .xls exports into Kalpataru Radiance apartment timelines.

IGR's "Download as .xls" exports are UTF-16 HTML tables. This parser is
offline-only: it reads local exports, identifies Kalpataru Radiance A/B/C/D
apartment rows, extracts the richest fields available from the list export, and
writes reviewable JSON/CSV files.

PAN/age/address are parsed if present in the export text, but these fields are
normally only available in Index II detail PDFs, not in the list-level .xls.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate as _transliterate

    HAVE_TRANSLITERATION = True
except Exception:  # noqa: BLE001
    HAVE_TRANSLITERATION = False


PHASE = "kalpataru_radiance_xls_timeline_v1"
SOURCE = "igr_xls_kalpataru_radiance_timeline"
TARGET_BUILDING = "Kalpataru Radiance"
DEFAULT_OUTPUT_DIR = Path("exports") / "igr_kalpataru_timelines"

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
PAN_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")

TOWER_LABELS = {
    "A": "Wing A-Ora",
    "B": "Wing B-Brilliance",
    "C": "Wing C-Allura",
    "D": "Wing D-Lumina",
}
UNITS_PER_FLOOR = {"A": 5, "B": 6, "C": 6, "D": 6}
FLOORS = range(1, 32)

DOCTYPE_RULES = [
    ("लिव्ह", "leave_and_license", "tenancy"),
    ("लायसन", "leave_and_license", "tenancy"),
    ("leave and licen", "leave_and_license", "tenancy"),
    ("भाडेपट्टा", "lease", "tenancy"),
    ("lease", "lease", "tenancy"),
    ("बक्षीस", "gift_deed", "ownership"),
    ("gift", "gift_deed", "ownership"),
    ("सेल डीड", "sale_deed", "ownership"),
    ("खरेदीखत", "sale_deed", "ownership"),
    ("विक्रीपत्र", "sale_deed", "ownership"),
    ("sale deed", "sale_deed", "ownership"),
    ("अँग्रीमेंट टू सेल", "agreement_to_sell", "ownership"),
    ("करारनामा", "agreement_to_sell", "ownership"),
    ("agreement to sell", "agreement_to_sell", "ownership"),
    ("agreement relating to deposit of title deeds", "mortgage", "encumbrance"),
    ("deposit of title deeds", "mortgage", "encumbrance"),
    ("pawn", "mortgage", "encumbrance"),
    ("गहाण", "mortgage", "encumbrance"),
    ("mortgage", "mortgage", "encumbrance"),
    ("रिकन्व्हेन्स", "reconveyance", "encumbrance"),
    ("reconveyance", "reconveyance", "encumbrance"),
    ("रद्दलेख", "cancellation", "other"),
    ("release", "release_deed", "ownership"),
    ("रिलीज", "release_deed", "ownership"),
]

ROLE_BY_CATEGORY = {
    "ownership": ("seller", "purchaser"),
    "tenancy": ("lessor", "lessee"),
    "encumbrance": ("mortgagee", "mortgagor"),
    "other": ("seller", "purchaser"),
}

OTHER_BUILDING = re.compile(
    r"एस्क्वायर|एस्क्वा|एक्सक्वायर|एक्सवायर|exquire|esquire|"
    r"ओबेरॉय|oberoi|शीतल|एलिसियन|elysian|एकता|ekta|म्हाडा|mhada|"
    r"अनमोल|anmol|34 पार्क|park estate|वूड्स|woods|एक्सक्यू|exquisite|"
    r"एव्हेलॉन|avalon|सिध्दगिरी|सिद्धगिरी|मिडोस|मेडोस|meadows|"
    r"सिटी सेंटर|city center|सायबा|saiba",
    re.I,
)

KALPATARU = re.compile(
    r"कल्पतर|कलपतर|kalpataru|kalapatru|kalaptru|kalpatar|kalapatr|"
    r"radiance|radianc|radian|rediance|redianc|residence|"
    r"रेडियंस|रेडीयंस|रेडिअन्स|रेिडयंस|रेिडअन्स",
    re.I,
)
CTS_260_5A = re.compile(r"260\s*[/\-]?\s*5\s*(?:a|ए|अ)", re.I)
PROJECT_LEVEL = re.compile(
    r"डेव्हलोपमेंट|development\s+right|प्रोजेक्ट|project|जमीन|land|"
    r"एफ\.?एस\.?आई|fsi|unsold|विकलेले|future|भविष्य",
    re.I,
)
ADDRESS_SIGNALS = (
    "सिद्धार्थ नगर",
    "सिध्दार्थ नगर",
    "siddharth nagar",
    "road no 13",
    "road no 14",
    "पोस्ट ऑफिस",
    "post office",
    "motilal nagar",
    "pahadi goregaon",
    "पहाडी गोरेगाव",
    "goregaon west",
    "गोरेगाव पश्चिम",
    "400104",
)
TOWER_SOCIETY_SIGNALS = (
    "allura",
    "allure",
    "alora",
    "lumina",
    "brilliance",
    "ora",
    "अल्लुरा",
    "अल्ल्युरा",
    "अलोरा",
    "एल्लूरा",
    "लुमिना",
    "लुमीना",
    "ब्रिलियन्स",
    "ब्रिल्लीयन्स",
    "ब्रिलीयन्स",
    "ओरा",
    "ऑरा",
)
TOKEN_GLOSSARY = {
    "सदनिका": "apartment",
    "फ्लॅट": "flat",
    "शॉप": "shop",
    "दुकान": "shop",
    "मजला": "floor",
    "माळा": "floor",
    "विंग": "wing",
    "टॉवर": "tower",
    "इमारतीचे": "building",
    "नाव": "name",
    "क्षेत्र": "area",
    "क्षेत्रफळ": "area",
    "कारपेट": "carpet",
    "चौ": "square",
    "मी": "meter",
    "मीटर": "meter",
    "फूट": "feet",
    "फुट": "feet",
    "मासिक": "monthly",
    "भाडे": "rent",
    "अनामत": "deposit",
    "रक्कम": "amount",
    "कालावधी": "term",
    "महिने": "months",
    "वर्ष": "years",
    "करारनामा": "agreement",
    "गहाणखत": "mortgage",
    "बक्षीसपत्र": "gift-deed",
    "रिकन्व्हेन्स": "reconveyance",
    "रद्दलेख": "cancellation",
}


def ascii_fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))


def skeleton(text: str) -> str:
    """Comparable form for Devanagari with marks/spaces stripped."""
    return "".join(c for c in (text or "") if unicodedata.category(c)[0] != "M" and not c.isspace()).lower()


def transliterate_text(raw: str) -> str:
    if not raw:
        return ""
    text = raw
    if DEVANAGARI.search(text) and HAVE_TRANSLITERATION:
        try:
            text = _transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
        except Exception:  # noqa: BLE001
            pass
    text = ascii_fold(text)
    text = re.sub(r"[^A-Za-z0-9 .,&()/:\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def english_title(raw: str) -> str:
    return transliterate_text(raw).title()


def tokenize(text: str) -> list[dict[str, str]]:
    tokens = re.findall(r"[A-Za-z0-9]+|[ऀ-ॿ]+", text or "")
    out = []
    for token in tokens:
        out.append({"raw": token, "english": TOKEN_GLOSSARY.get(token, transliterate_text(token).lower())})
    return out


def load_export(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-16", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def table_cells(row_html: str) -> list[str]:
    cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row_html, re.S)
    return [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in cells]


def read_rows(path: Path) -> list[dict[str, str]]:
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", load_export(path), re.S)
    if len(rows) < 2:
        return []
    headers = [h.lower() for h in table_cells(rows[0])]
    index = {h: i for i, h in enumerate(headers)}
    out = []
    for row in rows[1:]:
        cells = table_cells(row)
        if not cells:
            continue
        parsed = {h: cells[i] if i < len(cells) else "" for h, i in index.items()}
        parsed["_source_file"] = str(path)
        out.append(parsed)
    return out


def parse_money(value: str | None) -> int | None:
    if not value:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(value))
    if not cleaned:
        return None
    try:
        amount = int(round(float(cleaned)))
    except ValueError:
        return None
    return amount if amount > 0 else None


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    match = re.search(r"([0-3]?\d)[/\-]([01]?\d)[/\-](\d{4})", value)
    if not match:
        return None
    return f"{match.group(3)}-{int(match.group(2)):02d}-{int(match.group(1)):02d}"


def add_months(start: date, months: int) -> date:
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(
        start.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return date(year, month, day)


def parse_name_array(cell: str) -> list[str]:
    text = (cell or "").strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    names: list[str] = []
    buf: list[str] = []
    quoted = False
    for char in text:
        if char == '"':
            quoted = not quoted
        elif char == "," and not quoted:
            names.append("".join(buf))
            buf = []
        else:
            buf.append(char)
    if buf:
        names.append("".join(buf))
    cleaned = []
    for name in names:
        name = re.sub(r"^\s*[-–—]+", "", name).strip().strip('"').strip()
        name = re.sub(r"\s+", " ", name)
        if name:
            cleaned.append(name)
    return cleaned


def classify_doctype(raw: str) -> tuple[str, str]:
    sk = skeleton(raw)
    low = (raw or "").lower()
    for needle, doc_type, category in DOCTYPE_RULES:
        if skeleton(needle) in sk or needle.lower() in low:
            return doc_type, category
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_fold(low)).strip("_")[:50] or "other"
    return slug, "other"


def detect_tower(text: str) -> tuple[str | None, str | None, float, str]:
    sk = skeleton(text)
    low = (text or "").lower()
    checks = [
        ("C", ("wing c", "c wing", "c-wing", "tower c", "टॉवर सी", "विंग सी", "विंग नं. सी", "सी विंग", "c allur", "allura", "allure", "alora", "allora", "अलुरा", "अलोरा", "अल्लुरा", "अल्लोरा", "अल्ल्युरा", "ॲलुरा", "एल्लूरा")),
        ("B", ("wing b", "b wing", "b-wing", "tower b", "टॉवर बी", "विंग बी", "विंग नं. बी", "बी विंग", "brilliance", "ब्रिलियन्स", "ब्रिल्लीयन्स", "ब्रिलीयन्स")),
        ("D", ("wing d", "d wing", "d-wing", "tower d", "टॉवर डी", "विंग डी", "विंग नं. डी", "डी विंग", "lumina", "लुमिना", "लुमीना")),
        ("A", ("wing a", "a wing", "a-wing", "tower a", "टॉवर ए", "विंग ए", "विंग नं. ए", "ए विंग", "a ora", "a-ora", "ora", "ओरा", "ऑरा")),
    ]
    for letter, needles in checks:
        for needle in needles:
            if skeleton(needle) in sk or needle.lower() in low:
                return letter, TOWER_LABELS[letter], 0.95, f"matched:{needle}"
    prefix = re.match(r"\s*([ABCD])\s*/\s*[0-9]{1,3}\b", text or "", re.I)
    if prefix:
        letter = prefix.group(1).upper()
        return letter, TOWER_LABELS[letter], 0.9, "matched:prefix wing/unit"
    return None, None, 0.0, "no tower marker"


def extract_first(patterns: list[str], text: str, flags: int = re.I | re.S) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text or "", flags)
        if match:
            return match.group(1).strip()
    return None


MARATHI_FLOOR_WORDS = {
    "पहिला": "1",
    "पिहला": "1",
    "पहिल्या": "1",
    "दुसरा": "2",
    "दुसऱ्या": "2",
    "तिसरा": "3",
    "तिसऱ्या": "3",
    "चौथा": "4",
    "चौथ्या": "4",
    "पाचवा": "5",
    "सहावा": "6",
    "सातवा": "7",
    "आठवा": "8",
    "नववा": "9",
    "दहावा": "10",
}


def normalize_unit(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.upper().strip()
    text = (
        text.replace("ए", "A")
        .replace("बी", "B")
        .replace("सी", "C")
        .replace("डी", "D")
    )
    text = re.sub(r"^(?:FLAT|APARTMENT|SHOP|UNIT)\s*(?:NO\.?)?\s*", "", text)
    text = re.sub(r"^[ABCD][\-/\s]+", "", text)
    match = re.search(r"([0-9]{1,4})(?=\D|$)", text)
    if match:
        return match.group(1)
    compact = re.sub(r"[\s,;:]+", "", text)
    match = re.search(r"([0-9]{1,4})", compact)
    return match.group(1) if match else None


def infer_floor_from_unit(unit: str | None, units_per_floor: int | None) -> str | None:
    if not unit or not units_per_floor:
        return None
    match = re.match(r"(\d+)", unit)
    if not match:
        return None
    digits = match.group(1)
    if len(digits) <= 1:
        return None
    stack = int(digits[-1])
    floor = int(digits[:-1])
    if 1 <= stack <= units_per_floor and 1 <= floor <= 31:
        return str(floor)
    return None


def infer_stack_from_unit(unit: str | None, units_per_floor: int | None) -> str | None:
    if not unit or not units_per_floor:
        return None
    match = re.match(r"(\d+)", unit)
    if not match:
        return None
    stack = int(match.group(1)[-1])
    return str(stack) if 1 <= stack <= units_per_floor else None


def possible_wings_for_unit(unit: str | None) -> list[str]:
    if not unit:
        return []
    match = re.match(r"(\d+)", unit)
    if not match:
        return []
    digits = match.group(1)
    if len(digits) <= 1:
        return []
    try:
        stack = int(digits[-1])
        floor = int(digits[:-1])
    except ValueError:
        return []
    return [wing for wing, stacks in UNITS_PER_FLOOR.items() if 1 <= floor <= 31 and 1 <= stack <= stacks]


def parse_property(desc: str, tower_letter: str | None = None) -> dict[str, Any]:
    unit_raw = extract_first(
        [
            r"Apartment/Flat No\s*:\s*(.*?)\s*Floor No",
            r"Flat No\.?\s*[:\-]?\s*(.*?)\s*(?:[0-9]{1,2}(?:st|nd|rd|th)|Floor|Building|Address|Wing|,|$)",
            r"FLAT NO\.?\s*[:\-]?\s*(.*?)\s*(?:[0-9]{1,2}(?:ST|ND|RD|TH)|FLOOR|WING|,|$)",
            r"सदनिका\s*(?:नं|नंबर|क्रं|क्र|क्रमांक)?\.?\s*[:\-]?\s*(?:सदनिका\s*(?:नं|नंबर|क्रं|क्र|क्रमांक)?\.?\s*)?([A-Zएबीसीडी0-9\-/]+)",
            r"फ्लॅट\s*(?:नं|नंबर|न|क्रं|क्र)?\.?\s*[:\-]?\s*([A-Zएबीसीडी0-9\-/]+)",
            r"शॉप\s*(?:नं|नंबर|क्र)?\.?\s*[:\-]?\s*([0-9A-Z,\-\s]+)",
        ],
        desc,
    )
    if not unit_raw:
        unit_raw = extract_first(
            [
                r"\b[ABCD]\s*/\s*([0-9]{1,3})",
                r"\b(?:[ABCD][\-/])?([0-9]{1,3})\s+(?:KAL[A-Z]*|RADIANCE|[ABCD][\-\s]?WING|ALLURA|LUMINA|BRILLIANCE)",
                r"\b([0-9]{1,3})/[ABCD]\s+WING",
            ],
            desc,
        )
    if not unit_raw and tower_letter and not re.search(r"डेव्हलोपमेंट|प्रोजेक्ट|जमीन|unsold|विकलेले", desc, re.I):
        first_number = re.match(r"\s*([0-9]{1,3})\b", desc or "")
        if first_number:
            unit_raw = first_number.group(1)
    unit = normalize_unit(unit_raw)

    floor_raw = extract_first(
        [
            r"Floor No\s*:\s*([0-9]+)",
            r"([0-9]+)(?:st|nd|rd|th)\s+(?:habitable\s+)?fl(?:oo)?r",
            r"माळा\s*नं\s*:\s*([0-9]+)",
            r"([0-9]+)\s*(?:वा|व्या|था|रा|ला)?\s*(?:हॅबिटेबल\s*)?मजल",
            r"([0-9]+)\s*(?:वा|व्या|था|रा|ला)?\s*(?:हॅबिटेबल\s*)?फ्लोर",
        ],
        desc,
    )
    if not floor_raw and re.search(r"तळ\s*मजल|ground floor", desc, re.I):
        floor_raw = "ground"
    if not floor_raw:
        for word, number in MARATHI_FLOOR_WORDS.items():
            if re.search(rf"{word}\s*(?:मजल|फ्लोर)", desc):
                floor_raw = number
                break
    if not floor_raw:
        floor_raw = infer_floor_from_unit(unit, UNITS_PER_FLOOR.get(tower_letter or ""))

    stack = infer_stack_from_unit(unit, UNITS_PER_FLOOR.get(tower_letter or ""))

    area_matches = []
    for value, unit_name in re.findall(r"([0-9][0-9,.]*)\s*चौ\.?\s*(मी|मीटर|फूट|फुट)", desc):
        area_matches.append({"value": parse_money(value), "unit": "sqm" if unit_name in ("मी", "मीटर") else "sqft"})
    for value, unit_name in re.findall(r"([0-9][0-9,.]*)\s*(sq\.?\s*ft|sq\.?\s*m|sqm|square feet|square meter)", desc, re.I):
        area_matches.append({"value": parse_money(value), "unit": "sqm" if "m" in unit_name.lower() else "sqft"})

    parking_count = None
    parking_match = re.search(r"([0-9]+)\s*(?:car\s*parking|कार\s*पार्किंग|वाहनतळ)", desc, re.I)
    if parking_match:
        parking_count = int(parking_match.group(1))

    building_text = extract_first(
        [
            r"Building Name\s*:\s*([^,\n]+)",
            r"इमारतीचे नाव\s*:\s*([^,\n]+)",
        ],
        desc,
    )
    cts = extract_first([r"(260\s*[/\-]?\s*5\s*(?:A|ए|अ))"], desc, flags=re.I)

    return {
        "unit_raw": unit_raw,
        "unit_number": unit,
        "possible_wings": possible_wings_for_unit(unit),
        "floor": floor_raw,
        "stack": stack,
        "areas": area_matches,
        "primary_area": area_matches[0] if area_matches else None,
        "parking_count": parking_count,
        "building_text": building_text,
        "cts": cts,
    }


def parse_tenancy(desc: str, execution_date: str | None, consideration: int | None, market_value: int | None) -> dict[str, Any]:
    rent_values = []
    for value in re.findall(r"(?:मासिक\s*भाडे|monthly\s*rent|भाडे)[^0-9]{0,40}([0-9,]+)", desc, re.I):
        amount = parse_money(value)
        if amount:
            rent_values.append(amount)
    for value in re.findall(r"(?:महिन्यासाठी|महिने|months?)[^0-9]{0,30}(?:रु\.?|rs\.?)?\s*([0-9,]+)\s*/?-?", desc, re.I):
        amount = parse_money(value)
        if amount and amount not in rent_values:
            rent_values.append(amount)

    deposit = parse_money(extract_first([r"अनामत(?:\s*रक्कम)?[^0-9]{0,20}([0-9,]+)", r"डिपॉजीट\s*([0-9,]+)", r"deposit[^0-9]{0,20}([0-9,]+)"], desc))
    tenure_months = parse_money(
        extract_first(
            [
                r"कालावधी[^0-9]{0,25}([0-9]+)\s*महिन",
                r"([0-9]+)\s*महिन(?:्यासाठी|े|े\s*करिता)?",
                r"period[^0-9]{0,25}([0-9]+)\s*months?",
                r"([0-9]+)\s*months?\s*(?:period|term|tenure|for)?",
            ],
            desc,
        )
    )
    tenure_years = parse_money(
        extract_first(
            [
                r"कालावधी[^0-9]{0,25}([0-9]+)\s*वर्ष",
                r"([0-9]+)\s*वर्ष(?:ासाठी|े)?",
                r"period[^0-9]{0,25}([0-9]+)\s*years?",
                r"([0-9]+)\s*years?\s*(?:period|term|tenure|for)?",
            ],
            desc,
        )
    )
    if not tenure_months and tenure_years:
        tenure_months = tenure_years * 12

    start_date = execution_date
    end_date = None
    if start_date and tenure_months:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = (add_months(start, tenure_months) - timedelta(days=1)).isoformat()

    return {
        "tenancy_start_date": start_date,
        "tenancy_end_date": end_date,
        "tenure_months": tenure_months,
        "rent_schedule": rent_values,
        "tenancy_monthly_rent": rent_values[0] if rent_values else consideration,
        "tenancy_deposit": deposit or market_value,
    }


def parse_parties(row: dict[str, str], category: str) -> list[dict[str, Any]]:
    seller_role, purchaser_role = ROLE_BY_CATEGORY.get(category, ROLE_BY_CATEGORY["other"])
    parties = []
    for role, col in ((seller_role, "sellerparty"), (purchaser_role, "purchaserparty")):
        for order, raw_name in enumerate(parse_name_array(row.get(col, ""))):
            pan = PAN_RE.search(raw_name)
            parties.append(
                {
                    "role": role,
                    "name_raw": raw_name,
                    "name_english": english_title(raw_name),
                    "name_devanagari": raw_name if DEVANAGARI.search(raw_name) else None,
                    "pan": pan.group(1) if pan else None,
                    "display_order": len(parties) + order,
                    "party_type": "company"
            if re.search(r"llp|ltd|limited|private|pvt|bank|authority|एलएलपी|लिमिटेड|बँक|प्रा|डेव्हलपर|बिल्डर", raw_name, re.I)
                    else "individual",
                }
            )
    return parties


def building_signals(desc: str, tower_reason: str = "") -> dict[str, Any]:
    text = desc or ""
    low = text.lower()
    sk = skeleton(text)
    has_kalpataru = bool(KALPATARU.search(text) or "कलपतर" in sk or "कलपतरर" in sk)
    has_cts_260_5a = bool(CTS_260_5A.search(text))
    address = [signal for signal in ADDRESS_SIGNALS if signal in low]
    society = [signal for signal in TOWER_SOCIETY_SIGNALS if signal in low or skeleton(signal) in sk]
    return {
        "has_kalpataru_or_radiance": has_kalpataru,
        "has_cts_260_5a": has_cts_260_5a,
        "address_signals": address,
        "tower_society_signals": society,
        "project_level": bool(PROJECT_LEVEL.search(text)),
        "tower_reason": tower_reason,
    }


def is_target_building(desc: str, tower_letter: str | None) -> tuple[bool, str]:
    if OTHER_BUILDING.search(desc):
        return False, "other named building"
    if "Patra Chawl" in desc or "पत्रा" in desc:
        return False, "Patra Chawl / rehab entry"
    if re.search(r"\bE[\-/ ]?\s*wing|ई\s*[- ]?\s*विंग|शॉप|shop", desc, re.I):
        return False, "non A-D shop/E-wing entry"
    signals = building_signals(desc)
    if tower_letter in TOWER_LABELS and signals["has_kalpataru_or_radiance"]:
        return True, "A-D tower + fuzzy Kalpataru/Radiance"
    if tower_letter in TOWER_LABELS and signals["has_cts_260_5a"] and signals["address_signals"]:
        return True, "A-D tower + CTS 260/5A + address"
    if tower_letter in TOWER_LABELS and signals["tower_society_signals"] and signals["address_signals"]:
        return True, "A-D tower society + address"
    return False, "missing A-D Kalpataru tower signal"


def build_inventory() -> list[dict[str, Any]]:
    inventory = []
    for wing, stacks in UNITS_PER_FLOOR.items():
        for floor in FLOORS:
            for stack in range(1, stacks + 1):
                unit_number = f"{floor}{stack}"
                inventory.append(
                    {
                        "wing": wing,
                        "wing_label": TOWER_LABELS[wing],
                        "floor": str(floor),
                        "stack": str(stack),
                        "unit_number": unit_number,
                        "apartment_key": f"{wing}-{unit_number}",
                    }
                )
    return inventory


def parse_files(files: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    seen: set[str] = set()

    def review_item(row: dict[str, str], reason: str, tower_reason: str, prop: dict[str, Any] | None = None) -> dict[str, Any]:
        desc = row.get("propertydescription", "")
        signals = building_signals(desc, tower_reason)
        if prop is None:
            prop = parse_property(desc)
        return {
            "source_file": row.get("_source_file"),
            "docno": row.get("docno"),
            "registration_date": row.get("registrationdate"),
            "docname": row.get("docname"),
            "reason": reason,
            "tower_reason": tower_reason,
            "unit_number": prop.get("unit_number"),
            "unit_raw": prop.get("unit_raw"),
            "possible_wings": ",".join(prop.get("possible_wings") or []),
            "has_kalpataru_or_radiance": signals["has_kalpataru_or_radiance"],
            "has_cts_260_5a": signals["has_cts_260_5a"],
            "address_signals": ";".join(signals["address_signals"]),
            "tower_society_signals": ";".join(signals["tower_society_signals"]),
            "project_level": signals["project_level"],
            "property_description": desc,
        }

    for path in files:
        for row in read_rows(path):
            uid = row.get("internaldocumentnumber") or "|".join(
                [row.get("srocode", ""), row.get("docno", ""), row.get("registrationdate", "")]
            )
            if uid in seen:
                continue
            seen.add(uid)

            desc = row.get("propertydescription", "")
            tower_letter, tower_label, tower_confidence, tower_reason = detect_tower(desc)
            target, reason = is_target_building(desc, tower_letter)
            if not target:
                signals = building_signals(desc, tower_reason)
                if signals["has_kalpataru_or_radiance"] or signals["has_cts_260_5a"] or (
                    signals["tower_society_signals"] and signals["address_signals"]
                ):
                    review.append(review_item(row, reason, tower_reason))
                continue

            prop = parse_property(desc, tower_letter)
            if not prop["unit_number"]:
                review.append(review_item(row, "target tower but unit not parsed", tower_reason, prop))
                continue

            doc_type, category = classify_doctype(row.get("docname", ""))
            registration_date = parse_date(row.get("registrationdate"))
            execution_date = parse_date(row.get("dateofexecution"))
            consideration = parse_money(row.get("consideration_amt"))
            market_value = parse_money(row.get("marketvalue"))
            tenancy = parse_tenancy(desc, execution_date, consideration, market_value) if category == "tenancy" else {}
            parties = parse_parties(row, category)
            apartment_key = f"{tower_letter}-{prop['unit_number']}"

            event = {
                "source": SOURCE,
                "phase": PHASE,
                "source_file": row.get("_source_file"),
                "building_name": TARGET_BUILDING,
                "apartment_key": apartment_key,
                "wing": tower_letter,
                "wing_label": tower_label,
                "tower_parse_confidence": tower_confidence,
                "unit_number": prop["unit_number"],
                "unit_raw": prop["unit_raw"],
                "floor": prop["floor"],
                "stack": prop["stack"],
                "doc_number": row.get("docno"),
                "internal_document_number": row.get("internaldocumentnumber"),
                "sro_code": row.get("srocode"),
                "sro_office": row.get("sroname"),
                "document_type_raw": row.get("docname"),
                "document_type": doc_type,
                "category": category,
                "registration_date": registration_date,
                "registration_year": int(registration_date[:4]) if registration_date else None,
                "date_of_execution": execution_date,
                "consideration_amount": consideration,
                "market_value": market_value,
                "stamp_duty": parse_money(row.get("stampdutypaid")),
                "registration_fee": parse_money(row.get("registrationfees")),
                "area_name": row.get("areaname"),
                "property": prop,
                "property_description_raw": desc,
                "property_description_english": transliterate_text(desc),
                "property_tokens": tokenize(desc),
                "parties": parties,
                "party_names_english": [p["name_english"] for p in parties],
                "pan_count": sum(1 for p in parties if p["pan"]),
                "parse_notes": [
                    tower_reason,
                    "PAN usually unavailable in list-level .xls; use Index II PDFs for PAN/age/address.",
                ],
            }
            event.update(tenancy)
            events.append(event)
    events.sort(key=lambda e: (e["apartment_key"], e.get("registration_date") or "", e.get("doc_number") or ""))
    return events, review


def write_outputs(events: list[dict[str, Any]], review: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_unit[event["apartment_key"]].append(event)

    inventory = build_inventory()
    event_counts = defaultdict(int)
    latest_dates: dict[str, str] = {}
    for event in events:
        event_counts[event["apartment_key"]] += 1
        if event.get("registration_date"):
            latest_dates[event["apartment_key"]] = max(latest_dates.get(event["apartment_key"], ""), event["registration_date"])

    for item in inventory:
        key = item["apartment_key"]
        item["registration_event_count"] = event_counts[key]
        item["latest_registration_date"] = latest_dates.get(key)
        item["has_registration"] = event_counts[key] > 0

    summary = {
        "source": SOURCE,
        "building_name": TARGET_BUILDING,
        "structure": {
            "floors": 31,
            "units_per_floor": UNITS_PER_FLOOR,
            "total_units": len(inventory),
        },
        "event_count": len(events),
        "units_with_events": len(by_unit),
        "review_count": len(review),
        "events_by_wing": {wing: sum(1 for e in events if e["wing"] == wing) for wing in TOWER_LABELS},
        "events_by_category": {
            category: sum(1 for e in events if e["category"] == category)
            for category in sorted({e["category"] for e in events})
        },
        "pan_note": "List-level .xls exports normally do not include PAN/age/address; these remain null unless present in raw text.",
    }

    timeline_json = output_dir / "kalpataru_radiance_timelines.json"
    timeline_csv = output_dir / "kalpataru_radiance_events.csv"
    inventory_csv = output_dir / "kalpataru_radiance_inventory.csv"
    review_csv = output_dir / "kalpataru_radiance_review.csv"
    summary_json = output_dir / "kalpataru_radiance_summary.json"

    timeline_doc = {
        "summary": summary,
        "units": [
            {
                "apartment_key": key,
                "wing": key.split("-", 1)[0],
                "unit_number": key.split("-", 1)[1],
                "events": unit_events,
            }
            for key, unit_events in sorted(by_unit.items())
        ],
    }
    timeline_json.write_text(json.dumps(timeline_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    event_fields = [
        "apartment_key",
        "wing",
        "unit_number",
        "floor",
        "stack",
        "registration_date",
        "date_of_execution",
        "doc_number",
        "internal_document_number",
        "document_type",
        "category",
        "sro_office",
        "consideration_amount",
        "market_value",
        "stamp_duty",
        "registration_fee",
        "tenancy_start_date",
        "tenancy_end_date",
        "tenancy_monthly_rent",
        "tenancy_deposit",
        "party_names_english",
        "pan_count",
        "source_file",
        "property_description_english",
        "property_description_raw",
    ]
    with timeline_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=event_fields)
        writer.writeheader()
        for event in events:
            row = {field: event.get(field) for field in event_fields}
            row["party_names_english"] = "; ".join(event.get("party_names_english") or [])
            writer.writerow(row)

    with inventory_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["apartment_key", "wing", "wing_label", "floor", "stack", "unit_number", "has_registration", "registration_event_count", "latest_registration_date"],
        )
        writer.writeheader()
        writer.writerows(inventory)

    with review_csv.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "source_file",
            "docno",
            "registration_date",
            "docname",
            "reason",
            "tower_reason",
            "unit_number",
            "unit_raw",
            "possible_wings",
            "has_kalpataru_or_radiance",
            "has_cts_260_5a",
            "address_signals",
            "tower_society_signals",
            "project_level",
            "property_description",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in review:
            writer.writerow({field: row.get(field) for field in fields})

    return {
        "timeline_json": timeline_json,
        "timeline_csv": timeline_csv,
        "inventory_csv": inventory_csv,
        "review_csv": review_csv,
        "summary_json": summary_json,
    }


def resolve_inputs(args: argparse.Namespace) -> list[Path]:
    files = [Path(p).expanduser() for p in args.files]
    if args.xls_dir:
        files.extend(sorted(Path(args.xls_dir).expanduser().glob(args.glob)))
    unique = []
    seen = set()
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not resolved.exists():
            raise FileNotFoundError(f"Input not found: {resolved}")
        unique.append(resolved)
    if not unique:
        raise FileNotFoundError("No .xls inputs supplied. Pass files or --xls-dir/--glob.")
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Kalpataru Radiance A/B/C/D apartment timelines from IGR .xls exports.")
    parser.add_argument("files", nargs="*", help="Specific IGR .xls export files to parse.")
    parser.add_argument("--xls-dir", help="Directory to scan for .xls exports.")
    parser.add_argument("--glob", default="SearchResult*.xls", help="Glob used with --xls-dir.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Where JSON/CSV outputs are written.")
    args = parser.parse_args()

    files = resolve_inputs(args)
    events, review = parse_files(files)
    outputs = write_outputs(events, review, Path(args.output_dir))

    by_wing = {wing: sum(1 for e in events if e["wing"] == wing) for wing in TOWER_LABELS}
    by_category = {category: sum(1 for e in events if e["category"] == category) for category in sorted({e["category"] for e in events})}
    print(f"Parsed {len(files)} files.")
    print(f"Target A/B/C/D events: {len(events)} across {len({e['apartment_key'] for e in events})} apartments.")
    print(f"Events by wing: {by_wing}")
    print(f"Events by category: {by_category}")
    print(f"Review rows: {len(review)}")
    for label, path in outputs.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
