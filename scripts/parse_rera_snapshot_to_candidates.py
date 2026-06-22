#!/usr/bin/env python3
"""Phase 6.13: review-gated MahaRERA snapshot parser -> candidate facts (no canonical writes).

Parses ONE post-CAPTCHA MahaRERA snapshot (captured by fetch_rera_page_playwright.py, under the
git-ignored exports/rera_snapshots/) into UNTRUSTED, review-gated candidate facts, and compares
them against the Phase 6.9 manual RERA rows. Writes ONLY to the Phase 6.13 staging tables
(rera_snapshot_captures / rera_parsed_fact_candidates / rera_snapshot_compare_results /
rera_snapshot_review_items), all tagged raw_context={'phase':'6.13','source':'rera_snapshot_parser'}.

It NEVER updates rera_project_profiles / rera_building_match_candidates / rera_carpet_area_records
/ rera_project_status_checks / buildings / content gaps; never verifies a profile, accepts a
match, merges, resolves a gap, publishes, or sends. PRIVACY: complaint / litigation / appeal /
non-compliance sections are stored as COUNTS only — personal names (complainant / director /
allottee / respondent / advocate / petitioner) are never read into a stored value or printed.

Dry-run by default. Requires --real-ok to read a real snapshot; requires --apply to write. Prints
counts only.
"""

from __future__ import annotations
from _db import jsonb_lit, read_env_value, run_psql, sql_literal

import argparse
import json
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "rera_snapshots"
PHASE = "6.13"
SOURCE = "rera_snapshot_parser"
BASE_TAG = {"phase": PHASE, "source": SOURCE}

REG_RE = re.compile(r"\bP\d{11}\b")
DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
STATUS_WORDS = ("Completed", "Ongoing", "Lapsed", "New Project", "Registered")
# Section headers used to bound legal-risk row counting (counts only, never row content).
SECTION_HEADERS = (
    "Promoter Details", "Promoter Documents", "Litigation Details", "Building Details",
    "Technical Documents", "Complaint Details", "Appeal Details", "Non-Compliance Details",
    "Past Experience", "Project Status",
)
LEGAL_SECTIONS = {
    "litigation": "Litigation Details",
    "complaint": "Complaint Details",
    "appeal": "Appeal Details",
    "non_compliance": "Non-Compliance Details",
}
# Company suffixes — promoter NAME is stored ONLY if it clearly looks like a company, else
# presence-only (so we never store a landowner/person name).
COMPANY_SUFFIX_RE = re.compile(
    r"(LLP|LTD|LIMITED|PRIVATE|PVT|DEVELOPERS?|BUILDERS?|CONSTRUCTIONS?|ENTERPRISES?|"
    r"REALTY|REALTORS?|INFRA\w*|ASSOCIATES?|CORPORATION|VENTURES?|GROUP|ESTATES?)\b",
    re.IGNORECASE)

# --------------------------------------------------------------------------- DB helpers
def num_literal(value) -> str:
    return "NULL" if value is None else str(value)
# --------------------------------------------------------------------------- guards

def is_git_ignored(path: Path) -> bool:
    res = subprocess.run(["git", "check-ignore", str(path)], cwd=str(PROJECT_ROOT),
                         capture_output=True, text=True, check=False)
    return res.returncode == 0 and bool(res.stdout.strip())

def validate_snapshot(folder: Path) -> tuple[bool, str]:
    try:
        folder.resolve().relative_to(SNAPSHOT_ROOT.resolve())
    except ValueError:
        return False, f"Refusing: snapshot folder is not under {SNAPSHOT_ROOT}."
    if not folder.is_dir():
        return False, f"Refusing: snapshot folder not found: {folder}"
    if not is_git_ignored(folder):
        return False, f"Refusing: snapshot folder is not git-ignored: {folder}"
    if not (folder / "visible_text.txt").exists():
        return False, "Refusing: visible_text.txt missing (capture may have been gated/blocked)."
    return True, "ok"

# --------------------------------------------------------------------------- parsing

