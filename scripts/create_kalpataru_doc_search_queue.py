#!/usr/bin/env python3
"""Create an operator queue for IGR document-number search.

Uses the refined Kalpataru parser output to produce a checklist for the IGR
"Document Number" search tab. It does not scrape or call IGR; it only prepares
the human search inputs and marks which docs already have Index II PDFs parsed.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMELINE_JSON = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines" / "kalpataru_radiance_timelines.json"
INDEX22_MAPPING_JSON = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines" / "kalpataru_page1_index22_mapping.json"
OUTPUT_DIR = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines"
DISTRICT = "Mumbai Suburban"
SUGGESTED_REGISTRATION_TYPE = "eRegistration"
FALLBACK_REGISTRATION_TYPE = "Regular / iSarita 2.0"


def load_events() -> list[dict[str, Any]]:
    with TIMELINE_JSON.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    events: list[dict[str, Any]] = []
    for unit in payload["units"]:
        events.extend(unit["events"])
    return sorted(events, key=lambda e: (e.get("registration_date") or "", e.get("sro_office") or "", e.get("doc_number") or ""))


def load_index22() -> dict[str, dict[str, Any]]:
    if not INDEX22_MAPPING_JSON.exists():
        return {}
    with INDEX22_MAPPING_JSON.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return {str(row.get("doc_number")): row for row in payload.get("rows", []) if row.get("doc_number")}


def priority_for(event: dict[str, Any], has_index22: bool) -> tuple[int, str]:
    if has_index22:
        return 4, "already_downloaded_index22"
    if event.get("category") == "tenancy":
        return 1, "missing_index22_tenancy_high_value"
    if not event.get("pan_count"):
        return 2, "missing_index22_no_pan_details"
    return 3, "missing_index22"


def build_rows() -> list[dict[str, Any]]:
    index22 = load_index22()
    rows = []
    seen = set()
    for event in load_events():
        key = (
            str(event.get("registration_year") or ""),
            str(event.get("sro_code") or ""),
            str(event.get("doc_number") or ""),
            str(event.get("apartment_key") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        doc_number = str(event.get("doc_number") or "")
        detail = index22.get(doc_number)
        priority, status = priority_for(event, bool(detail))
        rows.append(
            {
                "priority": priority,
                "status": status,
                "apartment_key": event.get("apartment_key") or "",
                "wing": event.get("wing") or "",
                "unit_number": event.get("unit_number") or "",
                "category": event.get("category") or "",
                "document_type": event.get("document_type") or "",
                "doc_number": doc_number,
                "registration_year": event.get("registration_year") or "",
                "registration_date": event.get("registration_date") or "",
                "date_of_execution": event.get("date_of_execution") or "",
                "district": DISTRICT,
                "sro_code": event.get("sro_code") or "",
                "sro_office": event.get("sro_office") or "",
                "registration_type_primary": SUGGESTED_REGISTRATION_TYPE,
                "registration_type_fallback": FALLBACK_REGISTRATION_TYPE,
                "has_index22_pdf": bool(detail),
                "index22_file": detail.get("index_file", "") if detail else "",
                "index22_pan_count": detail.get("pan_count", "") if detail else "",
                "search_instruction": (
                    f"Doc Search -> {SUGGESTED_REGISTRATION_TYPE}; District {DISTRICT}; "
                    f"SRO {event.get('sro_office') or event.get('sro_code')}; "
                    f"Year {event.get('registration_year')}; Doc.No. {doc_number}; solve CAPTCHA; open IndexII."
                ),
                "property_description_raw": event.get("property_description_raw") or "",
            }
        )
    rows.sort(key=lambda r: (int(r["priority"]), str(r["registration_year"]), str(r["sro_office"]), int(r["doc_number"] or 0)))
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "priority", "status", "apartment_key", "wing", "unit_number", "category", "document_type",
        "doc_number", "registration_year", "registration_date", "date_of_execution", "district",
        "sro_code", "sro_office", "registration_type_primary", "registration_type_fallback",
        "has_index22_pdf", "index22_file", "index22_pan_count", "search_instruction",
        "property_description_raw",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_html(rows: list[dict[str, Any]], path: Path) -> None:
    visible_rows = "\n".join(
        f"""<tr data-status="{html.escape(str(row['status']))}">
  <td>{row['priority']}</td>
  <td>{html.escape(str(row['status']))}</td>
  <td><strong>{html.escape(str(row['apartment_key']))}</strong></td>
  <td>{html.escape(str(row['category']))}</td>
  <td><button data-copy="{html.escape(str(row['doc_number']))}">{html.escape(str(row['doc_number']))}</button></td>
  <td>{html.escape(str(row['registration_year']))}</td>
  <td>{html.escape(str(row['sro_office']))}<br><small>{html.escape(str(row['sro_code']))}</small></td>
  <td>{html.escape(str(row['registration_type_primary']))}<br><small>fallback: {html.escape(str(row['registration_type_fallback']))}</small></td>
  <td>{html.escape(str(row['index22_file']))}</td>
