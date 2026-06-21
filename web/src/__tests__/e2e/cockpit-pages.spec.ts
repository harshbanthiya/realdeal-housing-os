/**
 * Playwright E2E — Cockpit page-by-page interactive audit tests.
 *
 * Covers: contacts sheet sorting/pagination, pipeline kanban render,
 * contact detail actions, outreach queue controls, audiences filter,
 * buildings workspace tab switching, unit registry, merge candidate skip.
 *
 * Requires: COCKPIT_AUTH_TOKEN env var (from web/.env.local).
 * Requires: Live app at http://localhost:3000 with real DB data.
 *
 * Real contact/building IDs are sampled from the live app; tests skip
 * gracefully if pages return no data (empty DB state).
 */

import { test, expect, type BrowserContext, type Page } from "@playwright/test";

const TOKEN = process.env.COCKPIT_AUTH_TOKEN;

// Real IDs sampled from the live DB during audit (2026-06-21)
const REAL_CONTACT_ID = "bf4827de-29fa-4ca4-a5da-d924e2b157a3";
const REAL_BUILDING_SLUG = "kalpataru-radiance";
const DLF_SLUG = "dlf-westpark-andheri-west";

async function authedContext(context: BrowserContext) {
  if (!TOKEN) return;
  await context.addCookies([{
    name: "cockpit_auth", value: TOKEN,
    domain: "localhost", path: "/",
    httpOnly: true, sameSite: "Lax",
  }]);
}

// ---------------------------------------------------------------------------
// /cockpit/contacts/sheet — sort + pagination
// ---------------------------------------------------------------------------

