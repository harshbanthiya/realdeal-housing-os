/**
 * Contact-cleanup data layer (read-only).
 *
 * Reads the EXISTING masked review views (never raw PII columns):
 *   - vw_review_dashboard_summary           → per-batch rollup (+ is_real_import)
 *   - vw_review_queue                       → the import_review_items queue
 *   - vw_review_duplicate_candidates        → dedupe decisions
 *   - vw_canonical_contacts_review          → promoted canonical contacts
 *   - vw_contact_property_relationship_review → contact→building/unit links
 *
 * Every query runs through db.ts in a READ ONLY transaction. Mutations are NOT
 * here — they go through guarded server actions that shell out to the audited
 * Python scripts. When DATABASE_URL is unset, getters return seed samples so the
 * shell still renders.
 */
import { isDbConfigured, readQuery } from "@/lib/db";
import type {
  ReviewBatch, ReviewQueueItem, DuplicateCandidate, CanonicalContactRow,
  ContactRelationshipRow, QueueCount, QueueFilter,
} from "./contacts-types";

// Re-export types + pure helpers so existing server-side imports from
// "@/lib/cockpit/contacts" keep working. Client components import the same
// names from "./contacts-types" directly (this file pulls in pg via db.ts).
export * from "./contacts-types";

const live = isDbConfigured;
const num = (v: unknown) => Number(v ?? 0) || 0;

/**
 * Labels of REAL (non-test) import batches, read cheaply from import_batches
 * metadata. We deliberately avoid vw_review_dashboard_summary in the request
 * path: that view's 7-way LEFT JOIN + count(DISTINCT) fans out to ~300k rows
 * and takes ~6s (over the pool's 5s statement_timeout). See FIXME below.
 */
const REAL_BATCH_LABELS =
  `select ib2.metadata->>'batch_label' from import_batches ib2
   where coalesce((ib2.metadata->>'is_real_import')::boolean, false) = true`;

// ---------------- seed fallback ----------------
const SEED_BATCHES: ReviewBatch[] = [
  { importBatchId: "seed-1", batchLabel: "REAL_PHASE_3_5_TEST_001", isRealImport: true, canonicalMergeDone: false, sourceFiles: 1, importRows: 22, contactMethods: 62, duplicateCandidates: 1, pending: 40, approved: 4, rejected: 0, createdAt: "" },
  { importBatchId: "seed-2", batchLabel: "REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001", isRealImport: true, canonicalMergeDone: false, sourceFiles: 1, importRows: 58, contactMethods: 116, duplicateCandidates: 14, pending: 186, approved: 2, rejected: 0, createdAt: "" },
];
const SEED_QUEUE: ReviewQueueItem[] = [
  { reviewItemId: "seed-q1", batchLabel: "REAL_PHASE_3_5_TEST_001", reviewType: "merge_candidate", priority: "normal", status: "pending", title: "Merge candidate — masked contact", summary: "Has phone + lead requirement; no existing canonical link.", recommendedAction: "approve_merge", reviewedBy: null, createdAt: "" },
];

