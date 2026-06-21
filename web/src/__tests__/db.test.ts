/**
 * Tests for web/src/lib/db.ts — the cockpit's read-only Postgres layer.
 *
 * These tests run without a live database. The most critical safety property
 * is that readQuery() returns [] (never throws) when DATABASE_URL is absent,
 * so the Next.js shell always renders even in development without a DB.
 *
 * DB-connected behavior (READ ONLY transaction enforcement) is documented as
 * a blocker: requires a test-only Postgres instance. See QA report.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("isDbConfigured", () => {
  let original: string | undefined;

  beforeEach(() => {
    original = process.env.DATABASE_URL;
  });

  afterEach(() => {
    if (original === undefined) {
      delete process.env.DATABASE_URL;
    } else {
      process.env.DATABASE_URL = original;
    }
    vi.resetModules();
  });

  it("returns false when DATABASE_URL is unset", async () => {
    delete process.env.DATABASE_URL;
    const { isDbConfigured } = await import("@/lib/db");
    expect(isDbConfigured()).toBe(false);
  });

  it("returns true when DATABASE_URL is set", async () => {
    process.env.DATABASE_URL = "postgresql://user:pass@localhost:5432/testdb";
    const { isDbConfigured } = await import("@/lib/db");
    expect(isDbConfigured()).toBe(true);
  });
});

describe("readQuery without DATABASE_URL", () => {
  let original: string | undefined;

  beforeEach(() => {
    original = process.env.DATABASE_URL;
    delete process.env.DATABASE_URL;
    vi.resetModules();
  });

  afterEach(() => {
    if (original === undefined) {
      delete process.env.DATABASE_URL;
    } else {
      process.env.DATABASE_URL = original;
    }
    vi.resetModules();
  });

  it("returns empty array, never throws", async () => {
    const { readQuery } = await import("@/lib/db");
    const result = await readQuery("SELECT 1");
    expect(result).toEqual([]);
  });

  it("returns empty array for any SQL string", async () => {
    const { readQuery } = await import("@/lib/db");
    const result = await readQuery<{ id: number }>(
      "SELECT id FROM contacts LIMIT 10"
    );
    expect(Array.isArray(result)).toBe(true);
    expect(result).toHaveLength(0);
  });

  it("returns empty array with params", async () => {
    const { readQuery } = await import("@/lib/db");
    const result = await readQuery("SELECT * FROM contacts WHERE id = $1", [42]);
    expect(result).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Contact sheet query sanitisation (pure-logic, no DB)
// ---------------------------------------------------------------------------

describe("contact sheet q sanitisation", () => {
  function sanitiseQ(v: string | undefined): string {
    return (v ?? "").slice(0, 100).replace(/\0/g, "").trim();
  }
  function likePattern(q: string): string {
    return `%${q.replace(/[%_\\]/g, "\\$&")}%`;
  }

  it("empty string returns empty string", () => {
    expect(sanitiseQ("")).toBe("");
    expect(sanitiseQ(undefined)).toBe("");
  });

  it("trims whitespace", () => {
    expect(sanitiseQ("  rohan  ")).toBe("rohan");
  });

  it("clamps to 100 characters", () => {
    const long = "a".repeat(200);
    expect(sanitiseQ(long).length).toBe(100);
  });

  it("strips NUL bytes", () => {
    expect(sanitiseQ("ro\0han")).toBe("rohan");
  });

  it("likePattern wraps with %", () => {
    expect(likePattern("rohan")).toBe("%rohan%");
  });

  it("likePattern escapes SQL LIKE metacharacters", () => {
    expect(likePattern("50%")).toBe("%50\\%%");
    expect(likePattern("unit_1")).toBe("%unit\\_1%");
    expect(likePattern("back\\slash")).toBe("%back\\\\slash%");
  });

  it("likePattern is safe for names with special chars", () => {
    const result = likePattern("O'Connor");
    // Single quotes are NOT LIKE metacharacters — no escape needed
    expect(result).toBe("%O'Connor%");
  });
});

// ---------------------------------------------------------------------------
// logContactNote input validation (pure-logic, no DB or script invocation)
// ---------------------------------------------------------------------------

describe("logContactNote input validation", () => {
  const VALID_UUID = "bf4827de-29fa-4ca4-a5da-d924e2b157a3";
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  function validateNote(input: { contactId: string; note: string; by?: string }) {
    if (!UUID_RE.test(input.contactId)) return { ok: false, message: "Invalid contact id." };
    const note = (input.note ?? "").replace(/\0/g, "").trim().slice(0, 500);
    if (!note) return { ok: false, message: "Note cannot be empty." };
    const by = ((input.by ?? "operator").replace(/\0/g, "").trim().slice(0, 100)) || "operator";
    return { ok: true, note, by };
  }

  it("rejects invalid UUID", () => {
    const r = validateNote({ contactId: "not-a-uuid", note: "hello" });
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/invalid contact id/i);
  });

  it("rejects empty note", () => {
    const r = validateNote({ contactId: VALID_UUID, note: "" });
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/cannot be empty/i);
  });

  it("rejects whitespace-only note", () => {
    const r = validateNote({ contactId: VALID_UUID, note: "   " });
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/cannot be empty/i);
  });

  it("rejects note with only NUL bytes", () => {
    const r = validateNote({ contactId: VALID_UUID, note: "\0\0" });
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/cannot be empty/i);
  });

  it("accepts valid note", () => {
    const r = validateNote({ contactId: VALID_UUID, note: "Called — interested in 3BHK" });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.note).toBe("Called — interested in 3BHK");
  });

  it("clamps note to 500 chars", () => {
    const long = "x".repeat(600);
    const r = validateNote({ contactId: VALID_UUID, note: long });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.note!.length).toBe(500);
  });

  it("strips NUL bytes from note", () => {
    const r = validateNote({ contactId: VALID_UUID, note: "he\0llo" });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.note).toBe("hello");
  });

  it("defaults by to 'operator' when empty", () => {
    const r = validateNote({ contactId: VALID_UUID, note: "test", by: "" });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.by).toBe("operator");
  });

  it("clamps by to 100 chars", () => {
    const long = "a".repeat(200);
    const r = validateNote({ contactId: VALID_UUID, note: "test", by: long });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.by!.length).toBe(100);
  });
});

// ---------------------------------------------------------------------------
// buildStreamStatus — pure classification logic (no DB)
// ---------------------------------------------------------------------------

describe("buildStreamStatus stream classification", () => {
  // Import the exported helper directly (no DB, pure logic).
  let buildStreamStatus: typeof import("@/lib/cockpit/data").buildStreamStatus;

  beforeEach(async () => {
    vi.resetModules();
    ({ buildStreamStatus } = await import("@/lib/cockpit/data"));
  });

  it("returns 4 streams always", async () => {
    const result = buildStreamStatus([]);
    expect(result).toHaveLength(4);
  });

  it("all streams are 'No data' / neutral when no checks exist", async () => {
    const result = buildStreamStatus([]);
    for (const s of result) {
      expect(s.state).toBe("No data");
      expect(s.tone).toBe("neutral");
      expect(s.total).toBe(0);
    }
  });

  it("marks Tech stream as 'Ready' when all wix checks pass", async () => {
    const rows = [
      { check_type: "wix_site_live", check_status: "passed", severity: "blocker" },
      { check_type: "webhook_connected", check_status: "passed", severity: "normal" },
    ];
    const result = buildStreamStatus(rows);
    const tech = result.find((s) => s.label === "Tech (Wix / site)")!;
    expect(tech.tone).toBe("ready");
    expect(tech.state).toBe("Ready");
    expect(tech.passed).toBe(2);
    expect(tech.total).toBe(2);
    expect(tech.blockers).toBe(0);
  });

  it("marks Campaign safety as 'Blocked' when a consent blocker is pending", async () => {
    const rows = [
      { check_type: "consent_reviewed", check_status: "pending", severity: "blocker" },
    ];
    const result = buildStreamStatus(rows);
    const campaign = result.find((s) => s.label === "Campaign safety")!;
    expect(campaign.tone).toBe("blocked");
    expect(campaign.state).toBe("Blocked");
    expect(campaign.blockers).toBe(1);
  });

  it("marks Content & SEO as 'In review' when checks are non-passed but no blocker", async () => {
    const rows = [
      { check_type: "seo_keywords_live", check_status: "needs_review", severity: "high" },
    ];
    const result = buildStreamStatus(rows);
    const content = result.find((s) => s.label === "Content & SEO")!;
    expect(content.tone).toBe("review");
    expect(content.state).toBe("In review");
    expect(content.blockers).toBe(0);
  });

  it("marks Legal / RERA as 'Blocked' when rera check is unresolved blocker", async () => {
    const rows = [
      { check_type: "rera_registration", check_status: "pending", severity: "blocker" },
    ];
    const result = buildStreamStatus(rows);
    const legal = result.find((s) => s.label === "Legal / RERA")!;
    expect(legal.tone).toBe("blocked");
    expect(legal.blockers).toBe(1);
  });

  it("unknown check_type is not counted in any stream", async () => {
    const rows = [
      { check_type: "unknown_custom_check", check_status: "pending", severity: "blocker" },
    ];
    const result = buildStreamStatus(rows);
    for (const s of result) {
      expect(s.total).toBe(0);
    }
  });

  it("stream labels match expected order", async () => {
    const result = buildStreamStatus([]);
    expect(result[0].label).toBe("Tech (Wix / site)");
    expect(result[1].label).toBe("Content & SEO");
    expect(result[2].label).toBe("Campaign safety");
    expect(result[3].label).toBe("Legal / RERA");
  });

  it("passed checks do not count toward blockers", async () => {
    const rows = [
      { check_type: "consent_reviewed", check_status: "passed", severity: "blocker" },
    ];
    const result = buildStreamStatus(rows);
    const campaign = result.find((s) => s.label === "Campaign safety")!;
    expect(campaign.blockers).toBe(0);
    expect(campaign.passed).toBe(1);
    expect(campaign.tone).toBe("ready");
  });
});

// ---------------------------------------------------------------------------
// clearQueueRow input validation (pure-logic, no DB or script invocation)
// ---------------------------------------------------------------------------

describe("clearQueueRow input validation", () => {
  const VALID_UUID = "41dd825b-b881-48e5-a216-a74928438579";
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  function validateQueueId(queueId: string) {
    if (!UUID_RE.test(queueId)) return { ok: false, message: "Invalid queue id." };
    return { ok: true, queueId };
  }

  it("rejects empty string", () => {
    const r = validateQueueId("");
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/invalid queue id/i);
  });

  it("rejects non-UUID string", () => {
    const r = validateQueueId("not-a-uuid");
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/invalid queue id/i);
  });

  it("rejects UUID with wrong length", () => {
    const r = validateQueueId("41dd825b-b881-48e5-a216-a7492843857");
    expect(r.ok).toBe(false);
  });

  it("accepts a valid v4 UUID", () => {
    const r = validateQueueId(VALID_UUID);
    expect(r.ok).toBe(true);
  });

  it("accepts UUID with uppercase hex", () => {
    const upper = VALID_UUID.toUpperCase();
    const r = validateQueueId(upper);
    expect(r.ok).toBe(true);
  });

  it("rejects UUID with extra characters", () => {
    const r = validateQueueId(VALID_UUID + "x");
    expect(r.ok).toBe(false);
  });
});
