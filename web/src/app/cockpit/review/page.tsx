import { Card, PanelTitle, Mono } from "@/components/ui/primitives";
import { CohortCard } from "@/components/cockpit/cohort-card";
import { listCohorts } from "@/lib/cockpit/review-cohorts";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  const cohorts = await listCohorts();
  const total = cohorts.reduce((n, c) => n + c.pending, 0);

  // Group by queue so related cohorts sit together, biggest queue first.
  const byQueue = new Map<string, typeof cohorts>();
  for (const c of cohorts) {
    const list = byQueue.get(c.queue) ?? [];
    list.push(c);
    byQueue.set(c.queue, list);
  }
  const groups = [...byQueue.entries()]
    .map(([queue, list]) => ({
      queue,
      label: list[0].label,
      list,
      total: list.reduce((n, c) => n + c.pending, 0),
    }))
    .sort((a, b) => b.total - a.total);

  return (
    <div className="px-6 py-7">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-teal">Review</h1>
        <p className="mt-1 text-sm text-ink/55">
          {total.toLocaleString()} pending items in {cohorts.length} cohorts. Each queue is grouped by
          its natural batch — approve or reject a whole cohort in one decision, after checking a sample.
        </p>
      </div>

      {cohorts.length === 0 ? (
        <Card className="p-6">
          <p className="text-sm text-ink/60">
            Nothing pending — or the review script could not run. Check that Postgres is up
            (<Mono>docker ps</Mono>) and that <Mono>scripts/review_cohorts.py --list</Mono> returns JSON.
          </p>
        </Card>
      ) : (
        <div className="space-y-8">
          {groups.map((g) => (
            <div key={g.queue}>
              <PanelTitle hint={`${g.total.toLocaleString()} pending · ${g.list.length} cohorts`}>
                {g.label}
              </PanelTitle>
              <div className="space-y-3">
                {g.list.map((c) => (
                  <CohortCard key={`${c.queue}::${c.cohort}`} c={c} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="mt-8 font-mono text-[11px] text-ink/40">
        Every decision runs a dry-run first and shows the exact row count before the confirm step.
        Writes go through scripts/review_cohorts.py --apply. Two live queues are handled elsewhere:
        WhatsApp number confirms (/cockpit/whatsapp) and Zapkey transactions, which need unit-linking
        logic rather than a yes/no.
      </p>
    </div>
  );
}
