/**
 * Contact-cleanup types + pure helpers - client-safe (NO db/pg import).
 * Client components import from here; server-side getters live in contacts.ts
 * (which re-exports everything in this file).
 */
import type { Tone } from "@/components/ui/primitives";

/** Review-item / candidate status → design-system tone. */
export function statusTone(status: string): Tone {
  switch (status) {
    case "approved":
    case "merged":
    case "resolved":
      return "ready";
    case "rejected":
      return "blocked";
    case "needs_more_info":
    case "needs_review":
      return "review";
    case "pending":
    default:
      return "neutral";
  }
}

/** Duplicate strength → tone (strong dup = needs attention). */
export function strengthTone(strength: string): Tone {
  switch (strength) {
    case "strong":
      return "blocked";
    case "medium":
      return "review";
    default:
      return "neutral";
  }
}

export interface ReviewBatch {
  importBatchId: string;
  batchLabel: string;
  isRealImport: boolean;
  canonicalMergeDone: boolean;
  sourceFiles: number;
  importRows: number;
  contactMethods: number;
  duplicateCandidates: number;
  pending: number;
  approved: number;
  rejected: number;
  createdAt: string;
}

export interface ReviewQueueItem {
  reviewItemId: string;
  batchLabel: string;
  reviewType: string;
  priority: string;
  status: string;
  title: string;
  summary: string;
  recommendedAction: string;
  reviewedBy: string | null;
  createdAt: string;
}

export interface DuplicateCandidate {
  duplicateCandidateId: string;
  batchLabel: string;
  strength: string;
  candidateType: string;
  reason: string;
  status: string;
  leftHint: string;
  rightHint: string;
  maskedPhoneHint: string;
  maskedEmailHint: string;
}

export interface CanonicalContactRow {
  contactId: string;
  displayHint: string;
  canonicalStatus: string;
  isTest: boolean;
  methodCount: number;
  leadRequirementCount: number;
  sourceFileCount: number;
  mergeLabel: string | null;
  mergeStatus: string | null;
}

export interface ContactRelationshipRow {
  relationshipId: string;
  contactDisplayHint: string;
  buildingName: string;
  wing: string | null;
  unitNumber: string | null;
  relationshipType: string;
  relationshipStatus: string;
}

/** One row per (reviewType,status) for the queue summary grid. */
export interface QueueCount {
  reviewType: string;
  status: string;
  count: number;
}

export interface QueueFilter {
  batchLabel?: string;
  reviewType?: string;
  status?: string;
  realOnly?: boolean;
  limit?: number;
}

// ---- Pipeline Kanban ----
export type PipelineStage = "in_review" | "approved" | "canonical" | "attached";

export interface PipelineCard {
  key: string;
  primary: string;        // masked display hint / title
  secondary?: string;     // batch, source, or note
  role?: string;          // lead | owner | tenant | broker (attached stage)
  building?: string;      // building name (attached stage)
  tone: Tone;
}

export interface PipelineColumn {
  stage: PipelineStage;
  label: string;
  total: number;          // full count in this stage
  cards: PipelineCard[];  // capped sample
  tone: Tone;
}

export const PIPELINE_STAGE_META: Record<PipelineStage, { label: string; tone: Tone; hint: string }> = {
  in_review: { label: "In review", tone: "review", hint: "merge candidate, awaiting decision" },
  approved: { label: "Approved", tone: "active", hint: "ready to merge into a canonical contact" },
  canonical: { label: "Canonical", tone: "ready", hint: "cleaned contact, not yet attached" },
  attached: { label: "Attached", tone: "ready", hint: "linked to a building by role" },
};

/** Friendly label for a relationship role. */
export function roleLabel(role: string): string {
  const r = role.toLowerCase();
  if (r === "owner") return "owner";
  if (r === "tenant") return "tenant";
  if (r === "broker" || r === "agent") return "broker";
  if (r === "buyer" || r === "lead") return "lead";
  return r;
}

// ---- All-contacts sheet ----
export interface ContactSheetRow {
  contactId: string;
  displayHint: string;
  canonicalStatus: string;
  role: string | null;       // active relationship role, if any
  building: string | null;
  methodCount: number;
  leadRequirementCount: number;
  sourceFileCount: number;
  mergeLabel: string | null;
  createdAt: string;
}

/** Whitelisted sort keys → safe SQL columns (never interpolate raw input). */
export const SHEET_SORTS = {
  created: "c.created_at",
  contact: "c.display_hint",
  status: "c.canonical_status",
  methods: "c.method_count",
} as const;
export type SheetSortKey = keyof typeof SHEET_SORTS;

export interface ContactSheet {
  rows: ContactSheetRow[];
  total: number;
  page: number;
  pageSize: number;
  sort: SheetSortKey;
  dir: "asc" | "desc";
}
