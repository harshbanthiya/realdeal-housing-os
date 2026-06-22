import Link from "next/link";
import { Card, Pill, Dot, PanelTitle, Mono, type Tone } from "@/components/ui/primitives";
import {
  getBuildings,
  getGlobalReviewQueue,
  getAgentActivity,
  getGlobalBlockers,
  getStreamReadiness,
  type Mode,
} from "@/lib/cockpit/data";

const MODE_LABEL: Record<Mode, string> = {
  launch: "Launch", active: "Active", prospecting: "Prospecting", post_launch: "Post-launch",
};
const MODE_TONE: Record<Mode, Tone> = {
  launch: "blocked", active: "ready", prospecting: "review", post_launch: "neutral",
};

export default async function CockpitHome() {
  const [buildings, reviews, agents, blockers, streams] = await Promise.all([
    getBuildings(), getGlobalReviewQueue(), getAgentActivity(), getGlobalBlockers(), getStreamReadiness(),
  ]);

  return (
    <div className="px-6 py-7">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-teal">Portfolio</h1>
        <p className="mt-1 text-sm text-ink/55">{buildings.length} buildings · 1 in launch · {reviews.length} items awaiting review</p>
      </div>

      {/* DLF launch readiness strip */}
      <Card className="mb-7 p-5">
        <PanelTitle hint="DLF Westpark · T-58d">Launch readiness</PanelTitle>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {streams.map((s) => (
            <div key={s.label} className="rounded-lg border border-mist-deep p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-ink/60">{s.label}</span>
                <Dot tone={s.tone} />
              </div>
              <div className="mt-2 flex items-center justify-between">
                <Pill tone={s.tone}>{s.state}</Pill>
                {s.total > 0 && (
                  <span className="text-[10px] text-ink/40">{s.passed}/{s.total}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.8fr_1fr]">
        {/* Buildings */}
        <div>
          <PanelTitle hint="click to open workspace">Buildings</PanelTitle>
          <div className="grid gap-4 sm:grid-cols-2">
            {buildings.map((b) => (
              <Link key={b.slug} href={`/cockpit/buildings/${b.slug}`}>
                <Card className="h-full p-5 transition-colors hover:bg-mist/30">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-base font-semibold text-teal">{b.name}</div>
                      <div className="mt-0.5 text-xs text-ink/50">{b.location}</div>
                    </div>
                    <Pill tone={MODE_TONE[b.mode]}>{MODE_LABEL[b.mode]}</Pill>
                  </div>
                  {b.launchInDays && (
                    <div className="mt-2 font-mono text-[11px] text-warm">launch in {b.launchInDays}d</div>
                  )}
                  <div className="mt-4 grid grid-cols-4 gap-2 border-t border-mist pt-3 text-center">
                    <Stat n={b.stats.owners + b.stats.tenants} label="people" />
                    <Stat n={b.stats.leads} label="leads" sub={`${b.stats.warm} warm`} />
                    <Stat n={b.stats.listings} label="listings" />
                    <Stat n={b.stats.openReviews} label="reviews" tone={b.stats.openReviews > 0 ? "review" : "neutral"} />
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <Mono className="text-[11px]">SEO {b.seoRank}</Mono>
                    {b.stats.blockers > 0 ? <Pill tone="blocked">{b.stats.blockers} blockers</Pill> : <Pill tone="ready">clear</Pill>}
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>

        {/* Right rail */}
        <div className="space-y-6">
          <Card className="p-5">
            <PanelTitle hint={`${reviews.length}`}>Needs review</PanelTitle>
            <ul className="space-y-3">
              {reviews.map((r, i) => (
                <li key={i} className="flex items-start gap-3">
                  <Dot tone={r.tone} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-ink/80">{r.title}</div>
                    <div className="mt-0.5 text-[11px] text-ink/45">{r.building} · <Mono className="text-[11px]">{r.domain}</Mono> · {r.age}</div>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-5">
            <PanelTitle hint="last 24h">Agents</PanelTitle>
            <ul className="space-y-3">
              {agents.map((a, i) => (
                <li key={i} className="flex items-start gap-3">
                  <Dot tone={a.status} />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-ink/80">{a.action}</div>
                    <div className="mt-0.5 text-[11px] text-ink/45"><Mono className="text-[11px]">{a.agent}</Mono> · {a.building}</div>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-5">
            <PanelTitle hint={`${blockers.length} open`}>Blockers</PanelTitle>
            <ul className="space-y-3">
              {blockers.map((b) => (
                <li key={b.id} className="rounded-lg border border-mist-deep p-3">
                  <div className="flex items-center justify-between">
                    <Mono className="text-[11px] text-warm">{b.id}</Mono>
                    <span className="text-[11px] text-ink/45">open {b.openFor}</span>
                  </div>
                  <div className="mt-1 text-sm text-ink/80">{b.statement}</div>
                  <div className="mt-0.5 text-[11px] text-ink/45">{b.building}</div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Stat({ n, label, sub, tone = "neutral" }: { n: number; label: string; sub?: string; tone?: Tone }) {
  return (
    <div>
      <div className={`text-lg font-semibold ${tone === "review" ? "text-amber" : "text-teal"}`}>{n}</div>
      <div className="text-[10px] uppercase tracking-wide text-ink/40">{label}</div>
      {sub && <div className="text-[10px] text-teal/60">{sub}</div>}
    </div>
  );
}
