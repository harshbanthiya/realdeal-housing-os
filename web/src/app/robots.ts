import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

// Mirrors the root-layout `robots: noindex` flag: everything stays disallowed
// until the operator approves indexing at launch. Flip both together.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", disallow: "/" },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
