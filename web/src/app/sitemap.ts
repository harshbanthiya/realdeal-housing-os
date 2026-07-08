import type { MetadataRoute } from "next";
import { getProjects, getBlogPosts } from "@/lib/cms";
import { SITE_URL } from "@/lib/seo";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [projects, posts] = await Promise.all([getProjects(), getBlogPosts()]);
  const staticPaths = ["", "/projects", "/buy", "/rent", "/sell", "/blog", "/about", "/faq", "/contact"];
  return [
    ...staticPaths.map((p) => ({ url: `${SITE_URL}${p}`, changeFrequency: "weekly" as const })),
    ...projects.map((p) => ({ url: `${SITE_URL}/projects/${p.slug}`, changeFrequency: "weekly" as const })),
    ...posts.map((p) => ({
      url: `${SITE_URL}/blog/${p.slug}`,
      lastModified: p.publishedAt || undefined,
      changeFrequency: "monthly" as const,
    })),
  ];
}
