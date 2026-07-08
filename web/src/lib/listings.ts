/**
 * Listings catalogue — mirrored from the live realdealhousing.com Wix CMS
 * (Listings collection, read-only) on 2026-07-08. Facts (price, carpet area,
 * config, facing, baths, parking) are as published there; descriptions are
 * rewritten for this site, not copied. Images are the operator's own photos,
 * already hosted on the Wix CDN.
 */
import type { ProjectImage } from "@/lib/site";

export interface Listing {
  slug: string;
  title: string;
  project: string;
  location: string;
  config: string;
  sqft: string;
  price: string;
  type: "sale" | "rent";
  description: string[];
  image?: ProjectImage;
  featured?: boolean;
}

const img = (id: string, alt: string): ProjectImage => ({
  src: `https://static.wixstatic.com/media/${id}`,
  alt,
});

export const listings: Listing[] = [
  // ——— Imperial Heights, Goregaon West ———
  {
    slug: "imperial-heights-4-5-bhk-1893-sqft-for-sale",
    title: "4.5 BHK Apartment for Sale in Imperial Heights",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "4.5 BHK",
    sqft: "1893",
    price: "₹6,75,00,000",
    type: "sale",
    featured: true,
    image: img("44402a_6d73acbc536c4bf28f550445b38a901d~mv2.jpg", "Living space of a 4.5 BHK apartment in Imperial Heights, Goregaon West"),
    description: [
      "The largest family home currently on offer in Imperial Heights: 1,893 sq ft of carpet area on a higher floor of the 44-storey tower, with five bathrooms and long westward views towards the Versova and Madh–Marve creek belt.",
      "Imported marble flooring runs through the living, dining and bedrooms, and the columnless layout gives you unusually flexible furniture placement for an apartment of this size. A serious option for buyers who want space in Goregaon West without moving to a bungalow.",
    ],
  },
  {
    slug: "exclusive-3-5-bhk-imperial-heights-goregaon-west",
    title: "Exclusive 3.5 BHK in Imperial Heights — 1,409 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "3.5 BHK",
    sqft: "1409",
    price: "₹5,25,00,000",
    type: "sale",
    featured: true,
    image: img("44402a_f6885cdd2c154167a3e0b11a41da9f96~mv2.jpg", "Interior of an exclusive 3.5 BHK apartment in Imperial Heights"),
    description: [
      "An east–west facing 3.5 BHK with 1,409 sq ft of carpet area, four bathrooms and two dedicated car parks — a combination that rarely stays on the market long in this tower.",
      "The east–west orientation keeps the apartment bright through the day with genuine cross-ventilation, and the half-room works equally well as a study, staff room or walk-in wardrobe.",
    ],
  },
  {
    slug: "imperial-heights-3-5-bhk-1434-sqft-for-sale",
    title: "3.5 BHK Apartment for Sale in Imperial Heights — 1,434 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "3.5 BHK",
    sqft: "1434",
    price: "₹4,75,00,000",
    type: "sale",
    image: img("44402a_a9409d659f354c93b1683038d313cad1~mv2.jpg", "Bedroom in a 3.5 BHK apartment in Imperial Heights, Goregaon West"),
    description: [
      "A generously planned 3.5 BHK spanning 1,434 sq ft with four bathrooms and two car parks, in one of Goregaon West's most established 44-storey addresses.",
      "The layout separates the living zone cleanly from the bedroom wing, so families get privacy without sacrificing the open feel that Imperial Heights' columnless design is known for.",
    ],
  },
  {
    slug: "imperial-heights-luxurious-3-5-bhk-for-sale",
    title: "High-Floor 3.5 BHK in Imperial Heights — 1,434 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "3.5 BHK",
    sqft: "1434",
    price: "₹4,50,00,000",
    type: "sale",
    featured: true,
    image: img("44402a_0a7de425bd5b4611a788f311fab89dd5~mv2.jpg", "High-floor 3.5 BHK interior in Imperial Heights"),
    description: [
      "A north–south facing 3.5 BHK on a higher floor — 1,434 sq ft, four bathrooms, two car parks, and the elevated outlook that makes the top third of this tower the most requested.",
      "North–south orientation means comfortable light without the late-afternoon heat, and the higher elevation keeps the apartment quiet despite the Link Road connectivity below.",
    ],
  },
  {
    slug: "imperial-heights-3-5-bhk-high-floor-for-sale",
    title: "3.5 BHK Apartment for Sale in Imperial Heights — 1,445 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "3.5 BHK",
    sqft: "1445",
    price: "₹4,50,00,000",
    type: "sale",
    featured: true,
    image: img("44402a_262037f9bee34e538d1d6f5fd026a980~mv2.jpg", "Living room of a high-floor 3.5 BHK in Imperial Heights"),
    description: [
      "1,445 sq ft of carpet area on one of the higher floors of the 44-storey tower — among the largest 3.5 BHK footprints in Imperial Heights.",
      "The extra floor height buys you bigger views and quieter rooms; the extra carpet area buys a wider living-dining span than the standard stack. Worth comparing side by side with the other 3.5 BHKs we hold in this building.",
    ],
  },
  {
    slug: "imperial-heights-3-5-bhk-furnished-for-sale",
    title: "Fully Furnished 3.5 BHK in Imperial Heights — 1,445 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "3.5 BHK",
    sqft: "1445",
    price: "₹4,20,00,000",
    type: "sale",
    image: img("44402a_0665cd0e954543bb866767bee54c3692~mv2.jpg", "Furnished 3.5 BHK apartment in Imperial Heights, Goregaon West"),
    description: [
      "A fully furnished 3.5 BHK at 1,445 sq ft — move-in ready, with three spacious bedrooms plus the flexible half-room, priced sharper than comparable bare-shell units in the tower.",
      "For buyers who want to skip a year of fit-out, this is the practical route into Imperial Heights: the furniture and finishing work is already done, and the building's clubhouse, pools and podium parking come with it.",
    ],
  },
  {
    slug: "imperial-heights-3-bhk-1267-sqft-for-sale",
    title: "3 BHK Apartment for Sale in Imperial Heights — 1,267 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "3 BHK",
    sqft: "1267",
    price: "₹3,80,00,000",
    type: "sale",
    image: img("44402a_74950341ecbc48dda462251ad81a3612~mv2.jpg", "3 BHK apartment interior in Imperial Heights"),
    description: [
      "A full 3 BHK at 1,267 sq ft on a lower floor — the value pick among the three-bedroom stacks, with the same imported marble flooring and building amenities as the high-floor units.",
      "Lower floors in Imperial Heights suit buyers who prioritise quick lift access and a garden-side outlook over skyline views, typically at a meaningful discount per square foot.",
    ],
  },
  {
    slug: "imperial-heights-2-5-bhk-1025-sqft-for-sale",
    title: "2.5 BHK Apartment for Sale in Imperial Heights — 1,025 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "2.5 BHK",
    sqft: "1025",
    price: "₹3,50,00,000",
    type: "sale",
    image: img("44402a_c847aa5a63664f5d9aac22a36b4070f0~mv2.jpg", "2.5 BHK apartment in Imperial Heights, Goregaon West"),
    description: [
      "An east–west facing 2.5 BHK with 1,025 sq ft of carpet area, two bathrooms and a dedicated car park — a well-proportioned first step into a 44-storey landmark building.",
      "The half-room is the quiet advantage here: a home office or nursery you don't get in a standard 2 BHK, at a price still well under the tower's three-bedroom stacks.",
    ],
  },
  {
    slug: "imperial-heights-2-5-bhk-1042-sqft-for-sale",
    title: "2.5 BHK Apartment for Sale in Imperial Heights — 1,042 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "2.5 BHK",
    sqft: "1042",
    price: "₹3,35,00,000",
    type: "sale",
    featured: true,
    image: img("44402a_35e5ed4494754d4891e35951c9d76f50~mv2.jpg", "Bright 2.5 BHK apartment in Imperial Heights"),
    description: [
      "The keenest-priced 2.5 BHK we currently hold in Imperial Heights: 1,042 sq ft of carpet area in one of Goregaon West's most sought-after residential complexes.",
      "Slightly larger and slightly cheaper than the comparable stack — which is exactly the kind of spread our team negotiates for. Ask us to walk you through both units before you decide.",
    ],
  },
  {
    slug: "imperial-heights-2-bhk-duplex-for-sale",
    title: "2 BHK Duplex for Sale in Imperial Heights — 667 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "2 BHK Duplex",
    sqft: "667",
    price: "₹2,70,00,000",
    type: "sale",
    image: img("44402a_3002c074068d4f73aaa9fb9ab7d59cf9~mv2.jpg", "Compact duplex apartment in Imperial Heights"),
    description: [
      "A rare compact duplex: 667 sq ft over two levels on a higher floor, with one bathroom and a dedicated car park — the most affordable way to own in Imperial Heights.",
      "Duplex living at this size works beautifully for singles and couples: sleeping upstairs, living and entertaining downstairs, and a full 44-storey tower of amenities outside your door.",
    ],
  },
  {
    slug: "imperial-heights-4-5-bhk-furnished-for-rent",
    title: "Fully Furnished 4.5 BHK for Rent in Imperial Heights",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "4.5 BHK",
    sqft: "1893",
    price: "₹2,00,000 / mo",
    type: "rent",
    image: img("44402a_7204a096986b4216835d35124a263e81~mv2.jpg", "Furnished 4.5 BHK rental apartment in Imperial Heights"),
    description: [
      "1,893 sq ft, fully furnished, five bathrooms — the flagship rental in Imperial Heights for families who want to arrive with suitcases and nothing else.",
      "At ₹2,00,000 a month you get one of the largest layouts in the building plus the clubhouse, pools, tennis court and 24/7 security that come with it. Corporate leases welcome.",
    ],
  },
  {
    slug: "imperial-heights-2-bhk-duplex-for-rent",
    title: "2 BHK Duplex for Rent in Imperial Heights — 727 sq ft",
    project: "Imperial Heights",
    location: "Goregaon West",
    config: "2 BHK Duplex",
    sqft: "727",
    price: "₹85,000 / mo",
    type: "rent",
    featured: true,
    image: img("44402a_281c192f5a3f42f0af5e6278adee809b~mv2.jpg", "Duplex rental apartment in Imperial Heights, Goregaon West"),
    description: [
      "A higher-floor 2 BHK duplex at 727 sq ft with two bathrooms and a dedicated car park — a genuinely different rental from the standard flat format at this budget.",
      "Two levels give you separation between work and rest that no single-floor 2 BHK can match, and the elevated position in the 44-storey tower keeps light and views generous.",
    ],
  },

  // ——— Kalpataru Radiance, Goregaon West ———
  {
    slug: "kalpataru-radiance-3-bhk-c-wing-for-sale",
    title: "3 BHK in Kalpataru Radiance C Wing — 1,318 sq ft",
    project: "Kalpataru Radiance",
    location: "Goregaon West",
    config: "3 BHK",
    sqft: "1318",
    price: "₹4,75,00,000",
    type: "sale",
    image: img("44402a_b67ef72eda094732a59009a4ac26df3f~mv2.jpg", "Spacious 3 BHK apartment in Kalpataru Radiance C Wing"),
    description: [
      "The largest 3 BHK we hold in Kalpataru Radiance: 1,318 sq ft of carpet area in the C Wing, north–south facing, with a dedicated car park.",
      "Set within 4.2 acres of landscaped grounds five minutes from the metro, this is the configuration for buyers who want Kalpataru build quality — imported marble, smart switches, creek-side outlook — without compromising on room sizes.",
    ],
  },
  {
    slug: "kalpataru-radiance-3-bhk-1035-sqft-for-sale",
    title: "3 BHK Apartment for Sale in Kalpataru Radiance — ₹3.80 Cr",
    project: "Kalpataru Radiance",
    location: "Goregaon West",
    config: "3 BHK",
    sqft: "1035",
    price: "₹3,80,00,000",
    type: "sale",
    image: img("44402a_27d845e06b6d4f4ca80690e3707c456e~mv2.jpg", "3 BHK apartment interior in Kalpataru Radiance"),
    description: [
      "A north–south facing 3 BHK with a dedicated car park, planned for efficient space use — every square foot of the 1,035 sq ft carpet area does a job.",
      "The orientation delivers steady natural light and cross-ventilation through the day, and the complex's 15+ amenities — pools, clubhouse, five levels of secure parking — are included in the deal.",
    ],
  },
  {
    slug: "kalpataru-radiance-3-bhk-1033-sqft-for-sale",
    title: "3 BHK Apartment for Sale in Kalpataru Radiance — 1,033 sq ft",
    project: "Kalpataru Radiance",
    location: "Goregaon West",
    config: "3 BHK",
    sqft: "1033",
    price: "₹3,75,00,000",
    type: "sale",
    featured: true,
    image: img("44402a_4249569c612241b18dc1d2251ea57216~mv2.jpg", "North-south facing 3 BHK in Kalpataru Radiance"),
    description: [
      "A north–south facing 3 BHK at 1,033 sq ft — bright, cool and quietly one of the best-value three-bedroom entries into Kalpataru Radiance right now.",
      "You're five minutes from the metro and connected to the Western Express Highway, Link Road and SV Road, inside a four-tower complex whose creek views and open space are hard to replicate in Goregaon West.",
    ],
  },
  {
    slug: "kalpataru-radiance-3-bhk-1017-sqft-for-sale",
    title: "3 BHK Apartment for Sale in Kalpataru Radiance — 1,017 sq ft",
    project: "Kalpataru Radiance",
    location: "Goregaon West",
    config: "3 BHK",
    sqft: "1017",
    price: "₹3,60,00,000",
    type: "sale",
    image: img("44402a_7ec513c51e864c2dbf6822de6720b4e3~mv2.jpg", "East-west facing 3 BHK in Kalpataru Radiance"),
    description: [
      "An east–west facing 3 BHK at 1,017 sq ft — the most accessible three-bedroom price point in the complex as of this listing.",
      "Morning light in the bedrooms, evening light in the living room, and the full Kalpataru Radiance amenity set outside: swimming pools, clubhouse, tennis and badminton courts, and an amphitheatre in 4.2 acres of greenery.",
    ],
  },
  {
    slug: "kalpataru-radiance-2-bhk-a-wing-for-sale",
    title: "2 BHK in Kalpataru Radiance A Wing — 861 sq ft",
    project: "Kalpataru Radiance",
    location: "Goregaon West",
    config: "2 BHK",
    sqft: "861",
    price: "₹3,25,00,000",
    type: "sale",
    image: img("44402a_1929ecc865a848abadcf4b78963dc2f3~mv2.jpg", "2 BHK apartment in Kalpataru Radiance A Wing"),
    description: [
      "A north–south facing 2 BHK in the A Wing with 861 sq ft of carpet area and a dedicated parking spot — the cleanest entry point into Kalpataru Radiance ownership.",
      "The A Wing's orientation gives all-day light without harsh western sun, and you inherit the complex's full amenity deck and five-minute metro walk from day one.",
    ],
  },
  {
    slug: "kalpataru-radiance-3-bhk-for-rent",
    title: "Semi-Furnished 3 BHK for Rent in Kalpataru Radiance",
    project: "Kalpataru Radiance",
    location: "Goregaon West",
    config: "3 BHK",
    sqft: "1017",
    price: "₹1,10,000 / mo",
    type: "rent",
    image: img("44402a_3a7328fd5d6a4e779056a76733a0e5f2~mv2.jpg", "Semi-furnished 3 BHK rental in Kalpataru Radiance"),
    description: [
      "A semi-furnished, east–west facing 3 BHK at 1,017 sq ft with a dedicated car park — ready for a quick move with room to make it your own.",
      "Renting here buys the whole Kalpataru Radiance lifestyle: pools for adults and children, a fully equipped clubhouse, landscaped grounds, and metro connectivity that makes the daily commute genuinely easy.",
    ],
  },

  // ——— Ekta Tripolis, Goregaon West ———
  {
    slug: "ekta-tripolis-2-5-bhk-for-sale",
    title: "2.5 BHK Apartment for Sale in Ekta Tripolis — 908 sq ft",
    project: "Ekta Tripolis",
    location: "Goregaon West",
    config: "2.5 BHK",
    sqft: "908",
    price: "₹2,90,00,000",
    type: "sale",
    image: img("44402a_b34a821db19745ebb562880cbdf3e2ba~mv2.jpg", "2.5 BHK apartment in Ekta Tripolis, Goregaon West"),
    description: [
      "A north–south facing 2.5 BHK at 908 sq ft with two bathrooms and a car park, inside the Platinum pre-certified green towers of Ekta Tripolis.",
      "The trilogy — Skypolis, Caliopolis, Theopolis — pairs home automation with an infinity pool, Club Alpha fitness centre and sky lounge. This unit is the most affordable current route in.",
    ],
  },
  {
    slug: "ekta-tripolis-2-5-bhk-for-rent",
    title: "2.5 BHK Apartment for Rent in Ekta Tripolis — 908 sq ft",
    project: "Ekta Tripolis",
    location: "Goregaon West",
    config: "2.5 BHK",
    sqft: "908",
    price: "₹90,000 / mo",
    type: "rent",
    image: img("44402a_7723c6f1712f48a9b70263762a4ed57c~mv2.jpg", "2.5 BHK rental apartment in Ekta Tripolis"),
    description: [
      "Rent inside one of Goregaon West's signature towers: a 908 sq ft 2.5 BHK in Ekta Tripolis at ₹90,000 a month.",
      "Automated-home features, the infinity pool and a serious gym come standard with the address — as does the green-certified build quality that keeps interiors cooler and utility bills saner.",
    ],
  },

  // ——— Bharat Auravistas, Oshiwara, Andheri West ———
  {
    slug: "bharat-auravistas-royale-3-bhk-for-sale",
    title: "Royale 3 BHK in Bharat Auravistas — 1,360 sq ft",
    project: "Bharat Auravistas",
    location: "Andheri West",
    config: "3 BHK",
    sqft: "1360",
    price: "₹6,12,00,000 ++",
    type: "sale",
    image: img("44402a_6bd91e9a94a94ea78e3652371cd4d6f2~mv2.jpg", "Royale 3 BHK residence at Bharat Auravistas, Oshiwara"),
    description: [
      "The Royale is the largest of the three Auravistas configurations: 1,360 sq ft of carpet area with an open, light-filled layout and unobstructed city-and-greenery views from the living room.",
      "Three well-proportioned bedrooms and high-spec finishes make this the pick for buyers who want new-build Andheri West space at its most generous. Possession by 2028.",
    ],
  },
  {
    slug: "bharat-auravistas-grande-3-bhk-for-sale",
    title: "Grande 3 BHK in Bharat Auravistas — 1,275 sq ft",
    project: "Bharat Auravistas",
    location: "Andheri West",
    config: "3 BHK",
    sqft: "1275",
    price: "₹5,15,00,000",
    type: "sale",
    image: img("44402a_8605a36c0df3498cbf3473f186021fcd~mv2.jpg", "Grande 3 BHK residence at Bharat Auravistas"),
    description: [
      "The middle of the three Auravistas layouts: a 1,275 sq ft Grande 3 BHK balancing expansive living space against the sharper price of the Luxe.",
      "Large windows on the high floors of this 36-storey Oshiwara tower keep every room bright, with the Western Express Highway, metro and upcoming Oshiwara station minutes away.",
    ],
  },
  {
    slug: "bharat-auravistas-luxe-3-bhk-for-sale",
    title: "Luxe 3 BHK in Bharat Auravistas — 1,140 sq ft",
    project: "Bharat Auravistas",
    location: "Andheri West",
    config: "3 BHK",
    sqft: "1140",
    price: "₹4,59,00,000 ++",
    type: "sale",
    featured: true,
    image: img("44402a_b57318ddda1144c28716f295745c6810~mv2.jpg", "Luxe 3 BHK residence at Bharat Auravistas, Andheri West"),
    description: [
      "The entry point to Bharat Auravistas: a 1,140 sq ft Luxe 3 BHK that packs three bedrooms, open-plan living and unobstructed views into the sharpest price in the tower.",
      "For under-construction buyers, the arithmetic is simple — a new 3 BHK in Oshiwara, Andheri West with gym, pool and clubhouse, at a price several established towers charge for a 2.5 BHK. Possession by 2028.",
    ],
  },
];
