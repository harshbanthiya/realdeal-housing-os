#!/usr/bin/env python3
"""Cohort review engine — the operator surface for the big pending queues.

The review queues are cohort-shaped, not row-shaped: 886 Ekta registration
records all came from one IGR sweep with one layout, 2,060 media rows are all
disk-scanned videos. Deciding those one card at a time is not a workflow, so
this groups each queue by its natural cohort key, shows a sample, and applies
one decision to the whole cohort.

  --list                          all cohorts across all queues, as JSON
  --sample --queue Q --cohort K   up to 20 sample rows for one cohort, as JSON
  --apply-cohort --queue Q --cohort K --decision approve|reject
                                  dry-run unless --apply

Dry-run is the default everywhere. Output is JSON on one line (never pipe-
split; see workers/_lib.q()).

Two live queues are deliberately NOT here:
  wa_number_queue         — approving means attach/create a contact, not a
                            status flip. It already has a working UI.
  zapkey_transactions     — 3,058 'pending_review' rows await *linking logic*
                            (unit/tower parsing), not a human yes/no. Flipping
                            them to 'linked' without resolving building_unit_id
                            would record a link that does not exist.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql, sql_literal as lit  # noqa: E402

# Each queue: where the pending rows are, how they clump, what a decision writes.
# `cohort` and `sample` are SQL expressions over alias `t` (+ whatever `join`
# brings in). `approve`/`reject` are SET clause bodies; {by} and {note} are
# substituted with already-quoted literals.
QUEUES: dict[str, dict] = {
    "contact_import": {
        "label": "Legacy import stubs — NO reviewable content",
        "question": ("These Phase 5.4 rows have no entity attached and a title that just "
                     "repeats their own type. There is nothing to judge. Closing them only "
                     "clears the counter — the real decisions are in the queues below."),
        "table": "import_review_items",
        "join": "LEFT JOIN import_batches ib ON ib.id = t.import_batch_id",
        "pending": "t.status = 'pending'",
        "cohort": "t.review_type || ' · ' || coalesce(ib.metadata->>'batch_label', '(no batch)')",
        "sample": ("'(no content recorded — stub for ' || t.review_type || ', batch ' || "
                   "coalesce(ib.metadata->>'batch_label','?') || ')'"),
        "approve": "status = 'approved', reviewed_by = {by}, reviewed_at = now(), decision_notes = {note}",
        "reject": "status = 'rejected', reviewed_by = {by}, reviewed_at = now(), decision_notes = {note}",
    },
    "unit_registration": {
        "label": "Unit registration review",
        "question": ("Is this a real registration for this flat? The sample shows unit, "
                     "document type, date and price as parsed from the IGR record."),
        "table": "unit_registration_review_items",
        "join": ("LEFT JOIN buildings b ON b.id = t.building_id "
                 "LEFT JOIN unit_registration_records rec ON rec.id = t.unit_registration_record_id"),
        "pending": "t.status = 'pending'",
        "cohort": ("coalesce(b.name, '(no building)') || ' · ' || t.review_type || ' · ' || "
                   "coalesce(t.raw_context->>'source', '(no source)')"),
        # Show the actual registration being judged, not the review_type label.
        "sample": ("concat_ws(' · ', "
                   "nullif(concat_ws('-', rec.wing_text, rec.unit_text), ''), "
                   "rec.document_type, rec.registration_date::text, "
                   "nullif(rec.consideration_amount::text, ''), "
                   "coalesce(t.raw_context->>'src_file', t.raw_context->>'file'))"),
        "approve": "status = 'approved', reviewed_by = {by}, reviewed_at = now(), decision_notes = {note}",
        "reject": "status = 'rejected', reviewed_by = {by}, reviewed_at = now(), decision_notes = {note}",
    },
    "media": {
        "label": "Media library review",
        "table": "media_assets",
        "question": ("Is this file fit to publish? Approving marks it reviewed. NOTE: for an "
                     "'(untagged)' cohort this alone does NOT make the files usable in Shorts — "
                     "shorts_scout also needs an asset_type, which is set in /cockpit/media. "
                     "Reject archives the file."),
        "join": "LEFT JOIN buildings b ON b.id = t.building_id",
        "pending": "t.reviewed IS FALSE",
        "cohort": "coalesce(t.source, '(no source)') || ' · ' || coalesce(t.asset_type, '(untagged)')",
        "sample": ("regexp_replace(t.file_path, '^.*/', '') || '   [' || "
                   "coalesce(b.name, 'no building') || ']'"),
        "approve": "reviewed = TRUE, review_notes = {note}, updated_at = now()",
        "reject": "reviewed = TRUE, status = 'archived', review_notes = {note}, updated_at = now()",
    },
    "property_rels": {
        "label": "Contact → property links",
        "table": "contact_property_relationships",
        "question": ("Does this person really hold this flat, in this role? Approving makes "
                     "them targetable for outreach about that unit."),
        "join": ("LEFT JOIN buildings b ON b.id = t.building_id "
                 "LEFT JOIN contacts c ON c.id = t.contact_id "
                 "LEFT JOIN building_units u ON u.id = t.building_unit_id"),
        "pending": "t.relationship_status = 'pending_review'",
        "cohort": "coalesce(b.name, '(no building)') || ' · ' || t.relationship_type",
        "sample": ("concat_ws(' · ', coalesce(c.full_name, '(unnamed contact)'), "
                   "coalesce(nullif(u.unit_number,''), '(no unit)'), "
                   "coalesce(c.phone_primary, 'no phone'), "
                   "'from ' || coalesce(split_part(t.notes, ':', 1), 'unknown source'))"),
        "approve": "relationship_status = 'active', updated_at = now()",
        "reject": "relationship_status = 'rejected', updated_at = now()",
    },
    "contact_dupes": {
        "label": "Duplicate contact candidates",
        "table": "contact_duplicate_candidates",
        "question": ("Are these two rows the same person? Approving marks them safe to merge "
                     "into one contact."),
        "join": ("LEFT JOIN contact_import_rows r1 ON r1.id = t.contact_import_row_id_1 "
                 "LEFT JOIN contact_import_rows r2 ON r2.id = t.contact_import_row_id_2"),
        "pending": "t.status = 'pending_review'",
        "cohort": "t.candidate_type || ' · ' || coalesce(t.duplicate_strength, '(no strength)')",
        "sample": ("left(coalesce(r1.cleaned_display_name, r1.raw_name, '?'), 48) || '   ==   ' || "
                   "left(coalesce(r2.cleaned_display_name, r2.raw_name, '?'), 48) || "
                   "'   [' || coalesce(r1.phone_normalized, '?') || ']'"),
        "approve": "status = 'approved'",
        "reject": "status = 'rejected'",
    },
    "party_matches": {
        "label": "Registration party → contact matches",
        "table": "registration_party_contact_matches",
        "question": ("The registry names one person; our DB has another. Same human? Approving "
                     "links the registration to that contact."),
        "join": ("LEFT JOIN buildings b ON b.id = t.building_id "
                 "LEFT JOIN unit_registration_parties p ON p.id = t.unit_registration_party_id "
                 "LEFT JOIN contacts c ON c.id = t.contact_id "
                 "LEFT JOIN building_units u ON u.id = t.building_unit_id"),
        "pending": "t.match_status = 'needs_review'",
        "cohort": "coalesce(b.name, '(no building)') || ' · ' || coalesce(t.match_strength, '(no strength)')",
        "sample": ("'registry: ' || left(coalesce(p.party_name_english, p.party_name_raw, '?'), 40) || "
                   "'   ==   ours: ' || left(coalesce(c.full_name, '?'), 40) || "
                   "'   [' || coalesce(nullif(u.unit_number,''), 'no unit') || "
                   "' · sim ' || coalesce(round(t.name_similarity_score::numeric, 2)::text, '?') || ']'"),
        "approve": "match_status = 'matched', updated_at = now()",
        "reject": "match_status = 'rejected', updated_at = now()",
    },
    "drive_contacts": {
        "label": "Drive contact sheets — name near-misses",
        "question": ("A name on a drive sheet closely resembles an existing contact, but the "
                     "phone differs. Same person? Sample reads: sheet name → our contact (similarity)."),
        "table": "contact_sheet_rows",
        "join": "LEFT JOIN contact_sheet_files f ON f.id = t.sheet_file_id",
        "pending": "t.review_status = 'pending'",
        "cohort": ("coalesce(f.doc_kind, '(unknown)') || ' · ' || "
                   "regexp_replace(coalesce(f.file_path, ''), '^.*/', '')"),
        "sample": ("concat_ws(' → ', t.parsed_name, t.candidate_name) || ' (sim ' || "
                   "coalesce(round(t.name_similarity::numeric, 2)::text, '?') || ')'"),
        "approve": ("review_status = 'approved', resolution = 'matched_phone', "
                    "contact_id = candidate_contact_id, reviewed_by = {by}, "
                    "reviewed_at = now(), decision_notes = {note}"),
        "reject": ("review_status = 'rejected', resolution = 'pending', "
                   "reviewed_by = {by}, reviewed_at = now(), decision_notes = {note}"),
    },
    "phonebook_rename": {
        "label": "Sales phone — rename to canonical",
        "question": ("Rename this card on her phone. Sample reads: current name → proposed name. "
                     "Approving only queues it; nothing writes to the phone yet."),
        "table": "phonebook_proposals",
        "join": "",
        "pending": "t.status = 'pending' AND t.direction = 'to_phone'",
        "cohort": "coalesce(t.role, '(no role)') || ' · ' || t.confidence",
        "sample": "t.current_value || '  →  ' || t.proposed_value",
        "approve": ("status = 'approved', reviewed_by = {by}, reviewed_at = now(), "
                    "decision_notes = {note}"),
        "reject": ("status = 'rejected', reviewed_by = {by}, reviewed_at = now(), "
                   "decision_notes = {note}"),
    },
    "phonebook_to_db": {
        "label": "Sales phone → DB (unit links her phone knows)",
        "question": ("Her phonebook claims this number belongs to this flat, and we have no "
                     "phone for it. Accept her phone as the source? 'low' = more than one "
                     "number claims the same flat — check the sample before approving."),
        "table": "phonebook_proposals",
        "join": "",
        "pending": "t.status = 'pending' AND t.direction = 'to_db'",
        # Confidence leads the cohort key: the 'low' rows are units with more
        # than one competing phone and must never be bulk-approved blind.
        "cohort": "t.confidence || ' · ' || coalesce(t.role, '(no role)') || ' · ' || t.change_type",
        "sample": "t.proposed_value || '  ←  ' || coalesce(t.note_block, '')",
        "approve": ("status = 'approved', reviewed_by = {by}, reviewed_at = now(), "
                    "decision_notes = {note}"),
        "reject": ("status = 'rejected', reviewed_by = {by}, reviewed_at = now(), "
                   "decision_notes = {note}"),
    },
    "worker_findings": {
        "label": "Worker findings inbox",
        "question": "A worker flagged this. Approve = acknowledged, Reject = dismiss.",
        "table": "worker_findings",
        "join": "",
        "pending": "t.status = 'pending'",
        "cohort": "t.worker || ' · ' || t.severity",
        "sample": "t.title",
        "approve": "status = 'acknowledged'",
        "reject": "status = 'dismissed'",
    },
}


def q_json(sql: str) -> object:
    """Run a query whose single column is JSON. Avoids the pipe-split trap."""
    code, out = run_psql(sql)
    if code != 0:
        print(json.dumps({"error": out}))
        sys.exit(1)
    return json.loads(out) if out.strip() else []


def list_cohorts() -> list[dict]:
    """One psql round-trip for every cohort in every queue."""
    parts = []
    for name, cfg in QUEUES.items():
        parts.append(f"""
        SELECT {lit(name)} AS queue, {lit(cfg['label'])} AS label,
               {lit(cfg.get('question', ''))} AS question,
               ({cfg['cohort']}) AS cohort, count(*) AS pending,
               min(t.created_at)::date::text AS oldest,
               max(t.created_at)::date::text AS newest
          FROM {cfg['table']} t {cfg['join']}
         WHERE {cfg['pending']}
         GROUP BY 3, 4
        """)
    union = " UNION ALL ".join(parts)
    return q_json(f"SELECT coalesce(json_agg(x ORDER BY x.pending DESC), '[]'::json) FROM ({union}) x")


def sample_rows(queue: str, cohort: str, limit: int = 20) -> list[dict]:
    cfg = QUEUES[queue]
    return q_json(f"""
        SELECT coalesce(json_agg(x), '[]'::json) FROM (
          SELECT ({cfg['sample']}) AS detail, t.created_at::date::text AS created
            FROM {cfg['table']} t {cfg['join']}
           WHERE {cfg['pending']} AND ({cfg['cohort']}) = {lit(cohort)}
           ORDER BY t.created_at DESC
           LIMIT {int(limit)}
        ) x
    """)


def apply_cohort(queue: str, cohort: str, decision: str, by: str, note: str,
                 apply: bool) -> dict:
    cfg = QUEUES[queue]
    count = q_json(f"""
        SELECT to_json(count(*)) FROM {cfg['table']} t {cfg['join']}
         WHERE {cfg['pending']} AND ({cfg['cohort']}) = {lit(cohort)}
    """)
    if not apply:
        return {"status": "ok", "dry_run": True, "queue": queue, "cohort": cohort,
                "decision": decision, "would_update": count}

    set_clause = cfg[decision].format(by=lit(by), note=lit(note))
    # The cohort expression may reference joined tables, so re-select ids first.
    updated = q_json(f"""
        WITH target AS (
          SELECT t.id FROM {cfg['table']} t {cfg['join']}
           WHERE {cfg['pending']} AND ({cfg['cohort']}) = {lit(cohort)}
        ), upd AS (
          UPDATE {cfg['table']} x SET {set_clause}
            FROM target WHERE x.id = target.id
          RETURNING 1
        )
        SELECT to_json(count(*)) FROM upd
    """)
    return {"status": "ok", "dry_run": False, "queue": queue, "cohort": cohort,
            "decision": decision, "updated": updated}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--apply-cohort", action="store_true")
    ap.add_argument("--queue")
    ap.add_argument("--cohort")
    ap.add_argument("--decision", choices=["approve", "reject"])
    ap.add_argument("--by", default="operator")
    ap.add_argument("--note", default="")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if a.list:
        print(json.dumps(list_cohorts()))
        return

    if a.queue not in QUEUES:
        print(json.dumps({"error": f"unknown queue: {a.queue}"}))
        sys.exit(1)
    if not a.cohort:
        print(json.dumps({"error": "--cohort required"}))
        sys.exit(1)

    if a.sample:
        print(json.dumps(sample_rows(a.queue, a.cohort)))
        return

    if a.apply_cohort:
        if not a.decision:
            print(json.dumps({"error": "--decision required"}))
            sys.exit(1)
        note = a.note or f"Cohort {a.decision} from cockpit."
        print(json.dumps(apply_cohort(a.queue, a.cohort, a.decision, a.by, note, a.apply)))
        return

    print(json.dumps({"error": "nothing to do — pass --list, --sample or --apply-cohort"}))
    sys.exit(1)


if __name__ == "__main__":
    main()
