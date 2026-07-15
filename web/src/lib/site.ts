/**
 * Real Deal Housing — company + catalogue content.
 *
 * Content reproduced from the live site realdealhousing.com (the operator's own
 * site), restyled into the Gallery White aesthetic. The live site was read-only;
 * nothing there was modified. Prices/areas are shown as captured.
 */

export const company = {
  name: "Real Deal Housing",
  legalName: "Real Deal Housing Private Limited",
  tagline: "Your Future Home Is Right Here",
  /** Editorial hero statement, one array item per display line. */
  heroStatement: ["Few buildings.", "Every floor known."],
  years: 15,
  phone: "+91 829 129 3889",
  phoneHref: "tel:+918291293889",
  email: "support@realdealhousing.com",
  address:
    "173/135 Ground Floor, Motilal Nagar, Near Post Office, Siddhart Nagar, Goregaon West, Mumbai 400104",
  areas: ["Goregaon", "Andheri", "Malad"],
  socials: {
    youtube: "https://www.youtube.com/@RealDealHousing",
    instagram: "https://www.instagram.com/realdealhousing_mumbai/",
    facebook: "https://www.facebook.com/realdealhousingpvtltd",
  },
  about:
    "At Real Deal Housing Pvt Ltd, we pride ourselves on expert market knowledge and personalised service to help you find your dream home. With 15 years in Mumbai's real estate market, we specialise in premium projects across Goregaon, Andheri, and Malad — a wide range of options for discerning buyers, from luxurious apartments to spacious family homes.",
};

/**
 * Map-hero buildings — the four focus towers. Coordinates: OSM/Nominatim where
 * verified; unverified ones carry coordsVerified=false and render a PIN_VERIFY
 * token until the operator confirms the pin. Future 5th pin: "Kalpataru Vial"
 * (operator to confirm exact name + location).
 */
export interface MapBuilding {
  slug: string;
  name: string;
  location: string;
  status: string;
  lat: number;
  lng: number;
  coordsVerified: boolean;
  facts: string[];
  href: string;
}

export const mapBuildings: MapBuilding[] = [
  {
    slug: "ekta-tripolis",
    name: "Ekta Tripolis",
    location: "Goregaon West",
    status: "Ready to move",
    // 8 Siddharth Nagar Rd, Motilal Nagar I — triangulated from operator's Google
    // Maps screenshot (2026-07-15), ±100m; operator to eyeball-confirm the pin.
    lat: 19.1544,
    lng: 72.8421,
    coordsVerified: false,
    facts: ["36 storeys × 3 towers", "2, 2.5 & 3 BHK · smart homes", "RERA-approved"],
    href: "/projects/ekta-tripolis",
  },
  {
    slug: "imperial-heights",
    name: "Imperial Heights",
    location: "Goregaon West",
    status: "Ready to move",
    lat: 19.15187,
    lng: 72.84022,
    coordsVerified: true,
    facts: ["44 storeys", "2–4.5 BHK · duplexes & penthouses", "Off Link Road"],
    href: "/projects/imperial-heights",
  },
  {
    slug: "kalpataru-radiance",
    name: "Kalpataru Radiance",
    location: "Goregaon West",
    status: "Ready to move",
    // Tower A, 60 Rd Number 13, Motilal Nagar I — OSM building footprint named
    // "Kalpataru Radiance", corroborated by operator's Google Maps screenshot (2026-07-15).
    lat: 19.15706,
    lng: 72.84116,
    coordsVerified: true,
    facts: ["4 towers · 4.2 acres", "2–4 BHK", "5 min to metro"],
    href: "/projects/kalpataru-radiance",
  },
  {
    slug: "dlf-westpark",
    name: "DLF Westpark",
    location: "Andheri West",
    status: "Now previewing",
    lat: 19.1298,
    lng: 72.8262,
    coordsVerified: false,
    facts: ["4 towers (T02–T05)", "3–5 BHK · duplexes & studios", "D.N. Nagar / Link Road"],
    href: "/dlf-westpark-andheri-west",
  },
];

