/**
 * Cockpit data layer.
 *
 * Shaped to mirror the Postgres masked views (vw_dlf_operator_cockpit_home,
 * vw_*_review_queue, vw_ai_agent_task_dashboard, vw_owner_relationship_dashboard,
 * etc.). Today it returns seed data derived from the real portfolio so the shell
 * is clickable without DB credentials; each getter is a drop-in seam for a
 * read-only `pg` query against the corresponding view. READ-ONLY by design.
 */
import { projects as siteProjects, listings, type Listing } from "@/lib/site";
import { facts as dlfFacts, faqs as dlfFaqs } from "@/lib/content";
import type { Tone } from "@/components/ui/primitives";

export type Mode = "prospecting" | "active" | "launch" | "post_launch";

export interface Building {
  slug: string;
  name: string;
  location: string;
  mode: Mode;
  launchInDays?: number;
  stats: { owners: number; tenants: number; leads: number; warm: number; listings: number; openReviews: number; blockers: number };
  seoRank: string;
}

const META: Record<string, Omit<Building, "slug" | "name" | "location">> = {
  "dlf-westpark-andheri-west": { mode: "launch", launchInDays: 58, seoRank: "#12 ↑", stats: { owners: 0, tenants: 0, leads: 0, warm: 0, listings: 0, openReviews: 14, blockers: 3 } },
  "imperial-heights": { mode: "active", seoRank: "#3 ↑", stats: { owners: 9, tenants: 4, leads: 6, warm: 2, listings: 8, openReviews: 5, blockers: 0 } },
  "kalpataru-radiance": { mode: "active", seoRank: "#5 →", stats: { owners: 6, tenants: 2, leads: 3, warm: 1, listings: 5, openReviews: 2, blockers: 0 } },
  "ekta-tripolis": { mode: "active", seoRank: "#7 ↑", stats: { owners: 4, tenants: 3, leads: 2, warm: 0, listings: 3, openReviews: 1, blockers: 0 } },
  "bharat-auravistas": { mode: "prospecting", seoRank: "#21 ↑", stats: { owners: 2, tenants: 0, leads: 1, warm: 0, listings: 3, openReviews: 1, blockers: 1 } },
};

export function getBuildings(): Building[] {
  const dlf: Building = {
    slug: "dlf-westpark-andheri-west",
    name: "DLF Westpark",
    location: "Andheri West",
    ...META["dlf-westpark-andheri-west"],
  };
  const rest = siteProjects.map((p) => ({
    slug: p.slug,
    name: p.name,
    location: p.location,
    ...META[p.slug],
  }));
  return [dlf, ...rest];
}

export function getBuilding(slug: string): Building | undefined {
  return getBuildings().find((b) => b.slug === slug);
}

export const TAB_KEYS = [
  "overview", "owners", "leads", "listings", "seo", "campaigns", "rera", "website", "reviews", "agents",
] as const;
export type TabKey = (typeof TAB_KEYS)[number];

export const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: "overview", label: "Overview", icon: "ti-layout-dashboard" },
  { key: "owners", label: "Owners & tenants", icon: "ti-users" },
  { key: "leads", label: "Leads", icon: "ti-inbox" },
  { key: "listings", label: "Listings", icon: "ti-home" },
  { key: "seo", label: "SEO & content", icon: "ti-search" },
  { key: "campaigns", label: "Campaigns", icon: "ti-send" },
  { key: "rera", label: "RERA facts", icon: "ti-shield-check" },
  { key: "website", label: "Website pages", icon: "ti-world" },
  { key: "reviews", label: "Reviews", icon: "ti-checkbox" },
  { key: "agents", label: "Agents", icon: "ti-robot" },
];

