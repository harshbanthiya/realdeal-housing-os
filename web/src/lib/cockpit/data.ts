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
function slugify(v: string) { return v.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
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
      slug: slugify(b.name),
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

// ---------------- unit registry (per-building, per-tower apartment stack) ----------------
type URegistry = import("./types").UnitRegistry;
type UCell = import("./types").UnitCell;
type UEvent = import("./types").UnitTimelineEvent;
type RParty = import("./types").RegParty;

const ZERO_STATS: URegistry["stats"] = {
  expected: 0, mappedUnits: 0, withRegistration: 0, owned: 0, tenanted: 0, registered: 0,
  occupancyPct: 0, avgRent: 0, expiring6mo: 0, expiring12mo: 0, avgOwnershipYears: 0,
  minPrice: 0, maxPrice: 0, panCount: 0, registrations: 0,
};
function towerLetter(wing: string | null): string {
  const m = String(wing ?? "").toUpperCase().match(/([A-Z])\s*$/);
  return m ? m[1] : "";
}
const MAX_FLOOR = 40; // Kalpataru Radiance ~31 habitable / 38 sanctioned; cap guards bad parses
// Flat-number scheme (per brochure): trailing 1-2 digits = unit on floor, rest = floor.
//   2706 -> floor 27, unit 6 ; 291 -> floor 29, unit 1 ; 134 -> floor 13, unit 4 ; 14 -> floor 1, unit 4.
function deriveFloorPos(u: string): { floor: number; pos: number } {
  const n = Number(String(u).replace(/\D/g, "")) || 0;
  const fa = Math.floor(n / 100), pa = n % 100;       // last two digits = unit (e.g. 2706 -> 27/06)
  if (fa >= 1 && fa <= MAX_FLOOR && pa >= 1 && pa <= 12) return { floor: fa, pos: pa };
  const fb = Math.floor(n / 10), pb = n % 10;          // last digit = unit (e.g. 291 -> 29/1)
  if (fb >= 1 && fb <= MAX_FLOOR) return { floor: fb, pos: pb || 10 };
  return { floor: Math.min(Math.max(1, n), MAX_FLOOR), pos: 1 };
}

export async function getUnitRegistry(slug: string): Promise<URegistry | null> {
  const b = (await getBuildings()).find((x) => x.slug === slug);
  const empty = (name: string): URegistry => ({ buildingName: name, towers: [], unitsPerFloor: 6, units: [], stats: ZERO_STATS });
  if (!b) return null;
  if (!live()) return empty(b.name);

  const recs = await readQuery<{
    building_name: string; building_unit_id: string | null; wing: string | null; unit_number: string | null;
    registration_date: string | null; registration_year: number | null; document_type: string | null;
    category: string | null; doc_number: string | null; sro_office: string | null;
    consideration_amount: string | null; market_value: string | null; stamp_duty: string | null;
    registration_fee: string | null; area_text: string | null; tenancy_start_date: string | null;
    tenancy_end_date: string | null; tenancy_monthly_rent: string | null; tenancy_deposit: string | null;
    parties: RParty[] | null;
  }>(
    `select building_name, building_unit_id::text, wing, unit_number, registration_date::text, registration_year,
            document_type, category, doc_number, sro_office, consideration_amount::text, market_value::text,
            stamp_duty::text, registration_fee::text, area_text, tenancy_start_date::text, tenancy_end_date::text,
            tenancy_monthly_rent::text, tenancy_deposit::text, parties
       from vw_unit_registration_full_operator order by registration_date`);
  const myRecs = recs.filter((r) => slugify(String(r.building_name ?? "")) === slug);

  const bunits = await readQuery<{ id: string; wing: string | null; unit_number: string | null; bn: string }>(
    `select bu.id::text, bu.wing, bu.unit_number, b.name bn
       from building_units bu join buildings b on b.id = bu.building_id where bu.canonical_status = 'active'`);
  const myUnits = bunits.filter((u) => slugify(u.bn) === slug && u.unit_number);

  const orel = await readQuery<{ building_unit_id: string | null; full_name: string }>(
    `select r.building_unit_id::text, c.full_name from contact_property_relationships r
       join contacts c on c.id = r.contact_id
      where r.relationship_type = 'owner' and r.building_unit_id is not null
        and r.relationship_status in ('active','approved','pending_review')`);
  const ownerByUnit = new Map<string, string>();
  for (const r of orel) if (r.building_unit_id) ownerByUnit.set(r.building_unit_id, r.full_name);

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
    const key = `${towerLetter(r.wing)}|${String(r.unit_number ?? "").replace(/\D/g, "")}`;
    (evByKey.get(key) ?? evByKey.set(key, []).get(key)!).push(toEvent(r));
  }

  const now = Date.now();
  const yrs = (d?: string) => (d ? Math.max(0, (now - new Date(d).getTime()) / 31_557_600_000) : 0);
  const partyNames = (ev: UEvent, roles: string[]) =>
    ev.parties.filter((p) => roles.includes(p.role)).map((p) => p.english).join(", ");

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
    const currentOwner = lastOwn ? partyNames(lastOwn, ["purchaser", "buyer"]) || undefined : relOwner ?? undefined;
    const status: UCell["status"] = activeLease ? "tenanted"
      : currentOwner ? "owned"
      : events.length ? "registered" : "unknown";
    const fp = deriveFloorPos(flat);
    units.push({
      flat, floor: fp.floor, position: fp.pos, tower,
      status, currentOwner, ownerContact: !lastOwn && Boolean(relOwner),
      ownerSince: lastOwn?.date, lastPrice: lastOwn?.consideration,
      currentTenant: activeLease ? partyNames(activeLease, ["lessee", "tenant"]) || undefined : undefined,
      rent: activeLease?.rent, tenancyEnd: activeLease?.tenancyEnd,
      registrationCount: events.length, events,
    });
  }

  const towersMap = new Map<string, { letter: string; floors: number; perFloor: number; count: number }>();
  for (const u of myUnits) {
    const t = towerLetter(u.wing); if (!t) continue;
    const fp = deriveFloorPos(String(u.unit_number));
    const cur = towersMap.get(t) ?? { letter: t, floors: 0, perFloor: 0, count: 0 };
    cur.floors = Math.max(cur.floors, fp.floor);
    cur.perFloor = Math.max(cur.perFloor, fp.pos);
    cur.count += 1; towersMap.set(t, cur);
  }
  // Authoritative apartments/floor per the brochure/operator: Wing A = 5, B/C/D/E = 6.
  // (Deriving from max unit-position overshoots: a few odd flats end in 7-9, e.g. shops/podium.)
  const TOWER_PER_FLOOR: Record<string, number> = { A: 5, B: 6, C: 6, D: 6, E: 6 };
  const towers = [...towersMap.values()].sort((a, z) => a.letter.localeCompare(z.letter))
    .map((t) => ({ letter: t.letter, label: `Tower ${t.letter}`, floors: Math.min(Math.max(t.floors, 1), MAX_FLOOR),
                   unitsPerFloor: TOWER_PER_FLOOR[t.letter] ?? Math.min(Math.max(t.perFloor, 4), 12), unitCount: t.count }));
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

  return {
    buildingName: b.name, towers, unitsPerFloor: overallPerFloor, units,
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
