"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { classifyChat, confirmNumber, completeWaTask } from "@/lib/cockpit/wa-actions";

const KINDS = [
  ["unclassified", "Unclassified"], ["client", "Client"], ["broker", "Broker"],
  ["broker_group", "Broker group"], ["tenant_group", "Tenant group"],
  ["community_ours", "Our community"], ["personal", "Personal (skip)"], ["other", "Other"],
] as const;

export function GroupKindControl({ chatId, kind, ingestEnabled, buildingId, buildings = [] }: {
  chatId: string; kind: string; ingestEnabled: boolean;
  buildingId?: string | null;
  buildings?: { id: string; name: string }[];
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  // A tenant/community group maps to one building — that link is what lets the
  // roster match members to contacts, so only offer it where it means something.
  const showBuilding = buildings.length > 0 && (kind === "tenant_group" || kind === "community_ours");
  return (
    <span className="flex items-center gap-2">
      <select
        defaultValue={kind}
        disabled={pending}
        onChange={(e) => start(async () => { await classifyChat({ chatId, kind: e.target.value }); router.refresh(); })}
        className="rounded-md border border-mist-deep bg-white px-2 py-1 text-[12px] text-ink"
      >
        {KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
      {showBuilding && (
        <select
          defaultValue={buildingId ?? ""}
          disabled={pending}
          onChange={(e) => {
            const id = e.target.value;
            if (!id) return;
            start(async () => { await classifyChat({ chatId, buildingId: id }); router.refresh(); });
          }}
          title="Link this group to a building so its roster can match contacts"
          className={`rounded-md border px-2 py-1 text-[12px] ${buildingId ? "border-mist-deep bg-white text-ink" : "border-amber/40 bg-amber/5 text-ink/70"}`}
        >
          <option value="">Set building…</option>
          {buildings.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
      )}
      <button
        disabled={pending}
        onClick={() => start(async () => { await classifyChat({ chatId, ingest: ingestEnabled ? "off" : "on" }); router.refresh(); })}
        className={`rounded-md px-2 py-1 text-[11px] font-medium ${ingestEnabled ? "bg-teal/10 text-teal" : "bg-amber/10 text-amber"}`}
        title={ingestEnabled ? "Ingesting — click to stop + purge" : "Skipped — click to ingest"}
      >
        {pending ? "…" : ingestEnabled ? "Ingest ON" : "Skipped"}
      </button>
    </span>
  );
}

export function ConfirmNumberControl({ phone, proposedContactId }: {
  phone: string; proposedContactId: string | null;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const act = (action: "attach" | "create" | "ignore") =>
    start(async () => {
      await confirmNumber({ phone, action, contactId: proposedContactId ?? undefined });
      router.refresh();
    });
  return (
    <span className="flex items-center gap-1.5">
      {proposedContactId && (
        <button disabled={pending} onClick={() => act("attach")}
          className="rounded-md bg-teal/10 px-2 py-1 text-[11px] font-medium text-teal">Attach</button>
      )}
      <button disabled={pending} onClick={() => act("create")}
        className="rounded-md bg-mist px-2 py-1 text-[11px] font-medium text-ink/70">New contact</button>
      <button disabled={pending} onClick={() => act("ignore")}
        className="rounded-md px-2 py-1 text-[11px] text-ink/40 hover:text-ink/70">Ignore</button>
    </span>
  );
}

export function TaskDoneControl({ taskId }: { taskId: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [done, setDone] = useState(false);
  if (done) return <span className="text-[11px] text-teal">✓ done</span>;
  return (
    <button
      disabled={pending}
      onClick={() => start(async () => { const r = await completeWaTask(taskId); if (r.ok) setDone(true); router.refresh(); })}
      className="rounded-md border border-mist-deep px-2 py-1 text-[11px] text-ink/70 hover:bg-teal/10 hover:text-teal"
    >
      {pending ? "…" : "Mark done"}
    </button>
  );
}
