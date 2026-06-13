/**
 * Cockpit data layer.
 *
 * When DATABASE_URL is set (web/.env.local), getters read the REAL local
 * Postgres (read-only, via db.ts) mapped to the masked views/tables. When it's
 * not set, they fall back to seed data so the shell still renders. READ-ONLY:
 * every query runs in a READ ONLY transaction — mutations stay with the guarded
 * apply/revert scripts.
 */
import { projects as siteProjects, listings as siteListings, type Listing } from "@/lib/site";
import { facts as dlfFacts } from "@/lib/content";
import type { Tone } from "@/components/ui/primitives";
import { isDbConfigured, readQuery } from "@/lib/db";
import type {
  Mode, Building, ReviewItem, AgentEvent, Blocker, Person, Keyword,
  Campaign, Fact, WebPage, AgentTask, KanbanTask, CalendarItem,
} from "./types";

export * from "./types";

const live = isDbConfigured;
const DLF_SLUG = "dlf-westpark-andheri-west";
const num = (v: unknown) => Number(v ?? 0) || 0;

function maskName(n: string) { const t = (n || "").trim().split(/\s+/); return t[0] ? `${t[0]} ••` : "Contact"; }
function maskPhone(p: string) { const d = String(p || "").replace(/\D/g, ""); return d ? `•••• ••${d.slice(-2)}` : "—"; }
function launchDays(month?: string | null, date?: string | null) {
  const now = new Date();
  let target: Date | null = date ? new Date(date) : null;
  if (!target && month) { const m = ["january","february","march","april","may","june","july","august","september","october","november","december"].indexOf(month.toLowerCase()); if (m >= 0) { target = new Date(now.getFullYear(), m, 1); if (target < now) target = new Date(now.getFullYear() + 1, m, 1); } }
  if (!target) return undefined;
  return Math.max(0, Math.round((target.getTime() - now.getTime()) / 86_400_000));
}

// ---------------- seed fallback ----------------
const SEED_BUILDINGS: Building[] = [
  { slug: DLF_SLUG, name: "DLF Westpark", location: "Andheri West", mode: "launch", launchInDays: 58, seoRank: "#12 ↑", stats: { owners: 0, tenants: 0, leads: 0, warm: 0, listings: 0, openReviews: 14, blockers: 3 } },
  ...siteProjects.map((p) => ({ slug: p.slug, name: p.name, location: p.location, mode: "active" as Mode, seoRank: "#5", stats: { owners: 6, tenants: 3, leads: 3, warm: 1, listings: 4, openReviews: 2, blockers: 0 } })),
];

// ---------------- buildings ----------------
export async function getBuildings(): Promise<Building[]> {
  if (!live()) return SEED_BUILDINGS;

  const lps = await readQuery<{ launch_key: string; project_display_name: string; area: string; expected_launch_month: string; expected_launch_date: string; seo_status: string; id: string }>(
    `select id::text, launch_key, project_display_name, area, expected_launch_month, expected_launch_date::text, seo_status from launch_projects`);
  const blds = await readQuery<{ name: string; locality: string }>(
    `select name, max(locality) locality from buildings group by name`);
  const rd = await readQuery<{ id: string; open: string; blockers: string }>(
    `select launch_project_id::text id, count(*) filter (where check_status in ('pending','needs_review','failed')) open, count(*) filter (where severity='blocker' and check_status <> 'passed') blockers from launch_readiness_checks group by launch_project_id`);
  const owners = num((await readQuery<{ n: string }>(`select count(*) n from contact_property_relationships where relationship_type='owner'`))[0]?.n);
  const reraOpen = num((await readQuery<{ n: string }>(`select count(*) n from rera_project_profiles where verification_status <> 'verified'`))[0]?.n);
  const kw = num((await readQuery<{ n: string }>(`select count(*) n from seo_keywords`))[0]?.n);

  const out: Building[] = [];
  for (const p of lps) {
    const r = rd.find((x) => x.id === p.id);
    out.push({
      slug: p.launch_key, name: p.project_display_name, location: p.area, mode: "launch",
      launchInDays: launchDays(p.expected_launch_month, p.expected_launch_date),
      seoRank: p.seo_status || "—",
      stats: { owners: 0, tenants: 0, leads: 0, warm: 0, listings: 0, openReviews: num(r?.open), blockers: num(r?.blockers) },
    });
  }
  for (const b of blds) {
    out.push({
      slug: b.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
      name: b.name, location: b.locality || "Mumbai", mode: "active", seoRank: `${kw} kw`,
      stats: { owners, tenants: 0, leads: 0, warm: 0, listings: 0, openReviews: reraOpen, blockers: 0 },
    });
  }
  return out;
}
export async function getBuilding(slug: string): Promise<Building | undefined> {
  return (await getBuildings()).find((b) => b.slug === slug);
}

