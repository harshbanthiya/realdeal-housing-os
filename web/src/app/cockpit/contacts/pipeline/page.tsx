import { Card, Pill, Mono, type Tone } from "@/components/ui/primitives";
import { ContactsSubnav } from "@/components/cockpit/contacts-subnav";
import { getContactPipeline } from "@/lib/cockpit/contacts";
import { PIPELINE_STAGE_META, type PipelineColumn, type PipelineCard } from "@/lib/cockpit/contacts-types";

export const dynamic = "force-dynamic";

export default async function ContactPipeline() {
  const { columns, importedRows } = await getContactPipeline();
  const inPipeline = columns.reduce((n, c) => n + c.total, 0);

  return (
    <div className="px-6 py-7">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-teal">Contact pipeline</h1>
        <p className="mt-1 text-sm text-ink/55">
          {importedRows} imported rows · {inPipeline} contacts moving toward a building
        </p>
        <ContactsSubnav />
      </div>

      {/* Kanban */}
      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {columns.map((col) => (
          <Column key={col.stage} col={col} />
        ))}
      </div>

      <p className="mt-5 font-mono text-[11px] text-ink/40">
        Read-only · masked · real import batches only. A card moves right as you approve and merge it.
      </p>
    </div>
  );
}

function Column({ col }: { col: PipelineColumn }) {
  const hint = PIPELINE_STAGE_META[col.stage].hint;
  const hidden = col.total - col.cards.length;
  return (
    <section aria-label={`${col.label} - ${col.total}`} className="flex flex-col">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-teal">{col.label}</h2>
          <Pill tone={col.tone}>{col.total}</Pill>
        </div>
      </div>
      <p className="mb-3 text-[11px] text-ink/40">{hint}</p>

      <div className="flex-1 space-y-2 rounded-xl border border-dashed border-mist-deep bg-mist/20 p-2">
        {col.cards.length === 0 ? (
          <div className="px-3 py-8 text-center text-[12px] text-ink/40">Empty</div>
        ) : (
          <>
            {col.cards.map((c) => (
              <StageCard key={c.key} card={c} stage={col.stage} />
            ))}
            {hidden > 0 && (
              <div className="px-3 py-2 text-center text-[11px] font-medium text-ink/45">+{hidden} more</div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

const ROLE_TONE: Record<string, Tone> = { owner: "active", tenant: "ready", broker: "review", lead: "neutral" };

function StageCard({ card, stage }: { card: PipelineCard; stage: PipelineColumn["stage"] }) {
  return (
    <Card className="p-3">
      <div className="flex items-start gap-2">
        <span className="truncate text-[13px] font-medium text-ink/85">{card.primary}</span>
        {stage === "attached" && card.role && (
          <Pill tone={ROLE_TONE[card.role] ?? "neutral"}>{card.role}</Pill>
        )}
      </div>
      {stage === "attached" && card.building ? (
        <div className="mt-1 text-[11px] text-ink/50">{card.building}</div>
      ) : (
        card.secondary && <Mono className="mt-1 block truncate text-[10px]">{card.secondary}</Mono>
      )}
    </Card>
  );
}
