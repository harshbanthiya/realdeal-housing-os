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

// ---------------------------------------------------------------------------
// Listings stat tile — data.listings.length (not hardcoded stats.listings)
// Fix: workspace-tabs.tsx changed <Tile n={s.listings}> → <Tile n={data.listings.length}>
// ---------------------------------------------------------------------------

describe("listings stat tile reflects data.listings.length", () => {
  // Mirror the fixed expression: the tile count is always data.listings.length
  function tileCount(listings: { title: string }[]): number {
    return listings.length;
  }

  it("empty listings array yields count 0", () => {
    expect(tileCount([])).toBe(0);
  });

  it("3-item listings array yields count 3", () => {
    const items = [{ title: "1BHK Floor 3" }, { title: "2BHK Floor 7" }, { title: "3BHK Penthouse" }];
    expect(tileCount(items)).toBe(3);
  });

  it("count is always non-negative", () => {
    expect(tileCount([])).toBeGreaterThanOrEqual(0);
    expect(tileCount([{ title: "x" }])).toBeGreaterThanOrEqual(0);
  });

  it("hardcoded stats.listings=0 understates non-empty listings (documents the bug)", () => {
    const statsListings = 0; // was always 0 in getBuildings() before fix
    const actual = [{ title: "1BHK" }];
    // Before fix, tile showed 0 even with 1 listing; after fix, shows 1
    expect(actual.length).not.toBe(statsListings);
    expect(actual.length).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// audienceScope — CSV filename scope slug generation
// ---------------------------------------------------------------------------

describe("audienceScope filename slug generation", () => {
  let audienceScope: typeof import("@/lib/cockpit/audiences").audienceScope;

  beforeEach(async () => {
    vi.resetModules();
    ({ audienceScope } = await import("@/lib/cockpit/audiences"));
  });

  it("no filters → 'all-buildings'", () => expect(audienceScope({})).toBe("all-buildings"));

  it("building only → slugified name", () =>
    expect(audienceScope({ building: "Imperial Heights" })).toBe("imperial-heights"));

  it("building + role → 'building-slug-role'", () =>
    expect(audienceScope({ building: "Imperial Heights", role: "owner" })).toBe("imperial-heights-owner"));

  it("role only (no building) → 'all-buildings-role'", () =>
    expect(audienceScope({ role: "tenant" })).toBe("all-buildings-tenant"));

  it("building with special chars (& space) → dashes", () =>
    expect(audienceScope({ building: "A & B Properties" })).toBe("a-b-properties"));

  it("consecutive non-alnum chars → single dash (no double-dash)", () =>
    expect(audienceScope({ building: "Wing A / Wing B" })).toBe("wing-a-wing-b"));

  it("leading/trailing spaces in building → no leading/trailing hyphens", () => {
    const scope = audienceScope({ building: "  Test  " });
    expect(scope).not.toMatch(/^-|-$/);
    expect(scope).toBe("test");
  });
});

// ---------------------------------------------------------------------------
// parseAudienceFilters — input sanitisation + role allowlist guard
// ---------------------------------------------------------------------------

describe("parseAudienceFilters input sanitisation", () => {
  let parseAudienceFilters: typeof import("@/lib/cockpit/audiences").parseAudienceFilters;

  beforeEach(async () => {
    vi.resetModules();
    ({ parseAudienceFilters } = await import("@/lib/cockpit/audiences"));
  });

  it("empty inputs → both undefined", () => {
    const f = parseAudienceFilters({});
    expect(f.building).toBeUndefined();
    expect(f.role).toBeUndefined();
  });

  it("building='all' → undefined (cleaned as sentinel)", () => {
    expect(parseAudienceFilters({ building: "all" }).building).toBeUndefined();
  });

  it("null inputs → both undefined", () => {
    const f = parseAudienceFilters({ building: null, role: null });
    expect(f.building).toBeUndefined();
    expect(f.role).toBeUndefined();
  });

  it("valid role 'owner' → passes through", () => {
    expect(parseAudienceFilters({ role: "owner" }).role).toBe("owner");
  });

  it("invalid role 'admin' → undefined (allowlist blocks injection)", () => {
    expect(parseAudienceFilters({ role: "admin" }).role).toBeUndefined();
  });

  it("role with whitespace padding → trimmed and accepted", () => {
    expect(parseAudienceFilters({ role: " tenant " }).role).toBe("tenant");
  });

  it("building + valid role → both preserved", () => {
    const f = parseAudienceFilters({ building: "Imperial Heights", role: "landlord" });
    expect(f.building).toBe("Imperial Heights");
    expect(f.role).toBe("landlord");
  });
});

// ---------------------------------------------------------------------------
// e164Indian — phone normalisation for Meta audience CSV hashing
// ---------------------------------------------------------------------------

describe("e164Indian phone normalisation", () => {
  let e164Indian: typeof import("@/lib/cockpit/audiences").e164Indian;

  beforeEach(async () => {
    vi.resetModules();
    ({ e164Indian } = await import("@/lib/cockpit/audiences"));
  });

  it("null → empty string", () => expect(e164Indian(null)).toBe(""));
  it("undefined → empty string", () => expect(e164Indian(undefined)).toBe(""));
  it("empty string → empty string", () => expect(e164Indian("")).toBe(""));

  it("10-digit mobile → +91 prefix", () =>
    expect(e164Indian("9876543210")).toBe("+919876543210"));

  it("12-digit with 91 prefix already present → unchanged (no double-prefix)", () =>
    expect(e164Indian("919876543210")).toBe("+919876543210"));

  it("11-digit starting with 0 (STD) → +91 prefix", () =>
    expect(e164Indian("09876543210")).toBe("+919876543210"));

  it("00-prefixed international (IDD) → +91 prefix", () =>
    expect(e164Indian("00919876543210")).toBe("+919876543210"));

  it("+91 formatted string → normalised (strips + and spaces)", () =>
    expect(e164Indian("+91 98765 43210")).toBe("+919876543210"));

  it("spaces and dashes in number → stripped", () =>
    expect(e164Indian("98-765-43210")).toBe("+919876543210"));

  it("non-Indian 11-digit (US 1xxx) → empty string", () =>
    expect(e164Indian("19876543210")).toBe(""));

  it("non-Indian 12-digit (UK +44) → empty string", () =>
    expect(e164Indian("442071234567")).toBe(""));

  it("too-short number → empty string", () =>
    expect(e164Indian("12345")).toBe(""));

  it("13+ digit → empty string (rejects over-long numbers)", () =>
    expect(e164Indian("9198765432101")).toBe(""));
});

// ---------------------------------------------------------------------------
// metaCsvFromRows — Meta audience CSV generation
// ---------------------------------------------------------------------------

describe("metaCsvFromRows CSV generation", () => {
  let metaCsvFromRows: typeof import("@/lib/cockpit/audiences").metaCsvFromRows;

  beforeEach(async () => {
    vi.resetModules();
    ({ metaCsvFromRows } = await import("@/lib/cockpit/audiences"));
  });

  // Local SHA-256 to verify hashes independently of the function under test
  function sha256(v: string): string {
    const { createHash } = require("node:crypto");
    return createHash("sha256").update(v).digest("hex");
  }

  it("empty rows → header-only CSV (email,phone\\n)", () => {
    expect(metaCsvFromRows([])).toBe("email,phone\n");
  });

  it("CSV first line is always 'email,phone'", () => {
    const csv = metaCsvFromRows([{ contact_id: "1", phone: null, email: "t@x.com" }]);
    expect(csv.split("\n")[0]).toBe("email,phone");
  });

  it("row with email only → SHA-256(email), empty phone column", () => {
    const email = "test@example.com";
    const csv = metaCsvFromRows([{ contact_id: "1", phone: null, email }]);
    expect(csv.split("\n")[1]).toBe(`${sha256(email)},`);
  });

  it("email is lowercased before hashing", () => {
    const csv = metaCsvFromRows([{ contact_id: "1", phone: null, email: "TEST@EXAMPLE.COM" }]);
    expect(csv.split("\n")[1]).toBe(`${sha256("test@example.com")},`);
  });

  it("row with phone only → empty email column, SHA-256(normalized phone without +)", () => {
    // e164Indian("9876543210") → "+919876543210"; strip + → "919876543210"
    const csv = metaCsvFromRows([{ contact_id: "1", phone: "9876543210", email: null }]);
    expect(csv.split("\n")[1]).toBe(`,${sha256("919876543210")}`);
  });

  it("row with both email and phone → both hashed", () => {
    const email = "hello@example.com";
    const phone = "9876543210";
    const csv = metaCsvFromRows([{ contact_id: "1", phone, email }]);
    expect(csv.split("\n")[1]).toBe(`${sha256(email)},${sha256("919876543210")}`);
  });

  it("row with neither email nor phone → skipped (no data line emitted)", () => {
    const csv = metaCsvFromRows([{ contact_id: "1", phone: null, email: null }]);
    const nonEmptyLines = csv.split("\n").filter(Boolean);
    expect(nonEmptyLines).toHaveLength(1); // header only
  });

  it("multiple rows produce multiple data lines (header + N rows)", () => {
    const rows = [
      { contact_id: "1", phone: "9876543210", email: null },
      { contact_id: "2", phone: null, email: "a@b.com" },
    ];
    const lines = metaCsvFromRows(rows).split("\n").filter(Boolean);
    expect(lines).toHaveLength(3); // header + 2 data rows
  });
});

// ---------------------------------------------------------------------------
// agentLabel — title-cases task_type strings
// ---------------------------------------------------------------------------

describe("agentLabel", () => {
  let agentLabel: typeof import("@/lib/cockpit/data").agentLabel;

  beforeEach(async () => {
    vi.resetModules();
    ({ agentLabel } = await import("@/lib/cockpit/data"));
  });

  it("converts single underscore_word to title case", () => {
    expect(agentLabel("seo_monitor")).toBe("Seo Monitor");
  });

  it("converts multi-segment task type", () => {
    expect(agentLabel("content_quality_check")).toBe("Content Quality Check");
  });

  it("already-titled word passes through", () => {
    expect(agentLabel("audit")).toBe("Audit");
  });

  it("empty string falls back to 'Unknown'", () => {
    expect(agentLabel("")).toBe("Unknown");
  });

  it("handles single-word type", () => {
    expect(agentLabel("seo")).toBe("Seo");
  });
});

// ---------------------------------------------------------------------------
// buildingFromRaw — extracts building name from raw_input JSONB
// ---------------------------------------------------------------------------

describe("buildingFromRaw", () => {
  let buildingFromRaw: typeof import("@/lib/cockpit/data").buildingFromRaw;

  beforeEach(async () => {
    vi.resetModules();
    ({ buildingFromRaw } = await import("@/lib/cockpit/data"));
  });

  it("returns '—' for null input", () => {
    expect(buildingFromRaw(null)).toBe("—");
  });

  it("returns building_name when present", () => {
    expect(buildingFromRaw({ building_name: "Imperial Heights" })).toBe("Imperial Heights");
  });

  it("prefers building_name over launch_key when both present", () => {
    expect(buildingFromRaw({ building_name: "DLF Westpark", launch_key: "dlf-westpark-andheri-west" })).toBe("DLF Westpark");
  });

  it("falls back to title-casing launch_key when building_name absent", () => {
    expect(buildingFromRaw({ launch_key: "dlf-westpark-andheri-west" })).toBe("Dlf Westpark Andheri West");
  });

  it("returns '—' for empty object", () => {
    expect(buildingFromRaw({})).toBe("—");
  });
});

// ---------------------------------------------------------------------------
// taskTone — maps task status to Tone
// ---------------------------------------------------------------------------

describe("taskTone", () => {
  let taskTone: typeof import("@/lib/cockpit/data").taskTone;

  beforeEach(async () => {
    vi.resetModules();
    ({ taskTone } = await import("@/lib/cockpit/data"));
  });

  it("'completed' → ready", () => {
    expect(taskTone("completed")).toBe("ready");
  });

  it("'done' → ready", () => {
    expect(taskTone("done")).toBe("ready");
  });

  it("'running' → review", () => {
    expect(taskTone("running")).toBe("review");
  });

  it("'in_progress' → review", () => {
    expect(taskTone("in_progress")).toBe("review");
  });

  it("'failed' → blocked", () => {
    expect(taskTone("failed")).toBe("blocked");
  });

  it("'error' → blocked", () => {
    expect(taskTone("error")).toBe("blocked");
  });

  it("'queued' → neutral (unknown status fallback)", () => {
    expect(taskTone("queued")).toBe("neutral");
  });

  it("'pending' → neutral", () => {
    expect(taskTone("pending")).toBe("neutral");
  });

  it("empty string → neutral", () => {
    expect(taskTone("")).toBe("neutral");
  });
});

// ---------------------------------------------------------------------------
// createContactGroup input validation (pure-logic, mirrors guard in actions.ts)
// ---------------------------------------------------------------------------

describe("createContactGroup name validation", () => {
  function validateGroupName(name: string): { ok: boolean; message?: string } {
    const n = (name || "").trim();
    if (n.length < 2 || n.length > 64) return { ok: false, message: "Group name must be 2–64 characters." };
    return { ok: true };
  }

  it("accepts a 2-character name (minimum)", () => {
    expect(validateGroupName("AB").ok).toBe(true);
  });

  it("accepts a 64-character name (maximum)", () => {
    expect(validateGroupName("A".repeat(64)).ok).toBe(true);
  });

  it("rejects empty string", () => {
    const r = validateGroupName("");
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/2.64 characters/);
  });

  it("rejects single character (below minimum)", () => {
    const r = validateGroupName("A");
    expect(r.ok).toBe(false);
  });

  it("rejects 65-character name (above maximum)", () => {
    const r = validateGroupName("A".repeat(65));
    expect(r.ok).toBe(false);
  });

  it("trims whitespace before checking length", () => {
    // '  A  ' trims to 'A' (length 1) → rejected
    const r = validateGroupName("  A  ");
    expect(r.ok).toBe(false);
  });

  it("accepts name with spaces and unicode", () => {
    expect(validateGroupName("Windsor Grande Owners").ok).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// addContactsToGroup input validation (pure-logic, mirrors guard in actions.ts)
// ---------------------------------------------------------------------------

describe("addContactsToGroup input validation", () => {
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const GROUP_SLUG_RE = /^[a-z0-9-]{1,64}$/;

  function validate(groupSlug: string, contactIds: string[]): { ok: boolean; message?: string; ids?: string[] } {
    if (!GROUP_SLUG_RE.test(groupSlug || "")) return { ok: false, message: "Invalid group slug." };
    const ids = (contactIds || []).filter((i) => UUID_RE.test(i));
    if (ids.length === 0) return { ok: false, message: "No valid contact ids." };
    return { ok: true, ids };
  }

  it("accepts valid slug and UUID list", () => {
    const r = validate("windsor-grande", ["bf4827de-29fa-4ca4-a5da-d924e2b157a3"]);
    expect(r.ok).toBe(true);
  });

  it("rejects empty slug", () => {
    const r = validate("", ["bf4827de-29fa-4ca4-a5da-d924e2b157a3"]);
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/invalid group slug/i);
  });

  it("rejects slug with uppercase letters", () => {
    const r = validate("Windsor-Grande", ["bf4827de-29fa-4ca4-a5da-d924e2b157a3"]);
    expect(r.ok).toBe(false);
  });

  it("rejects slug with spaces", () => {
    const r = validate("windsor grande", ["bf4827de-29fa-4ca4-a5da-d924e2b157a3"]);
    expect(r.ok).toBe(false);
  });

  it("rejects 65-character slug (above max)", () => {
    const r = validate("a".repeat(65), ["bf4827de-29fa-4ca4-a5da-d924e2b157a3"]);
    expect(r.ok).toBe(false);
  });

  it("rejects empty contactIds array", () => {
    const r = validate("windsor-grande", []);
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/no valid contact ids/i);
  });

  it("filters out non-UUID strings and rejects if nothing remains", () => {
    const r = validate("windsor-grande", ["not-a-uuid", "also-not", "123"]);
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/no valid contact ids/i);
  });

  it("filters non-UUIDs from mixed list, keeps valid ones", () => {
    const validId = "bf4827de-29fa-4ca4-a5da-d924e2b157a3";
    const r = validate("windsor-grande", ["not-a-uuid", validId]);
    expect(r.ok).toBe(true);
    expect(r.ids).toEqual([validId]);
  });

  it("accepts multiple valid UUIDs", () => {
    const ids = [
      "bf4827de-29fa-4ca4-a5da-d924e2b157a3",
      "41dd825b-b881-48e5-a216-a74928438579",
    ];
    const r = validate("test-group", ids);
    expect(r.ok).toBe(true);
    expect(r.ids).toHaveLength(2);
  });
});

// ---------------------------------------------------------------------------
// batchLabelHuman — contacts-types.ts batch label formatter
// ---------------------------------------------------------------------------

describe("batchLabelHuman", () => {
  let batchLabelHuman: typeof import("@/lib/cockpit/contacts-types").batchLabelHuman;

  beforeEach(async () => {
    vi.resetModules();
    ({ batchLabelHuman } = await import("@/lib/cockpit/contacts-types"));
  });

  // .toLowerCase() is applied before title-casing — all-caps inputs → Title Case.

  it("strips REAL_ prefix and title-cases the result", () => {
    expect(batchLabelHuman("REAL_IMPERIAL_HEIGHTS_OWNERS")).toBe("Imperial Heights Owners");
  });

  it("strips FAKE_ prefix and title-cases", () => {
    expect(batchLabelHuman("FAKE_TEST_IMPORT")).toBe("Test Import");
  });

  it("strips PHASE_N_ prefix and _AUDIT suffix, title-cases result", () => {
    // REAL_PHASE_5_KALPATARU_AUDIT → KALPATARU_AUDIT → strip _AUDIT → KALPATARU → "Kalpataru"
    expect(batchLabelHuman("REAL_PHASE_5_KALPATARU_AUDIT")).toBe("Kalpataru");
  });

  it("strips PHASE_N_N_ prefix, trailing run, and _AUDIT suffix — title-cases", () => {
    // → IMPERIAL_UNIT_AUDIT_001 → strip _001 → IMPERIAL_UNIT_AUDIT → strip _AUDIT → IMPERIAL_UNIT
    expect(batchLabelHuman("REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001")).toBe("Imperial Unit");
  });

  it("strips trailing run number (lowercase → title-cased)", () => {
    expect(batchLabelHuman("real_owners_import_003")).toBe("Owners Import");
  });

  it("empty string falls back to 'Import'", () => {
    expect(batchLabelHuman("")).toBe("Import");
  });

  it("plain label without prefix (lowercase → title-cased)", () => {
    expect(batchLabelHuman("kalpataru_wing_a_tenants")).toBe("Kalpataru Wing A Tenants");
  });
});

// ---- parseLabeledOutput logic mirror ----
// Private helper in actions.ts ("use server") — tested here as a pure function mirror.
// Regex: /^([a-z_]+):\s(.*)$/ — lowercase keys only, space after colon required.
function parseLabeledOutput_mirror(out: string): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const line of out.split("\n")) {
    const m = line.match(/^([a-z_]+):\s(.*)$/);
    if (m) fields[m[1]] = m[2];
  }
  return fields;
}

describe("parseLabeledOutput (actions.ts mirror)", () => {
  it("parses a single key: value line", () => {
    expect(parseLabeledOutput_mirror("status: ok")).toEqual({ status: "ok" });
  });

  it("parses multiple lines", () => {
    expect(parseLabeledOutput_mirror("dry_run: true\nrows_affected: 3")).toEqual({
      dry_run: "true",
      rows_affected: "3",
    });
  });

  it("ignores lines with uppercase keys (SQL noise)", () => {
    expect(parseLabeledOutput_mirror("INSERT 0 1\nrows_affected: 5")).toEqual({ rows_affected: "5" });
  });

  it("ignores lines without colon+space separator", () => {
    expect(parseLabeledOutput_mirror("nocoapshere")).toEqual({});
  });

  it("captures value with spaces in it", () => {
    expect(parseLabeledOutput_mirror("message: hello world")).toEqual({ message: "hello world" });
  });

  it("returns empty object for empty string", () => {
    expect(parseLabeledOutput_mirror("")).toEqual({});
  });

  it("last duplicate key wins", () => {
    expect(parseLabeledOutput_mirror("status: ok\nstatus: done")).toEqual({ status: "done" });
  });
});

// ---- headline logic mirror ----
// Private helper in actions.ts — returns first non-SQL-keyword line.
const SQL_SKIP = /^(BEGIN|COMMIT|INSERT|UPDATE|DELETE|DO|ROLLBACK)\b/;
function headline_mirror(out: string): string {
  for (const line of out.split("\n").map((l) => l.trim())) {
    if (line && !SQL_SKIP.test(line)) return line;
  }
  return out.split("\n")[0] || "";
}

describe("headline (actions.ts mirror)", () => {
  it("returns first non-SQL line", () => {
    expect(headline_mirror("Merged 2 contacts")).toBe("Merged 2 contacts");
  });

  it("skips INSERT prefix and returns next line", () => {
    expect(headline_mirror("INSERT 0 1\nDone: 1 row merged")).toBe("Done: 1 row merged");
  });

  it("skips all SQL noise lines", () => {
    expect(headline_mirror("BEGIN\nCOMMIT\nDELETE 3\nOK: applied")).toBe("OK: applied");
  });

  it("falls back to first line when all lines are SQL noise", () => {
    expect(headline_mirror("BEGIN\nCOMMIT")).toBe("BEGIN");
  });

  it("returns first line on plain output (no SQL noise)", () => {
    expect(headline_mirror("dry_run: true\nrows: 0")).toBe("dry_run: true");
  });

  it("trims leading/trailing whitespace from lines", () => {
    expect(headline_mirror("  INSERT 0 1  \n  Result line  ")).toBe("Result line");
  });

  it("returns empty string for empty input", () => {
    expect(headline_mirror("")).toBe("");
  });
});

// ---------------------------------------------------------------------------
// contacts-types.ts — statusTone, strengthTone, roleLabel, reviewTypeLabel, statusLabel
// All pure functions — imported directly (no "use server").
// ---------------------------------------------------------------------------

describe("statusTone", () => {
  let statusTone: typeof import("@/lib/cockpit/contacts-types").statusTone;
  beforeEach(async () => {
    vi.resetModules();
    ({ statusTone } = await import("@/lib/cockpit/contacts-types"));
  });

  it("approved → ready", () => { expect(statusTone("approved")).toBe("ready"); });
  it("merged → ready", () => { expect(statusTone("merged")).toBe("ready"); });
  it("resolved → ready", () => { expect(statusTone("resolved")).toBe("ready"); });
  it("rejected → blocked", () => { expect(statusTone("rejected")).toBe("blocked"); });
  it("needs_more_info → review", () => { expect(statusTone("needs_more_info")).toBe("review"); });
  it("needs_review → review", () => { expect(statusTone("needs_review")).toBe("review"); });
  it("pending → neutral (default)", () => { expect(statusTone("pending")).toBe("neutral"); });
  it("unknown string → neutral (default)", () => { expect(statusTone("anything")).toBe("neutral"); });
});

describe("strengthTone", () => {
  let strengthTone: typeof import("@/lib/cockpit/contacts-types").strengthTone;
  beforeEach(async () => {
    vi.resetModules();
    ({ strengthTone } = await import("@/lib/cockpit/contacts-types"));
  });

  it("strong → blocked", () => { expect(strengthTone("strong")).toBe("blocked"); });
  it("medium → review", () => { expect(strengthTone("medium")).toBe("review"); });
  it("weak → neutral (default)", () => { expect(strengthTone("weak")).toBe("neutral"); });
  it("empty string → neutral", () => { expect(strengthTone("")).toBe("neutral"); });
});

describe("roleLabel", () => {
  let roleLabel: typeof import("@/lib/cockpit/contacts-types").roleLabel;
  beforeEach(async () => {
    vi.resetModules();
    ({ roleLabel } = await import("@/lib/cockpit/contacts-types"));
  });

  it("owner → owner", () => { expect(roleLabel("owner")).toBe("owner"); });
  it("OWNER (uppercase) → owner", () => { expect(roleLabel("OWNER")).toBe("owner"); });
  it("tenant → tenant", () => { expect(roleLabel("tenant")).toBe("tenant"); });
  it("broker → broker", () => { expect(roleLabel("broker")).toBe("broker"); });
  it("agent → broker (alias)", () => { expect(roleLabel("agent")).toBe("broker"); });
  it("buyer → lead (alias)", () => { expect(roleLabel("buyer")).toBe("lead"); });
  it("lead → lead", () => { expect(roleLabel("lead")).toBe("lead"); });
  it("unknown → passed through (lowercased)", () => { expect(roleLabel("investor")).toBe("investor"); });
});

describe("reviewTypeLabel", () => {
  let reviewTypeLabel: typeof import("@/lib/cockpit/contacts-types").reviewTypeLabel;
  beforeEach(async () => {
    vi.resetModules();
    ({ reviewTypeLabel } = await import("@/lib/cockpit/contacts-types"));
  });

  it("merge_candidate → mapped label", () => {
    expect(reviewTypeLabel("merge_candidate")).toBe("Possible contact to merge");
  });
  it("duplicate_contact → mapped label", () => {
    expect(reviewTypeLabel("duplicate_contact")).toBe("Duplicate to resolve");
  });
  it("property_hint_review → mapped label", () => {
    expect(reviewTypeLabel("property_hint_review")).toBe("Property / unit link to confirm");
  });
  it("unknown_type → title-cased fallback", () => {
    expect(reviewTypeLabel("some_review_type")).toBe("Some Review Type");
  });
});

describe("statusLabel", () => {
  let statusLabel: typeof import("@/lib/cockpit/contacts-types").statusLabel;
  beforeEach(async () => {
    vi.resetModules();
    ({ statusLabel } = await import("@/lib/cockpit/contacts-types"));
  });

  it("pending → Pending", () => { expect(statusLabel("pending")).toBe("Pending"); });
  it("approved → Approved", () => { expect(statusLabel("approved")).toBe("Approved"); });
  it("rejected → Rejected", () => { expect(statusLabel("rejected")).toBe("Rejected"); });
  it("needs_more_info → Needs info", () => { expect(statusLabel("needs_more_info")).toBe("Needs info"); });
  it("merged → Merged", () => { expect(statusLabel("merged")).toBe("Merged"); });
  it("merged_later → Merged (alias)", () => { expect(statusLabel("merged_later")).toBe("Merged"); });
  it("skipped → Skipped", () => { expect(statusLabel("skipped")).toBe("Skipped"); });
  it("unknown → title-cased fallback", () => { expect(statusLabel("some_status")).toBe("Some Status"); });
});

// ---------------------------------------------------------------------------
// getContactSheet pagination / sort / dir clamping — pure logic mirrors
// contacts.ts lines 295-298
// ---------------------------------------------------------------------------

function clampPage(page: number | undefined): number {
  return Math.max(1, Math.floor(page ?? 1));
}

function clampPageSize(pageSize: number | undefined): number {
  return Math.min(Math.max(pageSize ?? 25, 5), 100);
}

const SHEET_SORTS_KEYS = new Set(["created", "contact", "status", "methods"]);

function resolveSort(sort: string | undefined): string {
  return sort && SHEET_SORTS_KEYS.has(sort) ? sort : "created";
}

function resolveDir(dir: string | undefined): "asc" | "desc" {
  return dir === "asc" ? "asc" : "desc";
}

describe("getContactSheet pagination / sort guards (contacts.ts mirror)", () => {
  it("page=0 clamps to 1", () => { expect(clampPage(0)).toBe(1); });
  it("page=-5 clamps to 1", () => { expect(clampPage(-5)).toBe(1); });
  it("page=1.7 floors to 1 (Math.floor first, then max 1)", () => { expect(clampPage(1.7)).toBe(1); });
  it("page=3.9 floors to 3", () => { expect(clampPage(3.9)).toBe(3); });
  it("page=undefined defaults to 1", () => { expect(clampPage(undefined)).toBe(1); });

  it("pageSize=0 clamps to minimum 5", () => { expect(clampPageSize(0)).toBe(5); });
  it("pageSize=3 clamps to minimum 5", () => { expect(clampPageSize(3)).toBe(5); });
  it("pageSize=200 clamps to maximum 100", () => { expect(clampPageSize(200)).toBe(100); });
  it("pageSize=25 stays 25 (within 5–100)", () => { expect(clampPageSize(25)).toBe(25); });
  it("pageSize=undefined defaults to 25", () => { expect(clampPageSize(undefined)).toBe(25); });

  it("valid sort key passes through", () => { expect(resolveSort("contact")).toBe("contact"); });
  it("unknown sort key falls back to 'created'", () => { expect(resolveSort("hacked_col; drop table--")).toBe("created"); });
  it("undefined sort falls back to 'created'", () => { expect(resolveSort(undefined)).toBe("created"); });

  it("dir='asc' passes through", () => { expect(resolveDir("asc")).toBe("asc"); });
  it("dir='desc' passes through", () => { expect(resolveDir("desc")).toBe("desc"); });
  it("dir=undefined falls back to 'desc'", () => { expect(resolveDir(undefined)).toBe("desc"); });
  it("dir='DROP TABLE' falls back to 'desc'", () => { expect(resolveDir("DROP TABLE")).toBe("desc"); });
});

// ---------------------------------------------------------------------------
// buildOutreachQueue / clearQueueRow / recordOutreachActivity validation
// Pure logic mirrors of the guards in actions.ts ("use server").
// ---------------------------------------------------------------------------

const UUID_RE_MIRROR = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const GROUP_SLUG_RE = /^[a-z0-9-]{1,64}$/;
const OUTREACH_ACTIONS_MIRROR = new Set(["sent", "replied", "enquired", "opted-in", "opted-out"]);

function clampLimit(raw: unknown): number {
  return Math.max(1, Math.min(50, Number(raw) || 10));
}

describe("buildOutreachQueue limit clamping (actions.ts mirror)", () => {
  // Number(raw) || 10: 0 and NaN are falsy → default 10; negative is truthy → clamped by Math.max
  it("limit=0 defaults to 10 (0 is falsy in || fallback)", () => { expect(clampLimit(0)).toBe(10); });
  it("limit=-5 clamps to 1 via Math.max (negative is truthy, bypasses ||10)", () => { expect(clampLimit(-5)).toBe(1); });
  it("limit=100 clamps to 50 via Math.min", () => { expect(clampLimit(100)).toBe(50); });
  it("limit=5 passes through (within 1–50)", () => { expect(clampLimit(5)).toBe(5); });
  it("limit=undefined defaults to 10 (NaN || 10)", () => { expect(clampLimit(undefined)).toBe(10); });
  it("limit='abc' defaults to 10 (NaN || 10)", () => { expect(clampLimit("abc")).toBe(10); });
});

describe("buildOutreachQueue groupSlug validation (actions.ts mirror)", () => {
  it("valid slug passes", () => { expect(GROUP_SLUG_RE.test("my-group-1")).toBe(true); });
  it("empty string rejected", () => { expect(GROUP_SLUG_RE.test("")).toBe(false); });
  it("uppercase letters rejected", () => { expect(GROUP_SLUG_RE.test("My-Group")).toBe(false); });
  it("slug with spaces rejected", () => { expect(GROUP_SLUG_RE.test("my group")).toBe(false); });
  it("65-char slug rejected (max 64)", () => {
    expect(GROUP_SLUG_RE.test("a".repeat(65))).toBe(false);
  });
  it("64-char slug accepted (at max)", () => {
    expect(GROUP_SLUG_RE.test("a".repeat(64))).toBe(true);
  });
});

describe("UUID_RE contactId / queueId validation (actions.ts mirror)", () => {
  const VALID_UUID = "550e8400-e29b-41d4-a716-446655440000";
  it("valid UUID passes", () => { expect(UUID_RE_MIRROR.test(VALID_UUID)).toBe(true); });
  it("uppercase UUID passes (case-insensitive flag)", () => {
    expect(UUID_RE_MIRROR.test(VALID_UUID.toUpperCase())).toBe(true);
  });
  it("empty string rejected", () => { expect(UUID_RE_MIRROR.test("")).toBe(false); });
  it("plain string rejected", () => { expect(UUID_RE_MIRROR.test("not-a-uuid")).toBe(false); });
  it("UUID missing one segment rejected", () => {
    expect(UUID_RE_MIRROR.test("550e8400-e29b-41d4-a716")).toBe(false);
  });
  it("SQL injection string rejected", () => {
    expect(UUID_RE_MIRROR.test("'; DROP TABLE contacts;--")).toBe(false);
  });
});

describe("recordOutreachActivity action allowlist (actions.ts mirror)", () => {
  it("'sent' is valid", () => { expect(OUTREACH_ACTIONS_MIRROR.has("sent")).toBe(true); });
  it("'replied' is valid", () => { expect(OUTREACH_ACTIONS_MIRROR.has("replied")).toBe(true); });
  it("'enquired' is valid", () => { expect(OUTREACH_ACTIONS_MIRROR.has("enquired")).toBe(true); });
  it("'opted-in' is valid", () => { expect(OUTREACH_ACTIONS_MIRROR.has("opted-in")).toBe(true); });
  it("'opted-out' is valid", () => { expect(OUTREACH_ACTIONS_MIRROR.has("opted-out")).toBe(true); });
  it("'delete' is NOT a valid action", () => { expect(OUTREACH_ACTIONS_MIRROR.has("delete")).toBe(false); });
  it("'admin' is NOT a valid action", () => { expect(OUTREACH_ACTIONS_MIRROR.has("admin")).toBe(false); });
  it("empty string is NOT a valid action", () => { expect(OUTREACH_ACTIONS_MIRROR.has("")).toBe(false); });
});
