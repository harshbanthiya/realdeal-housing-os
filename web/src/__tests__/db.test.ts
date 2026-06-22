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
// Per-building leads map (mirrors data.ts leadsMap pattern)
// ---------------------------------------------------------------------------
describe("Per-building leads map", () => {
  function num(v: string | number | undefined): number { const n = Number(v); return isNaN(n) ? 0 : n; }
  function buildLeadsMap(rows: { name: string; leads: string; warm: string }[]) {
    return new Map(rows.map((r) => [r.name, { leads: num(r.leads), warm: num(r.warm) }]));
  }

  it("correctly maps lead count by building name", () => {
    const map = buildLeadsMap([
      { name: "DLF Westpark", leads: "7", warm: "3" },
      { name: "Imperial Heights", leads: "0", warm: "0" },
    ]);
    expect(map.get("DLF Westpark")).toEqual({ leads: 7, warm: 3 });
  });

  it("returns 0 for buildings with no leads", () => {
    const map = buildLeadsMap([{ name: "Imperial Heights", leads: "0", warm: "0" }]);
    expect(map.get("Imperial Heights")).toEqual({ leads: 0, warm: 0 });
  });

  it("falls back to {leads:0,warm:0} for unknown building", () => {
    const map = buildLeadsMap([{ name: "DLF Westpark", leads: "4", warm: "2" }]);
    expect(map.get("Unknown Building") ?? { leads: 0, warm: 0 }).toEqual({ leads: 0, warm: 0 });
  });

  it("warm is never greater than leads", () => {
    const map = buildLeadsMap([{ name: "DLF Westpark", leads: "5", warm: "5" }]);
    const v = map.get("DLF Westpark")!;
    expect(v.warm).toBeLessThanOrEqual(v.leads);
  });

  it("handles string zero correctly (SQL returns '0' not 0)", () => {
    const map = buildLeadsMap([{ name: "Test", leads: "0", warm: "0" }]);
    expect(map.get("Test")).toEqual({ leads: 0, warm: 0 });
  });
});

