"use server";

/**
 * WhatsApp-ingest write path — server actions shelling out to the guarded
 * scripts/update_wa_item.py (dry-run by default there; we pass --apply because
 * every call here is behind an explicit operator click in the cockpit).
 * Same safety pattern as actions.ts: execFile argv, validated inputs.
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { revalidatePath } from "next/cache";

const exec = promisify(execFile);
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PHONE_RE = /^\+?\d{8,15}$/;
const CHAT_RE = /^[!\w:.\-]{5,120}$/;
const KINDS = new Set(["unclassified", "client", "broker", "broker_group",
  "tenant_group", "community_ours", "personal", "other"]);

function root(): string {
  let dir = process.cwd();
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, "scripts", "update_wa_item.py"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error("repo root not found");
}

async function run(argv: string[]): Promise<{ ok: boolean; message: string }> {
  try {
    const { stdout, stderr } = await exec(
      "python3", [join(root(), "scripts", "update_wa_item.py"), ...argv, "--apply"],
      { cwd: root(), timeout: 30_000 });
    const out = `${stdout}${stderr}`;
    const ok = /status: ok/.test(out);
    revalidatePath("/cockpit/whatsapp");
    return { ok, message: ok ? "Applied." : out.split("\n")[0] };
  } catch (e) {
    return { ok: false, message: (e as Error).message };
  }
}

export async function classifyChat(input: {
  chatId: string; kind?: string; ingest?: "on" | "off"; buildingId?: string;
}): Promise<{ ok: boolean; message: string }> {
  if (!CHAT_RE.test(input.chatId)) return { ok: false, message: "bad chat id" };
  const argv = ["classify-chat", "--chat-id", input.chatId];
  if (input.kind) {
    if (!KINDS.has(input.kind)) return { ok: false, message: "bad kind" };
    argv.push("--kind", input.kind);
  }
  if (input.ingest) argv.push("--ingest", input.ingest);
  if (input.buildingId) {
    if (!UUID_RE.test(input.buildingId)) return { ok: false, message: "bad building id" };
    argv.push("--building-id", input.buildingId);
  }
  return run(argv);
}

export async function confirmNumber(input: {
  phone: string; action: "attach" | "create" | "ignore"; contactId?: string;
}): Promise<{ ok: boolean; message: string }> {
  if (!PHONE_RE.test(input.phone)) return { ok: false, message: "bad phone" };
  const argv = ["confirm-number", "--phone", input.phone, "--action", input.action];
  if (input.action === "attach") {
    if (!input.contactId || !UUID_RE.test(input.contactId)) return { ok: false, message: "attach needs contact id" };
    argv.push("--contact-id", input.contactId);
  }
  return run(argv);
}

export async function completeWaTask(taskId: string): Promise<{ ok: boolean; message: string }> {
  if (!UUID_RE.test(taskId)) return { ok: false, message: "bad task id" };
  return run(["complete-task", "--task-id", taskId]);
}
