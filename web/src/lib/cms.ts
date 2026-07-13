/**
 * CMS adapter — the single boundary between the site and Wix headless CMS.
 *
 * WIX_CLIENT_ID is the OAuth app "RDH Next.js headless site" on the Wix
 * **Test** site (e8817980-3301-420f-856c-a4cd5184633e). Without it, every
 * getter serves the local fixtures in site.ts, so the site builds and deploys
 * with zero Wix dependency. With it, reads go to the Test-site collections
 * server-side (never client-side) and fall back to fixtures on any error.
 *
 * Review gate: only items marked published surface on the site —
 * Projects require `draft !== true`, BlogPosts require `status === "published"`.
 * Everything seeded so far is draft/staging, so Wix contributes nothing
 * until an editor explicitly publishes.
 *
 * Collections (verified 2026-07-08):
 *   Projects      title, slug, status, developer, locality, microMarket,
 *                 heroTagline, overview (RICH_TEXT), reraNumber, priceFrom,
 *                 brochureLink, seoTitle, seoDescription, osAnchorId,
 *                 displayOrder, draft
 *   BlogPosts     title, slug, excerpt, body (RICH_TEXT), heroImage (IMAGE),
 *                 publishedAt (DATETIME), seoTitle, seoDescription, tags,
 *                 status, displayOrder
 *   (also seeded: ProjectFacts, Residences, Amenities, ProjectFAQs)
 */
import { projects as fixtureProjects, projectImages, type Project } from "@/lib/site";

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

type WixItem = Record<string, unknown>;

async function getWixClient() {
  const [{ createClient, OAuthStrategy }, { items }] = await Promise.all([
    import("@wix/sdk"),
    import("@wix/data"),
  ]);
  return createClient({
    modules: { items },
    auth: OAuthStrategy({ clientId: WIX_CLIENT_ID! }),
  });
}

/** wix:image://v1/<uri>/... -> https://static.wixstatic.com/media/<uri> */
async function wixImageToUrl(value: unknown): Promise<string | null> {
  if (!value || typeof value !== "string") return null;
  if (value.startsWith("http")) return value;
  try {
    const { media } = await import("@wix/sdk");
    return media.getImageUrl(value).url;
  } catch {
    return null;
  }
}

function toIso(value: unknown): string {
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "string") return value;
  // Wix DATETIME sometimes arrives as {$date: "..."}
  if (value && typeof value === "object" && "$date" in value) {
    return String((value as { $date: unknown }).$date);
  }
  return "";
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

export async function getProjects(): Promise<Project[]> {
  if (!WIX_CLIENT_ID) return fixtureProjects;
  try {
    const wix = await getWixClient();
    const res = await wix.items
      .query("Projects")
      .ne("draft", true)
      .ascending("displayOrder")
      .find();
    const cmsProjects: Project[] = res.items.map((i: WixItem) => ({
      slug: String(i.slug ?? ""),
      name: String(i.title ?? ""),
      location: String(i.locality ?? ""),
      meta: String(i.microMarket ?? ""),
      blurb: stripHtml(String(i.overview ?? "")),
      highlights: [],
      image: projectImages[String(i.slug ?? "")],
    }));
    // Published CMS projects override same-slug fixtures; the rest of the
    // fixture catalogue stays until it too is migrated into the CMS.
    const cmsSlugs = new Set(cmsProjects.map((p) => p.slug));
    return [...cmsProjects, ...fixtureProjects.filter((p) => !cmsSlugs.has(p.slug))];
  } catch (err) {
    console.error("[cms] Wix Projects read failed, using fixtures:", err);
    return fixtureProjects;
  }
}

export async function getProject(slug: string): Promise<Project | undefined> {
  return (await getProjects()).find((p) => p.slug === slug);
}

export async function getBlogPosts(): Promise<BlogPost[]> {
  const { fixtureBlogPosts } = await import("@/lib/blog-fixtures");
  if (!WIX_CLIENT_ID) return fixtureBlogPosts;
  try {
    const wix = await getWixClient();
    const res = await wix.items
      .query("BlogPosts")
      .eq("status", "published")
      .find();
    const posts = await Promise.all(
      res.items.map(async (i: WixItem): Promise<BlogPost> => ({
        slug: String(i.slug ?? ""),
        title: String(i.title ?? ""),
        excerpt: String(i.excerpt ?? ""),
        body: String(i.body ?? ""),
        heroImageUrl: await wixImageToUrl(i.heroImage),
        tags: Array.isArray(i.tags) ? i.tags.map(String) : [],
        publishedAt: toIso(i.publishedAt) || toIso(i._createdDate),
        seoTitle: String(i.seoTitle ?? i.title ?? ""),
        seoDescription: String(i.seoDescription ?? i.excerpt ?? ""),
      }))
    );
    // Published CMS posts override same-slug fixtures; fixtures fill the rest.
    const cmsSlugs = new Set(posts.map((p) => p.slug));
    const merged = [...posts, ...fixtureBlogPosts.filter((p) => !cmsSlugs.has(p.slug))];
    return merged.sort((a, b) => (b.publishedAt || "").localeCompare(a.publishedAt || ""));
  } catch (err) {
    console.error("[cms] Wix BlogPosts read failed, using fixtures:", err);
    return fixtureBlogPosts;
  }
}
