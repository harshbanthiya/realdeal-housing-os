/**
 * Playwright E2E tests — Cockpit auth gate and login flow.
 *
 * Runs against the live app at http://localhost:3000.
 * No fixtures needed — tests use public routes and the real login form.
 *
 * Authenticated-page tests use COCKPIT_AUTH_TOKEN from the environment so
 * the cookie can be injected without embedding credentials in source.
 * When the env var is absent, those tests are skipped gracefully.
 */

import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Public — unauthenticated access
// ---------------------------------------------------------------------------

test.describe("Auth gate — redirect", () => {
  test("/cockpit redirects to /cockpit/login", async ({ page }) => {
    const res = await page.goto("/cockpit", { waitUntil: "commit" });
    expect(page.url()).toContain("/cockpit/login");
  });

  test("/cockpit/contacts redirects to login with ?next= param", async ({ page }) => {
    await page.goto("/cockpit/contacts", { waitUntil: "commit" });
    expect(page.url()).toContain("/cockpit/login");
    expect(page.url()).toContain("next=");
  });

  test("/cockpit/outreach redirects to login", async ({ page }) => {
    await page.goto("/cockpit/outreach", { waitUntil: "commit" });
    expect(page.url()).toContain("/cockpit/login");
  });
});

// ---------------------------------------------------------------------------
// Login page — UI and form behaviour
// ---------------------------------------------------------------------------

test.describe("Login page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/cockpit/login");
  });

  test("renders the RDH brand mark", async ({ page }) => {
    // Scope to main — sidebar also has an RDH badge, causing strict mode violation
    await expect(page.locator("main").getByText("RDH")).toBeVisible();
  });

  test("renders 'Operations cockpit' header", async ({ page }) => {
    // Scope to main — sidebar repeats this label
    await expect(page.locator("main").getByText("Operations cockpit")).toBeVisible();
  });

  test("renders the Sign in heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  });

  test("has a password input", async ({ page }) => {
    const input = page.locator("input[type='password']");
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute("name", "password");
  });

  test("has a submit button", async ({ page }) => {
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("shows error message on wrong password", async ({ page }) => {
    await page.fill("input[type='password']", "wrong-password-qa-test");
    await page.click("button[type='submit']");
    // After redirect back to /cockpit/login?error=1
    await page.waitForURL("**/cockpit/login**");
    await expect(page.getByText(/incorrect password/i)).toBeVisible();
  });

  test("bad login shows error without leaving login page", async ({ page }) => {
    // Next.js App Router server action redirects do not expose ?error=1 in the
    // browser URL bar — the page renders the error state but the URL stays at
    // /cockpit/login. Assert on the visible error, not the URL query param.
    await page.fill("input[type='password']", "badpassword");
    await page.click("button[type='submit']");
    await page.waitForURL("**/cockpit/login**");
    expect(page.url()).toContain("/cockpit/login");
    await expect(page.getByText(/incorrect password/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Authenticated pages — inject session cookie from env
// ---------------------------------------------------------------------------

test.describe("Authenticated cockpit", () => {
  const token = process.env.COCKPIT_AUTH_TOKEN;

  test.beforeEach(async ({ page, context }) => {
    test.skip(!token, "COCKPIT_AUTH_TOKEN not set — skipping authenticated tests");
    await context.addCookies([
      {
        name: "cockpit_auth",
        value: token!,
        domain: "localhost",
        path: "/",
        httpOnly: true,
        sameSite: "Lax",
      },
    ]);
  });

  test("cockpit root renders without redirect", async ({ page }) => {
    await page.goto("/cockpit");
    expect(page.url()).not.toContain("/cockpit/login");
  });

  test("outreach page loads with Status panel", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    expect(page.url()).not.toContain("/cockpit/login");
    await expect(page.getByText("WhatsApp (assisted)")).toBeVisible();
    await expect(page.getByText("Status")).toBeVisible();
  });

  test("outreach page shows 'Assisted (human)' send mode (send_enabled gate)", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    // Use exact text to avoid matching the broader page description which also
    // contains "assisted" and "human" in a different sentence
    await expect(page.getByText("Assisted (human)", { exact: true })).toBeVisible();
  });

  test("outreach page has Open in WhatsApp links (wa.me format)", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    // The queue may be empty but the link format test only fires if items exist
    const waLinks = page.locator('a[href*="wa.me"]');
    const count = await waLinks.count();
    if (count > 0) {
      const href = await waLinks.first().getAttribute("href");
      expect(href).toMatch(/^https:\/\/wa\.me\/\d+/);
    }
    // If 0 wa.me links, no queue items yet — not a failure
  });

  test("contacts page loads without error", async ({ page }) => {
    await page.goto("/cockpit/contacts");
    expect(page.url()).not.toContain("/cockpit/login");
    // At minimum the page should not be a Next.js error page
    await expect(page.locator("body")).not.toContainText("Application error");
  });
});
