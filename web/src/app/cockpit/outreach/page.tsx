import { Card, Pill, PanelTitle, Mono, type Tone } from "@/components/ui/primitives";
import { OutreachQueue } from "@/components/cockpit/outreach-queue";
import { getOutreachOverview, getOutreachQueue, getActivityTimeline } from "@/lib/cockpit/outreach";

export const dynamic = "force-dynamic";

const TIER_TONE: Record<string, Tone> = {
  hot: "ready", warm: "active", cold: "review", untouched: "neutral", opted_out: "blocked",
};

export default async function OutreachPage() {
  const [overview, queue, timeline] = await Promise.all([
    getOutreachOverview(),
    getOutreachQueue(),
    getActivityTimeline(14),
  ]);

  return (
    <div className="px-6 py-7">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-teal">Outreach · WhatsApp (assisted)</h1>
        <p className="mt-1 text-sm text-ink/55">
          Lane A — free, human-in-loop from the director&apos;s personal number. The cockpit drafts and queues; the
          director sends in WhatsApp Web. Nothing sends automatically.
        </p>
      </div>

      {/* Safety / status strip */}
      <Card className="mb-6 p-5">
        <PanelTitle hint="owners only · review-gated">Status</PanelTitle>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Send mode" value={overview.sendEnabled ? "AUTOSEND" : "Assisted (human)"} tone={overview.sendEnabled ? "blocked" : "ready"} sub="send_enabled gate" />
          <Stat label="Daily cap" value={`${overview.sentToday}/${overview.dailyCap}`} tone="neutral" sub={`${overview.remainingToday} left today`} />
          <Stat label="Ready owners" value={overview.readyToEnroll} tone="active" sub={`of ${overview.eligibleOwners} eligible`} />
          <Stat label="WhatsApp opt-ins" value={overview.whatsappPermissionsAllowed} tone={overview.whatsappPermissionsAllowed > 0 ? "ready" : "neutral"} sub="real consent granted" />
        </div>
        {!overview.live && (
          <p className="mt-3 font-mono text-[11px] text-warm">
            DATABASE_URL not set — showing empty state. Set web/.env.local to read the live cockpit DB.
          </p>
        )}
        {overview.directorName === "[DIRECTOR_NAME]" && overview.live && (
          <p className="mt-3 font-mono text-[11px] text-amber">
            Director name still a placeholder — re-seed the sequence with the real name before sending.
          </p>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
        {/* Queue — the operator's working surface */}
        <div>
          <PanelTitle hint={`${overview.pendingToday} pending today`}>Today&apos;s send queue</PanelTitle>
          <OutreachQueue
            rows={queue}
            remainingToday={overview.remainingToday}
            readyToEnroll={overview.readyToEnroll}
            hasActiveSequence={overview.activeSequences > 0}
          />
        </div>

        {/* Right rail — engagement + timeline */}
        <div className="space-y-6">
          <div>
            <PanelTitle hint="warm vs cold">Engagement</PanelTitle>
            <Card className="p-4">
              {overview.tiers.length === 0 ? (
                <p className="text-sm text-ink/45">No activity recorded yet.</p>
              ) : (
                <ul className="space-y-2">
                  {overview.tiers.map((t) => (
                    <li key={t.tier} className="flex items-center justify-between text-sm">
                      <Pill tone={TIER_TONE[t.tier] ?? "neutral"}>{t.tier}</Pill>
                      <span className="tabular-nums text-ink/70">
                        {t.count}
                        {t.flagged > 0 && <span className="ml-2 font-mono text-[11px] text-warm">{t.flagged} no-engage</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <div>
            <PanelTitle hint="latest activity">Timeline</PanelTitle>
            <Card className="p-4">
              {timeline.length === 0 ? (
                <p className="text-sm text-ink/45">No interactions logged yet.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {timeline.map((e, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <span className="flex-1 truncate text-ink/75">{e.contactMasked}</span>
                      <Pill tone={e.direction === "inbound" ? "ready" : "neutral"}>{e.eventType.replace(/_/g, " ")}</Pill>
                      <Mono className="text-[10px]">{e.occurredAt.slice(5, 16).replace("T", " ")}</Mono>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, tone, sub }: { label: string; value: string | number; tone: Tone; sub?: string }) {
  return (
    <div className="rounded-lg border border-mist-deep bg-mist/20 px-3 py-3">
      <div className="mb-1 flex items-center gap-2">
        <Pill tone={tone}>{label}</Pill>
      </div>
      <div className="text-lg font-semibold tabular-nums text-ink/85">{value}</div>
      {sub && <div className="font-mono text-[10px] text-ink/40">{sub}</div>}
    </div>
  );
}