/** YouTube walkthrough tours per building (channel: @RealDealHousing). */
export const buildingVideos: Record<string, { id: string; title: string }[]> = {
  "imperial-heights": [
    { id: "ZR0WXq_CQ4k", title: "Exclusive 4.5 BHK Fully Furnished Apartment for Sale — Home Tour" },
    { id: "IWDvHayCAUs", title: "Fully Furnished 2 BHK Duplex for Rent — Home Tour" },
  ],
  "ekta-tripolis": [
    { id: "-MOxDqpL-K0", title: "6.5 BHK Duplex Penthouse for Sale — Raw Apartment Tour" },
  ],
  "kalpataru-radiance": [
    { id: "FLVZh8LFrUM", title: "Luxurious 3 BHK Show Apartment — Complete House Tour" },
    { id: "H_c1resHf3I", title: "2 BHK Apartment for Sale — Amazing Mumbai City View" },
  ],
};

export interface ProjectImage {
  src: string; // static.wixstatic.com CDN URL (uploaded from RDH DATA 2024 archive)
  alt: string;
}

export interface Project {
  slug: string;
  name: string;
  location: string;
  meta: string;
  blurb: string;
  highlights: string[];
  isNew?: boolean;
  image?: ProjectImage;
  /** Long-form page copy (rewritten from the operator's live-site content). */
  description?: string[];
  /** e.g. "Ready to move" / "Possession by 2028" — as published on the live site. */
  status?: string;
  /** What the residences themselves offer — specs, layouts, finishes. */
  residences?: string[];
}

/** Wix CDN heroes — lineage lives in media_assets (wix_url, upload_status='wix_uploaded'). */
export const projectImages: Record<string, ProjectImage> = {
  "imperial-heights": {
    src: "https://static.wixstatic.com/media/77ab1a_2fe36223c0714ce1975be611cfec708a~mv2.jpg",
    alt: "Imperial Heights entrance plaza, Goregaon West",
  },
  "kalpataru-radiance": {
    src: "https://static.wixstatic.com/media/77ab1a_82e97de8f9e243159da10efe0c8ab6c1~mv2.jpg",
    alt: "Kalpataru Radiance towers with landscaped palms, Goregaon West",
  },
  "ekta-tripolis": {
    src: "https://static.wixstatic.com/media/77ab1a_2f1bc82a42644317b116066e8135f0e3~mv2.jpg",
    alt: "Ekta Tripolis three towers at night over the Goregaon West skyline",
  },
  "bharat-auravistas": {
    src: "https://static.wixstatic.com/media/44402a_f9cc55a06d81421ca2d3142f42d55b49~mv2.jpg",
    alt: "Bharat Auravistas tower render, Oshiwara Andheri West",
  },
  "bharat-auravistas-showflat": {
    src: "https://static.wixstatic.com/media/77ab1a_5c3ab8a816094afba95cdc259e796085~mv2.jpg",
    alt: "Bharat Auravistas show flat bedroom, Oshiwara Andheri West",
  },
  "dlf-westpark-andheri-west": {
    src: "https://static.wixstatic.com/media/77ab1a_eae74130f478465aabe8fa7061303407~mv2.jpg",
    alt: "DLF The Westpark towers, artist's impression, Andheri West",
  },
};

