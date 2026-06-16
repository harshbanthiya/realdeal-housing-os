import { Card, Pill, PanelTitle, Mono, type Tone } from "@/components/ui/primitives";
import { MergeCandidateCard } from "@/components/cockpit/merge-candidate-card";
import { ContactsSubnav } from "@/components/cockpit/contacts-subnav";
import {
  getReviewBatches, getQueueCounts, getReviewQueue, getCanonicalContacts,
  type QueueCount,
} from "@/lib/cockpit/contacts";

export const dynamic = "force-dynamic";

// Friendly labels for the raw review_type / status enums.
const TYPE_LABEL: Record<string, string> = {
  merge_candidate: "Merge candidates",
  duplicate_contact: "Duplicates",
  property_hint_review: "Property hints",
  inventory_match_review: "Inventory matches",
  lead_requirement_review: "Lead requirements",
};
const typeLabel = (t: string) => TYPE_LABEL[t] ?? t.replace(/_/g, " ");

export default async function ContactsCleanup() {
  const [batches, counts, mergeQueue, canonical] = await Promise.all([
    getReviewBatches(true),
    getQueueCounts(true),
    getReviewQueue({ realOnly: true, reviewType: "merge_candidate", status: "pending", limit: 12 }),
    getCanonicalContacts(),
  ]);

  const importRows = batches.reduce((n, b) => n + b.importRows, 0);
  const pending = sumStatus(counts, "pending");
  const approved = sumStatus(counts, "approved");
  const realCanonical = canonical.filter((c) => !c.isTest).length;

  // Group the queue counts by review_type for the summary grid.
  const byType = groupByType(counts);

  return (
    <div className="px-6 py-7">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-teal">Contacts</h1>
        <p className="mt-1 text-sm text-ink/55">
          {realCanonical} cleaned canonical · {pending} awaiting review across {batches.length} real import batches
        </p>
        <ContactsSubnav />
      </div>

      {/* Pipeline funnel - where the jam is */}
      <Card className="mb-7 p-5">
        <PanelTitle hint="programmatic pipeline · review-gated">Cleanup funnel</PanelTitle>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stage n={importRows} label="Imported rows" tone="neutral" />
          <Stage n={pending} label="In review" tone="review" sub="needs your decision" />
          <Stage n={approved} label="Approved" tone="active" sub="ready to merge" />
          <Stage n={realCanonical} label="Canonical" tone="ready" sub="cleaned contacts" />
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
        {/* Merge-candidate queue: the bottleneck */}
        <div>
          <PanelTitle hint={`${countOf(counts, "merge_candidate", "pending")} pending`}>
            Merge candidates
          </PanelTitle>
          {mergeQueue.length === 0 ? (
            <Empty>No pending merge candidates - the queue is clear.</Empty>
          ) : (
            <div className="space-y-3">
              {mergeQueue.map((item) => (
                <MergeCandidateCard key={item.reviewItemId} item={item} />
              ))}
              <p className="font-mono text-[11px] text-ink/40">
                &ldquo;Preview approve&rdquo; runs the guarded script in dry-run (no writes). Applying stays disabled until enabled.
              </p>
            </div>
          )}
        </div>

        {/* Right rail: queue-by-type + batches */}
        <div className="space-y-6">
          <Card className="p-5">
            <PanelTitle hint={`${pending + approved} items`}>Review queues</PanelTitle>
            <ul className="space-y-2.5">
              {byType.map((g) => (
                <li key={g.reviewType} className="flex items-center justify-between border-b border-mist pb-2.5 last:border-0 last:pb-0">
                  <span className="text-sm text-ink/75">{typeLabel(g.reviewType)}</span>
                  <span className="flex items-center gap-2">
                    {g.approved > 0 && <Pill tone="ready">{g.approved} ok</Pill>}
                    <Pill tone={g.pending > 0 ? "review" : "neutral"}>{g.pending} pending</Pill>
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-5">
            <PanelTitle hint={`${batches.length} real`}>Import batches</PanelTitle>
            <ul className="space-y-3">
              {batches.map((b) => (
                <li key={b.importBatchId} className="rounded-lg border border-mist-deep p-3">
                  <div className="flex items-center justify-between gap-2">
                    <Mono className="truncate text-[11px] text-teal">{b.batchLabel}</Mono>
                    {b.isRealImport ? <Pill tone="active">real</Pill> : <Pill tone="neutral">test</Pill>}
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-center text-[11px]">
                    <BatchStat n={b.importRows} label="rows" />
                    <BatchStat n={b.pending} label="pending" tone="review" />
                    <BatchStat n={b.approved} label="approved" tone="ready" />
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ---------------- helpers + small components ----------------
function sumStatus(counts: QueueCount[], status: string) {
  return counts.filter((c) => c.status === status).reduce((n, c) => n + c.count, 0);
}
function countOf(counts: QueueCount[], type: string, status: string) {
  return counts.find((c) => c.reviewType === type && c.status === status)?.count ?? 0;
}
function groupByType(counts: QueueCount[]) {
  const map = new Map<string, { reviewType: string; pending: number; approved: number; other: number }>();
  for (const c of counts) {
    const g = map.get(c.reviewType) ?? { reviewType: c.reviewType, pending: 0, approved: 0, other: 0 };
    if (c.status === "pending") g.pending += c.count;
    else if (c.status === "approved") g.approved += c.count;
    else g.other += c.count;
    map.set(c.reviewType, g);
  }
  return [...map.values()].sort((a, b) => b.pending - a.pending);
}

function Stage({ n, label, sub, tone }: { n: number; label: string; sub?: string; tone: Tone }) {
  const color = tone === "review" ? "text-amber" : tone === "ready" ? "text-teal" : tone === "active" ? "text-accent" : "text-ink/70";
  return (
    <div className="rounded-lg border border-mist-deep p-3">
      <div className={`text-xl font-semibold ${color}`}>{n}</div>
      <div className="mt-0.5 text-[11px] uppercase tracking-wide text-ink/45">{label}</div>
      {sub && <div className="mt-0.5 text-[10px] text-ink/40">{sub}</div>}
    </div>
  );
}
function BatchStat({ n, label, tone = "neutral" }: { n: number; label: string; tone?: Tone }) {
  const color = tone === "review" ? "text-amber" : tone === "ready" ? "text-teal" : "text-ink/70";
  return (
    <div>
      <div className={`text-sm font-semibold ${color}`}>{n}</div>
      <div className="text-[10px] uppercase tracking-wide text-ink/40">{label}</div>
    </div>
  );
}
function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-dashed border-mist-deep bg-mist/30 px-5 py-10 text-center text-sm text-ink/45">{children}</div>;
}
