/**
 * Recover wing + flat and clean party names from messy IGR registration text.
 *
 * Why this exists: the IGR parser dumps raw register text into wing_text/unit_text
 * ("B 176Shop No:", "C-43, (WITH 1 COVERED CAR PARKING),") and a mechanical, wrong
 * romanization into party_name_english ("Kiyana Vencarsa Ela El" for कियाना वेन्चर्स एल एल पी).
 * The TRUE wing+flat almost always sit in property_description_raw, in Marathi
 * ("सदनिका नं: 174, माळा नं: 17 वा मजला, इमारतीचे नाव: डी विंग"). This module reads that
 * truth so the UI can place units correctly and lead with Devanagari instead of garbage.
 *
 * Pure functions, no db/react import — testable. Run the self-check with:
 *   npx tsx src/lib/cockpit/units-clean.ts
 */

// Marathi/English spellings of the wing letter (sound-spelled in Devanagari on the register).
const WING_DEV: Record<string, string> = { "ए": "A", "बी": "B", "सी": "C", "डी": "D", "ई": "E", "एफ": "F" };

export type Confidence = "clean" | "recovered" | "partial" | "unknown";

export interface RecoverInput {
  unitWing?: string | null;       // building_units.wing (authoritative when linked)
  unitNumber?: string | null;     // building_units.unit_number (authoritative when linked)
  wingText?: string | null;       // raw r.wing_text
  unitText?: string | null;       // raw r.unit_text
  descriptionRaw?: string | null; // r.property_description_raw (Marathi/English truth)
}
export interface Recovered { wing: string; unit: string; confidence: Confidence; }

const onlyLetter = (s: string | null | undefined): string => {
  const m = String(s ?? "").toUpperCase().match(/\b([A-F])\b|\b([A-F])[\s-]?WING|WING[\s-]?([A-F])\b/);
  return (m && (m[1] || m[2] || m[3])) || "";
};
const firstNum = (s: string | null | undefined): string => {
  const m = String(s ?? "").match(/(\d{1,4})/); // first run of digits = flat ("B 176Shop" -> 176, "52," -> 52)
  return m ? m[1] : "";
};

function wingFromDescription(d: string): string {
  // Marathi: "...इमारतीचे नाव: डी विंग" or "डी विंग, इमारतीचे नाव:". Find <letter-word> विंग.
  const dev = d.match(/([ऀ-ॿ]{1,3})\s*विंग/);
  if (dev && WING_DEV[dev[1]]) return WING_DEV[dev[1]];
  return onlyLetter(d); // English "A WING" / "A-WING"
}
function unitFromDescription(d: string): string {
  const m = d.match(/सदनिका\s*नं[:\s]*([0-9]+)/); // "Flat no: 174"
  if (m) return m[1];
  return firstNum(d); // English "34  A WING" -> 34
}

/** Resolve wing + flat from the best available source, with a confidence grade. */
export function recoverWingUnit(i: RecoverInput): Recovered {
  // 1. Linked building_unit is authoritative.
  const linkedWing = onlyLetter(i.unitWing) || (String(i.unitWing ?? "").trim().match(/^[A-Fa-f]$/)?.[0]?.toUpperCase() ?? "");
  const linkedUnit = /^\d{1,4}$/.test(String(i.unitNumber ?? "").trim()) ? String(i.unitNumber).trim() : "";
  if (linkedWing && linkedUnit) return { wing: linkedWing, unit: linkedUnit, confidence: "clean" };

  // 2. Recover from raw text + description.
  const desc = i.descriptionRaw ?? "";
  const wing = linkedWing || onlyLetter(i.wingText) || onlyLetter(i.unitText) || wingFromDescription(desc);
  const unit = linkedUnit || firstNum(i.unitText) || unitFromDescription(desc);

  let confidence: Confidence;
  if (wing && unit) confidence = "recovered";
  else if (wing || unit) confidence = "partial";
  else confidence = "unknown";
  return { wing, unit, confidence };
}