// ---------------- portfolio panels ----------------
export async function getGlobalReviewQueue(): Promise<ReviewItem[]> {
  if (!live()) return [
    { domain: "design", title: "DLF Gallery White — 14 refinement actions", building: "DLF Westpark", age: "2d", tone: "review" },
    { domain: "contacts", title: "3 duplicate owner candidates", building: "Imperial Heights", age: "3d", tone: "review" },
  ];
  const out: ReviewItem[] = [];
  const rc = await readQuery<{ title: string; severity: string }>(
    `select coalesce(safe_summary, check_type) title, severity from launch_readiness_checks where check_status in ('needs_review','pending') and severity in ('blocker','high') order by severity limit 8`);
  for (const r of rc) out.push({ domain: "launch", title: r.title, building: "DLF Westpark", age: "open", tone: r.severity === "blocker" ? "blocked" : "review" });
  const rr = await readQuery<{ official_project_name: string }>(`select official_project_name from rera_project_profiles where verification_status <> 'verified'`);
  for (const r of rr) out.push({ domain: "rera", title: `Verify RERA — ${r.official_project_name}`, building: "Imperial Heights", age: "open", tone: "review" });
  return out;
}
export async function getAgentActivity(): Promise<AgentEvent[]> {
  if (!live()) return [{ agent: "SEO monitor", action: "Captured SERP positions", building: "Imperial Heights", status: "ready" }];
  return [{ agent: "runtime", action: "AI agent runtime not deployed yet — agents are planned, not running", building: "—", status: "neutral" }];
}
export async function getGlobalBlockers(): Promise<Blocker[]> {
  if (!live()) return [{ id: "BLK-101", building: "DLF Westpark", statement: "RERA registration unverified", openFor: "2d" }];
  const rows = await readQuery<{ check_type: string; safe_summary: string }>(
    `select check_type, coalesce(safe_summary, check_type) safe_summary from launch_readiness_checks where severity='blocker' and check_status <> 'passed' order by created_at limit 8`);
  return rows.map((r, i) => ({ id: `BLK-${String(i + 1).padStart(3, "0")}`, building: "DLF Westpark", statement: r.safe_summary, openFor: r.check_type }));
}