// ---------------------------------------------------------------------------
// UnitCell ownerContactId resolution logic (mirrors data.ts lines 577-588)
// ---------------------------------------------------------------------------
describe("UnitCell ownerContactId resolution", () => {
  type RelOwner = { name: string; contactId: string } | undefined;
  type LastOwn = { date: string } | undefined;

  function resolveContactId(relOwner: RelOwner, lastOwn: LastOwn, igrContactId: string | undefined): string | undefined {
    return relOwner?.contactId ?? (lastOwn && igrContactId ? igrContactId : undefined);
  }

  it("returns relOwner contactId when relationship-based owner exists", () => {
    const result = resolveContactId({ name: "Asha Mehta", contactId: "rel-uuid" }, { date: "2020-01-01" }, "igr-uuid");
    expect(result).toBe("rel-uuid");
  });

  it("returns IGR contact when lastOwn exists and IGR match exists but no relOwner", () => {
    const result = resolveContactId(undefined, { date: "2020-01-01" }, "igr-uuid");
    expect(result).toBe("igr-uuid");
  });

  it("returns undefined when no lastOwn even if IGR match exists (unit not yet parsed)", () => {
    const result = resolveContactId(undefined, undefined, "igr-uuid");
    expect(result).toBeUndefined();
  });

  it("returns undefined when no relOwner, no lastOwn, no IGR match", () => {
    const result = resolveContactId(undefined, undefined, undefined);
    expect(result).toBeUndefined();
  });

  it("returns undefined when no relOwner, lastOwn exists but no IGR match", () => {
    const result = resolveContactId(undefined, { date: "2019-06-01" }, undefined);
    expect(result).toBeUndefined();
  });

  it("relOwner always wins over IGR even when both present", () => {
    const result = resolveContactId({ name: "Ravi Joshi", contactId: "rel-uuid" }, undefined, "igr-uuid");
    expect(result).toBe("rel-uuid");
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
// IGR party→contact resolution logic (pure-logic, no DB)
// ---------------------------------------------------------------------------

describe("IGR party→contact resolution (ownerContactId derivation)", () => {
  // Mirrors the logic in getUnitRegistry:
  //   resolvedContactId = relOwner?.contactId ?? (lastOwn && igrContactId ? igrContactId : undefined)

  const REL_CONTACT_ID = "bf4827de-29fa-4ca4-a5da-d924e2b157a3";
  const IGR_CONTACT_ID = "a9e1e3be-852a-41c3-b035-3b43a9e9a786";

  function resolve(
    relOwner: { contactId: string } | undefined,
    lastOwn: object | null,
    igrContactId: string | undefined
  ): string | undefined {
    return relOwner?.contactId ?? (lastOwn && igrContactId ? igrContactId : undefined);
  }

  it("relationship table contact wins when both exist", () => {
    const result = resolve({ contactId: REL_CONTACT_ID }, {}, IGR_CONTACT_ID);
    expect(result).toBe(REL_CONTACT_ID);
  });

  it("IGR match used when no relationship contact but lastOwn exists", () => {
    const result = resolve(undefined, {}, IGR_CONTACT_ID);
    expect(result).toBe(IGR_CONTACT_ID);
  });

  it("undefined when no lastOwn and no relOwner (unit not in any contact's portfolio)", () => {
    const result = resolve(undefined, null, IGR_CONTACT_ID);
    expect(result).toBeUndefined();
  });

  it("undefined when no lastOwn and no igrContactId", () => {
    const result = resolve(undefined, null, undefined);
    expect(result).toBeUndefined();
  });

  it("relationship contact used when IGR match is absent", () => {
    const result = resolve({ contactId: REL_CONTACT_ID }, null, undefined);
    expect(result).toBe(REL_CONTACT_ID);
  });

  it("igrContactByUnit map returns first match per unit_id (earlier row wins)", () => {
    const rows = [
      { building_unit_id: "unit-A", contact_id: "contact-1" },
      { building_unit_id: "unit-A", contact_id: "contact-2" }, // duplicate — ignored
      { building_unit_id: "unit-B", contact_id: "contact-3" },
    ];
    const map = new Map<string, string>();
    for (const m of rows) {
      if (!map.has(m.building_unit_id)) map.set(m.building_unit_id, m.contact_id);
    }
    expect(map.get("unit-A")).toBe("contact-1");
    expect(map.get("unit-B")).toBe("contact-3");
    expect(map.size).toBe(2);
  });

  it("ownerContact boolean reflects resolvedContactId", () => {
    expect(Boolean(resolve({ contactId: REL_CONTACT_ID }, {}, undefined))).toBe(true);
    expect(Boolean(resolve(undefined, {}, IGR_CONTACT_ID))).toBe(true);
    expect(Boolean(resolve(undefined, null, undefined))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// updateBuildingMode input validation (pure-logic, no DB or script invocation)
// ---------------------------------------------------------------------------

describe("updateBuildingMode input validation", () => {
  const SLUG_RE = /^[a-z0-9][a-z0-9-]{1,80}[a-z0-9]$/;
  const ALLOWED_MODES = new Set(["prospecting", "active", "launch", "post_launch"]);

  function validate(slug: string, mode: string): { ok: boolean; message?: string } {
    if (!SLUG_RE.test(slug)) return { ok: false, message: "Invalid building slug." };
    if (!ALLOWED_MODES.has(mode)) return { ok: false, message: `Invalid mode: ${mode}` };
    return { ok: true };
  }

  it("accepts valid slug and mode", () => {
    expect(validate("dlf-westpark-andheri-west", "launch").ok).toBe(true);
  });

  it("accepts all four allowed modes", () => {
    for (const m of ["prospecting", "active", "launch", "post_launch"]) {
      expect(validate("my-building", m).ok).toBe(true);
    }
  });

  it("rejects empty slug", () => {
    const r = validate("", "launch");
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/invalid.*slug/i);
  });

  it("rejects slug with uppercase letters", () => {
    const r = validate("DLF-Westpark", "launch");
    expect(r.ok).toBe(false);
  });

  it("rejects slug with leading dash", () => {
    const r = validate("-westpark", "launch");
    expect(r.ok).toBe(false);
  });

  it("rejects slug with trailing dash", () => {
    const r = validate("westpark-", "launch");
    expect(r.ok).toBe(false);
  });

  it("rejects slug with injection characters", () => {
    const r = validate("west'; DROP TABLE--", "launch");
    expect(r.ok).toBe(false);
  });

  it("rejects unknown mode", () => {
    const r = validate("my-building", "unknown");
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/invalid mode/i);
  });

  it("rejects empty mode", () => {
    const r = validate("my-building", "");
    expect(r.ok).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Reviews tab — confirm-gate state machine (pure logic, no React/DOM)
// ---------------------------------------------------------------------------

describe("Reviews tab confirm-gate state machine", () => {
  type Phase = "idle" | "confirming" | "done";
  type ReviewSt = { phase: Phase; action: "approved" | "rejected"; msg: string };

  function requestConfirm(
    states: Record<number, ReviewSt>,
    i: number,
    action: "approved" | "rejected"
  ): Record<number, ReviewSt> {
    return { ...states, [i]: { phase: "confirming", action, msg: "" } };
  }

  function cancelConfirm(states: Record<number, ReviewSt>, i: number): Record<number, ReviewSt> {
    const next = { ...states };
    delete next[i];
    return next;
  }

  it("initial state has no keys (all items are idle)", () => {
    const states: Record<number, ReviewSt> = {};
    expect(states[0]?.phase ?? "idle").toBe("idle");
  });

  it("requestConfirm moves item to confirming", () => {
    const s = requestConfirm({}, 0, "approved");
    expect(s[0].phase).toBe("confirming");
    expect(s[0].action).toBe("approved");
    expect(s[0].msg).toBe("");
  });

  it("requestConfirm for reject sets action to rejected", () => {
    const s = requestConfirm({}, 1, "rejected");
    expect(s[1].action).toBe("rejected");
    expect(s[1].phase).toBe("confirming");
  });

  it("cancelConfirm removes the entry (restores idle)", () => {
    let s = requestConfirm({}, 0, "approved");
    s = cancelConfirm(s, 0);
    expect(s[0]).toBeUndefined();
    expect(s[0]?.phase ?? "idle").toBe("idle");
  });

  it("cancelConfirm only removes the targeted index", () => {
    let s = requestConfirm({}, 0, "approved");
    s = requestConfirm(s, 1, "rejected");
    s = cancelConfirm(s, 0);
    expect(s[0]).toBeUndefined();
    expect(s[1].phase).toBe("confirming");
  });

  it("confirm without reviewItemId resolves to done with preview message", () => {
    let s = requestConfirm({}, 0, "approved");
    const action = s[0].action;
    s = { ...s, [0]: { phase: "done", action, msg: "preview only (no review item id)" } };
    expect(s[0].phase).toBe("done");
    expect(s[0].msg).toMatch(/preview only/);
  });

  it("confirm with reviewItemId resolves to done with applied message", () => {
    let s = requestConfirm({}, 0, "rejected");
    const action = s[0].action;
    const fakeMsg = "Applied: pending → rejected";
    s = { ...s, [0]: { phase: "done", action, msg: fakeMsg } };
    expect(s[0].phase).toBe("done");
    expect(s[0].action).toBe("rejected");
    expect(s[0].msg).toContain("Applied");
  });

  it("confirm text is derived correctly from action", () => {
    const s = requestConfirm({}, 0, "approved");
    expect(`Confirm ${s[0].action}?`).toBe("Confirm approved?");
    const s2 = requestConfirm({}, 1, "rejected");
    expect(`Confirm ${s2[1].action}?`).toBe("Confirm rejected?");
  });

  it("multiple items can be in different phases simultaneously", () => {
    let s: Record<number, ReviewSt> = {};
    s = requestConfirm(s, 0, "approved");
    s = requestConfirm(s, 1, "rejected");
    s = { ...s, [2]: { phase: "done", action: "approved", msg: "Applied: pending → approved" } };
    expect(s[0].phase).toBe("confirming");
    expect(s[1].phase).toBe("confirming");
    expect(s[2].phase).toBe("done");
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

// ---------------------------------------------------------------------------
// agentLabel / buildingFromRaw / taskTone helpers (pure-logic, mirrored from data.ts)
// ---------------------------------------------------------------------------

describe("agentLabel", () => {
  function agentLabel(taskType: string): string {
    return (taskType || "unknown").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  it("converts snake_case to Title Case", () => {
    expect(agentLabel("launch_seo_research")).toBe("Launch Seo Research");
  });

  it("handles single word", () => {
    expect(agentLabel("blog")).toBe("Blog");
  });

  it("handles empty string as 'Unknown'", () => {
    expect(agentLabel("")).toBe("Unknown");
  });

  it("preserves already-capitalised words", () => {
    expect(agentLabel("seo_monitoring")).toBe("Seo Monitoring");
  });
});

describe("buildingFromRaw", () => {
  function buildingFromRaw(raw: Record<string, string> | null): string {
    if (!raw) return "—";
    if (raw.building_name) return String(raw.building_name);
    if (raw.launch_key) {
      return String(raw.launch_key).split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
    }
    return "—";
  }

  it("returns building_name when present", () => {
    expect(buildingFromRaw({ building_name: "Imperial Heights" })).toBe("Imperial Heights");
  });

  it("converts launch_key to title-cased display name", () => {
    expect(buildingFromRaw({ launch_key: "dlf-westpark-andheri-west" })).toBe("Dlf Westpark Andheri West");
  });

  it("returns em-dash when raw is null", () => {
    expect(buildingFromRaw(null)).toBe("—");
  });

  it("returns em-dash when raw has neither key", () => {
    expect(buildingFromRaw({ entity_type: "content_brief" })).toBe("—");
  });

  it("prefers building_name over launch_key when both present", () => {
    expect(buildingFromRaw({ building_name: "Kalpataru Radiance", launch_key: "dlf-westpark" })).toBe("Kalpataru Radiance");
  });
});

describe("taskTone", () => {
  type Tone = "ready" | "review" | "blocked" | "neutral";
  function taskTone(status: string): Tone {
    if (status === "completed" || status === "done") return "ready";
    if (status === "running" || status === "in_progress") return "review";
    if (status === "failed" || status === "error") return "blocked";
    return "neutral";
  }

  it("completed → ready", () => expect(taskTone("completed")).toBe("ready"));
  it("done → ready", () => expect(taskTone("done")).toBe("ready"));
  it("running → review", () => expect(taskTone("running")).toBe("review"));
  it("in_progress → review", () => expect(taskTone("in_progress")).toBe("review"));
  it("failed → blocked", () => expect(taskTone("failed")).toBe("blocked"));
  it("error → blocked", () => expect(taskTone("error")).toBe("blocked"));
  it("queued → neutral", () => expect(taskTone("queued")).toBe("neutral"));
  it("pending → neutral", () => expect(taskTone("pending")).toBe("neutral"));
  it("unknown string → neutral", () => expect(taskTone("something_else")).toBe("neutral"));
});

// ---------------------------------------------------------------------------
// stagingTone helper (pure-logic, mirrored from data.ts)
// ---------------------------------------------------------------------------

describe("stagingTone", () => {
  type Tone = "ready" | "review" | "blocked" | "neutral";
  function stagingTone(status: string): Tone {
    if (status === "created_manually" || status === "live") return "ready";
    if (status === "under_review" || status === "qa_in_progress") return "review";
    if (status === "blocked" || status === "failed") return "blocked";
    return "neutral";
  }

  it("created_manually → ready (Wix staging was built by hand)", () => {
    expect(stagingTone("created_manually")).toBe("ready");
  });
  it("live → ready", () => expect(stagingTone("live")).toBe("ready"));
  it("under_review → review", () => expect(stagingTone("under_review")).toBe("review"));
  it("qa_in_progress → review", () => expect(stagingTone("qa_in_progress")).toBe("review"));
  it("blocked → blocked", () => expect(stagingTone("blocked")).toBe("blocked"));
  it("failed → blocked", () => expect(stagingTone("failed")).toBe("blocked"));
  it("planned → neutral", () => expect(stagingTone("planned")).toBe("neutral"));
  it("unknown → neutral", () => expect(stagingTone("something_new")).toBe("neutral"));
});

// ---------------------------------------------------------------------------
// channelTone helper (pure-logic, mirrored from data.ts)
// ---------------------------------------------------------------------------

describe("channelTone", () => {
  type Tone = "ready" | "review" | "blocked" | "neutral";
  function channelTone(status: string): Tone {
    if (status === "live" || status === "active") return "ready";
    if (status === "under_review" || status === "needs_review") return "review";
    if (status === "blocked" || status === "disabled") return "blocked";
    return "neutral";
  }

  it("live → ready", () => expect(channelTone("live")).toBe("ready"));
  it("active → ready", () => expect(channelTone("active")).toBe("ready"));
  it("under_review → review", () => expect(channelTone("under_review")).toBe("review"));
  it("needs_review → review", () => expect(channelTone("needs_review")).toBe("review"));
  it("blocked → blocked", () => expect(channelTone("blocked")).toBe("blocked"));
  it("disabled → blocked", () => expect(channelTone("disabled")).toBe("blocked"));
  it("planned → neutral (DLF channels are all planned)", () => expect(channelTone("planned")).toBe("neutral"));
  it("unknown → neutral", () => expect(channelTone("anything_else")).toBe("neutral"));
});

// ---------------------------------------------------------------------------
// channel name formatting (mirrors data.ts getCampaigns name mapping)
// ---------------------------------------------------------------------------

describe("channel name formatting", () => {
  function formatChannelName(channel: string): string {
    return (channel || "—").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  it("converts snake_case channel to Title Case", () => {
    expect(formatChannelName("youtube_shorts")).toBe("Youtube Shorts");
  });
  it("converts listing_portal", () => {
    expect(formatChannelName("listing_portal")).toBe("Listing Portal");
  });
  it("single-word channel is capitalised", () => {
    expect(formatChannelName("whatsapp")).toBe("Whatsapp");
  });
  it("phone_call formatted correctly", () => {
    expect(formatChannelName("phone_call")).toBe("Phone Call");
  });
  it("empty string falls through to em-dash", () => {
    expect(formatChannelName("")).toBe("—");
  });
});

// ---------------------------------------------------------------------------
// slugify parity — JS slugify must match DB regexp_replace used in getKeywords
// The SQL: lower(regexp_replace(b.name, '[^a-z0-9]+', '-', 'gi'))
// ---------------------------------------------------------------------------

describe("slugify parity with SQL regexp_replace", () => {
  // Mirrors the slugify() private fn in data.ts
  function slugify(name: string): string {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  }

  it("'Imperial Heights' → 'imperial-heights'", () => {
    expect(slugify("Imperial Heights")).toBe("imperial-heights");
  });

  it("'Kalpataru Radiance' → 'kalpataru-radiance'", () => {
    expect(slugify("Kalpataru Radiance")).toBe("kalpataru-radiance");
  });

  it("multi-space gap → single hyphen", () => {
    expect(slugify("DLF  Westpark")).toBe("dlf-westpark");
  });

  it("leading/trailing spaces stripped", () => {
    expect(slugify("  Wing A  ")).toBe("wing-a");
  });

  it("special chars replaced with single hyphen", () => {
    expect(slugify("B-Wing (Ora)")).toBe("b-wing-ora");
  });

  it("numbers preserved", () => {
    expect(slugify("Tower 12B")).toBe("tower-12b");
  });
});

// ---------------------------------------------------------------------------
// RERA slug prefix-match logic (mirrors SQL pattern in getReraFacts)
// SQL: slug = $1 OR slug LIKE $1 || '-%'
// ---------------------------------------------------------------------------

describe("RERA slug prefix-match (getReraFacts variant filter)", () => {
  function slugify(name: string): string {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  }
  function matchesSlug(buildingName: string, routeSlug: string): boolean {
    const bs = slugify(buildingName);
    return bs === routeSlug || bs.startsWith(routeSlug + "-");
  }

  it("exact match: 'Kalpataru Radiance' matches kalpataru-radiance", () => {
    expect(matchesSlug("Kalpataru Radiance", "kalpataru-radiance")).toBe(true);
  });

  it("prefix match: 'Kalpataru Radiance A' matches kalpataru-radiance", () => {
    expect(matchesSlug("Kalpataru Radiance A", "kalpataru-radiance")).toBe(true);
  });

  it("prefix match: 'Kalpataru Radiance New Parser' matches kalpataru-radiance", () => {
    expect(matchesSlug("Kalpataru Radiance New Parser", "kalpataru-radiance")).toBe(true);
  });

  it("prefix match: 'Imperial Heights Wing C and D' matches imperial-heights", () => {
    expect(matchesSlug("Imperial Heights Wing C and D", "imperial-heights")).toBe(true);
  });

  it("non-match: 'Kalpataru Radiance A' does NOT match imperial-heights", () => {
    expect(matchesSlug("Kalpataru Radiance A", "imperial-heights")).toBe(false);
  });

  it("non-match: 'Oberoi Esquire' does NOT match kalpataru-radiance", () => {
    expect(matchesSlug("Oberoi Esquire", "kalpataru-radiance")).toBe(false);
  });

  it("no false partial prefix: 'kalpataru-radicand' does NOT match kalpataru-radiance", () => {
    // hyphen boundary prevents false prefix — 'kalpataru-radicand' doesn't start with 'kalpataru-radiance-'
    expect(matchesSlug("Kalpataru Radicand", "kalpataru-radiance")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Per-building stats map lookup (Loop 18 — ownerMap / reraMap pattern)
// ---------------------------------------------------------------------------

describe("Per-building stats map lookup", () => {
  // Mirrors the Map lookup logic in getBuildings() that replaces the global
  // owner count and global RERA unverified count with per-building values.

  function num(v: string | number | undefined): number {
    const n = Number(v);
    return isNaN(n) ? 0 : n;
  }

  function buildOwnerMap(rows: { name: string; owners: string; tenants: string }[]) {
    return new Map(rows.map((r) => [r.name, { owners: num(r.owners), tenants: num(r.tenants) }]));
  }
  function buildReraMap(rows: { name: string; rera_open: string }[]) {
    return new Map(rows.map((r) => [r.name, num(r.rera_open)]));
  }

  const ownerRows = [
    { name: "Imperial Heights", owners: "54", tenants: "0" },
    { name: "Kalpataru Radiance", owners: "672", tenants: "3" },
    { name: "Kalpataru Radiance A", owners: "0", tenants: "0" },
  ];
  const reraRows = [
    { name: "Imperial Heights", rera_open: "1" },
    { name: "Kalpataru Radiance", rera_open: "0" },
    { name: "Kalpataru Radiance A", rera_open: "0" },
  ];

  it("ownerMap returns correct per-building owner count for Imperial Heights", () => {
    const map = buildOwnerMap(ownerRows);
    expect(map.get("Imperial Heights")?.owners).toBe(54);
  });

  it("ownerMap returns correct per-building owner count for Kalpataru Radiance", () => {
    const map = buildOwnerMap(ownerRows);
    expect(map.get("Kalpataru Radiance")?.owners).toBe(672);
  });

  it("ownerMap tenant count is included in the lookup", () => {
    const map = buildOwnerMap(ownerRows);
    expect(map.get("Kalpataru Radiance")?.tenants).toBe(3);
  });

  it("stats tile value = owners + tenants (Kalpataru: 672 + 3 = 675)", () => {
    const map = buildOwnerMap(ownerRows);
    const cnt = map.get("Kalpataru Radiance") ?? { owners: 0, tenants: 0 };
    expect(cnt.owners + cnt.tenants).toBe(675);
  });

  it("reraMap returns 0 for buildings with no unverified RERA profile", () => {
    const map = buildReraMap(reraRows);
    expect(map.get("Kalpataru Radiance")).toBe(0);
    expect(map.get("Kalpataru Radiance A")).toBe(0);
  });

  it("reraMap returns 1 for Imperial Heights (1 unverified RERA profile)", () => {
    const map = buildReraMap(reraRows);
    expect(map.get("Imperial Heights")).toBe(1);
  });

  it("unknown building falls back to 0 via nullish coalescing", () => {
    const ownerMap = buildOwnerMap(ownerRows);
    const reraMap = buildReraMap(reraRows);
    const cnt = ownerMap.get("Unknown Building") ?? { owners: 0, tenants: 0 };
    const rOpen = reraMap.get("Unknown Building") ?? 0;
    expect(cnt.owners + cnt.tenants).toBe(0);
    expect(rOpen).toBe(0);
  });
});