export const projects: Project[] = [
  {
    slug: "imperial-heights",
    status: "Ready to move",
    description: [
      "Imperial Heights sits just off Link Road in Goregaon West, behind the Goregaon bus depot — four 44-storey towers whose columnless apartments give every layout more usable space than the floor plan suggests. Homes range from 2 and 2.5 BHKs through 3, 3.5 and 4 BHK apartments to duplexes and penthouses, many with lavish balconies looking out over the Andheri–Versova skyline and the Madh–Marve creek.",
      "The address works as hard as the homes: SV Road and the Western Express Highway are minutes away, and the complex itself carries landscaped gardens, a residents' clubhouse, swimming pools, a tennis court, an amphitheatre and a 4-level podium car park with high-speed elevators and round-the-clock security.",
    ],
    residences: [
      "Interiors are finished to a consistent premium spec: imported marble flooring through the living, dining and bedrooms, gypsum-finished walls in low-VOC paint, laminate-finished doors, and smart lighting switches in the living areas and bedrooms. 3 BHKs add a servant's room with attached toilet.",
      "Kitchens come with granite flooring and platforms, a stainless-steel sink, exhaust and an enclosed utility balcony with PNG and heat detection. Master bathrooms are marble-clad with a rain shower and glass partition; every apartment gets a video door phone at the entrance.",
    ],
    image: projectImages["imperial-heights"],
    name: "Imperial Heights",
    location: "Goregaon West",
    meta: "44-storey tower · 2–4.5 BHK",
    blurb:
      "Welcome to Imperial Heights, where the finest flats for rent or sale in Mumbai meet unmatched luxury and style. Nestled in the heart of Goregaon West, this 44-storey tower offers expansive 2 BHK, 3 BHK, 3.5 BHK, and 4 BHK apartments, duplexes, and penthouses for those seeking the ultimate living experience.",
    highlights: ["44 storeys", "2–4.5 BHK + duplexes & penthouses", "Goregaon West"],
  },
  {
    slug: "kalpataru-radiance",
    status: "Ready to move",
    description: [
      "Kalpataru Radiance spreads four towers across 4.2 acres of landscaped grounds in Siddharth Nagar, Goregaon West — one of the few complexes in the area where open space, creek views and city skyline all belong to the same address. Apartments span 2, 2.5, 3 and 4 BHK configurations, each planned around light, ventilation and a clean separation of living and sleeping zones.",
      "Connectivity is the everyday advantage: the newly opened metro station is a five-minute walk, and the Western Express Highway, Link Road and SV Road are all within easy reach, alongside established schools and hospitals. Inside the gates, 15+ amenities include adult and children's swimming pools, a fully equipped clubhouse, tennis and badminton courts, an amphitheatre and five levels of secure parking.",
    ],
    residences: [
      "Every apartment opens through an entrance foyer into living and dining spaces floored in imported marble, with split ACs in the living room and bedrooms, smart lighting-scenario switches, and a video door phone at the entrance. 3 BHKs include a servant's room with attached toilet.",
      "Kitchens are granite-built with a service platform, enclosed utility balcony and PNG heat detection; master bathrooms carry imported marble to door height with a rain shower and glass partition, premium sanitaryware, and storage water heaters throughout.",
    ],
    image: projectImages["kalpataru-radiance"],
    name: "Kalpataru Radiance",
    location: "Goregaon West",
    meta: "4 towers · 4.2 acres · 2–4 BHK",
    blurb:
      "A luxurious residential complex nestled in the heart of Goregaon West. Spanning 4.2 acres of lush greenery, Kalpataru Radiance offers expansive open spaces, serene creek views, and a breathtaking cityscape. Just 5 minutes from the newly launched metro station, with exceptional connectivity to the Western Express Highway, Link Road, and SV Road. Four towers offer spacious 2, 2.5, 3, and 4 BHK apartments and 15+ luxurious amenities.",
    highlights: ["4 towers across 4.2 acres", "5 min from metro · WEH / Link Road / SV Road", "15+ amenities"],
  },
  {
    slug: "ekta-tripolis",
    status: "Ready to move",
    description: [
      "Ekta Tripolis is a trilogy — Skypolis, Caliopolis and Theopolis — of 36-storey residential towers in Goregaon West, built around the idea that a home should do some of the work for you. Apartments come with smart-home automation as standard, and the towers hold a Platinum green-building pre-certification that shows up in cooler interiors and lower running costs.",
      "The amenity set is led by an infinity pool, the Club Alpha fitness centre and a sky lounge, with 24-hour security and high-speed elevators underneath it all. For buyers and tenants who want a building with presence — the kind you can point out on the skyline — this is it.",
    ],
    residences: [
      "The 2, 2.5 and 3 BHK layouts are open-plan with contemporary interiors and premium finishes; master bedrooms carry ensuite bathrooms, and large balconies frame sweeping views across Goregaon's green belt.",
      "Modular kitchens with durable countertops and dedicated utility areas come fitted, and every home includes the automation layer — lighting, appliances and access controlled from a single interface — plus 24/7 power backup for the essentials.",
    ],
    image: projectImages["ekta-tripolis"],
    name: "Ekta Tripolis",
    location: "Goregaon West",
    meta: "36 storeys · Skypolis · Caliopolis · Theopolis",
    blurb:
      "A trilogy of indulgence — Skypolis, Caliopolis, and Theopolis — a collection of exquisite apartments crafted for those who demand the best. 36 residential storeys of glamour with state-of-the-art automated flats and uninterrupted views of clear skies and greenery. With the Holyfield Gym at your doorstep, a superior security system, and 24-hour guard, Ekta Tripolis is RERA-approved for total peace of mind.",
    highlights: ["36 residential storeys", "Holyfield Gym · 24-hour security", "RERA-approved"],
  },
  {
    slug: "bharat-auravistas",
    status: "Possession by 2028",
    description: [
      "Bharat Auravistas is a 36-storey new-build rising in Oshiwara, Andheri West, offering 3 BHK residences in three sizes — Luxe (1,140 sq ft), Grande (1,275 sq ft) and Royale (1,360 sq ft) — so buyers choose their space rather than settle for one floor plan. Large windows and unobstructed elevations give the homes long views over the city and the green pockets around Oshiwara.",
      "The location earns its price: the Western Express Highway, the metro and the upcoming Oshiwara railway station are all close, and the tower carries a fully equipped gym, landscaped swimming pool and residents' clubhouse. Developed by Bharat Infrastructure, with possession scheduled by 2028.",
    ],
    residences: [
      "All three configurations are 3 BHKs with open-plan living and dining areas that flow toward the window line, keeping the city view part of daily life rather than a balcony-only event.",
      "Finishes are contemporary and consistent across the line — the difference between Luxe, Grande and Royale is genuinely just space, which makes comparing them on a site visit unusually straightforward.",
    ],
    image: projectImages["bharat-auravistas"],
    name: "Bharat Auravistas",
    location: "Oshiwara, Andheri West",
    meta: "36-storey · 3 BHK · Luxe & Grande",
    blurb:
      "Located in the prime area of Oshiwara, Andheri West, Bharat Aura Vistas offers a stunning selection of 3 BHK residences that bring together contemporary luxury and thoughtfully designed spaces. This 36-storey high-rise presents two unique configurations — Luxe and Grande — allowing homeowners to choose the layout that suits them best.",
    highlights: ["36-storey high-rise", "3 BHK · Luxe & Grande layouts", "Oshiwara, Andheri West"],
  },
];

