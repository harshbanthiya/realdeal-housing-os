"use server";

/**
 * Cockpit write path — server actions that shell out to the EXISTING guarded
 * Python scripts (the only audited writers). The cockpit DB layer stays
 * read-only; all mutations go through these scripts, which are dry-run by
 * default and require --apply to write.
 *
 * Safety:
 *  - execFile with an argv array (NEVER a shell string) — no injection.
 *  - Inputs validated (UUID, allow-listed status) before spawning.
 *  - Only an allow-listed set of scripts can be invoked.
 *  - `apply` defaults to false; callers must opt in explicitly per run.
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

const exec = promisify(execFile);

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ALLOWED_STATUSES = new Set([
  "pending", "approved", "rejected", "skipped", "needs_more_info", "merged_later",
]);

export interface ActionResult {
  ok: boolean;
  applied: boolean;       // true only if a real write was requested AND succeeded
  dryRun: boolean;        // true when no --apply was passed
  message: string;        // headline for the operator
  fields: Record<string, string>; // parsed labeled output (review_item_id, old_status, …)
  raw: string;            // full stdout/stderr for debugging
}

/** Walk up from the web app cwd to the repo root that holds scripts/. */
function findProjectRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, "scripts", "update_review_item.py"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error("Could not locate repo root (scripts/update_review_item.py not found).");
}

/** Parse the scripts' "key: value" labeled output into a flat map. */
function parseLabeledOutput(out: string): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const line of out.split("\n")) {
    const m = line.match(/^([a-z_]+):\s(.*)$/);
    if (m) fields[m[1]] = m[2];
  }
  return fields;
}

async function runScript(scriptFile: string, argv: string[]): Promise<{ code: number; out: string }> {
  const root = findProjectRoot();
  const scriptPath = join(root, "scripts", scriptFile);
  if (!existsSync(scriptPath)) throw new Error(`Script not allow-listed or missing: ${scriptFile}`);
  try {
    const { stdout, stderr } = await exec("python3", [scriptPath, ...argv], {
      cwd: root,
      timeout: 30_000,
      maxBuffer: 4 * 1024 * 1024,
    });
    return { code: 0, out: `${stdout}${stderr}`.trim() };
  } catch (e) {
    const err = e as { code?: number; stdout?: string; stderr?: string; message?: string };
    const out = `${err.stdout ?? ""}${err.stderr ?? ""}`.trim() || err.message || "script failed";
    return { code: typeof err.code === "number" ? err.code : 1, out };
  }
}

/**
 * Update one import_review_item's status via scripts/update_review_item.py.
 * Defaults to DRY-RUN (no writes). Pass apply=true only behind an explicit,
 * operator-confirmed action.
 */
export async function updateReviewItem(input: {
  reviewItemId: string;
  status: string;
  reviewedBy: string;
  decisionNotes?: string;
  apply?: boolean;
}): Promise<ActionResult> {
  const apply = input.apply === true;
  const base: ActionResult = { ok: false, applied: false, dryRun: !apply, message: "", fields: {}, raw: "" };

  if (!UUID_RE.test(input.reviewItemId)) return { ...base, message: "Invalid review item id." };
  if (!ALLOWED_STATUSES.has(input.status)) return { ...base, message: `Invalid status: ${input.status}` };
  const reviewedBy = (input.reviewedBy || "").trim();
  if (!reviewedBy) return { ...base, message: "reviewedBy is required." };

  const argv = [
    "--review-item-id", input.reviewItemId,
    "--status", input.status,
    "--reviewed-by", reviewedBy,
    "--decision-notes", input.decisionNotes ?? "",
  ];
  if (apply) argv.push("--apply");

  const { code, out } = await runScript("update_review_item.py", argv);
  const fields = parseLabeledOutput(out);
  const notFound = /not found/i.test(out);
  const ok = code === 0 && !notFound;

  return {
    ok,
    applied: ok && apply,
    dryRun: !apply,
    message: ok
      ? apply
        ? `Applied: ${fields.old_status ?? "?"} → ${input.status}`
        : `Dry run: would set ${fields.old_status ?? "?"} → ${input.status} (no write)`
      : out.split("\n")[0] || "Script failed.",
    fields,
    raw: out,
  };
}

const OUTREACH_ACTIONS: Record<string, string> = {
  sent: "--mark-sent",
  replied: "--mark-replied",
  enquired: "--mark-enquired",
  "opted-in": "--mark-opted-in",
  "opted-out": "--mark-opted-out",
};

/** First non-empty, non-boilerplate line of the script output. */
function headline(out: string): string {
  const skip = /^(BEGIN|COMMIT|INSERT|UPDATE|DELETE|DO|ROLLBACK)\b/;
  for (const line of out.split("\n").map((l) => l.trim())) {
    if (line && !skip.test(line)) return line;
  }
  return out.split("\n")[0] || "";
}

/**
 * Build today's owners-only assisted WhatsApp queue via
 * scripts/build_owner_outreach_queue.py. Dry-run by default; apply requires
 * BOTH --real-ok and --apply (passed together). Never sends.
 */
