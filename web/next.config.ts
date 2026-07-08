import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Wix Media Manager CDN — all CMS-served images resolve here.
    remotePatterns: [{ protocol: "https", hostname: "static.wixstatic.com" }],
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
};

export default nextConfig;
