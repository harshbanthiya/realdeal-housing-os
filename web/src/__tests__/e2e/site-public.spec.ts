/**
 * Playwright E2E — public site QA for the 2026-07 redesign.
 *
 * Runs against the live app at http://localhost:3000 (dev or `next start`).
 * Covers: map hero pins/panel, mobile nav overlay, homepage chapters (focus
 * four, no Bharat), DLF landing facts + pricing-absence policy, floor-plan
 * explorer (floors, refuge, unit panel, lightbox, list view), listing detail
 * (price + JSON-LD), sticky WhatsApp CTA, SEO surfaces.
 *
 * Map tests need WebGL (maplibre); they self-skip when headless GL is absent.
 */

import { test, expect, type Page } from "@playwright/test";

const hasWebgl = async (page: Page) =>
  page.evaluate(() => {
    try {
      return !!document.createElement("canvas").getContext("webgl2");
    } catch {
      return false;
    }
  });

// ---------------------------------------------------------------------------
// Home — map hero
// ---------------------------------------------------------------------------

test.describe("Home — map hero", () => {
  test("hero statement and single primary CTA render", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText(/few buildings/i);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.getByRole("link", { name: /see what.s available/i })).toBeVisible();
  });

  test("four building pins appear; pin click opens facts panel", async ({ page }) => {
    await page.goto("/");
    test.skip(!(await hasWebgl(page)), "no WebGL in this environment");
    const pins = page.locator(".rdh-pin");
    await expect(pins).toHaveCount(4, { timeout: 20_000 });
    await pins.filter({ hasText: "Kalpataru Radiance" }).click();
    const panel = page.getByTestId("map-building-panel");
    await expect(panel).toBeVisible();
    await expect(panel.locator("h2")).toHaveText("Kalpataru Radiance");
    await expect(panel.getByRole("link", { name: /view building/i })).toBeVisible();
    // close it
    await page.getByRole("button", { name: /close building details/i }).click();
    await expect(panel).toBeHidden();
  });
});

// ---------------------------------------------------------------------------
// Home — chapters & focus four
// ---------------------------------------------------------------------------

test.describe("Home — building chapters", () => {
  test("focus four chapters link out; Bharat absent from homepage", async ({ page }) => {
    await page.goto("/");
    for (const name of ["Imperial Heights", "Kalpataru Radiance", "Ekta Tripolis", "DLF Westpark"]) {
      await expect(page.getByRole("heading", { name, exact: true }).first()).toBeVisible();
    }
    await expect(page.getByText(/bharat auravistas/i)).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// Mobile navigation
// ---------------------------------------------------------------------------

test.describe("Mobile nav", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("hamburger opens overlay; link navigates", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /open menu/i }).click();
    const buyLink = page.locator("header div.absolute nav a", { hasText: "Buy" });
    await expect(buyLink).toBeVisible();
    await buyLink.click();
    await expect(page).toHaveURL(/\/buy$/);
  });
});

// ---------------------------------------------------------------------------
// DLF Westpark landing — facts & pricing policy
// ---------------------------------------------------------------------------