export { listings, type Listing } from "@/lib/listings";

export const pillars = [
  {
    title: "Buildings chosen, not aggregated",
    points: [
      "Handpicked for builder reputation and build quality",
      "Spacious apartments, generous common areas, well-run resident communities",
      "Minutes from the metro, Link Road and SV Road",
    ],
  },
  {
    title: "Every flat in our buildings",
    points: [
      "We track each building unit by unit — for sale, for rent, and quietly available",
      "If it's available in one of our four buildings, it's on our books",
      "More options in the same tower means the right layout at the right floor",
    ],
  },
  {
    title: "Negotiated end to end",
    points: [
      "We negotiate knowing the building's registration history, floor by floor",
      "Price and layout weighed against what comparable flats actually closed at",
      "Documentation handled for you, start to finish",
    ],
  },
];

export const testimonial = {
  quote:
    "Ms. Padmini Jain came to the forefront in lining up various apartments to choose from and helped me at each step until I registered my own apartment. They make sure tenants are duly researched and matched to my taste before arranging any meetings. I'm sure you'll be satisfied with their service.",
  author: "Dr. Gopal Kewalramani",
  role: "Physician — Andheri West",
};

export const siteFaqs = [
  { q: "What areas does Real Deal Housing operate in?", a: "We specialise across Mumbai's Western Suburbs — Goregaon, Andheri, and Malad — with deep expertise in premium buildings such as Imperial Heights, Ekta Tripolis, and Kalpataru Radiance." },
  { q: "What is the location of Kalpataru Radiance?", a: "Kalpataru Radiance is located in Siddharth Nagar, Goregaon West, Mumbai — an ideal choice for those searching for flats to buy or rent, just 5 minutes from the metro." },
  { q: "Is Kalpataru Radiance close to public transportation?", a: "Yes — it is roughly 5 minutes from the newly launched metro station, with exceptional connectivity to the Western Express Highway, Link Road, and SV Road." },
  { q: "What types of properties are available?", a: "2 BHK, 3 BHK, 3.5 BHK and 4 BHK apartments, duplexes and penthouses, for both sale and rent across our premium projects." },
  { q: "How can I schedule a property viewing?", a: `Call us on ${company.phone} or email ${company.email} and our team will arrange a viewing at a time that suits you.` },
];
