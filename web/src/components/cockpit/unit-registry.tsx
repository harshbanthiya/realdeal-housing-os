"use client";

import Link from "next/link";
import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Card, Pill, Mono, type Tone } from "@/components/ui/primitives";
import { enqueueContact } from "@/lib/cockpit/actions";
import { cleanName } from "@/lib/cockpit/units-clean";
import type {
  UnitRegistry as UnitRegistryData, UnitCell, UnitTimelineEvent, RegParty,
  ExpiringLease, UnitReviewItem, Confidence, ProbableContact,
} from "@/lib/cockpit/types";

const STATUS_META: Record<UnitCell["status"], { label: string; dot: string; cell: string; tone: Tone }> = {
  tenanted: { label: "Tenanted", dot: "bg-emerald-500", cell: "border-emerald-300 bg-emerald-50 text-emerald-900", tone: "ready" },
  owned: { label: "Owner-held", dot: "bg-teal", cell: "border-teal/40 bg-teal/10 text-teal", tone: "active" },
  registered: { label: "Registered", dot: "bg-amber-500", cell: "border-amber-300 bg-amber-50 text-amber-900", tone: "review" },
  unknown: { label: "No data", dot: "bg-mist-deep", cell: "border-mist bg-white text-ink/30", tone: "neutral" },
};
const CAT_TONE: Record<string, Tone> = { ownership: "active", tenancy: "ready", encumbrance: "review", other: "neutral" };
const CONF: Record<Confidence, { label: string; tone: Tone }> = {
  clean: { label: "Confirmed", tone: "ready" },
  recovered: { label: "Auto-placed", tone: "review" },
  partial: { label: "Wing or flat missing", tone: "review" },
  unknown: { label: "Unreadable", tone: "blocked" },
};

function inr(n?: number): string {
  if (!n) return "—";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
}
function ymd(d?: string): string { return d ? d.slice(0, 10) : "—"; }
function expiringTone(end?: string): Tone {
  if (!end) return "neutral";
  const days = (new Date(end).getTime() - Date.now()) / 86_400_000;
  if (days < 0) return "blocked";
  if (days < 183) return "review";
  return "ready";
}

