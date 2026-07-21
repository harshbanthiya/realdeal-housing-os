import Link from "next/link";
import { Card, Pill, Mono, PanelTitle, type Tone } from "@/components/ui/primitives";
import {
  getWaToday, getWaActivity, getWaGroups, getWaConfirmQueue, waLink,
} from "@/lib/cockpit/whatsapp";
import { GroupKindControl, ConfirmNumberControl, TaskDoneControl } from "@/components/cockpit/wa-controls";

export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false } };

const KIND_TONE: Record<string, Tone> = {
  client: "ready", broker: "review", broker_group: "review",
  tenant_group: "active", community_ours: "ready", personal: "blocked",
  unclassified: "neutral", other: "neutral",
};

function fmt(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default async function WhatsAppPage() {
  const [{ tasks, quiet }, activity, groups, confirm] = await Promise.all([
    getWaToday(), getWaActivity(), getWaGroups(), getWaConfirmQueue(),
  ]);

  return (
    <div className="px-6 py-7">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-teal">WhatsApp</h1>
          <p className="mt-1 text-[13px] text-ink/60">
            Read-only Beeper ingest · sends only via official WhatsApp (wa.me links)
          </p>
        </div>
        <Mono className="text-[11px]">⌂V viewing · ⌂F follow-up · ⌂N note · ⌂L listing</Mono>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Today */}
        <Card className="p-4">
          <PanelTitle>Today · {tasks.length} task{tasks.length === 1 ? "" : "s"}</PanelTitle>
          {tasks.length === 0 && <p className="mt-2 text-[13px] text-ink/50">Nothing due. ⌂V / ⌂F codes in sent messages create tasks here.</p>}
          <ul className="mt-2 divide-y divide-mist">
            {tasks.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <div className="truncate text-[13px] text-ink">
                    {t.overdue && <span className="mr-1.5 text-[11px] font-semibold text-amber">OVERDUE</span>}
                    {t.title}
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-[11px] text-ink/50">
                    <span>{fmt(t.dueAt)}</span>
                    {t.contactId && (
                      <Link href={`/cockpit/contacts/c/${t.contactId}`} className="text-teal hover:underline">
                        {t.contactName || "contact"}
                      </Link>
                    )}
                    {t.contactPhone && (
                      <a href={waLink(t.contactPhone)} target="_blank" className="text-teal/70 hover:text-teal">wa.me ↗</a>
                    )}
                  </div>
                </div>
                <TaskDoneControl taskId={t.id} />
              </li>
            ))}
          </ul>

          {quiet.length > 0 && (
            <>
              <div className="mt-5"></div><PanelTitle>Gone quiet · {quiet.length} client{quiet.length === 1 ? "" : "s"}</PanelTitle>
              <ul className="mt-2 divide-y divide-mist">
                {quiet.map((c) => (
                  <li key={c.chatId} className="flex items-center justify-between gap-3 py-2">
                    <div className="text-[13px] text-ink">
                      {c.contactId
                        ? <Link href={`/cockpit/contacts/c/${c.contactId}`} className="text-teal hover:underline">{c.contactName || c.title}</Link>
                        : c.title}
                      <span className="ml-2 text-[11px] text-ink/50">{c.quietDays}d silent</span>
                    </div>
                    {c.contactPhone && (
                      <a href={waLink(c.contactPhone, "Hi! ")} target="_blank"
                        className="rounded-md bg-teal/10 px-2 py-1 text-[11px] font-medium text-teal">Nudge ↗</a>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>

        {/* Confirm numbers */}
        <Card className="p-4">
          <PanelTitle>Confirm numbers · {confirm.length}</PanelTitle>
          <p className="mt-1 text-[12px] text-ink/50">
            Numbers seen in chats with a saved name but no canonical contact.
          </p>
          <ul className="mt-2 divide-y divide-mist">
            {confirm.map((r) => (
              <li key={r.phone} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <div className="truncate text-[13px] text-ink">{r.waName || r.phone}</div>
                  <div className="mt-0.5 text-[11px] text-ink/50">
                    <Mono>{r.phone}</Mono> · seen {r.seenCount}× · {r.firstSeenChat}
                    {r.proposedName && <span className="ml-1 text-teal">≈ {r.proposedName}?</span>}
                  </div>
                </div>
                <ConfirmNumberControl phone={r.phone} proposedContactId={r.proposedContactId} />
              </li>
            ))}
            {confirm.length === 0 && <p className="mt-2 text-[13px] text-ink/50">Queue clear.</p>}
          </ul>
        </Card>
      </div>

      {/* Groups */}
      <Card className="mt-6 p-4">
        <PanelTitle>Groups · {groups.length}</PanelTitle>
        <p className="mt-1 text-[12px] text-ink/50">
          Classify each once — kind drives what the AI layer does; Personal stops ingest and purges stored messages.
        </p>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wide text-ink/40">
                <th className="py-1.5 pr-3">Group</th>
                <th className="py-1.5 pr-3">Members</th>
                <th className="py-1.5 pr-3">Matched</th>
                <th className="py-1.5 pr-3">Last activity</th>
                <th className="py-1.5">Kind / ingest</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-mist">
              {groups.map((g) => (
                <tr key={g.chatId}>
                  <td className="max-w-[260px] truncate py-2 pr-3 text-ink">
                    {g.title}
                    {g.kind !== "unclassified" && <span className="ml-2"><Pill tone={KIND_TONE[g.kind] ?? "neutral"}>{g.kind.replace("_", " ")}</Pill></span>}
                  </td>
                  <td className="py-2 pr-3 text-ink/70">{g.memberCount || g.rosterMembers}</td>
                  <td className="py-2 pr-3 text-ink/70">
                    {g.rosterMembers ? `${g.matchedMembers}/${g.rosterMembers}` : "—"}
                  </td>
                  <td className="py-2 pr-3 text-ink/50">{fmt(g.lastActivity)}</td>
                  <td className="py-2">
                    <GroupKindControl chatId={g.chatId} kind={g.kind} ingestEnabled={g.ingestEnabled} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Activity */}
      <Card className="mt-6 p-4">
        <PanelTitle>Recent activity</PanelTitle>
        <ul className="mt-2 divide-y divide-mist">
          {activity.map((a) => (
            <li key={a.id} className="py-2">
              <div className="flex items-center gap-2 text-[11px] text-ink/50">
                <span>{fmt(a.occurredAt)}</span>
                <Pill tone={KIND_TONE[a.kind] ?? "neutral"}>{a.isGroup ? a.chatTitle : a.kind}</Pill>
                <span className={a.direction === "outbound" ? "text-teal" : ""}>
                  {a.direction === "outbound" ? "→ sent" : `← ${a.sender || "received"}`}
                </span>
                {a.contactId && (
                  <Link href={`/cockpit/contacts/c/${a.contactId}`} className="text-teal hover:underline">{a.contactName}</Link>
                )}
                {a.rdhCode && <Mono className="text-amber">⌂{a.rdhCode}</Mono>}
                {a.messageType !== "TEXT" && <Mono>{a.messageType.toLowerCase()}</Mono>}
              </div>
              {a.body && <p className="mt-1 line-clamp-2 text-[13px] text-ink/80">{a.body}</p>}
            </li>
          ))}
          {activity.length === 0 && <p className="mt-2 text-[13px] text-ink/50">No ingested messages yet — run workers/beeper_ingest.py.</p>}
        </ul>
      </Card>
    </div>
  );
}