def line_index_of(lines: list[str], label: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if lines[i].strip().lower() == label.lower():
            return i
    return -1

def section_bounds_count(lines: list[str], header: str) -> int:
    """Count numbered (^N\\t...) rows after `header` until the next known section header.

    Counts rows only — never reads/returns row CONTENT (which may contain personal names)."""
    start = line_index_of(lines, header)
    if start < 0:
        return 0
    # Find the nearest following line that is another known section header.
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = lines[j].strip()
        if s in SECTION_HEADERS and s != header:
            end = j
            break
    count = 0
    for k in range(start + 1, end):
        if re.match(r"^\d+\t", lines[k]):
            count += 1
    return count

def parse_snapshot(folder: Path) -> dict:
    text = (folder / "visible_text.txt").read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")

    facts: list[dict] = []

    def add(group, key, *, text_val=None, num_val=None, date_val=None, unit=None,
            conf=None, hint=None, status="candidate", safe=False):
        facts.append({"group": group, "key": key, "text": text_val, "num": num_val,
                      "date": date_val, "unit": unit, "conf": conf, "hint": hint,
                      "status": status, "safe": safe})

    # 1. Registration number token.
    reg = None
    m = REG_RE.search(text)
    if m:
        reg = m.group(0)
        add("project_profile", "rera_registration_number", text_val=reg, conf=0.99,
            hint="visible_text.txt", status="candidate")

    # 2. Date of registration.
    reg_date = None
    for ln in lines:
        if "date of registration" in ln.lower():
            dm = DATE_RE.search(ln)
            if dm:
                d, mo, y = dm.groups()
                reg_date = f"{y}-{mo}-{d}"
                add("project_profile", "registration_date", date_val=reg_date, conf=0.9,
                    hint="visible_text.txt")
            break

    # 3. Project status (value is the next status-word line after the label).
    status_val = None
    si = line_index_of(lines, "Project Status")
    if si >= 0:
        for j in range(si + 1, min(si + 6, len(lines))):
            cand = lines[j].strip()
            if cand in STATUS_WORDS:
                status_val = cand
                break
    if status_val:
        add("project_profile", "project_status", text_val=status_val, conf=0.9,
            hint="visible_text.txt")

    # 4. Official project name (line after the first standalone "Project Name" label).
    proj_name = None
    pi = line_index_of(lines, "Project Name")
    if pi >= 0:
        for j in range(pi + 1, min(pi + 4, len(lines))):
            cand = lines[j].strip()
            if cand:
                proj_name = cand
                break
    if proj_name:
        add("project_profile", "official_project_name", text_val=proj_name, conf=0.85,
            hint="visible_text.txt")

    # 5. Wing / building identification rows (e.g. "N<TAB>Imperial Heights Wing C<TAB>NA").
    wings = []
    for ln in lines:
        wm = re.match(r"^\d+\t(.+?Wing\s+[A-Z])\tNA\b", ln)
        if wm:
            wings.append(wm.group(1).strip())
    wings = sorted(set(wings))
    if wings:
        add("wing_building", "wing_count", num_val=len(wings), conf=0.85,
            hint="visible_text.txt:building_details")
        # Wing labels are building identifiers (not personal data).
        add("wing_building", "wing_labels", text_val=", ".join(wings), conf=0.85,
            hint="visible_text.txt:building_details")

    # 6. Carpet table: rows + apartment total (header line contains "Number of Apartment").
    carpet_rows = 0
    apt_total = 0
    chi = -1
    for i, ln in enumerate(lines):
        if "number of apartment" in ln.lower() and "\t" in ln:
            chi = i
            break
    if chi >= 0:
        end = len(lines)
        for j in range(chi + 1, len(lines)):
            if lines[j].strip() in SECTION_HEADERS:
                end = j
                break
        for k in range(chi + 1, end):
            cols = lines[k].split("\t")
            if len(cols) >= 5 and cols[0].strip().isdigit() and cols[4].strip().isdigit():
                carpet_rows += 1
                apt_total += int(cols[4].strip())
    if carpet_rows:
        add("carpet_area", "carpet_area_row_count", num_val=carpet_rows, conf=0.9,
            hint="visible_text.txt:carpet_table")
        add("carpet_area", "apartment_total_count", num_val=apt_total, conf=0.8,
            unit="apartments", hint="visible_text.txt:carpet_table")

    # 7. Legal-risk COUNTS only (never names). Each is needs_human_review.
    legal_counts = {}
    for key, header in LEGAL_SECTIONS.items():
        c = section_bounds_count(lines, header)
        legal_counts[key] = c
        add("legal_risk_count", f"{key}_row_count", num_val=c, conf=0.4,
            hint=f"visible_text.txt:{header}", status="needs_human_review")

    # 8. Financial encumbrance presence (status flag only).
    fin_present = any("encumbrance" in ln.lower() for ln in lines)
    if fin_present:
        add("status_check", "financial_encumbrance_section_present", text_val="true", conf=0.6,
            hint="visible_text.txt")

    # 9. Document / section presence booleans (no contents).
    for label, key in (("Promoter Details", "promoter_section_present"),
                       ("Promoter Documents", "promoter_documents_section_present"),
                       ("Technical Documents", "technical_documents_section_present"),
                       ("Building Details", "building_details_section_present")):
        if line_index_of(lines, label) >= 0:
            grp = "promoter" if "promoter" in key else "document_check"
            add(grp, key, text_val="true", conf=0.7, hint="visible_text.txt")

    # 10. Promoter name ONLY if it clearly looks like a company (else presence-only above).
    promoter_label_i = line_index_of(lines, "Promoter Details")
    if promoter_label_i >= 0:
        for j in range(promoter_label_i + 1, min(promoter_label_i + 12, len(lines))):
            cand = lines[j].strip()
            if cand and COMPANY_SUFFIX_RE.search(cand) and len(cand) < 80 and "\t" not in cand:
                add("promoter", "promoter_company_name", text_val=cand, conf=0.6,
                    hint="visible_text.txt:promoter")
                break

    return {
        "facts": facts,
        "reg": reg,
        "status": status_val,
        "reg_date": reg_date,
        "proj_name": proj_name,
        "wings": wings,
        "carpet_rows": carpet_rows,
        "apt_total": apt_total,
        "legal_counts": legal_counts,
        "legal_rows_skipped": sum(legal_counts.values()),
    }

# --------------------------------------------------------------------------- DB lookups

def fetch_profile(slug: str, reg: str) -> dict | None:
    sql = (
        "SELECT p.id, coalesce(p.project_status,''), coalesce(p.registration_date::text,''), "
        "coalesce(p.rera_registration_number,''), (p.official_project_name IS NOT NULL), "
        "coalesce(p.verification_status,'') "
        "FROM rera_project_profiles p "
        "JOIN building_web_profiles wp ON wp.id = p.building_web_profile_id "
        f"WHERE wp.profile_slug = {sql_literal(slug)} "
        f"AND p.rera_registration_number = {sql_literal(reg)};"
    )
    code, out = run_psql(sql)
    if code != 0 or not out:
        return None
    parts = out.split("|")
    if len(parts) < 6:
        return None
    return {"id": parts[0], "status": parts[1], "reg_date": parts[2], "reg": parts[3],
            "name_present": parts[4] == "t", "verification_status": parts[5]}

def fetch_manual_carpet(pid: str) -> tuple[int, int]:
    code, out = run_psql(
        "SELECT count(*), coalesce(sum(apartment_count),0) "
        f"FROM rera_carpet_area_records WHERE rera_project_profile_id = {sql_literal(pid)};")
    if code != 0 or not out:
        return 0, 0
    a, b = out.split("|")
    return int(a), int(b)

def fetch_manual_status_types(pid: str) -> set[str]:
    code, out = run_psql(
        "SELECT string_agg(check_type, ',') FROM rera_project_status_checks "
        f"WHERE rera_project_profile_id = {sql_literal(pid)};")
    if code != 0 or not out:
        return set()
    return {x for x in out.split(",") if x}

# --------------------------------------------------------------------------- compare

def build_compares(parsed: dict, profile: dict, manual_carpet: int, manual_apt: int,
                   manual_types: set[str]) -> list[dict]:
    cmps: list[dict] = []

    def cmp(ctype, status, parsed_v, manual_v, summary):
        cmps.append({"type": ctype, "status": status, "parsed": parsed_v,
                     "manual": manual_v, "summary": summary})

    # project_profile_compare (per safe attribute)
    if parsed["reg"] is not None:
        cmp("project_profile_compare",
            "matched" if parsed["reg"] == profile["reg"] else "mismatch",
            parsed["reg"], profile["reg"], "registration_number")
    if parsed["status"]:
        cmp("project_profile_compare",
            "matched" if parsed["status"].lower() == profile["status"].lower() else "mismatch",
            parsed["status"], profile["status"], "project_status")
    if parsed["reg_date"]:
        cmp("project_profile_compare",
            "matched" if parsed["reg_date"] == profile["reg_date"] else "mismatch",
            parsed["reg_date"], profile["reg_date"], "registration_date")

    # carpet_count_compare
    cmp("carpet_count_compare",
        "matched" if parsed["carpet_rows"] == manual_carpet else "mismatch",
        str(parsed["carpet_rows"]), str(manual_carpet), "carpet_area_record_count")

    # apartment_total_compare
    cmp("apartment_total_compare",
        "matched" if parsed["apt_total"] == manual_apt else "mismatch",
        str(parsed["apt_total"]), str(manual_apt), "apartment_total")

    # status_check_compare — snapshot legal/financial sections vs manual status-check presence
    snap_present = []
    for key in ("litigation", "complaint", "appeal", "non_compliance"):
        if parsed["legal_counts"].get(key, 0) >= 0:
            snap_present.append(key)
    manual_has = any(t for t in manual_types if t.endswith("_present") or t == "financial_encumbrance")
    cmp("status_check_compare",
        "matched" if (snap_present and manual_has) else "pending_review",
        f"{len(snap_present)} sections", f"{len(manual_types)} manual checks",
        "section_presence_overlap")

    # risk_count_compare — snapshot COUNTS vs manual presence flags (needs human judgement)
    for key in ("litigation", "complaint", "appeal", "non_compliance"):
        cmp("risk_count_compare", "pending_review", str(parsed["legal_counts"].get(key, 0)),
            "present_flag" if f"{key}_present" in manual_types else "absent",
            f"{key}_count_vs_manual_flag")

    return cmps

# --------------------------------------------------------------------------- SQL emit

def build_apply_sql(parsed: dict, profile_id: str, capture_meta: dict, compares: list[dict]) -> str:
    tag = jsonb_lit(BASE_TAG)
    out = ["BEGIN;", "DO $$", "DECLARE", "  v_cap uuid;", "  v_fact uuid;", "  v_cmp uuid;",
           "BEGIN"]
    # capture
    out.append(
        "  INSERT INTO rera_snapshot_captures "
        "(source_url, output_label, snapshot_folder, capture_method, captcha_solved_by_human, "
        "external_call_made, trusted_for_db, human_review_required, captured_at, "
        "metadata_summary, raw_context) VALUES ("
        f"{sql_literal(capture_meta['source_url'])}, {sql_literal(capture_meta['output_label'])}, "
        f"{sql_literal(capture_meta['snapshot_folder'])}, {sql_literal(capture_meta['capture_method'])}, "
        f"{str(capture_meta['captcha_solved_by_human']).lower()}, true, false, true, "
        f"{sql_literal(capture_meta['captured_at']) if capture_meta['captured_at'] else 'NULL'}, "
        f"{jsonb_lit(capture_meta['metadata_summary'])}, {tag}) RETURNING id INTO v_cap;")
    # one overall parsed_fact_review for the capture
    out.append(
        "  INSERT INTO rera_snapshot_review_items "
        "(rera_snapshot_capture_id, review_type, status, priority, raw_context) "
        f"VALUES (v_cap, 'parsed_fact_review', 'pending', 'normal', {tag});")
    # parsed facts
    for f in parsed["facts"]:
        out.append(
            "  INSERT INTO rera_parsed_fact_candidates "
            "(rera_snapshot_capture_id, rera_project_profile_id, fact_group, fact_key, "
            "fact_value_text, fact_value_numeric, fact_value_date, unit, confidence_score, "
            "parse_status, safe_for_public_use, personal_data_excluded, source_location_hint, "
            "raw_context) VALUES (v_cap, "
            f"{sql_literal(profile_id)}, {sql_literal(f['group'])}, {sql_literal(f['key'])}, "
            f"{sql_literal(f['text'])}, {num_literal(f['num'])}, "
            f"{sql_literal(f['date']) if f['date'] else 'NULL'}, {sql_literal(f['unit'])}, "
            f"{num_literal(f['conf'])}, {sql_literal(f['status'])}, false, true, "
            f"{sql_literal(f['hint'])}, {tag}) RETURNING id INTO v_fact;")
        # legal-risk facts get a privacy_safety_review item
        if f["group"] == "legal_risk_count":
            out.append(
                "  INSERT INTO rera_snapshot_review_items "
                "(rera_snapshot_capture_id, rera_parsed_fact_candidate_id, review_type, status, "
                f"priority, raw_context) VALUES (v_cap, v_fact, 'privacy_safety_review', 'pending', "
                f"'high', {tag});")
    # compares + their review items
    for c in compares:
        out.append(
            "  INSERT INTO rera_snapshot_compare_results "
            "(rera_snapshot_capture_id, rera_project_profile_id, compare_type, compare_status, "
            "parsed_value, manual_value, safe_summary, raw_context) VALUES (v_cap, "
            f"{sql_literal(profile_id)}, {sql_literal(c['type'])}, {sql_literal(c['status'])}, "
            f"{sql_literal(c['parsed'])}, {sql_literal(c['manual'])}, {sql_literal(c['summary'])}, "
            f"{tag}) RETURNING id INTO v_cmp;")
        rtype = ("parser_manual_match_review" if c["status"] == "matched"
                 else "parser_manual_mismatch_review" if c["status"] == "mismatch"
                 else "parsed_fact_review")
        out.append(
            "  INSERT INTO rera_snapshot_review_items "
            "(rera_snapshot_capture_id, rera_snapshot_compare_result_id, review_type, status, "
            f"priority, raw_context) VALUES (v_cap, v_cmp, {sql_literal(rtype)}, 'pending', "
            f"'normal', {tag});")
    out += ["END $$;", "COMMIT;"]
    return "\n".join(out)

# --------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="Parse a MahaRERA snapshot into review-gated candidate facts.")
    ap.add_argument("--snapshot-folder", required=True)
    ap.add_argument("--profile-slug", required=True)
    ap.add_argument("--rera-registration-number", required=True)
    ap.add_argument("--real-ok", action="store_true", help="required to parse a real snapshot")
    ap.add_argument("--apply", action="store_true", help="required to write to the DB")
    args = ap.parse_args()

    if not args.real_ok:
        print("Refusing: --real-ok is required to parse a real snapshot. (Dry-run plan still needs it.)")
        return 1

    folder = Path(args.snapshot_folder)
    ok, msg = validate_snapshot(folder)
    if not ok:
        print(msg)
        return 1

    profile = fetch_profile(args.profile_slug, args.rera_registration_number)
    if not profile:
        print(f"Refusing: no RERA profile for slug={args.profile_slug!r} "
              f"reg={args.rera_registration_number!r} (profile/slug not found).")
        return 1

    parsed = parse_snapshot(folder)
    manual_carpet, manual_apt = fetch_manual_carpet(profile["id"])
    manual_types = fetch_manual_status_types(profile["id"])
    compares = build_compares(parsed, profile, manual_carpet, manual_apt, manual_types)

    # Capture metadata (counts/booleans only — never raw page text).
    meta_path = folder / "metadata.json"
    netsum_path = folder / "network_summary.json"
    md = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    ns = json.loads(netsum_path.read_text(encoding="utf-8")) if netsum_path.exists() else {}
    capture_meta = {
        "source_url": md.get("url", ""),
        "output_label": folder.name,
        "snapshot_folder": str(folder),
        "capture_method": "playwright_human_captcha",
        "captcha_solved_by_human": bool(md.get("captcha_solved_by_human", False)),
        "captured_at": md.get("fetched_at"),
        "metadata_summary": {
            "status": md.get("status"),
            "http_status": md.get("http_status"),
            "captcha_detected": md.get("captcha_detected"),
            "captcha_solved_by_human": md.get("captcha_solved_by_human"),
            "total_responses": ns.get("total_responses"),
            "json_like_responses": ns.get("json_like_responses"),
            "candidate_endpoint_count": ns.get("candidate_endpoint_count"),
        },
    }

    # ----- counts (printed in both dry-run and apply) -----
    by_group: dict[str, int] = {}
    for f in parsed["facts"]:
        by_group[f["group"]] = by_group.get(f["group"], 0) + 1
    cmp_by_type: dict[str, int] = {}
    cmp_by_status: dict[str, int] = {}
    for c in compares:
        cmp_by_type[c["type"]] = cmp_by_type.get(c["type"], 0) + 1
        cmp_by_status[c["status"]] = cmp_by_status.get(c["status"], 0) + 1
    review_by_type = {"parsed_fact_review": 1}  # the overall capture review
    review_by_type["privacy_safety_review"] = sum(1 for f in parsed["facts"] if f["group"] == "legal_risk_count")
    for c in compares:
        rt = ("parser_manual_match_review" if c["status"] == "matched"
              else "parser_manual_mismatch_review" if c["status"] == "mismatch"
              else "parsed_fact_review")
        review_by_type[rt] = review_by_type.get(rt, 0) + 1

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Phase 6.13 RERA snapshot parser [{mode}] ===")
    print(f"snapshot_folder={folder.name}  profile_slug={args.profile_slug}  reg={args.rera_registration_number}")
    print(f"profile_verification_status={profile['verification_status']} (unchanged; parser never updates it)")
    print(f"capture_rows_planned=1")
    print(f"parsed_facts_planned_total={len(parsed['facts'])}")
    for g in sorted(by_group):
        print(f"  fact_group[{g}]={by_group[g]}")
    print(f"compare_results_planned_total={len(compares)}")
    for t in sorted(cmp_by_type):
        print(f"  compare_type[{t}]={cmp_by_type[t]}")
    for s in sorted(cmp_by_status):
        print(f"  compare_status[{s}]={cmp_by_status[s]}")
    review_total = sum(review_by_type.values())
    print(f"review_items_planned_total={review_total}")
    for r in sorted(review_by_type):
        print(f"  review_type[{r}]={review_by_type[r]}")
    print(f"personal_data_excluded_count={len(parsed['facts'])} (all parsed facts; personal_data_excluded=true)")
    print(f"unsafe_skipped_count={parsed['legal_rows_skipped']} "
          "(legal-section rows counted but names NOT stored)")

    if not args.apply:
        print("DRY-RUN only: no DB writes. Re-run with --apply to write the staging rows.")
        print("No canonical RERA rows are ever updated by this parser.")
        return 0

    sql = build_apply_sql(parsed, profile["id"], capture_meta, compares)
    code, out = run_psql(sql)
    if code != 0:
        print(f"DB write FAILED (transaction rolled back): {out[:300]}")
        return 2
    print("APPLIED: staging rows written in one transaction (tagged phase=6.13/source=rera_snapshot_parser).")
    print("No canonical RERA/building/content rows were updated. Outputs are untrusted + review-gated.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