// ---------------- workspace panels ----------------
export async function getOwnersTenants(slug: string): Promise<Person[]> {
  if (!live()) return slug === DLF_SLUG ? [] : [{ name: "Masked · owner A", role: "owner", unit: "Wing A-102", phone: "+91 •••• ••3889" }];
  if (slug === DLF_SLUG) return [];
  const rows = await readQuery<{ full_name: string; relationship_type: string; phone_primary: string; building_unit_id: string | null }>(
    `select c.full_name, r.relationship_type, c.phone_primary, r.building_unit_id::text from contact_property_relationships r join contacts c on c.id = r.contact_id order by r.relationship_type`);
  return rows.map((r) => ({
    name: maskName(r.full_name),
    role: r.relationship_type === "owner" ? "owner" : r.relationship_type === "tenant" ? "tenant" : "client",
    unit: r.building_unit_id ? "unit linked" : "—",
    phone: maskPhone(r.phone_primary),
  }));
}
export async function getListings(slug: string): Promise<Listing[]> {
  if (!live()) { const b = SEED_BUILDINGS.find((x) => x.slug === slug); return b ? siteListings.filter((l) => l.project === b.name) : []; }
  return []; // no inventory imported into Postgres yet — honest empty state
}
export async function getKeywords(slug: string): Promise<Keyword[]> {
  if (!live()) return [{ term: "imperial heights goregaon", rank: "#3", volume: "1.9k", status: "ready" }];
  const rows = await readQuery<{ keyword: string; status: string; intent: string }>(
    `select keyword, status, intent from seo_keywords order by priority nulls last limit 30`);
  return rows.map((r) => ({ term: r.keyword, rank: "—", volume: r.intent || "—", status: r.status === "ranking" ? "ready" : "review" }));
}
export async function getCampaigns(slug: string): Promise<Campaign[]> {
  if (!live()) return [{ name: "Launch teaser", channel: "WhatsApp", status: "blocked", note: "consent pending" }];
  const rows = await readQuery<{ channel_type: string; channel_status: string }>(
    `select channel_type, channel_status from launch_channels order by channel_type limit 20`).catch(() => []);
  return rows.map((r) => ({ name: `${r.channel_type} channel`, channel: r.channel_type, status: "neutral", note: r.channel_status || "planned" }));
}
export async function getReraFacts(slug: string): Promise<Fact[]> {
  if (slug === DLF_SLUG) {
    return dlfFacts.map((f) => ({ label: f.label, value: f.value, status: f.status === "operator_confirmed" ? "ready" : f.status === "pending_review" ? "review" : "blocked" }));
  }
  if (!live()) return [{ label: "RERA Registration", value: "Verified", status: "ready" }];
  const rows = await readQuery<{ official_project_name: string; rera_registration_number: string; registration_status: string; verification_status: string; district: string; locality: string }>(
    `select official_project_name, rera_registration_number, registration_status, verification_status, district, locality from rera_project_profiles limit 1`);
  if (!rows.length) return [{ label: "RERA", value: "No profile captured yet", status: "review" }];
  const r = rows[0];
  const vtone: Tone = r.verification_status === "verified" ? "ready" : "review";
  return [
    { label: "Official project name", value: r.official_project_name || "—", status: vtone },
    { label: "RERA registration", value: r.rera_registration_number || "RERA_VERIFY", status: r.registration_status?.includes("registered") ? "ready" : "review" },
    { label: "Verification status", value: r.verification_status || "—", status: vtone },
    { label: "Location", value: [r.locality, r.district].filter(Boolean).join(", ") || "—", status: "review" },
  ];
}
export async function getWebsitePages(slug: string): Promise<WebPage[]> {
  if (slug === DLF_SLUG) return [
    { path: "/dlf-westpark-andheri-west", title: "Landing page (Next.js)", status: "ready" },
    { path: "wix:Test/cms", title: "Wix Test CMS — 7 collections", status: "ready" },
    { path: "publish", title: "Production publish", status: "blocked" },
  ];
  return [{ path: `/projects/${slug}`, title: "Project page (Next.js)", status: "ready" }];
}
export async function getBuildingReviews(slug: string): Promise<ReviewItem[]> {
  const b = await getBuilding(slug);
  if (!b) return [];
  return (await getGlobalReviewQueue()).filter((r) => r.building === b.name);
}
export async function getAgentTasks(slug: string): Promise<AgentTask[]> {
  const planned: AgentTask[] = [
    { agent: "SEO monitor", task: "Track SERP positions daily", cadence: "daily 06:00", status: "neutral" },
    { agent: "Content drafter", task: "Draft blog/landing per gap", cadence: "on gap", status: "neutral" },
    { agent: "Data cleaner", task: "Dedupe + classify contacts", cadence: "nightly", status: "neutral" },
    { agent: "Campaign drafter", task: "Draft compliant outreach", cadence: "weekly", status: "neutral" },
  ];
  return planned; // runtime not deployed yet — shown as planned
}

// ---------------- launch mode ----------------
export async function getLaunchKanban(slug: string): Promise<KanbanTask[]> {
  if (!live()) return [
    { title: "Confirm official project name", col: "done", stream: "identity" },
    { title: "Verify RERA registration", col: "blocked", stream: "legal" },
    { title: "Build staging landing page", col: "doing", stream: "website" },
    { title: "Segment owner/tenant audience", col: "todo", stream: "data" },
  ];
  const rows = await readQuery<{ task_type: string; task_status: string; safe_summary: string }>(
    `select t.task_type, t.task_status, coalesce(t.safe_summary, t.task_type) safe_summary
     from launch_operator_tasks t join launch_projects p on p.id = t.launch_project_id
     where p.launch_key = $1 order by t.created_at`, [slug]);
  const colOf = (s: string): KanbanTask["col"] => s === "done" ? "done" : s === "in_progress" ? "doing" : s === "blocked" ? "blocked" : "todo";
  return rows.map((r) => ({ title: r.safe_summary, col: colOf(r.task_status), stream: r.task_type?.split("_")[0] || "task" }));
}
export function getLaunchCalendar(): CalendarItem[] {
  return [
    { when: "T-45d", title: "Publish first SEO blog", channel: "Website" },
    { when: "T-30d", title: "Owner teaser (after consent)", channel: "WhatsApp" },
    { when: "T-14d", title: "Andheri West awareness email", channel: "Email" },
    { when: "T-7d", title: "Open pre-launch interest list", channel: "Landing form" },
    { when: "T-0", title: "Launch — go-live gate", channel: "All" },
  ];
}