// ---------------- getters ----------------
export async function getReviewBatches(realOnly = false): Promise<ReviewBatch[]> {
  if (!live()) return realOnly ? SEED_BATCHES.filter((b) => b.isRealImport) : SEED_BATCHES;
  // Same numbers as vw_review_dashboard_summary, but via per-batch scalar
  // subqueries (no cartesian fan-out): ~0.4s vs ~6s.
  const rows = await readQuery<Record<string, unknown>>(
    `select ib.id::text as import_batch_id,
            ib.metadata->>'batch_label' as batch_label,
            coalesce((ib.metadata->>'is_real_import')::boolean, false) as is_real_import,
            coalesce((ib.metadata->>'canonical_merge_done')::boolean, false) as canonical_merge_done,
            (select count(*) from source_files sf where sf.import_batch_id = ib.id) as source_files_count,
            (select count(*) from contact_import_rows cir where cir.import_batch_id = ib.id) as contact_import_rows_count,
            (select count(*) from contact_methods cm join contact_import_rows cir on cm.contact_import_row_id = cir.id where cir.import_batch_id = ib.id) as contact_methods_count,
            (select count(*) from contact_duplicate_candidates cdc where cdc.import_batch_id = ib.id) as duplicate_candidates_count,
            (select count(*) from import_review_items iri where iri.import_batch_id = ib.id and iri.status = 'pending') as pending_review_items_count,
            (select count(*) from import_review_items iri where iri.import_batch_id = ib.id and iri.status = 'approved') as approved_review_items_count,
            (select count(*) from import_review_items iri where iri.import_batch_id = ib.id and iri.status = 'rejected') as rejected_review_items_count,
            ib.created_at::text
     from import_batches ib
     where ib.metadata->>'batch_label' is not null
       ${realOnly ? "and coalesce((ib.metadata->>'is_real_import')::boolean, false) = true" : ""}
     order by coalesce((ib.metadata->>'is_real_import')::boolean, false) desc, ib.created_at`);
  return rows.map((r) => ({
    importBatchId: String(r.import_batch_id ?? ""),
    batchLabel: String(r.batch_label ?? ""),
    isRealImport: Boolean(r.is_real_import),
    canonicalMergeDone: Boolean(r.canonical_merge_done),
    sourceFiles: num(r.source_files_count),
    importRows: num(r.contact_import_rows_count),
    contactMethods: num(r.contact_methods_count),
    duplicateCandidates: num(r.duplicate_candidates_count),
    pending: num(r.pending_review_items_count),
    approved: num(r.approved_review_items_count),
    rejected: num(r.rejected_review_items_count),
    createdAt: String(r.created_at ?? ""),
  }));
}

export async function getQueueCounts(realOnly = true): Promise<QueueCount[]> {
  if (!live()) return [
    { reviewType: "merge_candidate", status: "pending", count: 77 },
    { reviewType: "merge_candidate", status: "approved", count: 6 },
    { reviewType: "duplicate_contact", status: "pending", count: 14 },
  ];
  const rows = await readQuery<Record<string, unknown>>(
    `select q.review_type, q.status, count(*) n
     from vw_review_queue q
     ${realOnly ? `where q.batch_label in (${REAL_BATCH_LABELS})` : ""}
     group by q.review_type, q.status
     order by q.review_type, q.status`);
  return rows.map((r) => ({ reviewType: String(r.review_type ?? ""), status: String(r.status ?? ""), count: num(r.n) }));
}

export async function getReviewQueue(filter: QueueFilter = {}): Promise<ReviewQueueItem[]> {
  if (!live()) return SEED_QUEUE;
  const where: string[] = [];
  const params: unknown[] = [];
  if (filter.realOnly) where.push(`q.batch_label in (${REAL_BATCH_LABELS})`);
  if (filter.batchLabel) { params.push(filter.batchLabel); where.push(`q.batch_label = $${params.length}`); }
  if (filter.reviewType) { params.push(filter.reviewType); where.push(`q.review_type = $${params.length}`); }
  if (filter.status) { params.push(filter.status); where.push(`q.status = $${params.length}`); }
  params.push(Math.min(filter.limit ?? 100, 500));
  const rows = await readQuery<Record<string, unknown>>(
    `select review_item_id::text, batch_label, review_type, priority, status, title,
            summary, recommended_action, reviewed_by, created_at::text
     from vw_review_queue q
     ${where.length ? `where ${where.join(" and ")}` : ""}
     order by case q.priority when 'high' then 0 when 'normal' then 1 else 2 end, q.created_at
     limit $${params.length}`, params);
  return rows.map((r) => ({
    reviewItemId: String(r.review_item_id ?? ""),
    batchLabel: String(r.batch_label ?? ""),
    reviewType: String(r.review_type ?? ""),
    priority: String(r.priority ?? "normal"),
    status: String(r.status ?? "pending"),
    title: String(r.title ?? ""),
    summary: String(r.summary ?? ""),
    recommendedAction: String(r.recommended_action ?? ""),
    reviewedBy: r.reviewed_by ? String(r.reviewed_by) : null,
    createdAt: String(r.created_at ?? ""),
  }));
}

