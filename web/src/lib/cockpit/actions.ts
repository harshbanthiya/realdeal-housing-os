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