</tr>"""
        for row in rows
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kalpataru IGR Doc Search Queue</title>
<style>
body{{font-family:Inter,system-ui,-apple-system,"Segoe UI","Noto Sans Devanagari",sans-serif;margin:0;background:#fbfcfb;color:#17211c}}
header{{position:sticky;top:0;background:#fbfcfb;border-bottom:1px solid #d9e0dc;padding:14px 18px;z-index:2}}
h1{{font-size:20px;margin:0}} .meta{{color:#66736c;font-size:12px;margin-top:6px}} input{{margin-top:10px;padding:8px 10px;border:1px solid #d9e0dc;border-radius:7px;min-width:min(680px,100%)}}
main{{padding:16px 18px}} table{{border-collapse:collapse;width:100%;font-size:12px;background:white}} th,td{{border:1px solid #d9e0dc;padding:7px 8px;vertical-align:top}} th{{position:sticky;top:88px;background:#edf5f2;text-align:left}} tr[data-hide="1"]{{display:none}} button{{font:inherit;border:1px solid #096c60;color:#096c60;background:white;border-radius:6px;padding:3px 8px;cursor:pointer}}
.done{{color:#66736c}} small{{color:#66736c}}
</style>
</head>
<body>
<header>
  <h1>Kalpataru IGR Doc Search Queue</h1>
  <div class="meta">{len(rows)} confident parser docs. Use the IGR Document Number tab: district Mumbai Suburban, SRO, year, doc number, human CAPTCHA, then open/save IndexII.</div>
  <input id="q" type="search" placeholder="Filter: A-14, tenancy, Mumbai 19, doc number...">
</header>
<main>
<table>
<thead><tr><th>Priority</th><th>Status</th><th>Unit</th><th>Category</th><th>Doc.No.</th><th>Year</th><th>SRO</th><th>Reg type</th><th>IndexII file</th></tr></thead>
<tbody>{visible_rows}</tbody>
</table>
</main>
<script>
document.querySelectorAll('button[data-copy]').forEach((b)=>b.addEventListener('click', async()=>{{await navigator.clipboard.writeText(b.dataset.copy); b.textContent='copied '+b.dataset.copy; setTimeout(()=>b.textContent=b.dataset.copy,900);}}));
const q=document.querySelector('#q'); const rows=[...document.querySelectorAll('tbody tr')];
q.addEventListener('input',()=>{{const s=q.value.toLowerCase(); rows.forEach(r=>r.dataset.hide=s&&!r.textContent.toLowerCase().includes(s)?'1':'0')}})
</script>
</body>
</html>
"""
    path.write_text(page, encoding="utf-8")


def write_md(rows: list[dict[str, Any]], path: Path) -> None:
    status_counts = Counter(row["status"] for row in rows)
    cat_counts = Counter(row["category"] for row in rows if not row["has_index22_pdf"])
    sro_counts = Counter(row["sro_office"] for row in rows if not row["has_index22_pdf"])
    lines = [
        "# Kalpataru Radiance IGR Document Search Queue",
        "",
        f"- Total confident parser docs: {len(rows)}",
        f"- Already have Index II parsed: {status_counts.get('already_downloaded_index22', 0)}",
        f"- Still to fetch: {len(rows) - status_counts.get('already_downloaded_index22', 0)}",
        "",
        "## Suggested Search Fields",
        "- Registration type: try `eRegistration` first, matching the document-search screenshot; if no result, try `Regular` and then `iSarita 2.0`.",
        "- District: `Mumbai Suburban`.",
        "- SRO: use the SRO office/name from the queue row.",
        "- Year: use `registration_year`.",
        "- Doc.No.: use `doc_number`.",
        "- CAPTCHA: solve manually; then open/download IndexII.",
        "",
        "## Missing Index II By Category",
    ]
    for key, value in cat_counts.most_common():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Missing Index II By SRO"])
    for key, value in sro_counts.most_common():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## First 25 To Fetch",
            "| Priority | Unit | Category | Doc | Year | SRO |",
            "|---:|---|---|---:|---:|---|",
        ]
    )
    for row in [r for r in rows if not r["has_index22_pdf"]][:25]:
        lines.append(
            f"| {row['priority']} | {row['apartment_key']} | {row['category']} | "
            f"{row['doc_number']} | {row['registration_year']} | {row['sro_office']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Kalpataru IGR document-search queue artifacts.")
    parser.parse_args()
    rows = build_rows()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "kalpataru_doc_search_queue.csv"
    json_path = OUTPUT_DIR / "kalpataru_doc_search_queue.json"
    html_path = OUTPUT_DIR / "kalpataru_doc_search_queue.html"
    md_path = OUTPUT_DIR / "KALPATARU_DOC_SEARCH_QUEUE.md"
    write_csv(rows, csv_path)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_html(rows, html_path)
    write_md(rows, md_path)

    counts = Counter(row["status"] for row in rows)
    print(f"Created doc-search queue for {len(rows)} confident docs.")
    print(f"Already have Index II: {counts.get('already_downloaded_index22', 0)}")
    print(f"Need fetch: {len(rows) - counts.get('already_downloaded_index22', 0)}")
    print(f"CSV: {csv_path}")
    print(f"HTML: {html_path}")
    print(f"MD: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
