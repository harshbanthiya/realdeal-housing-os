/**
 * Probable-contact matching for expiring leases.
 *
 * Reality of the data: contacts carry NO PAN (so no strong key), import rows aren't tagged to
 * Kalpataru, and IGR party names are messy romanizations. So we match by NAME, conservatively —
 * a single shared token ("Dilip") matches the wrong person, so we require >=2 significant shared
 * tokens AND >=60% coverage of the smaller name. We'd rather show nothing than a wrong number.
 *
 * Pure (no db/react) — testable. Run: npx tsx src/lib/cockpit/contact-match.ts
 */

const HONORIFICS = new Set(["mr", "mrs", "miss", "ms", "shri", "smt", "dr", "the", "late", "kum", "adv"]);

/** Significant name tokens: split camelCase concatenations, drop honorifics + initials (<3 chars). */
export function sigTokens(name?: string | null): string[] {
  return String(name ?? "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .split(/[^a-z]+/)
    .filter((t) => t.length >= 3 && !HONORIFICS.has(t));
}

export type MatchConfidence = "strong" | "probable";
export interface Candidate {
  name: string; tokens: string[]; source: "contact" | "import";
  phone?: string; email?: string; contactId?: string;
  /** wing must be a single letter, unit digits-only — normalized at index time for exact compare. */
  building?: string; wing?: string; unit?: string;
}
const bslug = (s?: string) => (s ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "");
export interface ProbableContact {
  name: string; role: "tenant" | "owner"; confidence: MatchConfidence; source: "contact" | "import";
  phone?: string; email?: string; contactId?: string; unitMatch?: boolean;
}

/** Score a party's tokens against one candidate. null = not a confident match. */
function score(party: Set<string>, candTokens: string[]): { shared: number; conf: MatchConfidence } | null {
  if (party.size < 2 || candTokens.length < 2) return null; // need 2+ sig tokens on BOTH sides
  const cand = new Set(candTokens);
  let shared = 0;
  for (const t of cand) if (party.has(t)) shared++;
  if (shared < 2) return null;
  const coverage = shared / Math.min(party.size, cand.size);
  if (coverage < 0.6) return null;
  return { shared, conf: shared >= 3 || coverage === 1 ? "strong" : "probable" };
}

export function buildCandidate(c: Omit<Candidate, "tokens">): Candidate {
  return { ...c, tokens: sigTokens(c.name) };
}

/** Stable key for direct building+wing+flat lookup; null if any part is missing/ill-formed. */
export function unitKey(building?: string | null, wing?: string | null, unit?: string | null): string | null {
  if (!building || !wing || !unit) return null;
  const w = String(wing).toUpperCase();
  const u = String(unit).replace(/\D/g, "");
  if (!u || !/^[A-F]$/.test(w)) return null; // wing must already be normalized to a letter
  return `${bslug(building)}|${w}|${u}`;
}
/** An import/contact tied to a specific flat → a probable contact (sheet rows are owners/brokers). */
export function toUnitContact(c: Candidate): ProbableContact {
  return { name: c.name, role: "owner", source: c.source, confidence: "strong",
    phone: c.phone, email: c.email, contactId: c.contactId, unitMatch: true };
}
/** Merge several match lists, dedupe by contact/phone/email/name, keep order, cap. */
export function dedupeContacts(lists: ProbableContact[][], cap = 4): ProbableContact[] {
  const seen = new Set<string>();
  const out: ProbableContact[] = [];
  for (const list of lists) for (const m of list) {
    const k = m.contactId || m.phone || m.email || m.name;
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(m);
    if (out.length >= cap) return out;
  }
  return out;
}

/**
 * Best probable contacts for a lease's parties. Caps at 3, dedupes by phone/contact.
 * ponytail: O(parties × candidates) linear scan — fine at a few hundred × a few thousand;
 * if the contact book grows past ~50k, index tokens into an inverted map.
 */
export function findMatches(
  parties: { name: string; role: "tenant" | "owner" }[],
  candidates: Candidate[],
  leaseWing?: string, leaseUnit?: string, leaseBuilding?: string,
): ProbableContact[] {
  const out: ProbableContact[] = [];
  const seen = new Set<string>();
  for (const p of parties) {
    const ptoks = new Set(sigTokens(p.name));
    if (ptoks.size < 2) continue; // pure-Devanagari or single-token names can't be matched safely
    const ranked: { c: Candidate; s: number; conf: MatchConfidence }[] = [];
    for (const c of candidates) {
      const sc = score(ptoks, c.tokens);
      if (sc) ranked.push({ c, s: sc.shared, conf: sc.conf });
    }
    ranked.sort((a, b) => b.s - a.s);
    for (const { c, conf } of ranked.slice(0, 2)) {
      const dedup = c.contactId || c.phone || c.email || c.name;
      if (seen.has(dedup)) continue;
      seen.add(dedup);
      // Unit boost only when the SAME building's wing+flat agree — avoids an Oberoi A-203
      // false-boosting a Kalpataru A-203. Building-less candidates never boost.
      const unitMatch = Boolean(leaseWing && leaseUnit && c.wing && c.unit && c.building && leaseBuilding &&
        bslug(c.building) === bslug(leaseBuilding) &&
        c.wing.toUpperCase() === leaseWing && String(c.unit).replace(/\D/g, "") === leaseUnit);
      out.push({
        name: c.name, role: p.role, source: c.source,
        confidence: unitMatch ? "strong" : conf,
        phone: c.phone, email: c.email, contactId: c.contactId, unitMatch: unitMatch || undefined,
      });
      if (out.length >= 3) return out;
    }
  }
  return out;
}

// ponytail: assert demo — matching threshold is the load-bearing logic, so it gets one check.
function demo() {
  const eq = (a: unknown, b: unknown, m: string) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${m}: ${JSON.stringify(a)}`); };
  const cands = [
    buildCandidate({ name: "Sunny Dilip Dalvi", source: "contact", phone: "+919811112222", contactId: "c1" }),
    buildCandidate({ name: "Chetan Dilip Negandhi", source: "contact", phone: "+919800000000", contactId: "c2" }),
    buildCandidate({ name: "Vijay Anand Chaudhary", source: "import", phone: "+919833334444", building: "Kalpataru Radiance", wing: "C", unit: "121" }),
    buildCandidate({ name: "Vijay Anand Chaudhary", source: "import", phone: "+910000000000", building: "Oberoi Esquire", wing: "C", unit: "121" }),
  ];
  // exact 3-token person -> strong, the single-shared-"Dilip" decoy rejected.
  eq(findMatches([{ name: "Sunny Dilip Dalvi", role: "tenant" }], cands).map((m) => [m.contactId, m.confidence]),
     [["c1", "strong"]], "strong person match, decoy rejected");
  // 1 shared token only -> no match (this is the bug we must avoid).
  eq(findMatches([{ name: "Anjali Dilip", role: "tenant" }], cands), [], "single shared token rejected");
  // unit hint promotes to strong — but only for the SAME building.
  eq(findMatches([{ name: "Vijay Chaudhary", role: "owner" }], cands, "C", "121", "Kalpataru Radiance")[0]?.unitMatch, true, "unit boost same building");
  eq(findMatches([{ name: "Vijay Chaudhary", role: "owner" }], cands, "C", "121", "Imperial Heights").some((m) => m.unitMatch), false, "no cross-building boost");
  // pure Devanagari -> unmatchable, no false positive.
  eq(findMatches([{ name: "सनी दिलीप दळवी", role: "tenant" }], cands), [], "devanagari unmatchable");
  console.log("contact-match: all checks passed");
}
if (typeof process !== "undefined" && process.argv[1]?.endsWith("contact-match.ts")) demo();
