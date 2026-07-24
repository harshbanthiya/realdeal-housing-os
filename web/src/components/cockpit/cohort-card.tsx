"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Card, Pill, Mono, type Tone } from "@/components/ui/primitives";
import {
  sampleCohort, applyCohort,
  type Cohort, type SampleRow, type CohortResult,
} from "@/lib/cockpit/review-cohorts";

const QUEUE_TONE: Record<string, Tone> = {
  contact_import: "review",
  unit_registration: "active",
  media: "neutral",
  property_rels: "blocked",
  contact_dupes: "review",
  party_matches: "active",
  drive_contacts: "review",
  phonebook_rename: "active",
  phonebook_to_db: "blocked",
  worker_findings: "neutral",
};


export function CohortCard({ c }: { c: Cohort }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [sample, setSample] = useState<SampleRow[] | null>(null);
  const [confirming, setConfirming] = useState<"approve" | "reject" | null>(null);
  const [result, setResult] = useState<CohortResult | null>(null);
  const [done, setDone] = useState(false);

  function loadSample() {
    if (sample) return setSample(null); // toggle closed
    start(async () => setSample(await sampleCohort(c.queue, c.cohort)));
  }

  /** Step 1: dry run. Shows the real count the write would touch. */
  function request(decision: "approve" | "reject") {
    setResult(null);
    start(async () => {
      const r = await applyCohort({ queue: c.queue, cohort: c.cohort, decision, apply: false });
      setResult(r);
      if (r.ok) setConfirming(decision);
    });
  }

  /** Step 2: the real write. */
  function confirm() {
    if (!confirming) return;
    const decision = confirming;
    start(async () => {
      const r = await applyCohort({ queue: c.queue, cohort: c.cohort, decision, apply: true });
      setResult(r);
      setConfirming(null);
      if (r.applied) {
        setDone(true);
        router.refresh();
      }
    });
  }

  if (done) {
    return (
      <Card className="border-teal/30 bg-teal/5 p-4">
        <div className="flex items-center justify-between gap-3">
          <span className="truncate text-sm text-ink/70">{c.cohort}</span>
          <Pill tone="ready">{result?.message ?? "done"}</Pill>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone={QUEUE_TONE[c.queue] ?? "neutral"}>{c.label}</Pill>
            <span className="text-lg font-semibold tabular-nums text-teal">{c.pending}</span>
            <span className="text-[11px] text-ink/45">pending</span>
          </div>
          <div className="mt-1.5 truncate text-sm font-medium text-ink/85" title={c.cohort}>
            {c.cohort}
          </div>
          <div className="mt-1 text-[11px] text-ink/45">
            {c.oldest === c.newest ? c.oldest : `${c.oldest} → ${c.newest}`}
          </div>
          {c.question && (
            <p className="mt-2 max-w-2xl rounded-md bg-mist/40 px-3 py-2 text-[12px] leading-relaxed text-ink/70">
              {c.question}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={loadSample}
            disabled={pending}
            className="rounded-full border border-mist-deep px-3 py-1.5 text-xs font-medium text-ink/65 hover:bg-mist/40 disabled:opacity-40"
          >
            {sample ? "Hide sample" : "Sample"}
          </button>
          <button
            onClick={() => request("approve")}
            disabled={pending || confirming !== null}
            className="rounded-full bg-teal px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-40"
          >
            Approve all
          </button>
          <button
            onClick={() => request("reject")}
            disabled={pending || confirming !== null}
            className="rounded-full border border-mist-deep px-3 py-1.5 text-xs font-semibold text-warm hover:bg-warm/5 disabled:opacity-40"
          >
            Reject all
          </button>
        </div>
      </div>

      {sample && (
        <div className="mt-3 rounded-lg border border-mist-deep bg-mist/20 p-3">
          {sample.length === 0 ? (
            <p className="text-[12px] text-ink/45">No sample rows returned.</p>
          ) : (
            <ul className="space-y-1">
              {sample.map((r, i) => (
                <li key={i} className="flex items-baseline justify-between gap-3 text-[12px]">
                  <span className="min-w-0 flex-1 truncate text-ink/75">{r.detail || "—"}</span>
                  <Mono className="shrink-0 text-[10px] text-ink/40">{r.created}</Mono>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 font-mono text-[10px] text-ink/40">
            showing {sample.length} of {c.pending}
          </p>
        </div>
      )}

      {result && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] text-ink/60">{result.message}</span>
          {confirming && (
            <>
              <button
                onClick={confirm}
                disabled={pending}
                className="rounded-full bg-warm px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-40"
              >
                {pending ? "Applying…" : `Yes — ${confirming} all ${result.count}`}
              </button>
              <button
                onClick={() => { setConfirming(null); setResult(null); }}
                disabled={pending}
                className="rounded-full border border-mist-deep px-3 py-1.5 text-xs font-semibold text-ink/60 hover:bg-mist/40 disabled:opacity-40"
              >
                Cancel
              </button>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