export function UnitRegistry({ data }: { data: UnitRegistryData }) {
  const towers = data.towers.length ? data.towers : [{ letter: "", label: "All units", floors: 1, unitsPerFloor: 6, unitCount: data.units.length }];
  const [tower, setTower] = useState(towers[0]?.letter ?? "");
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"stack" | "review">("stack");

  const tUnits = useMemo(() => data.units.filter((u) => u.tower === tower), [data.units, tower]);
  const byPos = useMemo(() => { const m = new Map<string, UnitCell>(); for (const u of tUnits) m.set(`${u.floor}-${u.position}`, u); return m; }, [tUnits]);
  const sel = selected ? data.units.find((u) => `${u.tower}-${u.flat}` === selected) ?? null : null;
  const tMeta = towers.find((t) => t.letter === tower) ?? towers[0];

  // Jump from an expiring-lease row or review card to the matching unit cell.
  function jumpToUnit(wing: string, unit: string) {
    const digits = unit.replace(/\D/g, "");
    const cell = data.units.find((u) => u.tower === wing && u.flat.replace(/\D/g, "") === digits);
    if (!cell) return false;
    setView("stack"); setTower(cell.tower); setSelected(`${cell.tower}-${cell.flat}`);
    return true;
  }

  if (!data.units.length && !data.reviewQueue.length) {
    return <Card className="p-6 text-sm text-ink/55">No units for {data.buildingName} yet.</Card>;
  }

  const s = data.stats;
  const perFloor = Math.max(tMeta.unitsPerFloor ?? data.unitsPerFloor, 1);
  const floors = Array.from({ length: Math.max(tMeta.floors, 1) }, (_, i) => Math.max(tMeta.floors, 1) - i);
  const reviewCount = data.reviewQueue.length;

  return (
    <div className="space-y-6">
      {/* stats strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat n={s.registrations} label="Registrations parsed" sub={`${s.withRegistration} units · ${s.panCount} PANs`} />
        <Stat n={`${s.occupancyPct}%`} label="Tenanted (of mapped)" sub={`${s.tenanted} active leases`} tone="ready" />
        <Stat n={s.owned} label="Owner-held" sub={`${s.mappedUnits} units with data`} tone="active" />
        <Stat n={inr(s.avgRent)} label="Avg monthly rent" sub="active leases" />
        <Stat n={s.expiring12mo} label="Leases expiring ≤12mo" sub={`${s.expiring6mo} within 6mo`} tone={s.expiring6mo ? "review" : "neutral"} />
        <Stat n={s.minPrice ? `${inr(s.minPrice)}–${inr(s.maxPrice)}` : "—"} label="Sale price range" sub={`avg tenure ${s.avgOwnershipYears}y`} />
      </div>

      {/* expiring leases */}
      {data.expiringLeases.length > 0 && <ExpiringLeasesPanel leases={data.expiringLeases} onJump={jumpToUnit} />}

      {/* view toggle */}
      <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Unit registry view">
        <ViewTab active={view === "stack"} onClick={() => setView("stack")}>Building stack</ViewTab>
        <ViewTab active={view === "review"} onClick={() => setView("review")} disabled={!reviewCount}>
          Needs review {reviewCount > 0 && <span className="ml-1 rounded-full bg-amber-500 px-1.5 text-[11px] font-semibold text-white tabular-nums">{reviewCount}</span>}
        </ViewTab>
      </div>

      {view === "review" ? (
        <ReviewBoard items={data.reviewQueue} onJump={jumpToUnit} />
      ) : (
        <>
          {/* tower switcher */}
          <div className="flex flex-wrap items-center gap-2">
            {towers.map((t) => (
              <button key={t.letter} onClick={() => { setTower(t.letter); setSelected(null); }}
                className={`rounded-full border px-3.5 py-1 text-[13px] font-medium transition ${
                  t.letter === tower ? "border-teal bg-teal text-white" : "border-mist-deep text-ink/55 hover:text-teal"}`}>
                {t.label} <span className="opacity-60">· {t.unitCount}</span>
              </button>
            ))}
            <span className="ml-auto flex flex-wrap items-center gap-3 text-[12px] text-ink/55">
              {(Object.keys(STATUS_META) as UnitCell["status"][]).map((k) => (
                <span key={k} className="inline-flex items-center gap-1.5"><span className={`h-2.5 w-2.5 rounded-full ${STATUS_META[k].dot}`} />{STATUS_META[k].label}</span>
              ))}
            </span>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1fr_440px]">
            {/* building stack */}
            <Card className="overflow-hidden p-0">
              <div className="border-b border-mist px-4 py-2 text-[12px] text-ink/45">{tMeta.label} · {tMeta.floors} floors × {perFloor}/floor (inferred grid)</div>
              <div className="max-h-[620px] overflow-y-auto p-3">
                {floors.map((fl) => (
                  <div key={fl} className="flex items-center gap-2 border-b border-mist/60 py-1.5 last:border-0">
                    <span className="w-9 shrink-0 text-right text-[11px] tabular-nums text-ink/40">{fl}</span>
                    <div className="grid flex-1 gap-1.5" style={{ gridTemplateColumns: `repeat(${perFloor}, minmax(0, 1fr))` }}>
                      {Array.from({ length: perFloor }, (_, i) => i + 1).map((pos) => {
                        const u = byPos.get(`${fl}-${pos}`);
                        const meta = STATUS_META[u?.status ?? "unknown"];
                        const key = u ? `${u.tower}-${u.flat}` : "";
                        return (
                          <button key={pos} onClick={() => u && setSelected(key)} disabled={!u}
                            title={u ? `Flat ${u.flat} — ${meta.label}` : "no unit"}
                            aria-label={u ? `Flat ${u.flat}, ${meta.label}` : "empty"}
                            className={`h-9 rounded-md border text-[11px] font-medium tabular-nums transition ${meta.cell} ${
                              u ? "cursor-pointer hover:ring-2 hover:ring-teal/40" : "cursor-default opacity-50"} ${selected === key ? "ring-2 ring-teal" : ""}`}>
                            {u ? u.flat : ""}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <div className="space-y-3">
              {sel ? <UnitDetail unit={sel} /> : <Card className="p-5 text-sm text-ink/50">Select a unit to see its full ownership &amp; tenancy record.</Card>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ViewTab({ active, onClick, disabled, children }: { active: boolean; onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button role="tab" aria-selected={active} onClick={onClick} disabled={disabled}
      className={`inline-flex items-center rounded-lg border px-3.5 py-1.5 text-[13px] font-medium transition ${
        active ? "border-teal bg-teal text-white" : "border-mist-deep text-ink/60 hover:text-teal"} ${disabled ? "cursor-not-allowed opacity-40" : ""}`}>
      {children}
    </button>
  );
}

function UnitOutreachButton({ contactId }: { contactId: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => {
          setMsg(null);
          start(async () => {
            const res = await enqueueContact({ contactId, apply: true });
            setMsg(res.message);
            if (res.applied) router.refresh();
          });
        }}
        disabled={pending}
        className="rounded-lg bg-teal px-3 py-1.5 text-[13px] font-semibold text-white hover:bg-teal/90 disabled:opacity-40"
      >
        + Add to outreach
      </button>
      {msg && <span className="font-mono text-[11px] text-ink/55">{msg}</span>}
    </div>
  );
}

function UnitDetail({ unit }: { unit: UnitCell }) {
  const meta = STATUS_META[unit.status];
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold text-teal">Flat {unit.flat}</h3>
          {unit.ownerContactId && (
            <div className="mt-2">
              <UnitOutreachButton contactId={unit.ownerContactId} />
            </div>
          )}
        </div>
        <Pill tone={meta.tone}>{meta.label}</Pill>
      </div>
      <p className="mt-0.5 text-[12px] text-ink/45">Tower {unit.tower} · floor {unit.floor} · {unit.registrationCount} registration{unit.registrationCount === 1 ? "" : "s"}</p>

      {unit.contactMatches.length > 0 && <ContactMatches matches={unit.contactMatches} />}

      <div className="mt-4 grid grid-cols-2 gap-3 text-[13px]">
        <div>
          <div className="text-[11px] uppercase tracking-wide text-ink/40">
            {unit.ownerContact ? "Owner (from contacts)" : "Current owner"}
          </div>
          {unit.ownerContactId ? (
            <Link
              href={`/cockpit/contacts/c/${unit.ownerContactId}`}
              aria-label={`Open contact for ${unit.currentOwner ?? "owner"}`}
              className="text-teal underline underline-offset-2 hover:opacity-75"
            >
              {unit.currentOwner ?? "—"}
            </Link>
          ) : (
            <div className="text-ink/85">{unit.currentOwner ?? "—"}</div>
          )}
        </div>
        <Field label="Owned since" value={ymd(unit.ownerSince)} />
        <Field label="Last sale price" value={inr(unit.lastPrice)} />
        <Field label="Active tenant" value={unit.currentTenant ?? "—"} />
        {unit.currentTenant && <Field label="Rent / month" value={inr(unit.rent)} />}
        {unit.currentTenant && unit.deposit && <Field label="Deposit" value={inr(unit.deposit)} />}
        {unit.currentTenant && unit.tenancyStart && <Field label="Leased since" value={ymd(unit.tenancyStart)} />}
        {unit.currentTenant && (
          <div>
            <div className="text-[11px] uppercase tracking-wide text-ink/40">Lease expires</div>
            <Pill tone={expiringTone(unit.tenancyEnd)}>
              {unit.tenancyEnd ? ymd(unit.tenancyEnd) : "end unknown"}
            </Pill>
          </div>
        )}
      </div>

      {unit.events.length === 0 ? (
        <p className="mt-5 text-[12px] text-ink/40">No IGR registrations parsed for this unit yet — owner shown from imported contacts where available.</p>
      ) : (
        <div className="mt-5">
          <div className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-ink/45">Registration timeline</div>
          <Timeline events={unit.events} />
        </div>
      )}
      <p className="mt-4 text-[11px] text-ink/35">Sourced from IGR registrations (review-gated). Names shown in Devanagari as recorded; romanization is auto-generated — verify before action.</p>
    </Card>
  );
}

/** Vertical timeline: a connector rail with a dot per event, newest last. */
function Timeline({ events }: { events: UnitTimelineEvent[] }) {
  return (
    <ol className="relative space-y-4 border-l-2 border-mist pl-5">
      {events.map((e, i) => <TimelineEvent key={i} e={e} />)}
    </ol>
  );
}

function TimelineEvent({ e }: { e: UnitTimelineEvent }) {
  const isTenancy = e.category === "tenancy";
  const headline = isTenancy ? (e.rent ? `${inr(e.rent)}/mo` : "lease") : (e.consideration ? inr(e.consideration) : "—");
  const dotColor = isTenancy ? "bg-emerald-500" : e.category === "ownership" ? "bg-teal" : e.category === "encumbrance" ? "bg-amber-500" : "bg-mist-deep";
  const expired = isTenancy && expiringTone(e.tenancyEnd) === "blocked";
  return (
    <li className="relative">
      <span className={`absolute -left-[27px] top-1 h-3 w-3 rounded-full ring-2 ring-white ${dotColor}`} aria-hidden />
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13px] font-semibold text-ink/85">{e.year || "—"} · {e.docType.replace(/_/g, " ")}</span>
        <span className={`shrink-0 text-[12px] font-medium tabular-nums ${expired ? "text-red-600" : "text-ink/75"}`}>{headline}</span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1.5">
        <Pill tone={CAT_TONE[e.category] ?? "neutral"}>{e.category}</Pill>
        {e.active && <Pill tone={expiringTone(e.tenancyEnd)}>active{e.tenancyEnd ? ` · to ${ymd(e.tenancyEnd)}` : " · end unknown"}</Pill>}
        <Mono className="text-[11px] text-ink/40">doc {e.docNumber}{e.sro ? ` · ${e.sro}` : ""}{e.date ? ` · ${ymd(e.date)}` : ""}</Mono>
      </div>

      {(e.marketValue || e.stampDuty || e.regFee || e.area || e.deposit || isTenancy) && (
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-ink/55 sm:grid-cols-3">
          {isTenancy ? <Mini label="Lease period" v={`${ymd(e.tenancyStart)} → ${ymd(e.tenancyEnd)}`} /> : null}
          {e.marketValue ? <Mini label="Market value" v={inr(e.marketValue)} /> : null}
          {e.stampDuty ? <Mini label="Stamp duty" v={inr(e.stampDuty)} /> : null}
          {e.regFee ? <Mini label="Reg fee" v={inr(e.regFee)} /> : null}
          {e.deposit ? <Mini label="Deposit" v={inr(e.deposit)} /> : null}
          {e.area ? <Mini label="Area" v={e.area.replace(/^क्षेत्रफळ\s*/, "")} /> : null}
        </div>
      )}

      <div className="mt-2 space-y-1.5">
        {e.parties.map((p, i) => <PartyRow key={i} p={p} />)}
      </div>
    </li>
  );
}

function ExpiringLeasesPanel({ leases, onJump }: { leases: ExpiringLease[]; onJump: (w: string, u: string) => boolean }) {
  const urgencyTone = (days: number): Tone => days <= 30 ? "blocked" : days <= 90 ? "review" : "neutral";
  const urgencyBg = (days: number) => days <= 30 ? "border-red-200 bg-red-50" : days <= 90 ? "border-amber-200 bg-amber-50" : "border-mist bg-white";
  return (
    <Card className="p-0 overflow-hidden">
      <div className="flex items-center justify-between border-b border-mist px-4 py-2.5">
        <span className="text-[13px] font-semibold text-ink/80">Leases expiring within 6 months</span>
        <Pill tone="review">{leases.length}</Pill>
      </div>
      <ul className="divide-y divide-mist">
        {leases.map((l, i) => {
          const unclear = l.confidence !== "clean";
          const label = l.wing !== "—" || l.unit !== "—" ? `${l.wing === "—" ? "Wing ?" : `Wing ${l.wing}`} · ${l.unit}` : "Unit unresolved";
          return (
            <li key={i} className={`border-l-4 px-4 py-3 text-[13px] ${urgencyBg(l.daysRemaining)}`}>
              <div className="flex flex-wrap items-start gap-x-6 gap-y-1.5">
                <div className="min-w-[120px]">
                  <button
                    onClick={() => onJump(l.wing, l.unit)}
                    className="text-left font-semibold text-ink/85 hover:text-teal hover:underline disabled:cursor-default disabled:no-underline disabled:hover:text-ink/85"
                    disabled={l.wing === "—" || l.unit === "—"}
                    aria-label={`Open ${label}`}
                  >
                    {label}
                  </button>
                  <div className="mt-1 flex items-center gap-1.5">
                    <Pill tone={urgencyTone(l.daysRemaining)}>{l.daysRemaining}d left</Pill>
                    {unclear && <Pill tone={CONF[l.confidence].tone}>{CONF[l.confidence].label}</Pill>}
                  </div>
                </div>
                <div className="flex-1 min-w-[160px]">
                  <div className="text-ink/80">{l.tenantNames}</div>
                  {l.tenantPans && <Mono className="text-[11px] text-ink/45">{l.tenantPans}</Mono>}
                </div>
                <div className="text-right tabular-nums">
                  <div className="font-medium text-ink/80">{inr(l.rent)}<span className="text-ink/40 text-[11px]">/mo</span></div>
                  {l.deposit ? <div className="text-[11px] text-ink/45">dep {inr(l.deposit)}</div> : null}
                </div>
                <div className="text-[11px] text-ink/50 min-w-[150px]">
                  <div>{ymd(l.tenancyStart)} → <span className="font-medium text-ink/70">{ymd(l.tenancyEnd)}</span></div>
                  <div className="text-ink/35">owner: {l.ownerNames}</div>
                  <Mono className="text-[10.5px] text-ink/30">doc {l.docNumber}{l.sro ? ` · ${l.sro}` : ""}</Mono>
                </div>
              </div>
              {l.contactMatches.length > 0 && <ContactMatches matches={l.contactMatches} />}
              {unclear && l.descriptionRaw && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-[11px] text-teal/80 hover:text-teal">Read register description (place wing &amp; flat)</summary>
                  <p className="mt-1 rounded-md bg-white/70 p-2 text-[12px] leading-relaxed text-ink/70">{l.descriptionRaw}</p>
                </details>
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

/** Probable phone/email matched by name from contacts + imports — conservative, verify before use. */
function ContactMatches({ matches }: { matches: ProbableContact[] }) {
  const digits = (p?: string) => (p ?? "").replace(/[^\d+]/g, "");
  return (
    <div className="mt-2 rounded-md border border-teal/20 bg-teal/5 px-2.5 py-2">
      <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-wide text-teal/70">Probable contact info · name-matched, verify</div>
      <ul className="space-y-1.5">
        {matches.map((m, i) => (
          <li key={i} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12px]">
            <span className="font-medium text-ink/85">
              {m.contactId ? <Link href={`/cockpit/contacts/c/${m.contactId}`} className="text-teal underline underline-offset-2 hover:opacity-75">{m.name}</Link> : m.name}
            </span>
            <Pill tone={m.confidence === "strong" ? "ready" : "review"}>{m.confidence}{m.unitMatch ? " · unit" : ""}</Pill>
            <span className="text-[10px] uppercase tracking-wide text-ink/40">{m.role} · {m.source}</span>
            {m.phone && (
              <span className="flex items-center gap-1.5">
                <a href={`tel:${digits(m.phone)}`} className="font-mono text-[11px] text-ink/70 hover:text-teal">{m.phone}</a>
                <a href={`https://wa.me/${digits(m.phone).replace(/^\+/, "")}`} target="_blank" rel="noopener noreferrer"
                   className="rounded bg-emerald-500/90 px-1.5 py-0.5 text-[10px] font-semibold text-white hover:bg-emerald-500" aria-label={`WhatsApp ${m.name}`}>WA</a>
              </span>
            )}
            {m.email && <a href={`mailto:${m.email}`} className="font-mono text-[11px] text-ink/55 hover:text-teal">{m.email}</a>}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Kanban-style triage: registrations whose wing/flat couldn't be cleanly resolved. */
function ReviewBoard({ items, onJump }: { items: UnitReviewItem[]; onJump: (w: string, u: string) => boolean }) {
  const cols: { key: Confidence; title: string; hint: string }[] = [
    { key: "unknown", title: "Unreadable", hint: "No wing or flat — read the description" },
    { key: "partial", title: "Wing or flat missing", hint: "One half recovered, confirm the other" },
    { key: "recovered", title: "Auto-placed — verify", hint: "Read description, confirm placement" },
  ];
  return (
    <div>
      <p className="mb-3 text-[12px] text-ink/55">
        {items.length} registration{items.length === 1 ? "" : "s"} couldn&apos;t be cleanly mapped to a wing + flat. Read the register
        description (Devanagari or English) on each card and confirm where it belongs. Editing &amp; saving back is the next step —
        for now this surfaces every ambiguous record with its best-guess placement.
      </p>
      <div className="grid gap-4 md:grid-cols-3">
        {cols.map((c) => {
          const colItems = items.filter((it) => it.confidence === c.key);
          return (
            <div key={c.key} className="rounded-xl border border-mist bg-mist/20 p-2">
              <div className="flex items-center justify-between px-1.5 py-1">
                <span className="text-[12px] font-semibold text-ink/75">{c.title}</span>
                <Pill tone={CONF[c.key].tone}>{colItems.length}</Pill>
              </div>
              <p className="px-1.5 pb-2 text-[11px] text-ink/40">{c.hint}</p>
              <div className="max-h-[640px] space-y-2 overflow-y-auto">
                {colItems.length === 0
                  ? <p className="px-1.5 py-3 text-[12px] text-ink/35">Nothing here.</p>
                  : colItems.map((it) => <ReviewCard key={it.recordId} item={it} onJump={onJump} />)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReviewCard({ item, onJump }: { item: UnitReviewItem; onJump: (w: string, u: string) => boolean }) {
  const guess = [item.recoveredWing && `Wing ${item.recoveredWing}`, item.recoveredUnit && `Flat ${item.recoveredUnit}`].filter(Boolean).join(" · ");
  const canJump = Boolean(item.recoveredWing && item.recoveredUnit);
  return (
    <div className="rounded-lg border border-mist bg-white p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[12.5px] font-semibold text-ink/85">{item.year || "—"} · {item.docType.replace(/_/g, " ")}</span>
        <Pill tone={CAT_TONE[item.category] ?? "neutral"}>{item.category}</Pill>
      </div>
      <div className="mt-1 text-[11px] text-ink/45">
        best guess: {guess ? (
          canJump ? <button onClick={() => onJump(item.recoveredWing, item.recoveredUnit)} className="font-medium text-teal hover:underline">{guess}</button>
                  : <span className="font-medium text-ink/70">{guess}</span>
        ) : <span className="text-red-600">none</span>}
      </div>

      {/* raw signals the parser saw — the human reads these to place it */}
      <div className="mt-2 space-y-1 text-[11px]">
        {(item.wingTextRaw || item.unitTextRaw) && (
          <div className="text-ink/50"><span className="text-ink/35">register text:</span> <Mono className="text-ink/70">{[item.wingTextRaw, item.unitTextRaw].filter(Boolean).join(" / ")}</Mono></div>
        )}
        {item.descriptionRaw && (
          <p className="rounded-md bg-mist/40 p-2 leading-relaxed text-ink/70">{item.descriptionRaw}</p>
        )}
      </div>

      {item.parties.length > 0 && (
        <div className="mt-2 space-y-1.5">
          {item.parties.slice(0, 4).map((p, i) => <PartyRow key={i} p={p} />)}
          {item.parties.length > 4 && <div className="text-[11px] text-ink/35">+{item.parties.length - 4} more</div>}
        </div>
      )}
      <Mono className="mt-2 block text-[10.5px] text-ink/30">doc {item.docNumber}</Mono>
    </div>
  );
}

/** Devanagari is the recorded truth; romanization is auto-generated and often wrong, so demote it. */
function PartyRow({ p }: { p: RegParty }) {
  const { primary, roman } = cleanName(p.devanagari, p.english);
  return (
    <div className="rounded-md bg-mist/30 px-2.5 py-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span lang="mr" className="text-[12.5px] font-medium text-ink/85">{primary}</span>
        <span className="shrink-0 text-[10px] uppercase tracking-wide text-ink/45">{p.role}</span>
      </div>
      {roman && <div className="text-[11px] text-ink/40" title="auto-romanized — verify">{roman} <span className="text-ink/25">· auto</span></div>}
      <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[10.5px] text-ink/50">
        {p.pan && <span>PAN <Mono className="text-ink/70">{p.pan}</Mono></span>}
        {p.age ? <span>age {p.age}</span> : null}
        {p.type && p.type !== "individual" && <span className="text-teal">{p.type}</span>}
      </div>
      {p.address && <div className="mt-0.5 line-clamp-2 text-[10.5px] text-ink/40">{p.address}</div>}
    </div>
  );
}

function Stat({ n, label, sub, tone = "neutral" }: { n: string | number; label: string; sub?: string; tone?: Tone }) {
  const accent = tone === "ready" ? "text-emerald-600" : tone === "active" ? "text-teal" : tone === "review" ? "text-amber-600" : "text-ink";
  return (
    <Card className="p-3">
      <div className={`text-xl font-semibold tabular-nums ${accent}`}>{n}</div>
      <div className="text-[12px] text-ink/60">{label}</div>
      {sub && <div className="text-[11px] text-ink/40">{sub}</div>}
    </Card>
  );
}
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-ink/40">{label}</div>
      <div className="text-ink/85">{value}</div>
    </div>
  );
}
function Mini({ label, v }: { label: string; v: string }) {
  return <span><span className="text-ink/35">{label}:</span> <span className="text-ink/70 tabular-nums">{v}</span></span>;
}
