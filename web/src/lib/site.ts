/**
 * Real Deal Housing - company + catalogue content.
 *
 * Content reproduced from the live site realdealhousing.com (the operator's own
 * site), restyled into the Gallery White aesthetic. The live site was read-only;
 * nothing there was modified. Prices/areas are shown as captured.
 */

export const company = {
  name: "Real Deal Housing",
  legalName: "Real Deal Housing Private Limited",
  tagline: "Your Future Home Is Right Here",
  years: 15,
  phone: "+91 829 129 3889",
  phoneHref: "tel:+918291293889",
  email: "support@realdealhousing.com",
  address:
    "173/135 Ground Floor, Motilal Nagar, Near Post Office, Siddhart Nagar, Goregaon West, Mumbai 400104",
  areas: ["Goregaon", "Andheri", "Malad"],
  about:
    "At Real Deal Housing Pvt Ltd, we pride ourselves on expert market knowledge and personalised service to help you find your dream home. With 15 years in Mumbai's real estate market, we specialise in premium projects across Goregaon, Andheri, and Malad - a wide range of options for discerning buyers, from luxurious apartments to spacious family homes.",
};

export interface Project {
  slug: string;
  name: string;
  location: string;
  meta: string;
  blurb: string;
  highlights: string[];
  isNew?: boolean;
}

export const projects: Project[] = [
  {
    slug: "imperial-heights",
    name: "Imperial Heights",
    location: "Goregaon West",
    meta: "44-storey tower · 2-4.5 BHK",
    blurb:
      "Welcome to Imperial Heights, where the finest flats for rent or sale in Mumbai meet unmatched luxury and style. Nestled in the heart of Goregaon West, this 44-storey tower offers expansive 2 BHK, 3 BHK, 3.5 BHK, and 4 BHK apartments, duplexes, and penthouses for those seeking the ultimate living experience.",
    highlights: ["44 storeys", "2-4.5 BHK + duplexes & penthouses", "Goregaon West"],
  },
  {
    slug: "kalpataru-radiance",
    name: "Kalpataru Radiance",
    location: "Goregaon West",
    meta: "4 towers · 4.2 acres · 2-4 BHK",
    blurb:
      "A luxurious residential complex nestled in the heart of Goregaon West. Spanning 4.2 acres of lush greenery, Kalpataru Radiance offers expansive open spaces, serene creek views, and a breathtaking cityscape. Just 5 minutes from the newly launched metro station, with exceptional connectivity to the Western Express Highway, Link Road, and SV Road. Four towers offer spacious 2, 2.5, 3, and 4 BHK apartments and 15+ luxurious amenities.",
    highlights: ["4 towers across 4.2 acres", "5 min from metro · WEH / Link Road / SV Road", "15+ amenities"],
  },
  {
    slug: "ekta-tripolis",
    name: "Ekta Tripolis",
    location: "Goregaon West",
    meta: "36 storeys · Skypolis · Caliopolis · Theopolis",
    blurb:
      "A trilogy of indulgence - Skypolis, Caliopolis, and Theopolis - a collection of exquisite apartments crafted for those who demand the best. 36 residential storeys of glamour with state-of-the-art automated flats and uninterrupted views of clear skies and greenery. With the Holyfield Gym at your doorstep, a superior security system, and 24-hour guard, Ekta Tripolis is RERA-approved for total peace of mind.",
    highlights: ["36 residential storeys", "Holyfield Gym · 24-hour security", "RERA-approved"],
  },
  {
    slug: "bharat-auravistas",
    name: "Bharat Auravistas",
    location: "Oshiwara, Andheri West",
    meta: "36-storey · 3 BHK · Luxe & Grande",
    blurb:
      "Located in the prime area of Oshiwara, Andheri West, Bharat Aura Vistas offers a stunning selection of 3 BHK residences that bring together contemporary luxury and thoughtfully designed spaces. This 36-storey high-rise presents two unique configurations - Luxe and Grande - allowing homeowners to choose the layout that suits them best.",
    highlights: ["36-storey high-rise", "3 BHK · Luxe & Grande layouts", "Oshiwara, Andheri West"],
  },
];

export interface Listing {
  title: string;
  project: string;
  location: string;
  config: string;
  sqft: string;
  price: string;
  type: "sale" | "rent";
}

