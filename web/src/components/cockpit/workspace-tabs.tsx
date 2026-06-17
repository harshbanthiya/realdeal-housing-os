"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, Pill, Dot, Mono, type Tone } from "@/components/ui/primitives";
import { UnitRegistry } from "@/components/cockpit/unit-registry";
import {
  TABS, type TabKey, type Building, type Person, type Keyword, type Campaign,
  type Fact, type WebPage, type ReviewItem, type AgentTask, type KanbanTask, type CalendarItem, type Listing,
  type UnitRegistry as UnitRegistryData,
} from "@/lib/cockpit/types";

export interface WorkspaceData {
  building: Building;
  owners: Person[];
  units: UnitRegistryData | null;
  listings: Listing[];
  keywords: Keyword[];
  campaigns: Campaign[];
  rera: Fact[];
  pages: WebPage[];
  reviews: ReviewItem[];
  agents: AgentTask[];
  kanban: KanbanTask[];
  calendar: CalendarItem[];
}

const ROLE_TONE: Record<string, Tone> = { owner: "active", tenant: "ready", client: "review" };

export function WorkspaceTabs({ data }: { data: WorkspaceData }) {
  const [tab, setTab] = useState<TabKey>("overview");
  const launch = data.building.mode === "launch";

  return (
    <div>
      <div className="sticky top-0 z-10 -mx-6 mb-6 flex gap-1 overflow-x-auto border-b border-mist-deep bg-white/90 px-6 backdrop-blur">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`whitespace-nowrap border-b-2 px-3 py-3 text-[13px] font-medium transition-colors ${
              tab === t.key ? "border-teal text-teal" : "border-transparent text-ink/55 hover:text-teal"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <Overview data={data} launch={launch} />}
      {tab === "owners" && <Owners owners={data.owners} />}
      {tab === "units" && (data.units ? <UnitRegistry data={data.units} /> : <Empty>No unit registry for this building yet.</Empty>)}
      {tab === "leads" && <Leads launch={launch} count={data.building.stats.leads} warm={data.building.stats.warm} />}
      {tab === "listings" && <Listings items={data.listings} />}
      {tab === "seo" && <Seo keywords={data.keywords} />}
      {tab === "campaigns" && <Campaigns items={data.campaigns} />}
      {tab === "rera" && <Rera facts={data.rera} />}
      {tab === "website" && <Website pages={data.pages} />}
      {tab === "reviews" && <Reviews items={data.reviews} />}
      {tab === "agents" && <Agents items={data.agents} />}
    </div>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="grid items-center gap-3 border-b border-mist px-4 py-3 last:border-0">{children}</div>;
}
function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-dashed border-mist-deep bg-mist/30 px-5 py-10 text-center text-sm text-ink/45">{children}</div>;
}

function Overview({ data, launch }: { data: WorkspaceData; launch: boolean }) {
  const s = data.building.stats;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Tile n={s.owners + s.tenants} label="Owners & tenants" />
        <Tile n={s.leads} label="Leads" sub={`${s.warm} warm`} />
        <Tile n={s.listings} label="Listings" />
        <Tile n={s.openReviews} label="Open reviews" tone={s.openReviews ? "review" : "neutral"} />
      </div>

      {launch ? (
        <>
          <Card className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-teal">Launch kanban</h3>
              <Pill tone="blocked">go-live locked</Pill>
            </div>
            <div className="grid gap-4 md:grid-cols-4">
              {(["todo", "doing", "blocked", "done"] as const).map((col) => (
                <div key={col}>
                  <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-ink/40">{col}</div>
                  <div className="space-y-2">
                    {data.kanban.filter((k) => k.col === col).map((k, i) => (
                      <div key={i} className={`rounded-lg border p-3 text-xs ${col === "blocked" ? "border-warm/40 bg-warm/5" : "border-mist-deep bg-white"}`}>
                        <div className="text-ink/80">{k.title}</div>
                        <div className="mt-1"><Mono className="text-[10px]">{k.stream}</Mono></div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <h3 className="mb-4 text-sm font-semibold text-teal">Campaign calendar</h3>
            <ul className="space-y-2">
              {data.calendar.map((c, i) => (
                <li key={i} className="flex items-center gap-4 text-sm">
                  <Mono className="w-12 shrink-0 text-[12px] text-warm">{c.when}</Mono>
                  <span className="flex-1 text-ink/80">{c.title}</span>
                  <Pill tone="neutral">{c.channel}</Pill>
                </li>
              ))}
            </ul>
          </Card>
        </>
      ) : (
        <Card className="p-5 text-sm text-ink/65">
          Steady-state building. Agents monitor SEO, keep contact data clean, and draft campaigns — all landing in this building&rsquo;s review queue. Switch to <span className="text-teal">Launch</span> mode when a sale push begins.
        </Card>
      )}
    </div>
  );
}

function Owners({ owners }: { owners: Person[] }) {
  const router = useRouter();
  if (!owners.length) return <Empty>No owners or tenants linked yet — import contact data to populate.</Empty>;
  return (
    <Card>
      {owners.map((p, i) => {
        const href = p.contactId ? `/cockpit/contacts/c/${p.contactId}` : "";
        const open = () => href && router.push(href);
        return (
        <div
          key={`${p.contactId ?? "person"}-${i}`}
          role={href ? "link" : undefined}
          tabIndex={href ? 0 : undefined}
          aria-label={href ? `Open contact ${p.name}` : undefined}
          onClick={open}
          onKeyDown={(event) => {
            if (href && (event.key === "Enter" || event.key === " ")) {
              event.preventDefault();
              open();
            }
          }}
          className={`group grid items-center gap-3 border-b border-mist px-4 py-3 last:border-0 ${
            href ? "cursor-pointer hover:bg-mist/20 focus-visible:bg-mist/30 focus-visible:outline-none" : ""
          }`}
        >
          <div className="grid grid-cols-[1.4fr_0.8fr_1fr_1fr] items-center gap-3">
            <span className={`text-sm text-ink/80 underline-offset-2 ${href ? "group-hover:text-teal group-hover:underline" : ""}`}>
              {p.name}
            </span>
            <Pill tone={ROLE_TONE[p.role]}>{p.role}</Pill>
            <Mono className="text-[12px]">{p.unit}</Mono>
            <Mono className="text-[12px]">{p.phone}</Mono>
          </div>
        </div>
      );})}
    </Card>
  );
}

function Leads({ launch, count, warm }: { launch: boolean; count: number; warm: number }) {
  if (count === 0) return <Empty>{launch ? "Pre-launch interest list is preview-only — lead intake opens after consent + go-live review." : "0 leads captured. Run a campaign to convert contacts into warm leads."}</Empty>;
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <Tile n={count} label="Total leads" />
      <Tile n={warm} label="Warm" tone="ready" />
      <Tile n={count - warm} label="Cold" />
      <Tile n={0} label="Sent today" />
    </div>
  );
}

function Listings({ items }: { items: Listing[] }) {
  if (!items.length) return <Empty>No listings yet for this building.</Empty>;
  return (
    <Card>
      {items.map((l, i) => (
        <Row key={i}>
          <div className="grid grid-cols-[1.6fr_0.7fr_0.7fr_0.8fr] items-center gap-3">
            <span className="text-sm text-ink/80">{l.title}</span>
            <Pill tone={l.type === "rent" ? "review" : "active"}>{l.type}</Pill>
            <Mono className="text-[12px]">{l.config}</Mono>
            <span className="text-sm font-semibold text-teal">{l.price}</span>
          </div>
        </Row>
      ))}
    </Card>
  );
}

function Seo({ keywords }: { keywords: Keyword[] }) {
  if (!keywords.length) return <Empty>No keywords tracked yet — the SEO agent will populate these.</Empty>;
  return (
    <Card>
      <div className="border-b border-mist px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-ink/40">keyword · rank · volume · status</div>
      {keywords.map((k, i) => (
        <Row key={i}>
          <div className="grid grid-cols-[2fr_0.6fr_0.6fr_0.8fr] items-center gap-3">
            <span className="text-sm text-ink/80">{k.term}</span>
            <Mono className="text-[12px] text-teal">{k.rank}</Mono>
            <Mono className="text-[12px]">{k.volume}</Mono>
            <Pill tone={k.status}>{k.status === "ready" ? "ranking" : "draft"}</Pill>
          </div>
        </Row>
      ))}
    </Card>
  );
}

function Campaigns({ items }: { items: Campaign[] }) {
  if (!items.length) return <Empty>No campaigns yet — drafts appear here once the campaign agent runs (consent-gated).</Empty>;
  return (
    <Card>
      {items.map((c, i) => (
        <Row key={i}>
          <div className="grid grid-cols-[1.4fr_0.8fr_1.4fr] items-center gap-3">
            <span className="text-sm text-ink/80">{c.name}</span>
            <Pill tone="neutral">{c.channel}</Pill>
            <div className="flex items-center gap-2">
              <Pill tone={c.status}>{c.status}</Pill>
              <span className="text-[11px] text-ink/45">{c.note}</span>
            </div>
          </div>
        </Row>
      ))}
    </Card>
  );
}

function Rera({ facts }: { facts: Fact[] }) {
  if (!facts.length) return <Empty>No RERA facts captured yet.</Empty>;
  return (
    <Card>
      {facts.map((f, i) => (
        <Row key={i}>
          <div className="grid grid-cols-[1fr_1.4fr_0.6fr] items-center gap-3">
            <span className="text-sm font-medium text-teal">{f.label}</span>
            <Mono className="text-[12px]">{f.value}</Mono>
            <Pill tone={f.status}>{f.status === "ready" ? "verified" : f.status === "review" ? "review" : "pending"}</Pill>
          </div>
        </Row>
      ))}
    </Card>
  );
}

function Website({ pages }: { pages: WebPage[] }) {
  return (
    <Card>
      {pages.map((p, i) => (
        <Row key={i}>
          <div className="grid grid-cols-[1fr_1.4fr_0.6fr] items-center gap-3">
            <Mono className="text-[12px] text-teal">{p.path}</Mono>
            <span className="text-sm text-ink/75">{p.title}</span>
            <Pill tone={p.status}>{p.status === "ready" ? "live (staging)" : p.status === "review" ? "in review" : "gated"}</Pill>
          </div>
        </Row>
      ))}
    </Card>
  );
}

function Reviews({ items }: { items: ReviewItem[] }) {
  const [done, setDone] = useState<number[]>([]);
  if (!items.length) return <Empty>No pending reviews for this building.</Empty>;
  return (
    <div>
      <div className="space-y-3">
        {items.map((r, i) => (
          <Card key={i} className="flex items-center gap-4 p-4">
            <Dot tone={done.includes(i) ? "ready" : r.tone} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm text-ink/80">{r.title}</div>
              <div className="text-[11px] text-ink/45"><Mono className="text-[11px]">{r.domain}</Mono> · {r.age}</div>
            </div>
            {done.includes(i) ? (
              <Pill tone="ready">queued (preview)</Pill>
            ) : (
              <div className="flex gap-2">
                <button onClick={() => setDone([...done, i])} className="rounded-full bg-teal px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90">Approve</button>
                <button onClick={() => setDone([...done, i])} className="rounded-full border border-mist-deep px-3 py-1.5 text-xs font-semibold text-warm hover:bg-warm/5">Reject</button>
              </div>
            )}
          </Card>
        ))}
      </div>
      <p className="mt-4 font-mono text-[11px] text-ink/40">Actions are preview-only in the shell — they will call the guarded apply / revert scripts next.</p>
    </div>
  );
}

function Agents({ items }: { items: AgentTask[] }) {
  return (
    <Card>
      {items.map((a, i) => (
        <Row key={i}>
          <div className="grid grid-cols-[1fr_1.4fr_0.8fr_0.6fr] items-center gap-3">
            <span className="text-sm font-medium text-teal">{a.agent}</span>
            <span className="text-sm text-ink/70">{a.task}</span>
            <Mono className="text-[11px]">{a.cadence}</Mono>
            <Pill tone={a.status}>{a.status === "ready" ? "running" : a.status === "review" ? "needs review" : "planned"}</Pill>
          </div>
        </Row>
      ))}
    </Card>
  );
}

function Tile({ n, label, sub, tone = "neutral" }: { n: number; label: string; sub?: string; tone?: Tone }) {
  return (
    <Card className="p-4">
      <div className={`text-2xl font-semibold ${tone === "review" ? "text-amber" : tone === "ready" ? "text-teal" : "text-teal"}`}>{n}</div>
      <div className="mt-1 text-[11px] uppercase tracking-wide text-ink/45">{label}</div>
      {sub && <div className="text-[11px] text-teal/60">{sub}</div>}
    </Card>
  );
}
