import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Wix Media Manager CDN — all CMS-served images resolve here.
    remotePatterns: [
      { protocol: "https", hostname: "static.wixstatic.com" },
      { protocol: "https", hostname: "i.ytimg.com" }, // YouTube walkthrough thumbnails
    ],
  },
  // Allow the dev server's HMR websocket + /_next/* resources to be requested from the
  // Tailscale hostname/IP, not just localhost. Without this, Next 16 blocks the cross-origin
  // HMR socket and client-side tab navigation (e.g. Unit registry) throws a websocket error.
  // ponytail: dev-only knob; harmless in prod. Add a host here if the tailnet name changes.
  allowedDevOrigins: [
    "hershs-macbook-air.tail4e34c2.ts.net",
    "*.tail4e34c2.ts.net",
    "100.113.36.7",
  ],
  // Old Wix-site URLs (from its sitemap, captured 2026-07-15) → new equivalents.
  // Ambiguous old slugs map to the closest current listing.
  async redirects() {
    const listingMap: Record<string, string> = {
      "bharat-auravistas---3-bhk-apartment-for-sale": "bharat-auravistas-royale-3-bhk-for-sale",
      "bharat-auravistas---grande-3-bhk-apartment-for-sale": "bharat-auravistas-grande-3-bhk-for-sale",
      "bharat-auravistas---luxe-3-bhk-apartment-for-sale": "bharat-auravistas-luxe-3-bhk-for-sale",
      "imperial-heights---3.5-bhk-apartment-for-sale-": "imperial-heights-3-5-bhk-high-floor-for-sale",
      "imperial-heights---3.5-bhk-apartment-for-sale": "imperial-heights-3-5-bhk-1434-sqft-for-sale",
      "imperial-heights---4.5-bhk-fully-furnished-apartment-for-rent": "imperial-heights-4-5-bhk-furnished-for-rent",
      "exclusive-3.5-bhk-apartment-for-sale-in-imperial-heights-goregaon-west": "exclusive-3-5-bhk-imperial-heights-goregaon-west",
      "3.5-bhk-apartment-for-sale-in-imperial-heights": "imperial-heights-3-5-bhk-furnished-for-sale",
      "imperial-heights---2.5-bhk-apartment-for-sale": "imperial-heights-2-5-bhk-1025-sqft-for-sale",
      "imperial-heights---3-bhk-apartment-for-sale": "imperial-heights-3-bhk-1267-sqft-for-sale",
      "imperial-heights---luxurious-3.5-bhk-apartment-for-sale": "imperial-heights-luxurious-3-5-bhk-for-sale",
      "4.5-bhk-apartment-for-sale-in-imperial-heights-goregaon-west": "imperial-heights-4-5-bhk-1893-sqft-for-sale",
      "imperial-heights---2-bhk-duplex-for-sale": "imperial-heights-2-bhk-duplex-for-sale",
      "imperial-heights---2-bhk-duplex-for-rent": "imperial-heights-2-bhk-duplex-for-rent",
      "ekta-tripolis---2.5-bhk-apartment-for-sale": "ekta-tripolis-2-5-bhk-for-sale",
      "ekta-tripolis---2.5-bhk-apartment-for-rent": "ekta-tripolis-2-5-bhk-for-rent",
      "kalpataru-radiance---3-bhk-apartment-for-sale": "kalpataru-radiance-3-bhk-c-wing-for-sale",
      "kalpataru-radiance---2-bhk-apartment-for-sale": "kalpataru-radiance-2-bhk-a-wing-for-sale",
      "kalpataru-radiance---3-bhk-apartment-for-rent": "kalpataru-radiance-3-bhk-for-rent",
    };
    const projectMap: Record<string, string> = {
      "bharat-auravistas---andheri-west": "bharat-auravistas",
      "imperial-heights---goregaon-west": "imperial-heights",
      "ekta-tripolis---goregaon-west": "ekta-tripolis",
      "kalpataru-radiance---goregaon-west": "kalpataru-radiance",
    };
    return [
      ...Object.entries(listingMap).map(([from, to]) => ({
        source: `/listings/${from}`,
        destination: `/listings/${to}`,
        permanent: true,
      })),
      ...Object.entries(projectMap).map(([from, to]) => ({
        source: `/projects-1/${from}`,
        destination: `/projects/${to}`,
        permanent: true,
      })),
      // Any other old dynamic-page URL falls back to the section index.
      { source: "/projects-1/:path*", destination: "/projects", permanent: true },
      // No listings index page exists; /buy is the de-facto catalogue.
      { source: "/listings", destination: "/buy", permanent: true },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