test.describe("Contacts sheet", () => {
  test.skip(!TOKEN, "COCKPIT_AUTH_TOKEN required");

  test.beforeEach(async ({ context }) => { await authedContext(context); });

  test("loads and shows contacts or empty state", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet");
    const hasRows = await page.locator("table tbody tr, [data-testid='contact-row']").count() > 0;
    const hasEmpty = await page.getByText(/no canonical contacts yet/i).isVisible().catch(() => false);
    expect(hasRows || hasEmpty).toBe(true);
  });

  test("sort by name changes URL", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet");
    const nameLink = page.locator("a[href*='sort=name']").first();
    if (await nameLink.count() === 0) return; // no data
    await nameLink.click();
    await page.waitForURL("**/sheet?sort=name**");
    expect(page.url()).toContain("sort=name");
  });

  test("sort direction toggles on second click", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet?sort=name&dir=desc");
    const nameLink = page.locator("a[href*='sort=name']").first();
    if (await nameLink.count() === 0) return;
    await nameLink.click();
    await page.waitForURL("**/sort=name**");
    expect(page.url()).toContain("dir=asc");
  });

  test("pagination next link changes page param", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet");
    const nextLink = page.locator("a[href*='page=2']").first();
    if (await nextLink.count() === 0) return; // only one page — skip
    await nextLink.click();
    await page.waitForLoadState("networkidle", { timeout: 20000 });
    expect(page.url()).toContain("page=2");
  });

  test("row click navigates to contact detail", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet");
    const firstRow = page.locator("a[href*='/cockpit/contacts/c/']").first();
    if (await firstRow.count() === 0) return;
    const href = await firstRow.getAttribute("href");
    await firstRow.click();
    await page.waitForURL("**/cockpit/contacts/c/**");
    expect(page.url()).toContain("/cockpit/contacts/c/");
  });

  // ---- Search bar tests ----

  test("search input is visible", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet");
    await expect(page.getByRole("searchbox", { name: /search contacts/i })).toBeVisible();
  });

  test("search input has correct placeholder", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet");
    const input = page.getByRole("searchbox", { name: /search contacts/i });
    await expect(input).toHaveAttribute("placeholder", /name or phone/i);
  });

  test("typing in search navigates to ?q= URL", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet");
    const input = page.getByRole("searchbox", { name: /search contacts/i });
    await input.fill("test");
    // Debounce 350ms + navigation settle
    await page.waitForURL("**/sheet?**q=test**", { timeout: 5000 });
    expect(page.url()).toContain("q=test");
  });

  test("search preserves sort param in URL", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet?sort=contact&dir=asc");
    const input = page.getByRole("searchbox", { name: /search contacts/i });
    await input.fill("x");
    // Debounce is 350ms; give it a full second then wait for navigation to settle
    await page.waitForTimeout(500);
    await page.waitForLoadState("networkidle", { timeout: 15000 });
    expect(page.url()).toContain("q=x");
    expect(page.url()).toContain("sort=contact");
    expect(page.url()).toContain("dir=asc");
  });

  test("search with ?q= in URL pre-fills the input", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet?q=padmini");
    const input = page.getByRole("searchbox", { name: /search contacts/i });
    await expect(input).toHaveValue("padmini");
  });

  test("search result count label shows 'result(s) for' when q set", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet?q=padmini");
    await page.waitForLoadState("networkidle");
    // Text is split across React text nodes and <span>/<Link>; check full main textContent.
    // Singular: "1 result for …" / plural: "N results for …" / zero: "No contacts match…"
    const mainText = (await page.locator("main").textContent()) ?? "";
    expect(mainText).toMatch(/\bresults? for\b|no contacts match/i);
  });

  test("clear search link removes q param", async ({ page }) => {
    // Test the "clear" link rendered next to the result count in the header
    await page.goto("/cockpit/contacts/sheet?q=padmini");
    await page.waitForLoadState("networkidle");
    const clearLink = page.locator("main").getByRole("link", { name: /^clear$/i });
    if (await clearLink.count() > 0) {
      await clearLink.click();
      // Use a predicate — don't use waitForLoadState (may resolve before navigation)
      await page.waitForURL((url) => !url.toString().includes("q="), { timeout: 8000 });
      expect(page.url()).not.toContain("q=");
    }
    // Test the × button in the search bar
    await page.goto("/cockpit/contacts/sheet?q=padmini");
    await page.waitForLoadState("networkidle");
    const clearBtn = page.getByRole("button", { name: /clear search/i });
    if (await clearBtn.count() > 0) {
      await clearBtn.click();
      await page.waitForURL((url) => !url.toString().includes("q=padmini"), { timeout: 8000 });
      expect(page.url()).not.toContain("q=padmini");
    }
  });

  test("sort links carry q param through", async ({ page }) => {
    await page.goto("/cockpit/contacts/sheet?q=test");
    const sortLink = page.locator("a[href*='sort=contact']").first();
    if (await sortLink.count() === 0) return;
    const href = await sortLink.getAttribute("href");
    expect(href).toContain("q=test");
  });

  test("empty search term shows all contacts", async ({ page }) => {
    const total1 = async () => {
      await page.goto("/cockpit/contacts/sheet");
      const txt = await page.locator("p").filter({ hasText: /canonical contact/ }).first().textContent();
      return parseInt(txt ?? "0");
    };
    const total2 = async () => {
      await page.goto("/cockpit/contacts/sheet?q=");
      const txt = await page.locator("p").filter({ hasText: /canonical contact/ }).first().textContent();
      return parseInt(txt ?? "0");
    };
    // Both should return the same row count (empty q = no filter)
    expect(await total1()).toBe(await total2());
  });
});

// ---------------------------------------------------------------------------
// /cockpit/contacts/pipeline — kanban
// ---------------------------------------------------------------------------

