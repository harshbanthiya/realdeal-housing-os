"use client";

import { useState, useTransition } from "react";
import { Card, Pill, Dot } from "@/components/ui/primitives";
import { updateReviewItem, type ActionResult } from "@/lib/cockpit/actions";
import { statusTone, type ReviewQueueItem } from "@/lib/cockpit/contacts-types";

/**
 * One merge-candidate row with a DRY-RUN preview of approval.
 * Clicking "Preview approve" runs the guarded script with NO --apply, so it
 * never writes — it shows what the real apply would do. The actual apply path
 * stays intentionally unwired until explicitly enabled.
 */
export function MergeCandidateCard({ item }: { item: ReviewQueueItem }) {
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<ActionResult | null>(null);
  const [skipped, setSkipped] = useState(false);

  function previewApprove() {
    setResult(null);
    startTransition(async () => {
      const r = await updateReviewItem({
        reviewItemId: item.reviewItemId,
        status: "approved",
        reviewedBy: "cockpit operator",
        decisionNotes: "Preview from cockpit (dry-run).",
        apply: false, // dry-run only — never writes
      });
      setResult(r);
    });
  }

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Dot tone={statusTone(item.status)} />
            <span className="truncate text-sm font-medium text-ink/85">{item.title || "Merge candidate"}</span>
            {item.priority === "high" && <Pill tone="blocked">high</Pill>}
          </div>
          <p className="mt-1 line-clamp-2 text-[13px] text-ink/55">{item.summary}</p>
          <div className="mt-1.5 flex items-center gap-2 font-mono text-[11px] text-ink/40">
            <span>{item.batchLabel}</span>
            {item.recommendedAction && <span>· suggests {item.recommendedAction.replace(/_/g, " ")}</span>}
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            onClick={previewApprove}
            disabled={pending || skipped}
            className="rounded-full bg-teal px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            {pending ? "Checking…" : "Preview approve"}
          </button>
          <button
            onClick={() => { setSkipped(true); setResult(null); }}
            disabled={pending || skipped}
            className="rounded-full border border-mist-deep px-3 py-1.5 text-xs font-semibold text-ink/55 transition-colors hover:bg-mist/40 disabled:opacity-40"
          >
            Skip
          </button>
        </div>
      </div>

      {skipped && (
        <p role="status" className="mt-3 border-t border-mist pt-2 text-[12px] text-ink/45">
          Skipped in this view (no change written).
        </p>
      )}

      {result && (
        <div
          role="status"
          className={`mt-3 flex items-start gap-2 border-t border-mist pt-2 text-[12px] ${result.ok ? "text-ink/70" : "text-warm"}`}
        >
          <Dot tone={result.ok ? "review" : "blocked"} />
          <div>
            <span>{result.message}</span>
            {result.ok && result.dryRun && (
              <span className="ml-1 font-mono text-ink/40">— apply stays disabled until enabled</span>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
