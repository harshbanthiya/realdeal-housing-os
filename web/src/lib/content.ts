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
  price: string;
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
    "DLF Westpark in Andheri West is presented here as a structured, verifiable preview. Pricing, RERA registration, configurations and the official brochure remain placeholders until each is individually verified — we publish facts, not promises.",
  seoTitle: "DLF Westpark Andheri West - Premium Residences Preview",
  seoDescription:
    "Review DLF Westpark in Andheri West with verified placeholders, location context, residence notes, and a preview-only enquiry form.",
};

export const facts: ProjectFact[] = [
  { key: "project_name", label: "Project Name", value: "DLF Westpark (also referenced as The Westpark)", status: "operator_confirmed", source: "Operator naming confirmation" },
  { key: "developer", label: "Developer", value: "DLF", status: "pending_review", source: "Pending official confirmation" },
  { key: "location", label: "Location", value: "Andheri West, Mumbai (D.N. Nagar / Link Road)", status: "pending_review", source: "General locality; exact addressing VERIFY" },
  { key: "rera", label: "RERA Registration", value: "RERA_VERIFY", status: "pending", source: "MahaRERA verification pending" },
  { key: "price", label: "Starting Price", value: "PRICE_VERIFY", status: "pending", source: "Pending verified pricing" },
  { key: "configurations", label: "Configurations", value: "VERIFY", status: "pending", source: "Pending official brochure" },
  { key: "carpet_area", label: "Carpet Area Range", value: "VERIFY", status: "pending", source: "Pending official brochure" },
  { key: "possession", label: "Possession", value: "VERIFY", status: "pending", source: "Pending official timeline" },
  { key: "brochure", label: "Official Brochure", value: "BROCHURE_LINK_PENDING", status: "pending", source: "Pending approved brochure" },
];

export const residences: Residence[] = [
  { config: "Residence Layout A", carpetArea: "VERIFY", price: "PRICE_VERIFY", description: "Configuration details pending verification from the approved project brochure." },
  { config: "Residence Layout B", carpetArea: "VERIFY", price: "PRICE_VERIFY", description: "Configuration details pending verification from the approved project brochure." },
  { config: "Residence Layout C", carpetArea: "VERIFY", price: "PRICE_VERIFY", description: "Configuration details pending verification from the approved project brochure." },
];

export const amenities: Amenity[] = [
  { name: "Wellness & Clubhouse", category: "Wellness", description: "Pending verification from approved project brochure (BROCHURE_LINK_PENDING)." },
  { name: "Recreation & Sports", category: "Recreation", description: "Pending verification from approved project brochure (BROCHURE_LINK_PENDING)." },
  { name: "Landscaped Open Spaces", category: "Outdoor", description: "Pending verification from approved project brochure (BROCHURE_LINK_PENDING)." },
  { name: "Convenience & Retail", category: "Convenience", description: "Pending verification from approved project brochure (BROCHURE_LINK_PENDING)." },
  { name: "Security & Access", category: "Security", description: "Pending verification from approved project brochure (BROCHURE_LINK_PENDING)." },
];

export const faqs: Faq[] = [
  { question: "Is DLF Westpark RERA registered?", answer: "RERA registration details are being verified (RERA_VERIFY). We display only verified MahaRERA registration numbers once confirmed.", category: "Compliance" },
  { question: "What is the price of residences at DLF Westpark?", answer: "Pricing is pending verification (PRICE_VERIFY). We do not publish indicative prices until they are confirmed from an approved source.", category: "Pricing" },
  { question: "Where is DLF Westpark located?", answer: "Andheri West, Mumbai, within the D.N. Nagar / Link Road micro-market. Exact addressing and distances are under verification (VERIFY).", category: "Location" },
  { question: "Who is the developer?", answer: "DLF. Project naming is operator-confirmed as DLF Westpark; full developer and project details remain under review.", category: "Developer" },
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
