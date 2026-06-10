# Phase 6.13 — Review-Gated MahaRERA Snapshot Parser

Parses a **post-CAPTCHA** MahaRERA snapshot (captured in Phase 6.12, operator-assisted) into
**review-gated, untrusted candidate facts**, and compares them against the **Phase 6.9 manual
RERA rows**. This phase is **staging + parser only**: it does **not** verify a RERA profile,
accept a match, merge buildings, resolve source gaps, mark content ready, publish, or send
outreach, and it **never** updates the canonical RERA tables.

> RERA data remains an **internal verification aid, not legal advice**. Parser output is raw
> and **untrusted** until a human reviews it.

## Snapshot used

`exports/rera_snapshots/20260610T102843Z_imperial_heights_wing_cd_6231_post_captcha/`
(git-ignored), captured in Phase 6.12 for
`https://maharerait.maharashtra.gov.in/public/project/view/6231`
(Imperial Heights Wing C & D, reg `P51800003270`). The parser reads `visible_text.txt`,
`metadata.json`, and `network_summary.json`; it never commits or prints raw page text.

## Parser approach

`scripts/parse_rera_snapshot_to_candidates.py` (dry-run by default; `--real-ok` to read a real
snapshot; `--apply` to write). It **refuses** unless the snapshot folder is under
`exports/rera_snapshots/` **and** git-ignored, the profile slug + RERA registration number
resolve to a real `rera_project_profiles` row, and `visible_text.txt` exists. All writes go to
the Phase 6.13 staging tables only, in **one transaction**, tagged
`raw_context = {"phase":"6.13","source":"rera_snapshot_parser"}`.

Migration `schemas/020_rera_snapshot_parser_staging.sql` adds 4 tables —
`rera_snapshot_captures`, `rera_parsed_fact_candidates`, `rera_snapshot_compare_results`,
`rera_snapshot_review_items` — and 5 read-only dashboards:
`vw_rera_snapshot_capture_dashboard`, `vw_rera_parsed_fact_candidate_dashboard`,
`vw_rera_snapshot_compare_dashboard`, `vw_rera_snapshot_review_queue`, and
`vw_imperial_heights_rera_parser_readiness` (whose `ready_to_update_rera_profile` and
`ready_for_content_fact_use` are **hard-coded false** — parser output cannot flip any
readiness).

## Facts extracted as candidates (17 total)

Counts only; values shown are non-personal official/public facts:

| fact_group | facts | examples (safe) |
| ---------- | ----- | --------------- |
| project_profile | 4 | registration number, project name, project status, registration date |
| promoter | 3 | promoter **company** name (company-suffix-guarded), promoter section presence |
| wing_building | 2 | wing count (2: Wing C + Wing D), wing labels |
| carpet_area | 2 | carpet-area row count (26), apartment total (213) |
| document_check | 2 | building-details / technical-documents section presence |
| legal_risk_count | 4 | litigation / complaint / appeal / non-compliance **row counts** (`needs_human_review`) |

The `legal_risk_count` facts are **counts only**. Personal names from the
complaint / litigation / appeal / non-compliance sections are **never** read into a stored
value (51 legal-section rows were counted but **no names stored**).

## Compare results vs manual Phase 6.9 rows (10 total)

| compare_type | status | parsed vs manual |
| ------------ | ------ | ---------------- |
| project_profile_compare (×3) | **matched** | reg `P51800003270`, status `Completed`, reg date `2017-08-05` |
| carpet_count_compare | **matched** | 26 vs 26 |
| apartment_total_compare | **matched** | 213 vs 213 |
| status_check_compare | **matched** | section presence overlaps manual checks |
| risk_count_compare (×4) | **pending_review** | snapshot counts vs manual presence flags (human judgement) |

Result: **6 matched, 0 mismatch, 4 pending_review** — the snapshot **corroborates** the manual
Phase 6.9 data, with the legal-risk counts left for human review. 15 review items were created
(`parsed_fact_review`, `parser_manual_match_review`, `privacy_safety_review`), all `pending`.

## Privacy exclusions

- Stored values contain **no** personal names. A scan for
  `complainant|respondent|allottee|director|advocate|petitioner|vs.` in stored
  `fact_value_text` returns **0**.
- Complaint / litigation / appeal / non-compliance sections → **counts/flags only**.
- The promoter **company** name (`...PRIVATE LIMITED`) is an **official registered company**
  (public record), extracted only when a company-suffix pattern matches — never a landowner /
  person name. Promoter address and landowner names are **not** stored.
- Every parsed-fact row carries `personal_data_excluded=true` and `safe_for_public_use=false`.

## Why no canonical RERA rows were updated

The parser writes **only** to the Phase 6.13 staging tables. The canonical
`rera_project_profiles` row stays `needs_human_review`, both
`rera_building_match_candidates` stay `candidate`, and `rera_carpet_area_records` (26) /
`rera_project_status_checks` (13) / `rera_verification_review_items` (6) are untouched. Parser
output is untrusted by design: a human must work `vw_rera_snapshot_review_queue` before any
profile update, match acceptance, or content fact use. `ready_to_update_rera_profile` and
`ready_for_content_fact_use` remain **false**.

## Cleanup (dry-run only this phase)

`scripts/cleanup_rera_snapshot_parser_candidates.py` removes **only** rows tagged
`phase=6.13/source=rera_snapshot_parser`. It refuses if any parsed fact is already
`safe_for_public_use=true` or any review item is `approved`, never deletes Phase 6.9 manual
rows, and never deletes snapshot files.

```bash
# Dry-run (counts only; nothing deleted):
python3 scripts/cleanup_rera_snapshot_parser_candidates.py --profile-slug imperial-heights-goregaon-west
# Real delete requires BOTH flags (NOT run this phase):
#   python3 scripts/cleanup_rera_snapshot_parser_candidates.py --profile-slug imperial-heights-goregaon-west --apply --real-ok
```

## How to run the parser

```bash
# Dry-run plan (reads the real snapshot, no DB writes):
python3 scripts/parse_rera_snapshot_to_candidates.py \
  --snapshot-folder exports/rera_snapshots/<ts>_imperial_heights_wing_cd_6231_post_captcha \
  --profile-slug imperial-heights-goregaon-west \
  --rera-registration-number P51800003270 --real-ok

# Apply (writes staging rows in one transaction):
#   ... same as above plus --apply
```

## Next phase

**Human review of parser candidates** — an operator works `vw_rera_snapshot_review_queue`
(and `vw_rera_snapshot_compare_dashboard`) to approve/reject parsed facts and the
parser-vs-manual matches, including the four `risk_count_compare` items and the privacy-safety
reviews. Only after that does a separate, review-gated step consider updating the canonical
RERA profile / accepting a match / RERA-anchored building dedupe. Public drafting + Wix
publishing remain out of scope.