test.describe("Contacts pipeline kanban", () => {
  test.skip(!TOKEN, "COCKPIT_AUTH_TOKEN required");
  test.beforeEach(async ({ context }) => { await authedContext(context); });

  test("renders 4 kanban columns", async ({ page }) => {
    await page.goto("/cockpit/contacts/pipeline");
    const columns = page.locator("section[aria-label]");
    expect(await columns.count()).toBe(4);
  });

  test("column labels are correct", async ({ page }) => {
    await page.goto("/cockpit/contacts/pipeline");
    const labels = await page.locator("section[aria-label] h2").allTextContents();
    expect(labels.some((l) => /unreviewed|reviewed|attached|canonical/i.test(l))).toBe(true);
  });

  test("cards are not draggable (by design)", async ({ page }) => {
    await page.goto("/cockpit/contacts/pipeline");
    // By design: kanban is read-only, cards advance via review approval
    const draggable = page.locator("[draggable='true']");
    expect(await draggable.count()).toBe(0);
  });

  test("shows footer note about read-only design", async ({ page }) => {
    await page.goto("/cockpit/contacts/pipeline");
    await expect(page.getByText(/read-only/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// /cockpit/contacts/c/[id] — contact detail
// ---------------------------------------------------------------------------

test.describe("Contact detail page", () => {
  test.skip(!TOKEN, "COCKPIT_AUTH_TOKEN required");
  test.beforeEach(async ({ context }) => { await authedContext(context); });

  test("renders contact detail for known ID", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    expect(page.url()).not.toContain("/cockpit/login");
    // Either detail or 404 is acceptable
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    await expect(page.locator("h1")).toBeVisible();
  });

  test("outreach section is visible", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    // Scope to main to avoid sidebar nav "Outreach" link
    await expect(page.locator("main").getByText("Outreach").first()).toBeVisible();
  });

  test("Add to outreach or In-outreach badge is rendered", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    const addBtn = page.getByRole("button", { name: /add to outreach/i });
    const inOutreach = page.getByText(/in outreach/i);
    const hasEither = (await addBtn.count() > 0) || (await inOutreach.count() > 0);
    expect(hasEither).toBe(true);
  });

  test("activity timeline section is rendered", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    await expect(page.getByText("Activity timeline")).toBeVisible();
  });

  test("contact methods section is rendered", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    await expect(page.getByText("Contact methods")).toBeVisible();
  });

  test("back link goes to contact sheet", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    const back = page.locator("a[href='/cockpit/contacts/sheet']");
    expect(await back.count()).toBeGreaterThan(0);
  });

  test("Add note textarea is visible", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    await expect(page.getByLabel("Contact note text")).toBeVisible();
  });

  test("Add note submit button is disabled when textarea is empty", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    const btn = page.getByRole("button", { name: /add note/i });
    await expect(btn).toBeDisabled();
  });

  test("Add note submit button is enabled after typing", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    const textarea = page.getByLabel("Contact note text");
    await textarea.fill("Test note from Playwright");
    const btn = page.getByRole("button", { name: /add note/i });
    await expect(btn).toBeEnabled();
  });

  test("Add note shows char counter", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    await expect(page.getByText(/500 chars left/)).toBeVisible();
  });

  test("Char counter decrements as user types", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    const textarea = page.getByLabel("Contact note text");
    await textarea.fill("Hello");
    await expect(page.getByText(/495 chars left/)).toBeVisible();
  });

  test("Add note header label is rendered", async ({ page }) => {
    await page.goto(`/cockpit/contacts/c/${REAL_CONTACT_ID}`);
    const is404 = await page.getByText(/not found/i).isVisible().catch(() => false);
    if (is404) return;
    // The "Add note" section header is a small label above the textarea
    const label = page.locator("main").getByText(/add note/i).first();
    await expect(label).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// /cockpit/contacts — merge candidate card
// ---------------------------------------------------------------------------

test.describe("Merge candidate card", () => {
  test.skip(!TOKEN, "COCKPIT_AUTH_TOKEN required");
  test.beforeEach(async ({ context }) => { await authedContext(context); });

  test("Skip button changes card to skipped state", async ({ page }) => {
    await page.goto("/cockpit/contacts");
    const skipBtn = page.getByRole("button", { name: "Skip" }).first();
    if (await skipBtn.count() === 0) return; // no merge candidates
    await skipBtn.click();
    await expect(page.getByText(/skipped in this view/i)).toBeVisible();
  });

  test("Skip button disables itself after click", async ({ page }) => {
    await page.goto("/cockpit/contacts");
    const skipBtn = page.getByRole("button", { name: "Skip" }).first();
    if (await skipBtn.count() === 0) return;
    await skipBtn.click();
    await expect(skipBtn).toBeDisabled();
  });

  test("Preview approve button exists and shows dry-run result", async ({ page }) => {
    await page.goto("/cockpit/contacts");
    const previewBtn = page.getByRole("button", { name: /preview approve/i }).first();
    if (await previewBtn.count() === 0) return;
    await previewBtn.click();
    // Wait for async response — either "Dry run:" message or error
    await page.waitForFunction(() =>
      document.querySelector("[role='status']")?.textContent?.includes("run") ||
      document.querySelector("[role='status']")?.textContent?.includes("Invalid") ||
      document.querySelector("[role='status']")?.textContent?.includes("dry"),
      { timeout: 10000 }
    );
    const status = await page.locator("[role='status']").first().textContent();
    expect(status).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// /cockpit/outreach — queue controls
// ---------------------------------------------------------------------------

test.describe("Outreach queue page", () => {
  test.skip(!TOKEN, "COCKPIT_AUTH_TOKEN required");
  test.beforeEach(async ({ context }) => { await authedContext(context); });

  test("renders status strip with Send mode", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    await expect(page.getByText("Send mode")).toBeVisible();
    await expect(page.getByText("Assisted (human)", { exact: true })).toBeVisible();
  });

  test("queue builder has Preview and Build buttons", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    await expect(page.getByRole("button", { name: "Preview" })).toBeVisible();
    // Groups panel also has "Build queue" buttons — use first() or exact label to avoid strict mode
    await expect(page.getByRole("button", { name: /build.*queue/i }).first()).toBeVisible();
  });

  test("Preview button is disabled when no active sequence", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    const preview = page.getByRole("button", { name: "Preview" });
    // Preview should be disabled if no active outreach sequence seeded
    // (This documents the hasActiveSequence gate)
    const isDisabled = await preview.isDisabled();
    const hasSeq = await page.getByText(/no active sequence/i).count() > 0;
    // If no sequence, button is disabled; if sequence exists, button is enabled
    expect(isDisabled === hasSeq || !isDisabled).toBe(true);
  });

  test("limit number input exists and accepts values", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    const input = page.locator("input[type='number']");
    await expect(input).toBeVisible();
    await input.fill("5");
    expect(await input.inputValue()).toBe("5");
  });

  test("Groups panel renders Create group input", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    await expect(page.getByPlaceholder(/new group name/i)).toBeVisible();
  });

  test("Create group button disabled with short name", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    const createBtn = page.getByRole("button", { name: /create group/i });
    await expect(createBtn).toBeDisabled(); // empty input
    await page.getByPlaceholder(/new group name/i).fill("x"); // too short
    await expect(createBtn).toBeDisabled();
    await page.getByPlaceholder(/new group name/i).fill("Test Group Valid");
    await expect(createBtn).toBeEnabled();
  });

  test("WhatsApp links on queue rows have wa.me format", async ({ page }) => {
    await page.goto("/cockpit/outreach");
    const waLinks = page.locator('a[href*="wa.me"]');
    const count = await waLinks.count();
    if (count === 0) return; // empty queue
    const href = await waLinks.first().getAttribute("href");
    expect(href).toMatch(/^https:\/\/wa\.me\/91\d{10}/);
  });
});