export const listings: Listing[] = [
  // For sale
  { title: "Bharat Auravistas - Luxe 3 BHK", project: "Bharat Auravistas", location: "Andheri West", config: "3 BHK", sqft: "1140", price: "₹4,59,00,000", type: "sale" },
  { title: "Exclusive 3.5 BHK - Imperial Heights", project: "Imperial Heights", location: "Goregaon West", config: "3.5 BHK", sqft: "1409", price: "₹5,25,00,000", type: "sale" },
  { title: "Imperial Heights - 3.5 BHK", project: "Imperial Heights", location: "Goregaon West", config: "3.5 BHK", sqft: "1445", price: "₹4,50,00,000", type: "sale" },
  { title: "Kalpataru Radiance - 3 BHK", project: "Kalpataru Radiance", location: "Goregaon West", config: "3 BHK", sqft: "1033", price: "₹3,75,00,000", type: "sale" },
  { title: "Ekta Tripolis - 2.5 BHK", project: "Ekta Tripolis", location: "Goregaon West", config: "2.5 BHK", sqft: " - ", price: "On request", type: "sale" },
  { title: "Kalpataru Radiance - 2 BHK", project: "Kalpataru Radiance", location: "Goregaon West", config: "2 BHK", sqft: " - ", price: "On request", type: "sale" },
  // For rent
  { title: "Imperial Heights - 4.5 BHK Fully Furnished", project: "Imperial Heights", location: "Goregaon West", config: "4.5 BHK", sqft: "1893", price: "₹2,00,000 / mo", type: "rent" },
  { title: "Kalpataru Radiance - 3 BHK", project: "Kalpataru Radiance", location: "Goregaon West", config: "3 BHK", sqft: "1017", price: "₹1,10,000 / mo", type: "rent" },
  { title: "Ekta Tripolis - 2.5 BHK", project: "Ekta Tripolis", location: "Goregaon West", config: "2.5 BHK", sqft: "908", price: "₹90,000 / mo", type: "rent" },
  { title: "Imperial Heights - 2 BHK Duplex", project: "Imperial Heights", location: "Goregaon West", config: "2 BHK Duplex", sqft: "727", price: "₹85,000 / mo", type: "rent" },
];

export const pillars = [
  {
    title: "Truly Modern Buildings",
    points: [
      "Handpicked for builder reputation and credibility",
      "Spacious apartments and common areas",
      "Prime locations and proximity",
      "Top-notch modern amenities",
      "Vibrant resident communities",
    ],
  },
  {
    title: "All Apartments on Offer",
    points: [
      "Our dedicated team continually finds apartments for rent or sale",
      "If it's on the market, we have it",
      "Maximum choices for better negotiation and ideal layouts",
    ],
  },
  {
    title: "Best Deals for You",
    points: [
      "Negotiating the lowest prices and best layouts",
      "Maximum negotiation room across floors and layouts",
      "Relax and let us handle the documentation",
    ],
  },
];

export const testimonial = {
  quote:
    "Ms. Padmini Jain lined up apartment after apartment and stayed with me right through to registration. Every tenant is researched and matched to your taste before a single meeting.",
  author: "Dr. Gopal Kewalramani",
  role: "Physician - Andheri West",
};

export const siteFaqs = [
  { q: "What areas does Real Deal Housing operate in?", a: "We specialise across Mumbai's Western Suburbs - Goregaon, Andheri, and Malad - with deep expertise in premium buildings such as Imperial Heights, Ekta Tripolis, and Kalpataru Radiance." },
  { q: "What is the location of Kalpataru Radiance?", a: "Kalpataru Radiance is located in Siddharth Nagar, Goregaon West, Mumbai - an ideal choice for those searching for flats to buy or rent, just 5 minutes from the metro." },
  { q: "Is Kalpataru Radiance close to public transportation?", a: "Yes - it is roughly 5 minutes from the newly launched metro station, with exceptional connectivity to the Western Express Highway, Link Road, and SV Road." },
  { q: "What types of properties are available?", a: "2 BHK, 3 BHK, 3.5 BHK and 4 BHK apartments, duplexes and penthouses, for both sale and rent across our premium projects." },
  { q: "How can I schedule a property viewing?", a: `Call us on ${company.phone} or email ${company.email} and our team will arrange a viewing at a time that suits you.` },
];
