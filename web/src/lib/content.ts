/**
 * DLF Westpark content model.
 *
 * Mirrors the Wix Test CMS collections (Projects, ProjectFacts, Residences,
 * Amenities, ProjectFAQs) so this can be swapped for live `@wix/data` reads
 * once the Headless OAuth Client ID is provided — the page components stay
 * unchanged. Placeholders (PRICE_VERIFY / RERA_VERIFY / BROCHURE_LINK_PENDING /
 * VERIFY) are intentionally preserved; nothing is fabricated.
 */

export type VerificationStatus =
  | "operator_confirmed"
  | "brochure_verified"
  | "pending_review"
  | "pending";

export interface ProjectFact {
  key: string;
  label: string;
  value: string;
  status: VerificationStatus;
  source: string;
}

export interface Residence {
  config: string;
  carpetArea: string;
  description: string;
}

export interface Amenity {
  name: string;
  category: string;
  description: string;
}

export interface Faq {
  question: string;
  answer: string;
  category: string;
}

export const project = {
  slug: "dlf-westpark-andheri-west",
  name: "DLF Westpark, Andheri West",
  developer: "DLF",
  locality: "Andheri West, Mumbai",
  microMarket: "D.N. Nagar / Link Road",
  heroTagline: "A calmer way to evaluate a premium city residence.",
  overview:
    "DLF's return to Mumbai: four completed 40-storey towers in Andheri West, from studios to 5 BHK duplexes, documented here fact by fact from the official Phase 1 brochure — with Phase 2 bringing two more towers. Launch pricing is dynamic, so our team shares current price lists person-to-person. We publish facts, not promises.",
  seoTitle: "DLF Westpark Andheri West - Premium Residences Preview",
  seoDescription:
    "Review DLF Westpark in Andheri West with verified placeholders, location context, residence notes, and a preview-only enquiry form.",
};

export const facts: ProjectFact[] = [
  { key: "project_name", label: "Project Name", value: "DLF Westpark (also referenced as The Westpark)", status: "operator_confirmed", source: "Operator naming confirmation" },
  { key: "developer", label: "Developer", value: "Peegen Builders and Developers Pvt. Ltd. — a DLF + Trident Realty joint venture", status: "brochure_verified", source: "Official Phase 1 brochure (Presenter 1.pdf)" },
  { key: "location", label: "Location", value: "Andheri West, Mumbai (D.N. Nagar / Link Road)", status: "pending_review", source: "General locality; exact addressing VERIFY" },
  { key: "rera", label: "RERA Registration", value: "MahaRERA PR1181012500079 (Phase 1)", status: "brochure_verified", source: "Official Phase 1 brochure (Presenter 1.pdf)" },
  { key: "towers", label: "Towers & Floors", value: "4 towers (T02–T05), 40 floors each, residences from floor 3", status: "brochure_verified", source: "Official Phase 1 brochure floor plans" },
  { key: "price", label: "Pricing", value: "On request — launch pricing is dynamic and shared by our sales team on call/WhatsApp", status: "operator_confirmed", source: "Operator policy (2026-07-13)" },
  { key: "configurations", label: "Configurations", value: "Studios, 3 BHK, 4 BHK, 5 BHK and 4 BHK duplexes across T02–T05 (25 configuration types)", status: "brochure_verified", source: "Official Phase 1 brochure floor plans" },
  { key: "carpet_area", label: "Carpet Area Range", value: "245–2,534 sqft carpet (refuge studio to 4 BHK duplex)", status: "brochure_verified", source: "Official Phase 1 brochure area statements" },
  { key: "possession", label: "Phase Status", value: "Phase 1 (T02–T05) complete · Phase 2 with two additional towers upcoming", status: "operator_confirmed", source: "Operator confirmation (2026-07-13)" },
  { key: "phase_2", label: "Phase 2 Towers (upcoming)", value: "Tower 6 — 38 storeys, 2 units per floor: 3 BHK 1,500 sqft & 4 BHK 2,600 sqft · Tower 7 — 38 storeys, 2 units per floor (same carpets), plus one duplex on floors 39–40", status: "operator_confirmed", source: "Operator briefing (2026-07-13); official Phase 2 brochure pending" },
  { key: "brochure", label: "Official Brochure", value: "BROCHURE_LINK_PENDING", status: "pending", source: "Pending approved brochure" },
];