test.describe("DLF landing", () => {
  test("brochure-verified facts render; no rupee pricing anywhere", async ({ page }) => {
    await page.goto("/dlf-westpark-andheri-west");
    await expect(page.getByText("PR1181012500079").first()).toBeVisible();
    await expect(page.getByText(/peegen builders/i).first()).toBeVisible();
    await expect(page.getByText(/phase 1 complete/i).first()).toBeVisible();
    await expect(page.getByText(/pricing on request/i).first()).toBeVisible();
    // dynamic-pricing policy: no rupee amounts on the page
    expect(await page.locator("body").innerText()).not.toContain("₹");
  });

  test("Phase 2 tower details in the facts ledger", async ({ page }) => {
    await page.goto("/dlf-westpark-andheri-west");
    await expect(page.getByText(/tower 6 — 38 storeys/i).first()).toBeVisible();
    await expect(page.getByText(/duplex on floors 39–40/i).first()).toBeVisible();
  });

  test("gallery image opens and closes the lightbox", async ({ page }) => {
    await page.goto("/dlf-westpark-andheri-west");
    await page.locator('button[aria-label^="Enlarge image"]').first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });

  test("neighborhood legend renders with OSM categories and toggles", async ({ page }) => {
    await page.goto("/dlf-westpark-andheri-west");
    await expect(page.getByText(/explore the neighbourhood/i)).toBeVisible();
    const transit = page.getByRole("button", { name: /transit/i });
    await expect(transit).toBeVisible();
    await transit.click();
    await expect(transit).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByText(/openstreetmap contributors/i)).toBeVisible();
  });

  test("sticky WhatsApp CTA present", async ({ page }) => {
    await page.goto("/dlf-westpark-andheri-west");
    await expect(page.locator('a[href*="wa.me"]').first()).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// DLF floor-plan explorer
// ---------------------------------------------------------------------------

test.describe("DLF plans explorer", () => {
  test("tower → floor → unit → panel flow, refuge floor honesty", async ({ page }) => {
    await page.goto("/dlf-westpark-andheri-west/plans");
    // switch tower
    await page.getByRole("button", { name: "Tower-03" }).click();
    // floor 13 is a refuge floor with no residences
    await page.getByRole("button", { name: /^floor 13/i }).click();
    await expect(page.getByText(/refuge floor — no residences/i).first()).toBeVisible();
    // floor 36 on T03 carries the lone 4 BHK
    await page.getByRole("button", { name: /^floor 36$/i }).click();
    await page.getByRole("button", { name: /4 BHK/ }).first().click();
    await expect(page.getByText("T03-4BHK-03")).toBeVisible();
    await expect(page.getByText(/carpet area/i)).toBeVisible();
    // pricing handled by sales — panel links out, shows no rupee amount
    await expect(page.getByRole("link", { name: /get pricing for this layout/i })).toBeVisible();
    expect(await page.locator("body").innerText()).not.toContain("₹");
  });

  test("plate lightbox enlarges the floor plan", async ({ page }) => {
    await page.goto("/dlf-westpark-andheri-west/plans");
    await page.locator('button[aria-label^="Enlarge image"]').first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: /close enlarged image/i }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });

  test("All-configurations list view shows every layout", async ({ page }) => {
    await page.goto("/dlf-westpark-andheri-west/plans");
    await page.getByRole("button", { name: /all configurations/i }).click();
    await expect(page.getByText(/pricing on request →/i).first()).toBeVisible();
    // 25 configuration cards across the four towers
    await expect(page.locator('button[aria-label^="Enlarge image"]')).toHaveCount(25);
  });
});

// ---------------------------------------------------------------------------
// Listing detail (resale — keeps pricing)
// ---------------------------------------------------------------------------

test.describe("Listing detail", () => {
  const slug = "/listings/imperial-heights-4-5-bhk-1893-sqft-for-sale";

  test("renders price, facts and RealEstateListing JSON-LD", async ({ page }) => {
    await page.goto(slug);
    await expect(page.locator("h1")).toBeVisible();
    expect(await page.locator("body").innerText()).toContain("₹");
    const jsonLd = (await page.locator('script[type="application/ld+json"]').allTextContents()).join("");
    expect(jsonLd).toContain("RealEstateListing");
    expect(jsonLd).toContain("BreadcrumbList");
  });

  test("project page carries BreadcrumbList JSON-LD; home stats animate to values", async ({ page }) => {
    await page.goto("/projects/imperial-heights");
    const jsonLd = (await page.locator('script[type="application/ld+json"]').allTextContents()).join("");
    expect(jsonLd).toContain("BreadcrumbList");
    await page.goto("/");
    const stat = page.locator('span[aria-label="15+"]');
    await stat.scrollIntoViewIfNeeded();
    await expect(stat).toHaveText("15+", { timeout: 10_000 });
  });

  test("hero image lightbox opens", async ({ page }) => {
    await page.goto(slug);
    await page.locator('button[aria-label^="Enlarge image"]').first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Social & video
// ---------------------------------------------------------------------------

test.describe("Social & video", () => {
  test("footer links YouTube, Instagram and Facebook", async ({ page }) => {
    await page.goto("/");
    const footer = page.locator("footer");
    await expect(footer.locator('a[href*="youtube.com/@RealDealHousing"]')).toBeVisible();
    await expect(footer.locator('a[href*="instagram.com/realdealhousing_mumbai"]')).toBeVisible();
    await expect(footer.locator('a[href*="facebook.com/realdealhousingpvtltd"]')).toBeVisible();
  });

  test("building page shows walkthrough videos; facade loads iframe on click", async ({ page }) => {
    await page.goto("/projects/imperial-heights");
    await expect(page.getByRole("heading", { name: /walk through imperial heights/i })).toBeVisible();
    const facade = page.locator('button[aria-label^="Play video"]').first();
    await expect(facade).toBeVisible();
    // no YouTube iframe before interaction (perf guarantee)
    await expect(page.locator('iframe[src*="youtube"]')).toHaveCount(0);
    await facade.click();
    await expect(page.locator('iframe[src*="youtube-nocookie.com"]')).toHaveCount(1);
    // VideoObject structured data present
    const jsonLd = (await page.locator('script[type="application/ld+json"]').allTextContents()).join("");
    expect(jsonLd).toContain("VideoObject");
  });
});

// ---------------------------------------------------------------------------
// Blog — building-keyword content
// ---------------------------------------------------------------------------

test.describe("Blog", () => {
  test("index lists all four building guides", async ({ page }) => {
    await page.goto("/blog");
    for (const name of [/ekta tripolis/i, /imperial heights/i, /kalpataru radiance/i, /dlf westpark/i]) {
      await expect(page.getByRole("link", { name }).first()).toBeVisible();
    }
  });

  test("each building guide renders with keyword title and internal links", async ({ page }) => {
    for (const [slug, kw] of [
      ["imperial-heights-goregaon-west-guide", /imperial heights/i],
      ["kalpataru-radiance-goregaon-west-guide", /kalpataru radiance/i],
      ["dlf-westpark-andheri-west-guide", /dlf westpark/i],
    ] as const) {
      await page.goto(`/blog/${slug}`);
      await expect(page.locator("h1")).toContainText(kw);
      await expect(page).toHaveTitle(kw);
      await expect(page.locator('article a[href^="/"]').first()).toBeVisible();
    }
  });

  test("post renders with building-keyword title, body and BlogPosting JSON-LD", async ({ page }) => {
    await page.goto("/blog/ekta-tripolis-goregaon-west-guide");
    await expect(page).toHaveTitle(/ekta tripolis.*goregaon west/i);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("h1")).toContainText(/ekta tripolis/i);
    // body content + internal links to the building page and inventory
    await expect(page.getByText(/skypolis, caliopolis and theopolis/i).first()).toBeVisible();
    await expect(page.locator('a[href="/projects/ekta-tripolis"]').first()).toBeVisible();
    await expect(page.locator('a[href="/buy"]').first()).toBeVisible();
    const jsonLd = (await page.locator('script[type="application/ld+json"]').allTextContents()).join("");
    expect(jsonLd).toContain("BlogPosting");
  });
});

// ---------------------------------------------------------------------------
// SEO surfaces
// ---------------------------------------------------------------------------

test.describe("SEO", () => {
  test("sitemap and robots respond; robots still noindex pre-launch", async ({ request }) => {
    expect((await request.get("/sitemap.xml")).status()).toBe(200);
    const robots = await request.get("/robots.txt");
    expect(robots.status()).toBe(200);
    expect(await robots.text()).toContain("Disallow");
  });

  test("home title carries the four buildings; one h1 per page", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/ekta tripolis.*imperial heights.*kalpataru radiance.*dlf westpark/i);
    for (const path of ["/dlf-westpark-andheri-west", "/dlf-westpark-andheri-west/plans", "/buy"]) {
      await page.goto(path);
      await expect(page.locator("h1")).toHaveCount(1);
    }
  });
});
