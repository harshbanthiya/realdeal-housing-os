import { isDbConfigured, readQuery } from "@/lib/db";

export const dynamic = "force-dynamic";

interface Finding {
  id: string;
  worker: string;
  kind: string;
  title: string;
  severity: string;
  last_seen_at: string;
}

interface WorkerRun {
  worker: string;
  started_at: string;
  status: string;
  summary: string | null;
}

interface QueueRow {
  table: string;
  pending: number;
  oldest: string;
}

async function getFindings(): Promise<Finding[]> {
  if (!isDbConfigured()) return [];
  return readQuery<Finding>(`
    SELECT id, worker, kind, title, severity, last_seen_at::date::text AS last_seen_at
    FROM worker_findings
    WHERE status = 'pending'
    ORDER BY CASE severity WHEN 'action' THEN 0 WHEN 'warn' THEN 1 ELSE 2 END, last_seen_at DESC
    LIMIT 200
  `);
}

async function getQueueSnapshot(): Promise<{ asOf: string | null; queues: QueueRow[] }> {
  if (!isDbConfigured()) return { asOf: null, queues: [] };
  const rows = await readQuery<{ started_at: string; detail: { queues?: Record<string, { pending: number; oldest: string }> } }>(`
    SELECT started_at::text, detail FROM worker_runs
    WHERE worker = 'review_inbox' AND status = 'ok'
    ORDER BY started_at DESC LIMIT 1
  `);
  if (!rows.length) return { asOf: null, queues: [] };
  const queues = Object.entries(rows[0].detail.queues ?? {})
    .map(([table, v]) => ({ table, pending: v.pending, oldest: v.oldest }))
    .sort((a, b) => b.pending - a.pending);
  return { asOf: rows[0].started_at, queues };
}

async function getLastRuns(): Promise<WorkerRun[]> {
  if (!isDbConfigured()) return [];
  return readQuery<WorkerRun>(`
    SELECT DISTINCT ON (worker) worker, started_at::text, status, summary
    FROM worker_runs ORDER BY worker, started_at DESC
  `);
}

const sevTone: Record<string, string> = {
  action: "bg-teal text-white",
  warn: "bg-amber-100 text-amber-800",
  info: "bg-ink/5 text-ink/60",
};

export default async function InboxPage() {
  const [findings, snapshot, runs] = await Promise.all([
    getFindings(),
    getQueueSnapshot(),
    getLastRuns(),
  ]);
  const totalPending = snapshot.queues.reduce((s, q) => s + q.pending, 0);

  return (
    <div className="px-6 py-7 max-w-5xl">
      <h1 className="text-2xl font-semibold tracking-tight text-teal mb-1">Operator inbox</h1>
      <p className="text-sm text-ink/55 mb-6">
        Daily workers file everything needing a human here.
        {snapshot.asOf && ` Queue snapshot from ${snapshot.asOf.slice(0, 16)}.`}
      </p>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <section>
          <h2 className="mb-2 text-sm font-semibold text-ink/70">
            Findings · {findings.length} pending
          </h2>
          {findings.length === 0 && (
            <p className="text-sm text-ink/40">Nothing pending (or DB unavailable). Run workers/run_all.py.</p>
          )}
          <ul className="space-y-1.5">
            {findings.map((f) => (
              <li key={f.id} className="flex items-start gap-3 rounded-lg border border-ink/10 px-3 py-2">
                <span className={`mt-0.5 rounded px-1.5 py-0.5 font-mono text-[10px] uppercase ${sevTone[f.severity] ?? sevTone.info}`}>
                  {f.severity}
                </span>
                <div className="min-w-0">
                  <p className="text-sm text-ink/85">{f.title}</p>
                  <p className="text-[11px] text-ink/40">
                    {f.worker} · {f.kind} · seen {f.last_seen_at}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <aside className="space-y-6">
          <section>
            <h2 className="mb-2 text-sm font-semibold text-ink/70">
              Review queues · {totalPending.toLocaleString()} pending
            </h2>
            <table className="w-full text-xs">
              <tbody>
                {snapshot.queues.map((q) => (
                  <tr key={q.table} className="border-b border-ink/5">
                    <td className="py-1 pr-2 font-mono text-[11px] text-ink/60">{q.table.replace(/_review_items$/, "")}</td>
                    <td className="py-1 pr-2 text-right font-medium text-ink/80">{q.pending.toLocaleString()}</td>
                    <td className="py-1 text-right text-ink/40">{q.oldest}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2 className="mb-2 text-sm font-semibold text-ink/70">Worker pulse</h2>
            <ul className="space-y-1 text-xs">
              {runs.map((r) => (
                <li key={r.worker} className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[11px] text-ink/60">{r.worker}</span>
                  <span className={r.status === "ok" ? "text-teal" : "text-red-600"}>
                    {r.status} · {r.started_at.slice(5, 16)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
