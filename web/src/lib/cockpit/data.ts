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
import { recoverWingUnit, joinPartyNames } from "./units-clean";
import { buildCandidate, findMatches, unitKey, toUnitContact, dedupeContacts, type Candidate, type ProbableContact } from "./contact-match";
import type {
  Mode, Building, ReviewItem, AgentEvent, Blocker, Person, Keyword,
  Campaign, Fact, WebPage, AgentTask, KanbanTask, CalendarItem, LaunchStream,
} from "./types";

export * from "./types";

const live = isDbConfigured;
const DLF_SLUG = "dlf-westpark-andheri-west";
const num = (v: unknown) => Number(v ?? 0) || 0;

function maskName(n: string) { const t = (n || "").trim().split(/\s+/); return t[0] ? `${t[0]} ••` : "Contact"; }
function maskPhone(p: string) { const d = String(p || "").replace(/\D/g, ""); return d ? `•••• ••${d.slice(-2)}` : "—"; }
function slugify(v: string) { return v.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }

export function agentLabel(taskType: string) {
  return (taskType || "unknown").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
export function buildingFromRaw(raw: Record<string, string> | null): string {
  if (!raw) return "—";
  if (raw.building_name) return String(raw.building_name);
  if (raw.launch_key) {
    return String(raw.launch_key).split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
  }
  return "—";
}
export function taskTone(status: string): Tone {
  if (status === "completed" || status === "done") return "ready";
  if (status === "running" || status === "in_progress") return "review";
  if (status === "failed" || status === "error") return "blocked";
  return "neutral"; // queued, pending
}
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

  const lps = await readQuery<{ launch_key: string; project_display_name: string; area: string; expected_launch_month: string; expected_launch_date: string; seo_status: string; id: string; mode: string }>(
    `select id::text, launch_key, project_display_name, area, expected_launch_month, expected_launch_date::text, seo_status, mode from launch_projects`);
  const blds = await readQuery<{ name: string; locality: string }>(
    `select name, max(locality) locality from buildings group by name`);
  const rd = await readQuery<{ id: string; open: string; blockers: string }>(
    `select launch_project_id::text id, count(*) filter (where check_status in ('pending','needs_review','failed')) open, count(*) filter (where severity='blocker' and check_status <> 'passed') blockers from launch_readiness_checks group by launch_project_id`);
  // Per-building owner/tenant counts via building_units join (avoids global cross-contamination)
  const ownerRows = await readQuery<{ name: string; owners: string; tenants: string }>(
    `select b.name,
            count(cpr.id) filter (where cpr.relationship_type='owner')  owners,
            count(cpr.id) filter (where cpr.relationship_type='tenant') tenants
       from buildings b
       left join building_units bu on bu.building_id = b.id
       left join contact_property_relationships cpr on cpr.building_unit_id = bu.id
      group by b.name`
  );
  // Per-building open RERA reviews (buildings.id → rera_project_profiles.building_id)
  const reraRows = await readQuery<{ name: string; rera_open: string }>(
    `select b.name, count(rp.id) filter (where rp.verification_status <> 'verified') rera_open
       from buildings b
       left join rera_project_profiles rp on rp.building_id = b.id
      group by b.name`
  );
  // Per-building inbound leads (buildings.id → inbound_leads.related_building_id)
  const leadsRows = await readQuery<{ name: string; leads: string; warm: string }>(
    `select b.name,
            count(il.id) filter (where il.lead_status <> 'spam')                                          leads,
            count(il.id) filter (where il.lead_status <> 'spam' and il.lead_intent in ('warm','hot','buy')) warm
       from buildings b
       left join inbound_leads il on il.related_building_id = b.id
      group by b.name`
  );
  const ownerMap = new Map(ownerRows.map((r) => [r.name, { owners: num(r.owners), tenants: num(r.tenants) }]));
  const reraMap  = new Map(reraRows.map((r) => [r.name, num(r.rera_open)]));
  const leadsMap = new Map(leadsRows.map((r) => [r.name, { leads: num(r.leads), warm: num(r.warm) }]));
  const kw = num((await readQuery<{ n: string }>(`select count(*) n from seo_keywords`))[0]?.n);

  const out: Building[] = [];
  for (const p of lps) {
    const r = rd.find((x) => x.id === p.id);
    out.push({
      slug: p.launch_key, name: p.project_display_name, location: p.area, mode: (p.mode as Mode) || "launch",
      launchInDays: launchDays(p.expected_launch_month, p.expected_launch_date),
      seoRank: p.seo_status || "—",
      stats: { owners: 0, tenants: 0, leads: 0, warm: 0, listings: 0, openReviews: num(r?.open), blockers: num(r?.blockers) },
    });
  }
  for (const b of blds) {
    const cnt = ownerMap.get(b.name) ?? { owners: 0, tenants: 0 };
    const rOpen = reraMap.get(b.name) ?? 0;
    const lc = leadsMap.get(b.name) ?? { leads: 0, warm: 0 };
    out.push({
      slug: slugify(b.name),
      name: b.name, location: b.locality || "Mumbai", mode: "active", seoRank: `${kw} kw`,
      stats: { owners: cnt.owners, tenants: cnt.tenants, leads: lc.leads, warm: lc.warm, listings: 0, openReviews: rOpen, blockers: 0 },
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
  const rows = await readQuery<{
    task_type: string; entity_type: string; status: string;
    prompt_summary: string; raw_input: Record<string, string>;
  }>(
    `select task_type, entity_type, status,
            coalesce(prompt_summary, task_type) as prompt_summary,
            raw_input
       from ai_agent_tasks
      order by updated_at desc
      limit 8`
  );
  if (!rows.length) return [{ agent: "runtime", action: "No agent tasks queued yet — runtime not deployed", building: "—", status: "neutral" }];
  return rows.map((r) => ({
    agent: agentLabel(r.task_type),
    action: r.prompt_summary || r.task_type,
    building: buildingFromRaw(r.raw_input),
    status: taskTone(r.status),
  }));
}
export async function getGlobalBlockers(): Promise<Blocker[]> {
  if (!live()) return [{ id: "BLK-101", building: "DLF Westpark", statement: "RERA registration unverified", openFor: "2d" }];
  const rows = await readQuery<{ check_type: string; safe_summary: string }>(
    `select check_type, coalesce(safe_summary, check_type) safe_summary from launch_readiness_checks where severity='blocker' and check_status <> 'passed' order by created_at limit 8`);
  return rows.map((r, i) => ({ id: `BLK-${String(i + 1).padStart(3, "0")}`, building: "DLF Westpark", statement: r.safe_summary, openFor: r.check_type }));
}

const STREAM_DEFS: { label: string; keywords: string[] }[] = [
  { label: "Tech (Wix / site)",  keywords: ["wix", "n8n", "webhook", "utm", "tracking", "lead_capture", "lead_scoring"] },
  { label: "Content & SEO",      keywords: ["seo", "social", "content", "email_template", "whatsapp_template"] },
  { label: "Campaign safety",    keywords: ["consent", "suppression", "attribution", "privacy", "spam"] },
  { label: "Legal / RERA",       keywords: ["rera", "project_name", "lead_duplicate"] },
];

function classifyCheckType(checkType: string): number {
  for (let i = 0; i < STREAM_DEFS.length; i++) {
    if (STREAM_DEFS[i].keywords.some((kw) => checkType.includes(kw))) return i;
  }
  return -1;
}

export function buildStreamStatus(
  rows: { check_type: string; check_status: string; severity: string }[]
): LaunchStream[] {
  const buckets = STREAM_DEFS.map((d) => ({ label: d.label, total: 0, passed: 0, blockers: 0 }));
  for (const row of rows) {
    const idx = classifyCheckType(row.check_type);
    if (idx < 0) continue;
    const b = buckets[idx];
    b.total++;
    if (row.check_status === "passed") b.passed++;
    else if (row.severity === "blocker") b.blockers++;
  }
  return buckets.map((b) => {
    let tone: import("@/components/ui/primitives").Tone;
    let state: string;
    if (b.total === 0)              { tone = "neutral"; state = "No data"; }
    else if (b.blockers > 0)        { tone = "blocked"; state = "Blocked"; }
    else if (b.passed < b.total)    { tone = "review";  state = "In review"; }
    else                            { tone = "ready";   state = "Ready"; }
    return { label: b.label, tone, state, total: b.total, passed: b.passed, blockers: b.blockers };
  });
}

export async function getStreamReadiness(): Promise<LaunchStream[]> {
  const fallback: { check_type: string; check_status: string; severity: string }[] = [
    { check_type: "wix_site_live",          check_status: "passed",       severity: "blocker" },
    { check_type: "seo_keywords_live",      check_status: "needs_review", severity: "high" },
    { check_type: "consent_reviewed",       check_status: "pending",      severity: "blocker" },
    { check_type: "rera_registration",      check_status: "pending",      severity: "blocker" },
  ];
  if (!live()) return buildStreamStatus(fallback);
  const rows = await readQuery<{ check_type: string; check_status: string; severity: string }>(
    `select check_type, check_status, severity from launch_readiness_checks order by created_at`
  );
  return buildStreamStatus(rows.length ? rows : fallback);
}

// ---------------- workspace panels ----------------
export async function getOwnersTenants(slug: string): Promise<Person[]> {
  if (!live()) return slug === DLF_SLUG ? [] : [{ name: "Masked · owner A", role: "owner", unit: "Wing A-102", phone: "+91 •••• ••3889" }];
  if (slug === DLF_SLUG) return [];
  const rows = await readQuery<{
    contact_id: string;
    full_name: string;
    relationship_type: string;
    phone_primary: string;
    building_unit_id: string | null;
    building_name: string | null;
    wing: string | null;
    unit_number: string | null;
  }>(
    `select c.id::text contact_id, c.full_name, r.relationship_type, c.phone_primary,
            r.building_unit_id::text, coalesce(b.name, bu.building_name) building_name,
            bu.wing, bu.unit_number
     from contact_property_relationships r
     join contacts c on c.id = r.contact_id
     left join buildings b on b.id = r.building_id
     left join building_units bu on bu.id = r.building_unit_id
     where r.relationship_status in ('active', 'approved', 'pending_review')
     order by r.relationship_type`);
  return rows.filter((r) => slugify(String(r.building_name ?? "")) === slug).map((r) => ({
    contactId: r.contact_id,
    name: maskName(r.full_name),
    role: r.relationship_type === "owner" ? "owner" : r.relationship_type === "tenant" ? "tenant" : "client",
    unit: [r.wing ? `Wing ${r.wing}` : "", r.unit_number ? `Unit ${r.unit_number}` : ""].filter(Boolean).join(" · ") || (r.building_unit_id ? "unit linked" : "—"),
    phone: maskPhone(r.phone_primary),
  }));
}
export async function getListings(slug: string): Promise<Listing[]> {
  if (!live()) { const b = SEED_BUILDINGS.find((x) => x.slug === slug); return b ? siteListings.filter((l) => l.project === b.name) : []; }
  return []; // no inventory imported into Postgres yet — honest empty state
}
export async function getKeywords(slug: string): Promise<Keyword[]> {
  if (!live()) return [{ term: "imperial heights goregaon", rank: "#3", volume: "1.9k", status: "ready" }];
  // slugify(b.name) must match the JS slugify() fn: lowercase, non-alnum → hyphen, trim hyphens
  const rows = await readQuery<{ keyword: string; status: string; intent: string }>(
    `select k.keyword, k.status, k.intent
       from seo_keywords k
       join buildings b on b.id = k.building_id
      where lower(regexp_replace(b.name, '[^a-z0-9]+', '-', 'gi')) = $1
      order by k.priority nulls last limit 30`,
    [slug]
  );
  return rows.map((r) => ({ term: r.keyword, rank: "—", volume: r.intent || "—", status: r.status === "ranking" ? "ready" : "review" }));
}
function channelTone(status: string): Tone {
  if (status === "live" || status === "active") return "ready";
  if (status === "under_review" || status === "needs_review") return "review";
  if (status === "blocked" || status === "disabled") return "blocked";
  return "neutral";
}
export async function getCampaigns(slug: string): Promise<Campaign[]> {
  if (!live()) return [{ name: "Launch teaser", channel: "WhatsApp", status: "blocked", note: "consent pending" }];
  const rows = await readQuery<{ channel: string; channel_status: string; send_enabled: boolean }>(
    `select lc.channel, lc.channel_status, lc.send_enabled
       from launch_channels lc
       join launch_projects lp on lp.id = lc.launch_project_id
      where lp.launch_key = $1
      order by lc.channel limit 20`,
    [slug]
  );
  if (!rows.length) return [];
  return rows.map((r) => ({
    name: (r.channel || "—").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    channel: r.channel || "—",
    status: channelTone(r.channel_status),
    note: r.send_enabled ? "send enabled" : r.channel_status || "planned",
  }));
}
export async function getReraFacts(slug: string): Promise<Fact[]> {
  if (slug === DLF_SLUG) {
    return dlfFacts.map((f) => ({ label: f.label, value: f.value, status: f.status === "operator_confirmed" ? "ready" : f.status === "pending_review" ? "review" : "blocked" }));
  }
  if (!live()) return [{ label: "RERA Registration", value: "Verified", status: "ready" }];
  // Match building slug exactly OR as a hyphen-prefix variant (e.g. kalpataru-radiance-a).
  // slugify(b.name) = lower(regexp_replace(b.name, '[^a-z0-9]+', '-', 'gi'))
  const rows = await readQuery<{ official_project_name: string; rera_registration_number: string; registration_status: string; verification_status: string; district: string; locality: string }>(
    `select rp.official_project_name, rp.rera_registration_number, rp.registration_status,
            rp.verification_status, rp.district, rp.locality
       from rera_project_profiles rp
       join buildings b on b.id = rp.building_id
      where lower(regexp_replace(b.name, '[^a-z0-9]+', '-', 'gi')) = $1
         or lower(regexp_replace(b.name, '[^a-z0-9]+', '-', 'gi')) like $1 || '-%'
      order by rp.created_at
      limit 5`,
    [slug]
  );
  if (!rows.length) return [{ label: "RERA", value: "No profile captured yet", status: "review" }];
  const facts: Fact[] = [];
  for (const r of rows) {
    const vtone: Tone = r.verification_status === "verified" ? "ready" : "review";
    facts.push(
      { label: "Official project name", value: r.official_project_name || "—", status: vtone },
      { label: "RERA registration", value: r.rera_registration_number || "RERA_VERIFY", status: r.registration_status?.includes("registered") ? "ready" : "review" },
      { label: "Verification status", value: r.verification_status || "—", status: vtone },
      { label: "Location", value: [r.locality, r.district].filter(Boolean).join(", ") || "—", status: "review" },
    );
  }
  return facts;
}
function stagingTone(status: string): Tone {
  if (status === "created_manually" || status === "live") return "ready";
  if (status === "under_review" || status === "qa_in_progress") return "review";
  if (status === "blocked" || status === "failed") return "blocked";
  return "neutral"; // planned, pending
}
export async function getWebsitePages(slug: string): Promise<WebPage[]> {
  const landingPath = slug === DLF_SLUG ? `/dlf-westpark-andheri-west` : `/projects/${slug}`;
  const pages: WebPage[] = [
    { path: landingPath, title: "Landing page (Next.js)", status: "ready" },
  ];
  if (!live()) {
    if (slug === DLF_SLUG) {
      pages.push({ path: "wix:Test/cms", title: "Wix Test CMS — 7 collections", status: "ready" });
      pages.push({ path: "publish", title: "Production publish", status: "blocked" });
    }
    return pages;
  }
  const sites = await readQuery<{ staging_site_name: string; staging_site_url: string; staging_status: string; page_published: boolean }>(
    `select ws.staging_site_name, ws.staging_site_url, ws.staging_status, ws.page_published
       from wix_staging_sites ws
       join launch_projects lp on lp.id = ws.launch_project_id
      where lp.launch_key = $1
      order by ws.created_at desc
      limit 5`,
    [slug]
  );
  for (const s of sites) {
    pages.push({
      path: s.staging_site_url || "wix:staging",
      title: s.staging_site_name ? `Wix staging — ${s.staging_site_name}` : "Wix staging site",
      status: stagingTone(s.staging_status),
    });
  }
  const cms = await readQuery<{ collection_key: string; collection_name: string; status: string }>(
    `select collection_key, coalesce(collection_name, collection_key) collection_name, status
       from wix_cms_collections order by created_at limit 10`
  );
  for (const c of cms) {
    pages.push({
      path: `cms:${c.collection_key}`,
      title: `CMS: ${c.collection_name}`,
      status: c.status === "live" ? "ready" : c.status === "planned" ? "neutral" : "review",
    });
  }
  pages.push({ path: "publish", title: "Production publish", status: "blocked" });
  return pages;
}
function formatAge(ts: string | null | undefined): string {
  if (!ts) return "open";
  const ms = Date.now() - new Date(ts).getTime();
  const d = Math.floor(ms / 86_400_000);
  return d === 0 ? "today" : `${d}d`;
}

export async function getBuildingReviews(slug: string): Promise<ReviewItem[]> {
  const b = await getBuilding(slug);
  if (!b) return [];
  // derived: launch_readiness_checks / rera_profiles filtered by building name (see getGlobalReviewQueue)
  // import_review_items excluded: contact-pipeline rows have no building_id link and would
  // flood every building's Reviews tab with 4000+ unrelated inventory/duplicate review items.
  return (await getGlobalReviewQueue()).filter((r) => r.building === b.name);
}
export async function getAgentTasks(slug: string): Promise<AgentTask[]> {
  const fallback: AgentTask[] = [
    { agent: "SEO monitor", task: "Track SERP positions daily", cadence: "daily 06:00", status: "neutral" },
    { agent: "Content drafter", task: "Draft blog/landing per gap", cadence: "on gap", status: "neutral" },
    { agent: "Data cleaner", task: "Dedupe + classify contacts", cadence: "nightly", status: "neutral" },
    { agent: "Campaign drafter", task: "Draft compliant outreach", cadence: "weekly", status: "neutral" },
  ];
  if (!live()) return fallback;
  const rows = await readQuery<{
    task_type: string; status: string; prompt_summary: string; raw_input: Record<string, string>;
  }>(
    `select task_type, status, coalesce(prompt_summary, task_type) prompt_summary, raw_input
       from ai_agent_tasks
      order by created_at desc
      limit 20`
  );
  const matched = rows.filter((r) => {
    const ri = (r.raw_input as Record<string, string>) || {};
    return ri.launch_key === slug || (ri.building_name ? slugify(ri.building_name) === slug : false);
  });
  if (!matched.length) return fallback;
  return matched.map((r) => ({
    agent: agentLabel(r.task_type),
    task: r.prompt_summary || r.task_type,
    cadence: r.status,
    status: taskTone(r.status),
  }));
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
export async function getLaunchCalendar(slug?: string): Promise<CalendarItem[]> {
  const staticCalendar: CalendarItem[] = [
    { when: "T-45d", title: "Publish first SEO blog", channel: "Website" },
    { when: "T-30d", title: "Owner teaser (after consent)", channel: "WhatsApp" },
    { when: "T-14d", title: "Andheri West awareness email", channel: "Email" },
    { when: "T-7d", title: "Open pre-launch interest list", channel: "Landing form" },
    { when: "T-0", title: "Launch — go-live gate", channel: "All" },
  ];
  if (!live()) return staticCalendar;
  let rows: { planned_date: string; channel: string; title: string; status: string }[];
  if (slug) {
    rows = await readQuery<{ planned_date: string; channel: string; title: string; status: string }>(
      `select lcc.planned_date::text, lcc.channel, lcc.title, lcc.status
         from launch_campaign_calendar lcc
         join launch_projects lp on lp.id = lcc.launch_project_id
        where lp.launch_key = $1
        order by lcc.planned_date limit 30`,
      [slug]
    );
  } else {
    rows = await readQuery<{ planned_date: string; channel: string; title: string; status: string }>(
      `select planned_date::text, channel, title, status
         from launch_campaign_calendar
        order by planned_date limit 30`
    );
  }
  if (!rows.length) return staticCalendar;
  const now = Date.now();
  return rows.map((r) => {
    const dt = r.planned_date ? new Date(r.planned_date).getTime() : now;
    const diffDays = Math.round((dt - now) / 86_400_000);
    const when = diffDays === 0 ? "T-0" : diffDays > 0 ? `T-${diffDays}d` : `T+${Math.abs(diffDays)}d`;
    return { when, title: r.title || r.channel, channel: r.channel || "—" };
  });
}

// ---------------- unit registry (per-building, per-tower apartment stack) ----------------
type URegistry = import("./types").UnitRegistry;
type UCell = import("./types").UnitCell;
type ZapkeyTxn = import("./types").ZapkeyTxn;
type UEvent = import("./types").UnitTimelineEvent;
type RParty = import("./types").RegParty;
type UReview = import("./types").UnitReviewItem;

const ZERO_STATS: URegistry["stats"] = {
  expected: 0, mappedUnits: 0, withRegistration: 0, owned: 0, tenanted: 0, registered: 0,
  occupancyPct: 0, avgRent: 0, expiring6mo: 0, expiring12mo: 0, avgOwnershipYears: 0,
  minPrice: 0, maxPrice: 0, panCount: 0, registrations: 0,
};
function towerLetter(wing: string | null): string {
  const m = String(wing ?? "").toUpperCase().match(/([A-Z])\s*$/);
  return m ? m[1] : "";
}
const MAX_FLOOR = 55; // IH goes to 51F, Kalpataru ~38 sanctioned; cap guards bad parses
// Flat-number scheme (per brochure / IGR variants): compact parser rows use
// floor+stack for 1-31 (`291` -> floor 29, unit 1), while older raw imports can
// use zero-padded unit suffixes (`2706` -> floor 27, unit 6; `803` -> floor 8, unit 3).
// Prefer the floor stored on building_units over guessing from the flat number. The two
// buildings number flats differently, and the stored floor makes the scheme decidable:
//
//   Kalpataru Radiance   flat = floor*10  + position   (floor 1 flat 1 = 11,  floor 30 = 301)
//   Imperial Heights     flat = floor*100 + position   (floor 1 flat 1 = 101, floor 10 = 1001)
//
// Try both bases. They can never both be valid: the candidates differ by 90*floor, so for
// any floor >= 1 at most one lands in 1..12. Without this, deriveFloorPos misreads Kalpataru's
// "301" as floor 3 / unit 01, collides it with flat 31, and the 30th floor renders empty.
function floorPos(unitNumber: string, dbFloor: string | null): { floor: number; pos: number; known: boolean } {
  const fl = Number(dbFloor);
  if (dbFloor && Number.isInteger(fl) && fl >= 1 && fl <= MAX_FLOOR) {
    const n = Number(String(unitNumber).replace(/\D/g, "")) || 0;
    for (const base of [10, 100]) {
      const pos = n - fl * base;
      if (pos >= 1 && pos <= 12) return { floor: fl, pos, known: true };
    }
  }
  return { ...deriveFloorPos(unitNumber), known: false };
}

function deriveFloorPos(u: string): { floor: number; pos: number } {
  const n = Number(String(u).replace(/\D/g, "")) || 0;
  const raw = String(u).replace(/\D/g, "");
  if (raw.length === 3) {
    const fa3 = Math.floor(n / 100), pa3 = n % 100;  // standard: 501 -> floor 5 / unit 01
    if (fa3 >= 1 && fa3 <= 9 && pa3 >= 1 && pa3 <= 12) return { floor: fa3, pos: pa3 };
    const fc = Math.floor(n / 10), pc = n % 10;       // compact: 291 -> floor 29 / unit 1
    if (fc >= 10 && fc <= MAX_FLOOR && pc >= 1 && pc <= 9) return { floor: fc, pos: pc };
  }
  const fa = Math.floor(n / 100), pa = n % 100;       // last two digits = unit (e.g. 2706 -> 27/06)
  if (fa >= 1 && fa <= MAX_FLOOR && pa >= 1 && pa <= 12) return { floor: fa, pos: pa };
  const fb = Math.floor(n / 10), pb = n % 10;          // last digit = unit (e.g. 291 -> 29/1)
  if (fb >= 1 && fb <= MAX_FLOOR) return { floor: fb, pos: pb || 10 };
  return { floor: Math.min(Math.max(1, n), MAX_FLOOR), pos: 1 };
}

// Import sheets store the building only in the filename. ponytail: a 5-entry lookup beats a
// fuzzy filename matcher ("Kalptaru" vs "Kalpataru"); add a line when a new sheet is imported.
const SOURCE_FILE_BUILDING: Record<string, string> = {
  "Kalptaru Radiance new.xlsx": "Kalpataru Radiance",
  "Imperial Heights unit data.xlsx": "Imperial Heights",
  "Oberoi esquire units.xlsx": "Oberoi Esquire",
  "Ekta Tripolis Data new.xlsx": "Ekta Tripolis",
  "Windsor Grande Residences Condominium - Member Details (1).xlsx": "Windsor Grande Residences",
};

// Contacts + raw import rows, with phone/email resolved, as name-match candidates.
// Phone lives in contact_methods (contacts.phone_primary is empty), so we pull the best mobile there.
async function getContactIndex(): Promise<Candidate[]> {
  const contacts = await readQuery<{ id: string; full_name: string; email: string | null; phone: string | null }>(
    `select c.id::text id, c.full_name,
            coalesce(nullif(c.email,''),
              (select m.normalized_value from contact_methods m
                where m.contact_id=c.id and m.method_type='email' and m.normalized_value is not null limit 1)) email,
            (select m.normalized_value from contact_methods m
               where m.contact_id=c.id and m.method_type in ('mobile','phone') and m.normalized_value is not null
               order by (m.method_type='mobile') desc limit 1) phone
       from contacts c`);
  const imports = await readQuery<{ name: string; phone: string | null; email: string | null; contact_id: string | null; wing: string | null; unit: string | null; building: string | null; source_file: string | null }>(
    `select coalesce(cleaned_display_name, raw_name) name, phone_normalized phone, email_normalized email,
            matched_contact_id::text contact_id, parsed_wing wing, parsed_unit_number unit,
            parsed_building_name building, source_file
       from contact_import_rows
      where coalesce(cleaned_display_name, raw_name) is not null
        and (phone_normalized is not null or email_normalized is not null)`);
  const out: Candidate[] = [];
  for (const c of contacts) out.push(buildCandidate({ name: c.full_name, source: "contact", phone: c.phone ?? undefined, email: c.email ?? undefined, contactId: c.id }));
  for (const r of imports) {
    // The import sheets (Kalpataru/Oberoi/…) carry no building tag — derive it from source_file so
    // unit matches stay within-building. wing parses to a single letter for exact compare.
    // parsed_building_name is often "" (not NULL), so use || not ?? to fall through to the filename map.
    const building = (r.building && r.building.trim()) || (r.source_file ? SOURCE_FILE_BUILDING[r.source_file] : undefined);
    out.push(buildCandidate({
      name: r.name, source: "import", phone: r.phone ?? undefined, email: r.email ?? undefined,
      contactId: r.contact_id ?? undefined, building: building ?? undefined,
      wing: r.wing ? recoverWingUnit({ wingText: r.wing }).wing || undefined : undefined,
      unit: r.unit ?? undefined,
    }));
  }
  return out;
}

export async function getUnitRegistry(slug: string): Promise<URegistry | null> {
  const b = (await getBuildings()).find((x) => x.slug === slug);
  const empty = (name: string): URegistry => ({ buildingName: name, towers: [], unitsPerFloor: 6, units: [], expiringLeases: [], reviewQueue: [], stats: ZERO_STATS });
  if (!b) return null;
  if (!live()) return empty(b.name);

  const recs = await readQuery<{
    record_id: string; building_name: string; building_unit_id: string | null; wing: string | null; unit_number: string | null;
    wing_text: string | null; unit_text: string | null; property_description_raw: string | null;
    registration_date: string | null; registration_year: number | null; document_type: string | null;
    category: string | null; doc_number: string | null; sro_office: string | null;
    consideration_amount: string | null; market_value: string | null; stamp_duty: string | null;
    registration_fee: string | null; area_text: string | null; tenancy_start_date: string | null;
    tenancy_end_date: string | null; tenancy_monthly_rent: string | null; tenancy_deposit: string | null;
    parties: RParty[] | null;
  }>(
    `select record_id::text, building_name, building_unit_id::text, wing, unit_number,
            wing_text, unit_text, property_description_raw, registration_date::text, registration_year,
            document_type, category, doc_number, sro_office, consideration_amount::text, market_value::text,
            stamp_duty::text, registration_fee::text, area_text, tenancy_start_date::text, tenancy_end_date::text,
            tenancy_monthly_rent::text, tenancy_deposit::text, parties
       from vw_unit_registration_full_operator order by registration_date`);
  const myRecs = recs.filter((r) => slugify(String(r.building_name ?? "")) === slug);
  // Recover wing+flat once per record from the raw register text / Marathi description.
  const recovery = new Map<string, ReturnType<typeof recoverWingUnit>>();
  for (const r of myRecs) recovery.set(r.record_id, recoverWingUnit({
    unitWing: r.wing, unitNumber: r.unit_number, wingText: r.wing_text, unitText: r.unit_text, descriptionRaw: r.property_description_raw,
  }));

  // Order by record count DESC so the dedup below keeps the unit that has records.
  const bunits = await readQuery<{ id: string; wing: string | null; unit_number: string | null; floor: string | null; bn: string }>(
    `select bu.id::text, bu.wing, bu.unit_number, bu.floor, b.name bn,
            count(r.id) recs
       from building_units bu
       join buildings b on b.id = bu.building_id
       left join unit_registration_records r on r.building_unit_id = bu.id
      where bu.canonical_status = 'active'
        and (bu.metadata->>'offgrid') is distinct from 'true'
      group by bu.id, bu.wing, bu.unit_number, bu.floor, b.name
      order by recs desc`);
  // Deduplicate: IGR ingest creates a building_unit per record, so the same flat can appear
  // twice. Keep the first encountered per wing+unit_number key (DB order = creation order).
  const _seenUnit = new Set<string>();
  const myUnits = bunits.filter((u) => {
    if (!u.unit_number || slugify(u.bn) !== slug) return false;
    const k = `${towerLetter(u.wing)}|${u.unit_number}`;
    if (_seenUnit.has(k)) return false;
    _seenUnit.add(k);
    return true;
  });

  const orel = await readQuery<{ building_unit_id: string | null; full_name: string; contact_id: string }>(
    `select r.building_unit_id::text, c.full_name, c.id::text contact_id
       from contact_property_relationships r
       join contacts c on c.id = r.contact_id
      where r.relationship_type = 'owner' and r.building_unit_id is not null
        and r.relationship_status in ('active','approved','pending_review')`);
  const ownerByUnit = new Map<string, { name: string; contactId: string }>();
  for (const r of orel) if (r.building_unit_id) ownerByUnit.set(r.building_unit_id, { name: r.full_name, contactId: r.contact_id });

  // IGR-parsed owner→canonical contact matches (first match per unit wins).
  const igrPartyMatches = await readQuery<{ building_unit_id: string; contact_id: string }>(
    `select building_unit_id::text, contact_id::text
       from registration_party_contact_matches
      where match_status = 'matched' and building_unit_id is not null
      order by created_at`);
  const igrContactByUnit = new Map<string, string>();
  for (const m of igrPartyMatches) {
    if (!igrContactByUnit.has(m.building_unit_id)) igrContactByUnit.set(m.building_unit_id, m.contact_id);
  }

  // Current residents from MyGate (owner/tenant + family), keyed by building_unit_id.
  // These are directly unit-linked (not name-guessed), so they render as strong matches
  // with phone + WhatsApp actions. building_unit_id is globally unique, so no per-building filter needed.
  const mgRel = await readQuery<{ unit_id: string; wing: string | null; unit_number: string | null; role: string; mrole: string; name: string; phone: string | null; contact_id: string }>(
    `select r.building_unit_id::text unit_id, bu.wing, bu.unit_number, r.relationship_type role,
            coalesce(r.raw_context->>'mygate_role', r.relationship_type) mrole,
            c.full_name name, coalesce(c.whatsapp_number, c.phone_primary) phone, c.id::text contact_id
       from contact_property_relationships r
       join contacts c on c.id = r.contact_id
       join building_units bu on bu.id = r.building_unit_id
       join buildings bg on bg.id = bu.building_id
      where c.metadata->>'mygate_unit' is not null and r.building_unit_id is not null
        and bg.name = $1
      order by (r.relationship_type='owner') desc, c.full_name`, [b.name]);
  const mygateByUnit = new Map<string, ProbableContact[]>();     // keyed by building_unit_id
  const mygateByWingUnit = new Map<string, ProbableContact[]>(); // keyed by "wing|unit_number"
  for (const m of mgRel) {
    const pc: ProbableContact = {
      name: /_family$/.test(m.mrole) ? `${m.name} · family` : m.name,
      role: m.role === "owner" ? "owner" : "tenant",
      confidence: "strong", source: "contact",
      phone: m.phone ?? undefined, contactId: m.contact_id, unitMatch: true,
    };
    (mygateByUnit.get(m.unit_id) ?? mygateByUnit.set(m.unit_id, []).get(m.unit_id)!).push(pc);
    const wk = `${m.wing ?? ""}|${m.unit_number ?? ""}`;
    (mygateByWingUnit.get(wk) ?? mygateByWingUnit.set(wk, []).get(wk)!).push(pc);
  }

  // Zapkey's transaction index: date + type per flat, no doc number / parties / price. Kept in
  // its own table for that reason, and rendered apart from IGR events so the two are never
  // mistaken for each other. Only rows Zapkey resolved to a unit are shown.
  const zapRows = await readQuery<{ unit_id: string; d: string | null; t: string | null }>(
    `select z.building_unit_id::text unit_id, z.registration_date::text d, z.transaction_type t
       from zapkey_transactions z
       join building_units bu on bu.id = z.building_unit_id
       join buildings bg on bg.id = bu.building_id
      where bg.name = $1
      order by z.registration_date desc nulls last`, [b.name]);
  const zapByUnit = new Map<string, ZapkeyTxn[]>();
  for (const z of zapRows) {
    if (!z.unit_id) continue;
    const t = (["sale", "rent", "mortgage"].includes(z.t ?? "") ? z.t : "other") as ZapkeyTxn["type"];
    (zapByUnit.get(z.unit_id) ?? zapByUnit.set(z.unit_id, []).get(z.unit_id)!).push({ date: z.d ?? "", type: t });
  }

  // group registration events by unit key (tower + flat) — handles linked and unlinked records.
  const toEvent = (r: typeof myRecs[number]): UEvent => ({
    date: r.registration_date ?? "", year: r.registration_year ?? (r.registration_date ? Number(r.registration_date.slice(0, 4)) : 0),
    category: (r.category as UEvent["category"]) ?? "other", docType: r.document_type ?? "—", docNumber: r.doc_number ?? "—",
    sro: r.sro_office ?? undefined,
    consideration: r.consideration_amount ? num(r.consideration_amount) : undefined,
    marketValue: r.market_value ? num(r.market_value) : undefined,
    stampDuty: r.stamp_duty ? num(r.stamp_duty) : undefined,
    regFee: r.registration_fee ? num(r.registration_fee) : undefined,
    area: r.area_text ?? undefined,
    rent: r.tenancy_monthly_rent ? num(r.tenancy_monthly_rent) : undefined,
    deposit: r.tenancy_deposit ? num(r.tenancy_deposit) : undefined,
    tenancyStart: r.tenancy_start_date ?? undefined, tenancyEnd: r.tenancy_end_date ?? undefined,
    active: r.category === "tenancy" ? !r.tenancy_end_date || new Date(r.tenancy_end_date).getTime() >= Date.now() : undefined,
    parties: (r.parties ?? []).map((p) => ({
      role: p.role, english: p.english || p.devanagari || "—", devanagari: p.devanagari ?? undefined,
      pan: p.pan ?? undefined, age: p.age ?? undefined, address: p.address ?? undefined, type: p.type ?? undefined,
    })),
  });
  const evByKey = new Map<string, UEvent[]>();
  for (const r of myRecs) {
    const rec = recovery.get(r.record_id)!;
    const key = `${rec.wing}|${rec.unit}`;
    (evByKey.get(key) ?? evByKey.set(key, []).get(key)!).push(toEvent(r));
  }

  const now = Date.now();
  const yrs = (d?: string) => (d ? Math.max(0, (now - new Date(d).getTime()) / 31_557_600_000) : 0);
  const partyNames = (ev: UEvent, roles: string[]) => joinPartyNames(ev.parties, roles);

  const units: UCell[] = [];
  for (const u of myUnits) {
    const tower = towerLetter(u.wing);
    const flat = String(u.unit_number);
    const key = `${tower}|${flat.replace(/\D/g, "")}`;
    const events = (evByKey.get(key) ?? []).slice().sort((a, z) => a.date.localeCompare(z.date));
    const ownership = events.filter((e) => e.category === "ownership");
    const tenancy = events.filter((e) => e.category === "tenancy");
    const activeLease = tenancy.filter((e) => e.active).slice(-1)[0];
    const lastOwn = ownership.slice(-1)[0];
    const relOwner = ownerByUnit.get(u.id);
    const igrContactId = igrContactByUnit.get(u.id);
    const currentOwner = lastOwn ? partyNames(lastOwn, ["purchaser", "buyer"]) || undefined : relOwner?.name ?? undefined;
    const status: UCell["status"] = activeLease ? "tenanted"
      : currentOwner ? "owned"
      : events.length ? "registered" : "unknown";
    const resolvedContactId = relOwner?.contactId ?? (lastOwn && igrContactId ? igrContactId : undefined);
    const fp = floorPos(flat, u.floor);
    // mgRel is ordered owner-first, so the lead resident is the owner when one is on record.
    // Family members are suffixed "· name" upstream; strip that for the compact grid tile.
    const mg = mygateByUnit.get(u.id) ?? [];
    const lead = mg[0];
    const resident = lead ? { name: lead.name.replace(/ · family$/, ""), role: lead.role } : undefined;
    units.push({
      flat, floor: fp.floor, position: fp.pos, tower, floorKnown: fp.known, resident,
      status, currentOwner, ownerContact: Boolean(resolvedContactId),
      ownerContactId: resolvedContactId,
      ownerSince: lastOwn?.date, lastPrice: lastOwn?.consideration,
      currentTenant: activeLease ? partyNames(activeLease, ["lessee", "tenant"]) || undefined : undefined,
      rent: activeLease?.rent, deposit: activeLease?.deposit,
      tenancyStart: activeLease?.tenancyStart, tenancyEnd: activeLease?.tenancyEnd,
      registrationCount: events.length, events, contactMatches: mygateByUnit.get(u.id) ?? [],
      zapkey: zapByUnit.get(u.id) ?? [],
    });
  }

  // Authoritative apartments/floor per the brochure/operator: Wing A = 5, B/C/D/E = 6.
  // (Deriving from max unit-position overshoots: a few odd flats end in 7-9, e.g. shops/podium.)
  const TOWER_PER_FLOOR: Record<string, number> = { A: 5, B: 6, C: 6, D: 6, E: 6 };
  // Tower height comes from flats whose floor we KNOW; a bad heuristic parse must not stretch
  // the grid to a floor that does not exist. Fall back to derived floors only if none are known.
  const towersMap = new Map<string, { letter: string; floors: number; derived: number; perFloor: number; count: number }>();
  for (const u of units) {
    const t = u.tower; if (!t) continue;
    const cur = towersMap.get(t) ?? { letter: t, floors: 0, derived: 0, perFloor: 0, count: 0 };
    if (u.floorKnown) cur.floors = Math.max(cur.floors, u.floor);
    cur.derived = Math.max(cur.derived, u.floor);
    cur.perFloor = Math.max(cur.perFloor, u.position);
    cur.count += 1; towersMap.set(t, cur);
  }
  const towers = [...towersMap.values()].sort((a, z) => a.letter.localeCompare(z.letter))
    .map((t) => {
      const floors = Math.min(Math.max(t.floors || t.derived, 1), MAX_FLOOR);
      const unitsPerFloor = TOWER_PER_FLOOR[t.letter] ?? Math.min(Math.max(t.perFloor, 4), 12);
      const unplaced = units.filter((u) => u.tower === t.letter &&
        (u.floor > floors || u.position > unitsPerFloor)).length;
      return { letter: t.letter, label: `Tower ${t.letter}`, floors, unitsPerFloor, unitCount: t.count, unplaced };
    });
  const overallPerFloor = towers.reduce((m, t) => Math.max(m, t.unitsPerFloor), 6);

  const withReg = units.filter((u) => u.registrationCount > 0);
  const tenanted = units.filter((u) => u.status === "tenanted");
  const rents = tenanted.map((u) => u.rent ?? 0).filter((r) => r > 0);
  const within = (d: string | undefined, mo: number) => d ? new Date(d).getTime() <= now + mo * 2_629_800_000 && new Date(d).getTime() >= now : false;
  const prices = units.map((u) => u.lastPrice ?? 0).filter((p) => p > 0);
  const tenures = units.filter((u) => u.ownerSince && !u.ownerContact).map((u) => yrs(u.ownerSince));
  const expected = num((await readQuery<{ n: string }>(
    `select rera_expected_units::text n from vw_building_unit_accounting where building_name = $1`, [b.name]))[0]?.n);
  const panCount = myRecs.reduce((s, r) => s + (r.parties ?? []).filter((p) => p.pan).length, 0);

  // Expiring leases + review queue both derive from myRecs — no extra query, and we get
  // the Devanagari party names + raw description + recovered wing/flat for free.
  const MS_DAY = 86_400_000;
  const pansByRole = (parties: RParty[] | null, roles: string[]) =>
    (parties ?? []).filter((p) => roles.includes(p.role) && p.pan).map((p) => p.pan as string);
  const expRecs = myRecs
    .filter((r) => r.category === "tenancy" && r.tenancy_end_date &&
      new Date(r.tenancy_end_date).getTime() >= now && new Date(r.tenancy_end_date).getTime() <= now + 183 * MS_DAY)
    .sort((a, z) => (a.tenancy_end_date ?? "").localeCompare(z.tenancy_end_date ?? ""));
  // Probable contact info: pay for the contact+import scan if there's anything to enrich.
  const candidates = units.length || expRecs.length ? await getContactIndex() : [];
  // Index candidates by building+wing+flat for O(1) per-unit lookup (sheet rows are flat-tagged).
  const candByUnit = new Map<string, Candidate[]>();
  for (const c of candidates) {
    const k = unitKey(c.building, c.wing, c.unit);
    if (k) (candByUnit.get(k) ?? candByUnit.set(k, []).get(k)!).push(c);
  }
  // A party is matchable only via its romanized name (Devanagari can't match English contacts).
  const romanParties = (parties: RParty[] | null, roles: string[], role: "tenant" | "owner") =>
    (parties ?? []).filter((p) => roles.includes(p.role))
      .map((p) => ({ name: p.english && /[A-Za-z]/.test(p.english) ? p.english : "", role }))
      .filter((p) => p.name);
  const expiringLeases: import("./types").ExpiringLease[] = expRecs.map((r) => {
    const rec = recovery.get(r.record_id)!;
    const parties = [...romanParties(r.parties, ["lessee", "tenant"], "tenant"), ...romanParties(r.parties, ["lessor", "landlord"], "owner")];
    return {
      wing: rec.wing || "—", unit: rec.unit || "—",
      daysRemaining: Math.max(0, Math.round((new Date(r.tenancy_end_date!).getTime() - now) / MS_DAY)),
      rent: r.tenancy_monthly_rent ? num(r.tenancy_monthly_rent) : undefined,
      deposit: r.tenancy_deposit ? num(r.tenancy_deposit) : undefined,
      tenancyStart: r.tenancy_start_date ?? undefined, tenancyEnd: r.tenancy_end_date!,
      tenantNames: joinPartyNames(r.parties, ["lessee", "tenant"]) || "—",
      ownerNames: joinPartyNames(r.parties, ["lessor", "landlord"]) || "—",
      tenantPans: pansByRole(r.parties, ["lessee", "tenant"]).join(", "),
      docNumber: r.doc_number ?? "—", sro: r.sro_office ?? undefined,
      confidence: rec.confidence, descriptionRaw: r.property_description_raw ?? undefined,
      // MyGate current residents for this unit first, then name-matched registration contacts.
      contactMatches: dedupeContacts([
        mygateByWingUnit.get(`${rec.wing}|${rec.unit}`) ?? [],
        candidates.length ? findMatches(parties, candidates, rec.wing, rec.unit, b.name) : [],
      ], 6),
    };
  });

  // Attach probable contacts to EVERY unit: direct flat lookup (the sheet maps flat→owner) first,
  // then name-matched registration parties. Direct lookup is O(1); name-match only runs when the
  // unit has romanized party names, so this stays cheap across hundreds of units.
  if (candidates.length) {
    for (const u of units) {
      const flatDigits = u.flat.replace(/\D/g, "");
      const k = unitKey(b.name, u.tower, flatDigits);
      const direct = (k ? candByUnit.get(k) ?? [] : []).slice(0, 4).map(toUnitContact);
      const lastOwn = u.events.filter((e) => e.category === "ownership").slice(-1);
      const activeLease = u.events.filter((e) => e.category === "tenancy" && e.active).slice(-1);
      const parties = [
        ...lastOwn.flatMap((e) => romanParties(e.parties, ["purchaser", "buyer"], "owner")),
        ...activeLease.flatMap((e) => romanParties(e.parties, ["lessee", "tenant"], "tenant")),
      ];
      const named = parties.length ? findMatches(parties, candidates, u.tower, flatDigits, b.name) : [];
      // MyGate current residents (seeded at push) first — they're unit-linked, keep them.
      u.contactMatches = dedupeContacts([u.contactMatches, direct, named], 6);
    }
  }

  // Records whose wing/flat couldn't be cleanly resolved — the human triage board.
  const confRank: Record<string, number> = { unknown: 0, partial: 1, recovered: 2, clean: 3 };
  const reviewQueue: UReview[] = myRecs
    .map((r) => ({ r, rec: recovery.get(r.record_id)! }))
    .filter(({ rec }) => rec.confidence !== "clean")
    .sort((a, z) => confRank[a.rec.confidence] - confRank[z.rec.confidence] || (z.r.registration_date ?? "").localeCompare(a.r.registration_date ?? ""))
    .slice(0, 120)
    .map(({ r, rec }) => ({
      recordId: r.record_id, docNumber: r.doc_number ?? "—", docType: r.document_type ?? "—",
      year: r.registration_year ?? (r.registration_date ? Number(r.registration_date.slice(0, 4)) : 0),
      category: r.category ?? "other",
      wingTextRaw: r.wing_text ?? undefined, unitTextRaw: r.unit_text ?? undefined,
      descriptionRaw: r.property_description_raw ?? undefined,
      recoveredWing: rec.wing, recoveredUnit: rec.unit, confidence: rec.confidence,
      parties: (r.parties ?? []).map((p) => ({
        role: p.role, english: p.english || p.devanagari || "—", devanagari: p.devanagari ?? undefined,
        pan: p.pan ?? undefined, age: p.age ?? undefined, address: p.address ?? undefined, type: p.type ?? undefined,
      })),
    }));

  return {
    buildingName: b.name, towers, unitsPerFloor: overallPerFloor, units, expiringLeases, reviewQueue,
    stats: {
      expected, mappedUnits: units.filter((u) => u.status !== "unknown").length, withRegistration: withReg.length,
      owned: units.filter((u) => u.status === "owned").length, tenanted: tenanted.length,
      registered: units.filter((u) => u.status === "registered").length,
      occupancyPct: withReg.length ? Math.round((tenanted.length / withReg.length) * 100) : 0,
      avgRent: rents.length ? Math.round(rents.reduce((s, r) => s + r, 0) / rents.length) : 0,
      expiring6mo: units.filter((u) => within(u.tenancyEnd, 6)).length,
      expiring12mo: units.filter((u) => within(u.tenancyEnd, 12)).length,
      avgOwnershipYears: tenures.length ? Math.round((tenures.reduce((s, y) => s + y, 0) / tenures.length) * 10) / 10 : 0,
      minPrice: prices.length ? Math.min(...prices) : 0, maxPrice: prices.length ? Math.max(...prices) : 0,
      panCount, registrations: myRecs.length,
    },
  };
}