export async function buildOutreachQueue(input: {
  limit?: number;
  apply?: boolean;
  source?: "owners" | "group" | "contact";
  groupSlug?: string;
  contactId?: string;
}): Promise<ActionResult> {
  const apply = input.apply === true;
  const limit = Math.max(1, Math.min(50, Number(input.limit) || 10));
  const source = input.source ?? "owners";
  const base: ActionResult = { ok: false, applied: false, dryRun: !apply, message: "", fields: {}, raw: "" };

  const argv = ["--limit", String(limit), "--source", source];
  if (source === "group") {
    if (!input.groupSlug || !/^[a-z0-9-]{1,64}$/.test(input.groupSlug)) return { ...base, message: "Invalid group slug." };
    argv.push("--group-slug", input.groupSlug);
  }
  if (source === "contact") {
    if (!input.contactId || !UUID_RE.test(input.contactId)) return { ...base, message: "Invalid contact id." };
    argv.push("--contact-id", input.contactId);
  }
  if (apply) argv.push("--real-ok", "--apply");

  const { code, out } = await runScript("build_owner_outreach_queue.py", argv);
  const ok = code === 0;
  return {
    ...base,
    ok,
    applied: ok && apply,
    message: ok ? headline(out) : out.split("\n")[0] || "Queue build failed.",
    fields: parseLabeledOutput(out),
    raw: out,
  };
}

/**
 * Record a human-in-loop outreach activity (sent / replied / enquired /
 * opted-in / opted-out) via scripts/record_outreach_activity.py. Dry-run by
 * default; apply requires BOTH --real-ok and --apply. Never sends a message.
 */
export async function recordOutreachActivity(input: {
  queueId: string;
  action: string;
  by: string;
  note?: string;
  apply?: boolean;
}): Promise<ActionResult> {
  const apply = input.apply === true;
  const base: ActionResult = { ok: false, applied: false, dryRun: !apply, message: "", fields: {}, raw: "" };

  if (!UUID_RE.test(input.queueId)) return { ...base, message: "Invalid queue id." };
  const flag = OUTREACH_ACTIONS[input.action];
  if (!flag) return { ...base, message: `Invalid action: ${input.action}` };
  const by = (input.by || "").trim() || "director";

  const argv = ["--queue-id", input.queueId, flag, "--by", by];
  if (input.note) argv.push("--note", input.note);
  if (apply) argv.push("--real-ok", "--apply");

  const { code, out } = await runScript("record_outreach_activity.py", argv);
  const ok = code === 0 && !/Refusing:/i.test(out);
  return {
    ...base,
    ok,
    applied: ok && apply,
    message: ok
      ? apply ? headline(out) : `Dry run: would record ${input.action} (no write)`
      : out.split("\n").find((l) => /Refusing|FAILED|not found/i.test(l)) || out.split("\n")[0] || "Failed.",
    fields: parseLabeledOutput(out),
    raw: out,
  };
}

/** Add a single contact to the outreach queue (any contact, owner or not). */
export async function enqueueContact(input: { contactId: string; apply?: boolean }): Promise<ActionResult> {
  return buildOutreachQueue({ source: "contact", contactId: input.contactId, limit: 1, apply: input.apply });
}

/** Create a custom contact group via scripts/manage_contact_group.py. */
export async function createContactGroup(input: { name: string; apply?: boolean }): Promise<ActionResult> {
  const apply = input.apply === true;
  const base: ActionResult = { ok: false, applied: false, dryRun: !apply, message: "", fields: {}, raw: "" };
  const name = (input.name || "").trim();
  if (name.length < 2 || name.length > 64) return { ...base, message: "Group name must be 2–64 characters." };

  const argv = ["--create", "--name", name];
  if (apply) argv.push("--real-ok", "--apply");
  const { code, out } = await runScript("manage_contact_group.py", argv);
  const ok = code === 0 && !/Refusing:/i.test(out);
  return { ...base, ok, applied: ok && apply, message: ok ? headline(out) : out.split("\n")[0] || "Failed.", fields: parseLabeledOutput(out), raw: out };
}

/** Add picked contacts to a group via scripts/manage_contact_group.py. */
export async function addContactsToGroup(input: { groupSlug: string; contactIds: string[]; apply?: boolean }): Promise<ActionResult> {
  const apply = input.apply === true;
  const base: ActionResult = { ok: false, applied: false, dryRun: !apply, message: "", fields: {}, raw: "" };
  if (!/^[a-z0-9-]{1,64}$/.test(input.groupSlug || "")) return { ...base, message: "Invalid group slug." };
  const ids = (input.contactIds || []).filter((i) => UUID_RE.test(i));
  if (ids.length === 0) return { ...base, message: "No valid contact ids." };

  const argv = ["--add", "--group-slug", input.groupSlug, "--contact-ids", ids.join(",")];
  if (apply) argv.push("--real-ok", "--apply");
  const { code, out } = await runScript("manage_contact_group.py", argv);
  const ok = code === 0 && !/Refusing:/i.test(out);
  return { ...base, ok, applied: ok && apply, message: ok ? headline(out) : out.split("\n")[0] || "Failed.", fields: parseLabeledOutput(out), raw: out };
}
