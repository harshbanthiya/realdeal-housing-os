import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

// Flipped to index 2026-07-14 (operator-approved, realdealhousing.com live on
// Vercel). Cockpit/API stay disallowed; layout robots flag flipped together.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/cockpit", "/api/"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
