import { company } from "@/lib/site";

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");

/** Organization structured data for the (site) layout. */
export const orgJsonLd = {
  "@context": "https://schema.org",
  "@type": "RealEstateAgent",
  name: company.name,
  legalName: company.legalName,
  telephone: company.phone,
  email: company.email,
  url: SITE_URL,
  address: {
    "@type": "PostalAddress",
    streetAddress: company.address,
    addressLocality: "Mumbai",
    addressRegion: "MH",
    addressCountry: "IN",
  },
  areaServed: company.areas.map((a) => ({ "@type": "Place", name: `${a}, Mumbai` })),
  sameAs: Object.values(company.socials),
};
