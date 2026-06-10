# Phase 6.14 — Human Review of RERA Snapshot Parser Candidates

A first, **reversible** human-review pass over the Phase 6.13 parser staging outputs for
Imperial Heights Wing C & D. It approves **only safe, non-personal** parser review items that
corroborate the Phase 6.9 manual data, and leaves the legal-risk-count items for a later human
decision. It is **staging-only**: **no** canonical/manual RERA row changed, **no** profile
verified, **no** match accepted, **no** building merged, **no** content/source-gap change, and
**no** external call, publishing, or outreach.

> Parser facts remain **review-gated** and **not** safe for public use. Approving a
> `parser_manual_match_review` confirms the snapshot **corroborates** the manual record; it does
> **not** verify the RERA profile or make any fact publishable.

## Review items inspected (15 total, all were `pending`)

| review_type | count | linked to | decision |
| ----------- | ----- | --------- | -------- |
| `parser_manual_match_review` | 6 | matched compares (apartment_total, carpet_count, project_profile ×3, status_check) | **approved** |
| `privacy_safety_review` | 4 | legal_risk_count facts (appeal/complaint/litigation/non-compliance), `personal_data_excluded=true`, `safe_for_public_use=false` | **approved** (confirms names excluded) |
| `parsed_fact_review` (risk) | 4 | `risk_count_compare` (pending_review) | **left pending** |
| `parsed_fact_review` (capture) | 1 | overall snapshot | **left pending** |

## What was approved

- **6 `parser_manual_match_review`** items where the linked compare is `matched` and no personal
  data is involved. Approving these promoted the **5** mapped parsed facts to `matched_manual`:
  `rera_registration_number`, `project_status`, `registration_date`, `carpet_area_row_count`,
  `apartment_total_count` (`status_check_compare` maps to no single fact, so it only approved the
  review item).
- **4 `privacy_safety_review`** items — approved **only** because each linked legal-risk-count
  fact has `personal_data_excluded=true` and `safe_for_public_use=false`. This confirms personal
  names were excluded; it does **not** verify the count. The legal-count facts therefore stay
  `needs_human_review`.

Result after apply: parsed facts = **5 matched_manual / 8 candidate / 4 needs_human_review**;
review items = **6 + 4 approved / 5 pending**; compares unchanged (6 matched / 4 pending_review).

## What remains pending / needs_more_info

The **4 `risk_count_compare`** reviews (litigation / complaint / appeal / non-compliance row
counts) and the **1 capture-level** `parsed_fact_review` are **left pending**. The legal-risk
counts compare snapshot *counts* against manual *presence flags* and require human legal/context
judgement; they are **not** auto-approved. Their facts remain `needs_human_review` and are stored
as **counts only** (no names).

## Why canonical RERA rows were not updated

This phase writes **only** to the Phase 6.13 staging tables (`rera_snapshot_review_items`,
`rera_parsed_fact_candidates`). The canonical/manual rows are untouched: profile stays
`needs_human_review`, both matches stay `candidate`, `rera_carpet_area_records` (26),
`rera_project_status_checks` (13), and `rera_verification_review_items` (6) are unchanged.
Corroboration by the parser is evidence for a later, separate verification decision — it is not
itself a verification.

## Why content fact use remains blocked

`vw_imperial_heights_rera_parser_readiness` still reports
`ready_to_update_rera_profile = false` and `ready_for_content_fact_use = false` (both are
hard-false by design). No `ready_for_ai_draft` / `ready_for_publish` flag was set; nothing was
published or sent.

## Scripts

`scripts/review_rera_snapshot_parser_candidates.py` (dry-run default; `--real-ok` required;
`--apply` to write) — safe-batch helpers `--approve-safe-matched` and `--approve-privacy-safety`,
plus single-item `--review-item-id` + `--status`. It refuses without `--real-ok`, refuses to let
`--approve-safe-matched` touch risk/legal-count items, enforces `--limit`, and refuses
already-non-pending items unless `--allow-existing`. Every change is stamped
`raw_context.review_phase='6.14'`.

```bash
# The exact safe batch applied this phase (drop --apply for the dry-run):
python3 scripts/review_rera_snapshot_parser_candidates.py \
  --profile-slug imperial-heights-goregaon-west \
  --approve-safe-matched --approve-privacy-safety \
  --reviewed-by operator \
  --decision-notes "Phase 6.14: approve non-personal matched + privacy-safety (names excluded)" \
  --limit 10 --real-ok --apply
```

## Rollback (dry-run only this phase)

`scripts/revert_rera_snapshot_parser_review.py` reverts **only** rows stamped
`review_phase=6.14` (review items → `pending`, promoted facts → `candidate`). It refuses if the
RERA profile is now `verified` or any match `accepted`, and never touches canonical/manual RERA,
building, content, or gap rows.

```bash
# Dry-run (counts only; nothing changed):
python3 scripts/revert_rera_snapshot_parser_review.py --profile-slug imperial-heights-goregaon-west
# Real revert requires BOTH flags (NOT run this phase):
#   ... --apply --real-ok
```

## No external calls / no publishing

No MahaRERA scraping, no external API, no Playwright in this phase. Nothing published, nothing
sent.

## Next phase

**Profile verification and match acceptance after review** — a separate, deliberate, still
review-gated step that (a) works the remaining `risk_count_compare` / legal-context items in
`vw_rera_verification_review_queue` + `vw_rera_snapshot_review_queue`, then (b) considers marking
the RERA profile verified and **accepting** the building match, which would unlock the Phase 6.7
RERA-anchored building dedupe. Public drafting + Wix publishing remain out of scope.
