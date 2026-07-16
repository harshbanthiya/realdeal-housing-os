import { Card, PanelTitle, Mono } from "@/components/ui/primitives";
import { DraftCard, AnswerCard } from "@/components/cockpit/seo-panel";
import { getSeoDrafts, getAnswerOpportunities, getRecentLlmRuns } from "@/lib/cockpit/seo";

export const dynamic = "force-dynamic";

export default async function SeoPage() {
  const [drafts, answers, runs] = await Promise.all([
    getSeoDrafts(),
    getAnswerOpportunities(),
    getRecentLlmRuns(),
  ]);

  return (
    <div className="px-6 py-7">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-teal">SEO worker</h1>
        <p className="mt-1 text-sm text-ink/55">
          content_scout output — blog drafts and Reddit/Quora answer drafts, all
          review-gated. Approving here never publishes anything; approved blog
          drafts get published on deploy, approved answers you post by hand and
          record the permalink. <Mono>seo_content_drafts · answer_opportunities · llm_runs</Mono>, migration 064.
        </p>
      </div>

      <Card className="mb-6 p-5">
        <PanelTitle hint={`${drafts.filter((d) => d.status === "draft").length} awaiting review`}>
          Blog drafts
        </PanelTitle>
        {drafts.length === 0 ? (
          <p className="text-sm text-ink/45">
            No drafts yet — run <Mono>python3 workers/content_scout.py</Mono>.
          </p>
        ) : (
          drafts.map((d) => <DraftCard key={d.id} row={d} />)
        )}
      </Card>

      <Card className="mb-6 p-5">
        <PanelTitle hint={`${answers.filter((a) => a.status === "drafted").length} awaiting review`}>
          Reddit / Quora answer queue
        </PanelTitle>
        {answers.length === 0 ? (
          <p className="text-sm text-ink/45">
            Nothing found yet. Reddit discovery needs a free script app —
            see <Mono>secrets/reddit_client_id</Mono> in the worker header.
          </p>
        ) : (
          answers.map((a) => <AnswerCard key={a.id} row={a} />)
        )}
      </Card>

      <Card className="p-5">
        <PanelTitle hint="last 25">LLM run trace</PanelTitle>
        {runs.length === 0 ? (
          <p className="text-sm text-ink/45">No runs logged.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="font-mono text-[11px] uppercase tracking-wide text-ink/45">
                  <th className="py-2 pr-4">when</th>
                  <th className="py-2 pr-4">worker</th>
                  <th className="py-2 pr-4">tier</th>
                  <th className="py-2 pr-4">model</th>
                  <th className="py-2 pr-4">purpose</th>
                  <th className="py-2 pr-4">status</th>
                  <th className="py-2">ms</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r, i) => (
                  <tr key={i} className="border-t border-mist-deep text-ink/70">
                    <td className="py-2 pr-4 font-mono text-[11px]">{r.created_at.slice(0, 19)}</td>
                    <td className="py-2 pr-4">{r.worker}</td>
                    <td className="py-2 pr-4">{r.tier}</td>
                    <td className="py-2 pr-4 font-mono text-[11px]">{r.model}</td>
                    <td className="py-2 pr-4">{r.purpose}</td>
                    <td className="py-2 pr-4">{r.status}</td>
                    <td className="py-2 font-mono text-[11px]">{r.duration_ms ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