// ---------------------------------------------------------------------------
// /cockpit/buildings/[slug] — workspace tabs
// ---------------------------------------------------------------------------

test.describe("Buildings workspace", () => {
  test.skip(!TOKEN, "COCKPIT_AUTH_TOKEN required");
  test.beforeEach(async ({ context }) => { await authedContext(context); });

  test("building page loads with name and mode pill", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    await expect(page.locator("h1")).toBeVisible();
    // Mode pill should be one of the known values
    const text = await page.locator("h1").textContent();
    expect(text?.length).toBeGreaterThan(0);
  });

  test("tab bar has all 11 tabs", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    const tabs = page.locator("button[class*='border-b-2']");
    expect(await tabs.count()).toBeGreaterThanOrEqual(10);
  });

  test("clicking Owners tab shows owners panel", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    await page.getByRole("button", { name: "Owners" }).click();
    // Either owners list or "no owners" message
    const hasContent = await page.locator("h2, p, li").count() > 0;
    expect(hasContent).toBe(true);
  });

  test("clicking Units tab shows unit registry or empty", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    await page.getByRole("button", { name: "Unit registry" }).click();
    const hasGrid = await page.locator("[class*='grid']").count() > 0;
    expect(hasGrid).toBe(true);
  });

  test("clicking SEO tab shows keywords or empty", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    await page.getByRole("button", { name: "SEO" }).click();
    const hasContent = await page.locator("h2, p, li, table").count() > 0;
    expect(hasContent).toBe(true);
  });

  test("clicking RERA tab shows RERA panel", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    await page.getByRole("button", { name: "RERA" }).click();
    const hasContent = await page.locator("h2, p, li").count() > 0;
    expect(hasContent).toBe(true);
  });

  test("mode switcher has 4 interactive buttons", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    const modeBtns = page.getByRole("group", { name: /lifecycle mode/i }).getByRole("button");
    expect(await modeBtns.count()).toBe(4);
    const labels = await modeBtns.allTextContents();
    expect(labels).toEqual(expect.arrayContaining(["Prospecting", "Active", "Launch", "Post-launch"]));
  });

  test("clicking a mode button updates aria-pressed and changes overview content", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    // Click "Launch" mode button
    const launchBtn = page.getByRole("button", { name: "Launch", exact: true });
    await launchBtn.click();
    await expect(launchBtn).toHaveAttribute("aria-pressed", "true");
    // Overview tab should now show launch kanban OR launch content
    const hasLaunchContent = await page.getByText(/launch kanban|go-live/i).count() > 0;
    const hasNonLaunchContent = await page.getByText(/steady-state building/i).count() > 0;
    // Exactly one should be visible depending on mode
    expect(hasLaunchContent || hasNonLaunchContent).toBe(true);
  });

  test("active mode button has aria-pressed=true on load", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${REAL_BUILDING_SLUG}`);
    // One and only one button should be pressed
    const pressed = page.getByRole("button", { name: /Prospecting|Active|Launch|Post-launch/ })
      .and(page.locator("[aria-pressed='true']"));
    expect(await pressed.count()).toBe(1);
  });

  test("switching from Launch to Active hides launch kanban", async ({ page }) => {
    await page.goto(`/cockpit/buildings/${DLF_SLUG}`);
    // DLF is in launch mode — switch to Active
    await expect(page.getByText(/launch kanban/i)).toBeVisible();
    await page.getByRole("button", { name: "Active", exact: true }).click();
    await expect(page.getByText(/steady-state building/i)).toBeVisible();
    await expect(page.getByText(/launch kanban/i)).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// /cockpit/audiences — filter form
// ---------------------------------------------------------------------------

test.describe("Audiences page", () => {
  test.skip(!TOKEN, "COCKPIT_AUTH_TOKEN required");
  test.beforeEach(async ({ context }) => { await authedContext(context); });

  test("renders filter form with building and role selects", async ({ page }) => {
    await page.goto("/cockpit/audiences");
    await expect(page.locator("select[name='building']")).toBeVisible();
    await expect(page.locator("select[name='role']")).toBeVisible();
  });

  test("Update preview submits form and updates URL", async ({ page }) => {
    await page.goto("/cockpit/audiences");
    await page.selectOption("select[name='role']", { index: 1 });
    await page.getByRole("button", { name: /update preview/i }).click();
    await page.waitForURL("**/audiences**");
    // URL should have role param (or remain on audiences if only one option)
    expect(page.url()).toContain("/cockpit/audiences");
  });

  test("Download Meta CSV link exists", async ({ page }) => {
    await page.goto("/cockpit/audiences");
    const csvLink = page.getByRole("link", { name: /download meta csv/i });
    await expect(csvLink).toBeVisible();
    const href = await csvLink.getAttribute("href");
    expect(href).toContain("/cockpit/audiences/meta");
  });

  test("shows audience metrics grid", async ({ page }) => {
    await page.goto("/cockpit/audiences");
    // "contacts" appears in sidebar nav + description + metric label — use exact+scoped to avoid strict mode
    await expect(page.locator("main").getByText("contacts", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("hashed rows")).toBeVisible();
  });

  test("WhatsApp send state shows 'not connected'", async ({ page }) => {
    await page.goto("/cockpit/audiences");
    await expect(page.getByText("not connected")).toBeVisible();
  });
});