/** Devanagari is the truth; the romanization is mechanical and often wrong. Lead with Devanagari. */
export function cleanName(devanagari?: string | null, english?: string | null): { primary: string; roman?: string } {
  const strip = (s: string | null | undefined) =>
    String(s ?? "").replace(/^[-\s.]+/, "").replace(/^(मे|M\/?s\.?)\s+/i, "").trim();
  const dev = strip(devanagari);
  const eng = strip(english);
  const primary = dev || eng || "—";
  // Only surface the roman line if it's actually Latin and adds something beyond the Devanagari.
  const roman = eng && /[A-Za-z]/.test(eng) && eng !== primary ? eng : undefined;
  return { primary, roman };
}

/**
 * Join the cleaned names for a set of roles, collapsing duplicate party rows.
 * The IGR import frequently stores the same person twice — exact dupes ("Greenstone Lobo,
 * Greenstone Lobo") and reordered/concatenated variants ("Krishna Sankar Narayan" vs
 * "SankarNarayanKrishna"). An anagram signature (sorted chars) catches both; among a dup
 * group we keep the most-spaced (best-tokenized) form.
 * ponytail: anagram key false-merges only true anagrams of co-parties in one registration — negligible.
 */
export function joinPartyNames(
  parties: { role: string; devanagari?: string | null; english?: string | null }[] | null | undefined,
  roles: string[],
): string {
  const best = new Map<string, string>();
  for (const p of parties ?? []) {
    if (!roles.includes(p.role)) continue;
    const name = cleanName(p.devanagari, p.english).primary;
    if (!name || name === "—") continue;
    const sig = name.toLowerCase().replace(/[^a-z0-9ऀ-ॿ]/g, "").split("").sort().join("");
    const prev = best.get(sig);
    if (!prev || name.split(/\s+/).length > prev.split(/\s+/).length) best.set(sig, name);
  }
  return [...best.values()].join(", ");
}

// ponytail: tiny assert demo — the parsing is the risky part, so it earns one runnable check.
function demo() {
  const eq = (a: unknown, b: unknown, m: string) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${m}: got ${JSON.stringify(a)}`); };
  eq(recoverWingUnit({ unitWing: "D", unitNumber: "203" }).confidence, "clean", "linked");
  eq(recoverWingUnit({ unitText: "B 176Shop No:" }), { wing: "B", unit: "176", confidence: "recovered" }, "shop junk");
  eq(recoverWingUnit({ unitText: "C-43, (WITH 1 COVERED CAR PARKING)," }), { wing: "C", unit: "43", confidence: "recovered" }, "parking junk");
  eq(recoverWingUnit({ unitText: "101,A wing," }), { wing: "A", unit: "101", confidence: "recovered" }, "embedded wing");
  eq(recoverWingUnit({ descriptionRaw: "सदनिका नं: 174, माळा नं: 17 वा मजला, इमारतीचे नाव: डी विंग,कल्पतरू" }),
     { wing: "D", unit: "174", confidence: "recovered" }, "marathi desc");
  eq(recoverWingUnit({ descriptionRaw: "34  A WING KALPATARU RADIANCE" }), { wing: "A", unit: "34", confidence: "recovered" }, "english desc");
  eq(recoverWingUnit({ unitText: "52," }), { wing: "", unit: "52", confidence: "partial" }, "no wing");
  eq(recoverWingUnit({}), { wing: "", unit: "", confidence: "unknown" }, "nothing");
  eq(cleanName("कियाना वेन्चर्स एल एल पी", "Kiyana Vencarsa Ela El").primary, "कियाना वेन्चर्स एल एल पी", "dev primary");
  eq(cleanName("--गुरु आशिष", "--Guru Asisa").primary, "गुरु आशिष", "strip dashes");
  const dup = [{ role: "tenant", english: "Greenstone Lobo" }, { role: "tenant", english: "Greenstone Lobo" }];
  eq(joinPartyNames(dup, ["tenant"]), "Greenstone Lobo", "exact dup");
  const reord = [{ role: "tenant", english: "SankarNarayanKrishna" }, { role: "tenant", english: "Krishna Sankar Narayan" }];
  eq(joinPartyNames(reord, ["tenant"]), "Krishna Sankar Narayan", "reorder dup keeps spaced");
  console.log("units-clean: all checks passed");
}
// tsx/node entry — runs only when invoked directly, inert when imported by Next.
if (typeof process !== "undefined" && process.argv[1]?.endsWith("units-clean.ts")) demo();