export const residences: Residence[] = [
  { config: "3 BHK", carpetArea: "1,048–1,368 sqft carpet", description: "Nine 3 BHK variants across all four towers — the core of the project. Balconies of 78–148 sqft." },
  { config: "4 BHK", carpetArea: "1,246–2,136 sqft carpet", description: "Single-aspect 4 BHKs on the upper and refuge floors of T02, T03 and T04." },
  { config: "4 BHK Duplex", carpetArea: "2,079–2,534 sqft carpet", description: "Two-level residences on floors 39–40 of every tower — six duplexes in Phase 1." },
  { config: "5 BHK", carpetArea: "1,825 sqft carpet", description: "Tower T02 refuge floors 7, 15, 22 and 29 — one residence per floor." },
  { config: "Studio", carpetArea: "245–478 sqft carpet", description: "Compact studios on T05 refuge floors — the smallest tickets in the project." },
];

export const amenities: Amenity[] = [
  { name: "Spa & Wellness Centre", category: "Wellness", description: "Dedicated spa and wellness floor as shown in the official brochure." },
  { name: "Bowling Alley & Indoor Games", category: "Recreation", description: "Bowling alley plus indoor kids' play area, per brochure renders." },
  { name: "Eco-deck: Pool, Jogging Track & Courtyard", category: "Outdoor", description: "Landscaped eco-deck with swimming pool, jogging track and courtyard." },
  { name: "Café & Banquet Hall", category: "Convenience", description: "Resident café and banquet hall shown in the brochure amenity set." },
  { name: "Outdoor Kids' Play Area", category: "Family", description: "Dedicated outdoor children's play area within the landscaped deck." },
];

export const faqs: Faq[] = [
  { question: "Is DLF Westpark RERA registered?", answer: "Yes — Phase 1 is registered as MahaRERA PR1181012500079, per the official project brochure.", category: "Compliance" },
  { question: "What is the price of residences at DLF Westpark?", answer: "Launch pricing is dynamic and changes with inventory, so we don't publish price lists. Call or WhatsApp our team and we'll share current pricing for the configurations you're considering.", category: "Pricing" },
  { question: "Is Phase 1 complete?", answer: "Yes — the four Phase 1 towers (T02–T05) are complete. Phase 2 adds two towers: Tower 6 (38 storeys, 3 BHK 1,500 sqft and 4 BHK 2,600 sqft, two units per floor) and Tower 7 (same carpets, plus a duplex on floors 39–40). Register interest with our team for launch updates.", category: "Project status" },
  { question: "Where is DLF Westpark located?", answer: "Andheri West, Mumbai, within the D.N. Nagar / Link Road micro-market. Exact addressing and distances are under verification (VERIFY).", category: "Location" },
  { question: "Who is the developer?", answer: "Peegen Builders and Developers Pvt. Ltd. — a joint venture between DLF and Trident Realty — per the official Phase 1 brochure.", category: "Developer" },
  { question: "What configurations are available?", answer: "Studios (245–478 sqft), 3 BHKs (1,048–1,368 sqft), 4 BHKs (1,246–2,136 sqft), 5 BHKs (1,825 sqft) and 4 BHK duplexes (2,079–2,534 sqft carpet) across towers T02–T05. See the floor-plan explorer for every layout.", category: "Residences" },
  { question: "Can I download the brochure?", answer: "The official brochure link is pending (BROCHURE_LINK_PENDING). It will appear here once an approved brochure is available.", category: "Resources" },
  { question: "How do I enquire?", answer: "Use the enquiry section below. This is a staging preview: it does not submit live enquiries, and all submissions are manual-review only.", category: "Enquiry" },
];

/** Tokens that must always render as visible "pending" placeholders. */
export const PLACEHOLDER_TOKENS = [
  "RERA_VERIFY",
  "PRICE_VERIFY",
  "BROCHURE_LINK_PENDING",
  "VERIFY",
];
