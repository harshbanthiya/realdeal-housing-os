import type { BlogPost } from "@/lib/cms";

/**
 * Local fixture posts — served when Wix CMS is unreachable or a slug isn't
 * published there yet; CMS posts override same-slug fixtures (see cms.ts).
 * Editorial rule: only verifiable facts (site.ts / brochure-verified data),
 * no prices, no invented statistics. SEO focus: low-competition building-name
 * keywords.
 */
export const fixtureBlogPosts: BlogPost[] = [
  {
    slug: "ekta-tripolis-goregaon-west-guide",
    title: "Ekta Tripolis, Goregaon West: the complete guide to the three towers",
    excerpt:
      "Skypolis, Caliopolis and Theopolis — what buyers and tenants should know about Ekta Tripolis in Goregaon West: configurations, amenities, connectivity, and how to view a flat.",
    body: `
<p>Ask anyone to point out a building on the Goregaon West skyline and there's a fair chance they'll point at <strong>Ekta Tripolis</strong> — a trilogy of 36-storey towers named <strong>Skypolis, Caliopolis and Theopolis</strong>. We've helped families buy and rent here for years; this guide covers what we get asked most.</p>

<h2>Which flats does Ekta Tripolis have?</h2>
<p>The towers carry <strong>2, 2.5 and 3 BHK apartments</strong> in open-plan layouts with contemporary interiors, ensuite master bedrooms and large balconies over Goregaon's green belt. Every home ships with smart-home automation as standard — lighting, appliances and access from one interface — plus 24/7 power backup for the essentials.</p>

<h2>Amenities: what living here is actually like</h2>
<p>The amenity set is led by an <strong>infinity pool</strong>, the <strong>Club Alpha fitness centre</strong> and a <strong>sky lounge</strong>, with high-speed elevators and 24-hour security underneath it all. The project holds a Platinum green-building pre-certification, which shows up in practice as cooler interiors and lower running costs.</p>

<h2>Where it sits, and why that matters</h2>
<p>Ekta Tripolis is in <strong>Goregaon West</strong>, with Link Road, S.V. Road and the Western Express Highway all within easy reach — and the metro a short ride away. Schools, hospitals and the Oshiwara retail belt sit within a couple of kilometres. Explore the pins on our <a href="/projects/ekta-tripolis">Ekta Tripolis building page</a> — the neighbourhood map there is drawn from live map data.</p>

<h2>Buying vs renting in Ekta Tripolis</h2>
<p>The towers are <strong>ready to move and RERA-approved</strong>, so both resale purchases and leases move quickly compared to under-construction alternatives. Availability changes week to week; the honest answer on price is always the current one, so we quote per-flat rather than publishing stale numbers. See <a href="/buy">what's currently on the market</a> or <a href="/rent">current rentals</a>.</p>

<h2>Viewing a flat here</h2>
<p>We're a Goregaon West firm — Ekta Tripolis is one of the four buildings we track floor by floor, registration by registration. <a href="/contact">Ask us for a viewing</a> and we'll line up flats that match your configuration and floor preference, with every fact about the flat verified before you walk in.</p>
`,
    heroImageUrl: "/ekta-aerial-sunset.jpg",
    tags: ["Ekta Tripolis", "Goregaon West", "Buyer's guide"],
    publishedAt: "2026-07-13T09:00:00.000Z",
    seoTitle: "Ekta Tripolis, Goregaon West — Flats, Towers & Complete Guide",
    seoDescription:
      "Ekta Tripolis, Goregaon West: 2, 2.5 & 3 BHK flats across Skypolis, Caliopolis & Theopolis. Amenities, connectivity, and how to buy or rent — from the local specialists.",
  },
];
