"use server";

/**
 * Cohort review write path — shells out to scripts/review_cohorts.py, which is
 * the only writer. Same safety pattern as actions.ts: execFile with an argv
 * array (never a shell string), dry-run unless the caller opts in.
 *
 * Reads go through the same script rather than readQuery on purpose: the queue
 * registry (which table, what counts as pending, what a decision writes) lives
 * in one place, so the page can never drift from what the writer will do.
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { revalidatePath } from "next/cache";

const exec = promisify(execFile);

export interface Cohort {
  queue: string;
  label: string;
  /** Plain-English statement of what this cohort is asking. Comes from the
   *  engine's QUEUES registry so the page can never describe it differently
   *  from what the write actually does. */
  question: string;
  cohort: string;
  pending: number;
  oldest: string;
  newest: string;
}

export interface SampleRow {
  detail: string;
  created: string;
}

export interface CohortResult {
  ok: boolean;
  applied: boolean;
  dryRun: boolean;
  message: string;
  count: number;
}

const QUEUES = new Set([
  "contact_import", "unit_registration", "media",
  "property_rels", "contact_dupes", "party_matches", "drive_contacts", "phonebook_rename", "phonebook_to_db", "worker_findings",
]);

function root(): string {
  let dir = process.cwd();
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, "scripts", "review_cohorts.py"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error("repo root not found");
}

async function run(argv: string[]): Promise<unknown> {
  const dir = root();
  // Cohort applies can touch thousands of rows; give psql room.
  const { stdout } = await exec("python3", [join(dir, "scripts", "review_cohorts.py"), ...argv], {
    cwd: dir,
    timeout: 120_000,
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(stdout);
}

export async function listCohorts(): Promise<Cohort[]> {
  try {
    const rows = (await run(["--list"])) as Cohort[];
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

export async function sampleCohort(queue: string, cohort: string): Promise<SampleRow[]> {
  if (!QUEUES.has(queue) || !cohort) return [];
  try {
    const rows = (await run(["--sample", "--queue", queue, "--cohort", cohort])) as SampleRow[];
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

export async function applyCohort(input: {
  queue: string;
  cohort: string;
  decision: "approve" | "reject";
  apply?: boolean;
  by?: string;
}): Promise<CohortResult> {
  const apply = input.apply === true;
  const base: CohortResult = { ok: false, applied: false, dryRun: !apply, message: "", count: 0 };

  if (!QUEUES.has(input.queue)) return { ...base, message: `Unknown queue: ${input.queue}` };
  if (!input.cohort) return { ...base, message: "Cohort is required." };
  if (input.decision !== "approve" && input.decision !== "reject")
    return { ...base, message: `Invalid decision: ${input.decision}` };

  const argv = [
    "--apply-cohort",
    "--queue", input.queue,
    "--cohort", input.cohort,
    "--decision", input.decision,
    "--by", (input.by || "operator").slice(0, 100),
  ];
  if (apply) argv.push("--apply");

  try {
    const r = (await run(argv)) as {
      status?: string; error?: string; would_update?: number; updated?: number;
    };
    if (r.error) return { ...base, message: r.error };
    const count = apply ? Number(r.updated ?? 0) : Number(r.would_update ?? 0);
    if (apply) revalidatePath("/cockpit/review");
    return {
      ok: true,
      applied: apply,
      dryRun: !apply,
      count,
      message: apply
        ? `${input.decision === "approve" ? "Approved" : "Rejected"} ${count} items.`
        : `Dry run — would ${input.decision} ${count} items.`,
    };
  } catch (e) {
    return { ...base, message: (e as Error).message.slice(0, 300) };
  }
}
