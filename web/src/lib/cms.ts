/**
 * CMS adapter — the single boundary between the site and Wix headless CMS.
 *
 * Without WIX_CLIENT_ID (Wix dashboard → Settings → Headless → OAuth apps),
 * every getter serves the local fixtures in site.ts/content.ts, so the site
 * builds and deploys with zero Wix dependency. With it, reads go to the Wix
 * Test-site collections server-side (never client-side) and fall back to
 * fixtures on any error.
 *
 * Collections expected on the Wix site:
 *   Projects, ProjectFacts, Residences, Amenities, ProjectFAQs, BlogPosts
 */
import { projects as fixtureProjects, type Project } from "@/lib/site";

export interface BlogPost {
  slug: string;
  title: string;
  excerpt: string;
  body: string; // rich text / HTML from Wix
  heroImageUrl: string | null; // static.wixstatic.com CDN URL
  tags: string[];
  publishedAt: string; // ISO date
  seoTitle: string;
  seoDescription: string;
}

const WIX_CLIENT_ID = process.env.WIX_CLIENT_ID;

async function queryWix<T>(collectionId: string, map: (item: Record<string, unknown>) => T): Promise<T[] | null> {
  if (!WIX_CLIENT_ID) return null;
  try {
    const [{ createClient, OAuthStrategy }, { items }] = await Promise.all([
      import("@wix/sdk"),
      import("@wix/data"),
    ]);
    const wix = createClient({
      modules: { items },
      auth: OAuthStrategy({ clientId: WIX_CLIENT_ID }),
    });
    const res = await wix.items.query(collectionId).find();
    return res.items.map((i) => map(i as Record<string, unknown>));
  } catch (err) {
    console.error(`[cms] Wix read failed for ${collectionId}, using fixtures:`, err);
    return null;
  }
}

export async function getProjects(): Promise<Project[]> {
  const wix = await queryWix<Project>("Projects", (i) => ({
    slug: String(i.slug ?? ""),
    name: String(i.name ?? ""),
    location: String(i.location ?? ""),
    meta: String(i.meta ?? ""),
    blurb: String(i.blurb ?? ""),
    highlights: Array.isArray(i.highlights) ? i.highlights.map(String) : [],
    isNew: Boolean(i.isNew),
  }));
  return wix ?? fixtureProjects;
}

export async function getProject(slug: string): Promise<Project | undefined> {
  return (await getProjects()).find((p) => p.slug === slug);
}

export async function getBlogPosts(): Promise<BlogPost[]> {
  const wix = await queryWix<BlogPost>("BlogPosts", (i) => ({
    slug: String(i.slug ?? ""),
    title: String(i.title ?? ""),
    excerpt: String(i.excerpt ?? ""),
    body: String(i.body ?? ""),
    heroImageUrl: i.heroImageUrl ? String(i.heroImageUrl) : null,
    tags: Array.isArray(i.tags) ? i.tags.map(String) : [],
    publishedAt: String(i.publishedAt ?? ""),
    seoTitle: String(i.seoTitle ?? i.title ?? ""),
    seoDescription: String(i.seoDescription ?? i.excerpt ?? ""),
  }));
  return wix ?? []; // no fixture posts yet — blog renders empty-state until Wix is wired
}