// ---- portfolio-level ----
export interface ReviewItem { domain: string; title: string; building: string; age: string; tone: Tone }
export function getGlobalReviewQueue(): ReviewItem[] {
  return [
    { domain: "design", title: "DLF Gallery White — 14 refinement actions", building: "DLF Westpark", age: "2d", tone: "review" },
    { domain: "rera", title: "Verify carpet-area record vs MahaRERA", building: "DLF Westpark", age: "1d", tone: "review" },
    { domain: "content", title: "Blog draft: Andheri West connectivity", building: "DLF Westpark", age: "4h", tone: "review" },
    { domain: "contacts", title: "3 duplicate owner candidates", building: "Imperial Heights", age: "3d", tone: "review" },
    { domain: "seo", title: "5 new keyword targets proposed", building: "Imperial Heights", age: "6h", tone: "review" },
    { domain: "permissions", title: "9 WhatsApp permission rows need evidence", building: "DLF Westpark", age: "2d", tone: "blocked" },
  ];
}

export interface AgentEvent { agent: string; action: string; building: string; status: Tone }
export function getAgentActivity(): AgentEvent[] {
  return [
    { agent: "SEO monitor", action: "Captured SERP positions for 10 keywords", building: "Imperial Heights", status: "ready" },
    { agent: "Content drafter", action: "Drafted 'DLF debut in Mumbai' (pending review)", building: "DLF Westpark", status: "review" },
    { agent: "Data cleaner", action: "Proposed 3 owner dedupe merges", building: "Imperial Heights", status: "review" },
    { agent: "Campaign drafter", action: "Drafted 4 WhatsApp templates (consent-gated)", building: "DLF Westpark", status: "review" },
    { agent: "SEO monitor", action: "Rank for 'Andheri West luxury' rose to #12", building: "DLF Westpark", status: "ready" },
  ];
}

export interface Blocker { id: string; building: string; statement: string; openFor: string }
export function getGlobalBlockers(): Blocker[] {
  return [
    { id: "BLK-101", building: "DLF Westpark", statement: "RERA registration unverified — gates pricing publish", openFor: "2d 4h" },
    { id: "BLK-102", building: "DLF Westpark", statement: "WhatsApp template approval pending (provider)", openFor: "1d 9h" },
    { id: "BLK-103", building: "DLF Westpark", statement: "Official price not confirmed (PRICE_VERIFY)", openFor: "5d" },
  ];
}

// ---- workspace-level ----
export interface Person { name: string; role: "owner" | "tenant" | "client"; unit: string; phone: string }
export function getOwnersTenants(slug: string): Person[] {
  if (META[slug]?.stats.owners === 0) return [];
  return [
    { name: "Masked · owner A", role: "owner", unit: "Wing A-102", phone: "+91 •••• ••3889" },
    { name: "Masked · owner B", role: "owner", unit: "Wing A-203", phone: "+91 •••• ••1142" },
    { name: "Masked · tenant A", role: "tenant", unit: "Wing B-1104", phone: "+91 •••• ••7720" },
    { name: "Masked · client A", role: "client", unit: "—", phone: "+91 •••• ••3051" },
  ];
}

export function getListings(slug: string): Listing[] {
  const b = getBuilding(slug);
  if (!b) return [];
  return listings.filter((l) => l.project === b.name);
}

export interface Keyword { term: string; rank: string; volume: string; status: Tone }
export function getKeywords(slug: string): Keyword[] {
  const base = slug.includes("dlf")
    ? [["dlf westpark andheri west", "#12", "1.2k", "review"], ["dlf andheri new launch", "#9", "880", "review"], ["andheri west luxury flats", "#15", "2.4k", "ready"]]
    : [["imperial heights goregaon", "#3", "1.9k", "ready"], ["goregaon west 3 bhk", "#5", "3.1k", "ready"], ["imperial heights for sale", "#2", "720", "ready"]];
  return base.map(([term, rank, volume, status]) => ({ term, rank, volume, status: status as Tone }));
}

