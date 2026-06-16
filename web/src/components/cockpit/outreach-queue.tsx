"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Pill, Mono, type Tone } from "@/components/ui/primitives";
import { buildOutreachQueue, recordOutreachActivity } from "@/lib/cockpit/actions";
import type { QueueRow } from "@/lib/cockpit/outreach";

const STATUS_TONE: Record<string, Tone> = {
  pending: "review", sent_by_human: "active", replied: "ready", cancelled: "neutral", skipped: "neutral", failed: "blocked",
};

const ACTIONS: { key: string; label: string; tone: Tone }[] = [
  { key: "sent", label: "Mark sent", tone: "active" },
  { key: "replied", label: "Replied", tone: "ready" },
  { key: "enquired", label: "Enquired", tone: "ready" },
  { key: "opted-in", label: "Opted in", tone: "ready" },
  { key: "opted-out", label: "Opted out / STOP", tone: "blocked" },
];

function waHref(row: QueueRow): string {
  return `${row.waLink}?text=${encodeURIComponent(row.message)}`;
}

export function OutreachQueue({
  rows, remainingToday, readyToEnroll, hasActiveSequence,
}: {
  rows: QueueRow[];
  remainingToday: number;
  readyToEnroll: number;
  hasActiveSequence: boolean;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [limit, setLimit] = useState(Math.min(10, remainingToday || 10));
  const [banner, setBanner] = useState<string | null>(null);
  const [rowMsg, setRowMsg] = useState<Record<string, string>>({});

  function build(apply: boolean) {
    setBanner(null);
    startTransition(async () => {
      const res = await buildOutreachQueue({ limit, apply });
      setBanner(res.message);
      if (res.applied) router.refresh();
    });
  }

  function record(queueId: string, action: string) {
    startTransition(async () => {
      const res = await recordOutreachActivity({ queueId, action, by: "director", apply: true });
      setRowMsg((m) => ({ ...m, [queueId]: res.message }));
      if (res.applied) router.refresh();
    });
  }

  return (
    <div>
      {/* Build controls */}
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-mist-deep bg-white p-4">
        <span className="text-sm font-medium text-teal">Build today&apos;s queue</span>
        <label className="flex items-center gap-2 text-sm text-ink/60">
          limit
          <input
            type="number" min={1} max={Math.max(1, remainingToday)} value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="w-16 rounded-md border border-mist-deep px-2 py-1 text-sm tabular-nums"
          />
        </label>
        <button
          onClick={() => build(false)} disabled={pending || !hasActiveSequence}
          className="rounded-lg border border-mist-deep px-3 py-1.5 text-sm font-medium text-ink/70 hover:bg-mist/40 disabled:opacity-40"
        >
          Preview
        </button>
        <button
          onClick={() => build(true)} disabled={pending || !hasActiveSequence || remainingToday <= 0}
          className="rounded-lg bg-teal px-3 py-1.5 text-sm font-semibold text-white hover:bg-teal/90 disabled:opacity-40"
        >
          Build &amp; queue
        </button>
        <span className="font-mono text-[11px] text-ink/40">
          {readyToEnroll} ready · {remainingToday} left today
        </span>
        {!hasActiveSequence && (
          <span className="font-mono text-[11px] text-warm">no active sequence — seed it first</span>
        )}
      </div>

      {banner && (
        <div className="mb-4 rounded-lg border border-mist-deep bg-mist/30 px-4 py-2 font-mono text-[12px] text-ink/70">
          {banner}
        </div>
      )}

      {/* Queue rows */}
      {rows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-mist-deep px-5 py-10 text-center text-sm text-ink/50">
          No contacts queued for today. Build the queue above — nothing sends until the director taps send in WhatsApp Web.
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map((r) => (
            <div key={r.queueId} className="rounded-xl border border-mist-deep bg-white p-4">
              <div className="mb-2 flex items-center gap-2">
                <span className="text-sm font-semibold text-ink/85">{r.firstName}</span>
                <Mono className="text-[11px]">step {r.step}</Mono>
                <Pill tone={STATUS_TONE[r.status] ?? "neutral"}>{r.status.replace(/_/g, " ")}</Pill>
                {r.sentAt && <Mono className="text-[11px]">{r.sentAt.slice(0, 16).replace("T", " ")}</Mono>}
              </div>

              <p className="mb-3 whitespace-pre-wrap rounded-lg bg-mist/25 px-3 py-2 text-[13px] leading-relaxed text-ink/75">
                {r.message}
              </p>

              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={waHref(r)} target="_blank" rel="noopener noreferrer"
                  className="rounded-lg bg-[#25D366] px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90"
                >
                  Open in WhatsApp ↗
                </a>
                {ACTIONS.map((a) => (
                  <button
                    key={a.key} onClick={() => record(r.queueId, a.key)} disabled={pending}
                    className="rounded-lg border border-mist-deep px-2.5 py-1.5 text-[13px] font-medium text-ink/70 hover:bg-mist/40 disabled:opacity-40"
                  >
                    {a.label}
                  </button>
                ))}
                {r.trackedUrl && (
                  <Mono className="ml-auto truncate text-[10px] text-ink/35" title={r.trackedUrl}>
                    {r.trackedUrl}
                  </Mono>
                )}
              </div>

              {rowMsg[r.queueId] && (
                <div className="mt-2 font-mono text-[11px] text-ink/55">{rowMsg[r.queueId]}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
