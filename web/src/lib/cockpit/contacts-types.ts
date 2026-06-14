/**
 * Contact-cleanup types + pure helpers — client-safe (NO db/pg import).
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