export async function getDuplicateCandidates(filter: QueueFilter = {}): Promise<DuplicateCandidate[]> {
  if (!live()) return [];
  const where: string[] = [];
  const params: unknown[] = [];
  if (filter.realOnly) where.push(`d.batch_label in (${REAL_BATCH_LABELS})`);
  if (filter.batchLabel) { params.push(filter.batchLabel); where.push(`d.batch_label = $${params.length}`); }
  if (filter.status) { params.push(filter.status); where.push(`d.status = $${params.length}`); }
  params.push(Math.min(filter.limit ?? 100, 500));
  const rows = await readQuery<Record<string, unknown>>(
    `select duplicate_candidate_id::text, batch_label, duplicate_strength, candidate_type,
            reason, status, left_display_hint, right_display_hint, masked_phone_hint, masked_email_hint
     from vw_review_duplicate_candidates d
     ${where.length ? `where ${where.join(" and ")}` : ""}
     order by case d.duplicate_strength when 'strong' then 0 when 'medium' then 1 else 2 end
     limit $${params.length}`, params);
  return rows.map((r) => ({
    duplicateCandidateId: String(r.duplicate_candidate_id ?? ""),
    batchLabel: String(r.batch_label ?? ""),
    strength: String(r.duplicate_strength ?? ""),
    candidateType: String(r.candidate_type ?? ""),
    reason: String(r.reason ?? ""),
    status: String(r.status ?? "pending"),
    leftHint: String(r.left_display_hint ?? ""),
    rightHint: String(r.right_display_hint ?? ""),
    maskedPhoneHint: String(r.masked_phone_hint ?? ""),
    maskedEmailHint: String(r.masked_email_hint ?? ""),
  }));
}

export async function getCanonicalContacts(): Promise<CanonicalContactRow[]> {
  if (!live()) return [];
  const rows = await readQuery<Record<string, unknown>>(
    `select contact_id::text, display_hint, canonical_status, is_test,
            method_count, lead_requirement_count, source_file_count, merge_label, merge_status
     from vw_canonical_contacts_review
     order by is_test, created_at desc`);
  return rows.map((r) => ({
    contactId: String(r.contact_id ?? ""),
    displayHint: String(r.display_hint ?? ""),
    canonicalStatus: String(r.canonical_status ?? ""),
    isTest: Boolean(r.is_test),
    methodCount: num(r.method_count),
    leadRequirementCount: num(r.lead_requirement_count),
    sourceFileCount: num(r.source_file_count),
    mergeLabel: r.merge_label ? String(r.merge_label) : null,
    mergeStatus: r.merge_status ? String(r.merge_status) : null,
  }));
}

export async function getContactRelationships(): Promise<ContactRelationshipRow[]> {
  if (!live()) return [];
  const rows = await readQuery<Record<string, unknown>>(
    `select relationship_id::text, contact_display_hint, building_name, wing, unit_number,
            relationship_type, relationship_status
     from vw_contact_property_relationship_review
     order by building_name, relationship_type`);
  return rows.map((r) => ({
    relationshipId: String(r.relationship_id ?? ""),
    contactDisplayHint: String(r.contact_display_hint ?? ""),
    buildingName: String(r.building_name ?? ""),
    wing: r.wing ? String(r.wing) : null,
    unitNumber: r.unit_number ? String(r.unit_number) : null,
    relationshipType: String(r.relationship_type ?? ""),
    relationshipStatus: String(r.relationship_status ?? ""),
  }));
}
