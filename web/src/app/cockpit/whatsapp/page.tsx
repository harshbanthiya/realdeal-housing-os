import Link from "next/link";
import { Card, Pill, Mono, PanelTitle, type Tone } from "@/components/ui/primitives";
import {
  getWaToday, getWaActivity, getWaGroups, getWaConfirmQueue, searchWaMessages, waLink,
  getBuildingOptions,
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

const SEARCH_KINDS = [
  ["", "All chats"], ["client", "Clients"], ["broker", "Brokers"],
  ["broker_group", "Broker groups"], ["tenant_group", "Tenant groups"],
  ["community_ours", "Our community"],
] as const;

function Snippet({ text }: { text: string }) {
  // ts_headline marks matches with ⟦…⟧ — render them highlighted
  const parts = text.split(/(⟦[^⟧]*⟧)/g);
  return (
    <p className="mt-1 text-[13px] text-ink/80">
      {parts.map((p, i) =>
        p.startsWith("⟦")
          ? <mark key={i} className="rounded bg-amber/25 px-0.5 text-ink">{p.slice(1, -1)}</mark>
          : <span key={i}>{p}</span>
      )}
    </p>
  );
}

export default async function WhatsAppPage({ searchParams }: {
  searchParams: Promise<{ q?: string; kind?: string; dir?: string; days?: string }>;
}) {
  const sp = await searchParams;
  const q = (sp.q ?? "").trim();
  const [{ tasks, quiet }, activity, groups, confirm, buildings, results] = await Promise.all([
    getWaToday(), getWaActivity(), getWaGroups(), getWaConfirmQueue(), getBuildingOptions(),
    q ? searchWaMessages(q, {
      kind: sp.kind || undefined,
      direction: sp.dir || undefined,
      sinceDays: sp.days ? Number(sp.days) : undefined,
    }) : Promise.resolve([]),
  ]);

  return (
    <div className="px-6 py-7">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-teal">WhatsApp</h1>
          <p className="mt-1 text-[13px] text-ink/60">
            Read-only Beeper ingest · sends only via official WhatsApp (wa.me links)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/cockpit/whatsapp/market" className="rounded-lg bg-teal px-3 py-1.5 text-[12px] font-medium text-white">
            Broker market →
          </Link>
          <Mono className="text-[11px]">⌂V viewing · ⌂F follow-up · ⌂N note · ⌂L listing</Mono>
        </div>
      </div>

      {/* Search every message */}
      <Card className="mb-6 p-4">
        <form method="GET" className="flex flex-wrap items-center gap-2">
          <input
            type="search" name="q" defaultValue={q}
            placeholder='Search all messages… ("2bhk andheri", "rent", a name, a price)'
            className="min-w-[240px] flex-1 rounded-lg border border-mist-deep bg-white px-3 py-2 text-[13px] text-ink placeholder:text-ink/35"
          />
          <select name="kind" defaultValue={sp.kind ?? ""} className="rounded-lg border border-mist-deep bg-white px-2 py-2 text-[12px] text-ink">
            {SEARCH_KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <select name="dir" defaultValue={sp.dir ?? ""} className="rounded-lg border border-mist-deep bg-white px-2 py-2 text-[12px] text-ink">
            <option value="">In + out</option>
            <option value="inbound">Received</option>
            <option value="outbound">Sent</option>
          </select>
          <select name="days" defaultValue={sp.days ?? ""} className="rounded-lg border border-mist-deep bg-white px-2 py-2 text-[12px] text-ink">
            <option value="">Any time</option>
            <option value="1">24h</option>
            <option value="7">7 days</option>
            <option value="30">30 days</option>
          </select>
          <button type="submit" className="rounded-lg bg-teal px-4 py-2 text-[13px] font-medium text-white">Search</button>
          {q && <Link href="/cockpit/whatsapp" className="text-[12px] text-ink/50 hover:text-teal">Clear</Link>}
        </form>

        {q && (
          <div className="mt-4">
            <PanelTitle hint={`${results.length}${results.length === 60 ? "+" : ""}`}>Results for “{q}”</PanelTitle>
            {results.length === 0 && <p className="mt-2 text-[13px] text-ink/50">No matches. Try fewer words or a partial word.</p>}
            <ul className="mt-1 divide-y divide-mist">
              {results.map((r) => (
                <li key={r.id} className={`py-2.5 pl-3 ${r.direction === "outbound" ? "border-l-2 border-teal bg-teal/[0.04]" : "border-l-2 border-transparent"}`}>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-ink/50">
                    <span
                      className={`inline-block h-2 w-2 shrink-0 rounded-full ${r.direction === "outbound" ? "bg-teal" : "bg-ink/25"}`}
                      title={r.direction === "outbound" ? "she sent this" : "received"}
                    />
                    <span>{fmt(r.occurredAt)}</span>
                    <span className={r.direction === "outbound" ? "font-medium text-teal" : "font-medium text-ink/70"}>
                      {r.direction === "outbound" ? "she sent" : r.sender || "received"}
                    </span>
                    {r.senderPhone && (
                      <>
                        <Mono>{r.senderPhone}</Mono>
                        <a href={waLink(r.senderPhone)} target="_blank" className="font-medium text-teal/80 hover:text-teal">wa.me ↗</a>
                      </>
                    )}
                    <span className="text-ink/40">in</span>
                    <Pill tone={KIND_TONE[r.kind] ?? "neutral"}>{r.isGroup ? r.chatTitle : (r.kind || "chat")}</Pill>
                    {r.contactId && (
                      <Link href={`/cockpit/contacts/c/${r.contactId}`} className="text-teal hover:underline">
                        {r.contactName} →
                      </Link>
                    )}
                    {r.messageType !== "TEXT" && <Mono>{r.messageType.toLowerCase()}</Mono>}
                  </div>
                  {r.body.length > r.snippet.replace(/[⟦⟧]/g, "").length + 20 ? (
                    <details>
                      <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                        <Snippet text={r.snippet} />
                        <span className="text-[11px] text-teal/70 hover:text-teal">show full text ▾</span>
                      </summary>
                      <p className="mt-1 whitespace-pre-wrap rounded-md bg-mist/50 p-2.5 text-[13px] text-ink/85">{r.body}</p>
                    </details>
                  ) : (
                    <Snippet text={r.snippet} />
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

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
                    <GroupKindControl chatId={g.chatId} kind={g.kind} ingestEnabled={g.ingestEnabled}
                      buildingId={g.buildingId} buildings={buildings} />
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
