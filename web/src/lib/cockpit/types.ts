/**
 * Cockpit types + tab constants — client-safe (NO db/pg import).
 * Client components import from here; server data getters live in data.ts.
 */
import type { Tone } from "@/components/ui/primitives";
import type { Confidence } from "./units-clean";
import type { ProbableContact } from "./contact-match";
export type Mode = "prospecting" | "active" | "launch" | "post_launch";
export type { Confidence, ProbableContact };
export type { Listing } from "@/lib/site"; // re-export so cockpit components import all types from one barrel

export interface Building {
  slug: string; name: string; location: string; mode: Mode;
  launchInDays?: number; seoRank: string;
  stats: { owners: number; tenants: number; leads: number; warm: number; listings: number; openReviews: number; blockers: number };
}
export interface ReviewItem {
  domain: string; title: string; building: string; age: string; tone: Tone;
  /** UUID of the import_review_items row — present only for actionable items. */
  reviewItemId?: string;
}
export interface AgentEvent { agent: string; action: string; building: string; status: Tone }
export interface Blocker { id: string; building: string; statement: string; openFor: string }
export interface Person { contactId?: string; name: string; role: "owner" | "tenant" | "client"; unit: string; phone: string }
export interface Keyword { term: string; rank: string; volume: string; status: Tone }
export interface Campaign { name: string; channel: string; status: Tone; note: string }
export interface Fact { label: string; value: string; status: Tone }
export interface WebPage { path: string; title: string; status: Tone }
export interface AgentTask { agent: string; task: string; cadence: string; status: Tone }
export interface KanbanTask { title: string; col: "todo" | "doing" | "blocked" | "done"; stream: string }
export interface LaunchStream {
  label: string;
  tone: Tone;
  state: string;    // "Ready" | "Blocked" | "In review" | "No data"
  total: number;    // total checks classified to this stream
  passed: number;   // checks with check_status = 'passed'
  blockers: number; // active (non-passed) blocker checks
}
export interface CalendarItem { when: string; title: string; channel: string }

export interface RegParty {
  role: string; english: string; devanagari?: string;
  pan?: string; age?: number; address?: string; type?: string;
}
export interface UnitTimelineEvent {
  date: string; year: number;
  category: "ownership" | "tenancy" | "encumbrance" | "other";
  docType: string; docNumber: string; sro?: string;
  consideration?: number; marketValue?: number; stampDuty?: number; regFee?: number; area?: string;
  rent?: number; deposit?: number; tenancyStart?: string; tenancyEnd?: string; active?: boolean;
  parties: RegParty[];
}
export interface ZapkeyTxn {
  date: string;
  type: "sale" | "rent" | "mortgage" | "other";
}

export interface UnitCell {
  flat: string; floor: number; position: number; tower: string;
  status: "owned" | "tenanted" | "registered" | "unknown";
  currentOwner?: string; ownerSince?: string; lastPrice?: number; ownerContact?: boolean;
  /** Contact UUID when owner is a known canonical contact (no IGR reg yet). */
  ownerContactId?: string;
  currentTenant?: string; rent?: number; deposit?: number; tenancyStart?: string; tenancyEnd?: string;
  registrationCount: number;
  /**
   * Zapkey's third-party registration index: date + type only, no doc number, no parties,
   * no price. Shown separately from IGR events — it proves a transaction happened, nothing more.
   */
  zapkey: ZapkeyTxn[];
  /** True when floor came from the MyGate directory rather than being inferred from the flat number. */
  floorKnown: boolean;
  /** Lead resident shown on the grid tile: the owner if there is one, else the first tenant. */
  resident?: { name: string; role: "owner" | "tenant" };
  events: UnitTimelineEvent[];
  /** Probable phone/email for this flat: direct sheet lookup + name-matched parties (may be empty). */
  contactMatches: ProbableContact[];
}
export interface UnitTower { letter: string; label: string; floors: number; unitsPerFloor: number; unitCount: number; unplaced: number }
export interface ExpiringLease {
  wing: string; unit: string; daysRemaining: number;
  rent?: number; deposit?: number;
  tenancyStart?: string; tenancyEnd: string;
  tenantNames: string; ownerNames: string; tenantPans: string;
  docNumber: string; sro?: string;
  /** Devanagari truth + recovery grade so the operator can spot/fix bad placements. */
  confidence: Confidence; descriptionRaw?: string;
  /** Name-matched probable phone/email from contacts + imports (conservative, may be empty). */
  contactMatches: ProbableContact[];
}
/** A registration whose wing/flat couldn't be cleanly resolved — needs a human read. */
export interface UnitReviewItem {
  recordId: string; docNumber: string; docType: string; year: number; category: string;
  wingTextRaw?: string; unitTextRaw?: string; descriptionRaw?: string;
  recoveredWing: string; recoveredUnit: string; confidence: Confidence;
  parties: RegParty[];
}
export interface UnitRegistry {
  buildingName: string; towers: UnitTower[]; unitsPerFloor: number;
  units: UnitCell[];
  expiringLeases: ExpiringLease[];
  reviewQueue: UnitReviewItem[];
  stats: {
    expected: number; mappedUnits: number; withRegistration: number; owned: number; tenanted: number;
    registered: number; occupancyPct: number; avgRent: number;
    expiring6mo: number; expiring12mo: number; avgOwnershipYears: number;
    minPrice: number; maxPrice: number; panCount: number; registrations: number;
  };
}

export const TAB_KEYS = ["overview","owners","units","leads","listings","seo","campaigns","rera","website","reviews","agents"] as const;
export type TabKey = (typeof TAB_KEYS)[number];
export const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" }, { key: "owners", label: "Owners & tenants" },
  { key: "units", label: "Unit registry" },
  { key: "leads", label: "Leads" }, { key: "listings", label: "Listings" },
  { key: "seo", label: "SEO & content" }, { key: "campaigns", label: "Campaigns" },
  { key: "rera", label: "RERA facts" }, { key: "website", label: "Website pages" },
  { key: "reviews", label: "Reviews" }, { key: "agents", label: "Agents" },
];