export interface Campaign { name: string; channel: string; status: Tone; note: string }
export function getCampaigns(slug: string): Campaign[] {
  if (slug.includes("dlf")) {
    return [
      { name: "Launch teaser — owners", channel: "WhatsApp", status: "blocked", note: "consent evidence pending" },
      { name: "Andheri West awareness", channel: "Email", status: "review", note: "draft ready for review" },
      { name: "Pre-launch interest list", channel: "Landing form", status: "ready", note: "preview-only form live" },
    ];
  }
  return [
    { name: "Resale interest — Goregaon", channel: "WhatsApp", status: "review", note: "draft, consent-gated" },
    { name: "Newsletter — new listings", channel: "Email", status: "ready", note: "send disabled (staging)" },
  ];
}

export interface Fact { label: string; value: string; status: Tone }
export function getReraFacts(slug: string): Fact[] {
  if (slug.includes("dlf")) {
    return dlfFacts.map((f) => ({
      label: f.label,
      value: f.value,
      status: f.status === "operator_confirmed" ? "ready" : f.status === "pending_review" ? "review" : "blocked",
    }));
  }
  return [
    { label: "RERA Registration", value: "Verified · P51800000000", status: "ready" },
    { label: "Carpet area records", value: "Matched to MahaRERA", status: "ready" },
    { label: "Possession", value: "Ready-to-move", status: "ready" },
  ];
}

export interface WebPage { path: string; title: string; status: Tone }
export function getWebsitePages(slug: string): WebPage[] {
  if (slug.includes("dlf")) {
    return [
      { path: "/dlf-westpark-andheri-west", title: "Landing page (Next.js)", status: "ready" },
      { path: "wix:Test/cms", title: "Wix Test CMS — 7 collections", status: "ready" },
      { path: "publish", title: "Production publish", status: "blocked" },
    ];
  }
  return [
    { path: `/projects/${slug}`, title: "Project page (Next.js)", status: "ready" },
    { path: "listings", title: "Listing detail pages", status: "review" },
  ];
}

export function getBuildingReviews(slug: string): ReviewItem[] {
  const b = getBuilding(slug);
  return getGlobalReviewQueue().filter((r) => b && r.building === b.name);
}

export interface AgentTask { agent: string; task: string; cadence: string; status: Tone }
export function getAgentTasks(slug: string): AgentTask[] {
  return [
    { agent: "SEO monitor", task: "Track SERP positions daily", cadence: "daily 06:00", status: "ready" },
    { agent: "Content drafter", task: "Draft 1 blog/landing per gap", cadence: "on gap found", status: "review" },
    { agent: "Data cleaner", task: "Dedupe + classify contacts", cadence: "nightly", status: "ready" },
    { agent: "Campaign drafter", task: "Draft compliant outreach", cadence: "weekly", status: "review" },
  ];
}

// ---- launch mode ----
export interface KanbanTask { title: string; col: "todo" | "doing" | "blocked" | "done"; stream: string }
export function getLaunchKanban(): KanbanTask[] {
  return [
    { title: "Confirm official project name", col: "done", stream: "identity" },
    { title: "Approve Gallery White design", col: "done", stream: "design" },
    { title: "Build staging landing page", col: "doing", stream: "website" },
    { title: "Verify RERA registration", col: "blocked", stream: "legal" },
    { title: "Confirm starting price", col: "blocked", stream: "legal" },
    { title: "WhatsApp template approval", col: "blocked", stream: "campaign" },
    { title: "Draft launch blog series", col: "doing", stream: "seo" },
    { title: "Segment owner/tenant audience", col: "todo", stream: "data" },
    { title: "Set up lead intake (preview)", col: "todo", stream: "leads" },
  ];
}

export interface CalendarItem { when: string; title: string; channel: string }
export function getLaunchCalendar(): CalendarItem[] {
  return [
    { when: "T-45d", title: "Publish first SEO blog", channel: "Website" },
    { when: "T-30d", title: "Owner teaser (after consent)", channel: "WhatsApp" },
    { when: "T-14d", title: "Andheri West awareness email", channel: "Email" },
    { when: "T-7d", title: "Open pre-launch interest list", channel: "Landing form" },
    { when: "T-0", title: "Launch — go-live gate", channel: "All" },
  ];
}
