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
