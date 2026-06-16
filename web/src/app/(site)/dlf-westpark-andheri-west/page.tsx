import type { Metadata } from "next";
import { Reveal } from "@/components/reveal";
import { Media, Frame } from "@/components/media";
import { Facets } from "@/components/facets";
import { ButtonLink } from "@/components/ui/kit";
import { PendingChip, Tokenize } from "@/components/placeholder";
import { StickyCta } from "@/components/sticky-cta";
import { project, facts, residences, amenities, faqs } from "@/lib/content";

export const metadata: Metadata = {
  title: project.seoTitle,
  description: project.seoDescription,
};

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-5 font-mono text-xs uppercase tracking-[0.2em] text-warm">
      {children}
    </p>
  );
}

export default function DlfWestparkPage() {
  return (
    <article>
      {/* HERO: asymmetric split with real imagery */}
      <section className="mx-auto max-w-6xl px-6 pb-16 pt-16 md:pt-24">
        <div className="grid items-center gap-10 md:grid-cols-[1.05fr_0.95fr] lg:gap-16">
          <Reveal>
            <p className="mb-6 font-mono text-xs uppercase tracking-[0.2em] text-warm">
              {project.developer} · {project.locality}
            </p>
            <h1 className="display text-balance text-[clamp(2.4rem,5.2vw,4.25rem)] font-extrabold leading-[1.04] text-teal">
              {project.name}
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink/70">
              {project.heroTagline}
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-ink/60">
              <span>Pricing <PendingChip token="PRICE_VERIFY" /></span>
              <span>RERA <PendingChip token="RERA_VERIFY" /></span>
              <span>Micro-market · {project.microMarket}</span>
            </div>
            <div className="mt-9 flex flex-wrap gap-3.5">
              <ButtonLink href="#enquiry">Request details →</ButtonLink>
              <ButtonLink href="#facts" variant="secondary">
                See verified facts
              </ButtonLink>
            </div>
          </Reveal>

          <Reveal delay={0.12}>
            <div className="relative">
              <Facets className="facet-float absolute -right-4 -top-6 z-10 h-16 w-28 md:-right-6 md:h-20 md:w-36" />
              <Frame ratio="aspect-[4/5]" className="shadow-[0_30px_80px_-40px_rgba(31,61,77,0.55)]">
                <Media
                  seed="rdh-dlf-westpark-andheri-residence"
                  w={720}
                  h={900}
                  alt="DLF Westpark, Andheri West"
                  priority
                />
              </Frame>
            </div>
          </Reveal>
        </div>
      </section>

      {/* OVERVIEW */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <Reveal>
          <Label>Project overview</Label>
          <p className="max-w-3xl text-2xl font-medium leading-snug tracking-tight text-teal md:text-3xl">
            {project.overview}
          </p>
        </Reveal>
      </section>

      {/* DEVELOPER CONTEXT */}
      <section className="border-y border-mist-deep bg-mist/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <Reveal>
            <div className="grid gap-8 md:grid-cols-[1.2fr_1fr] md:items-end">
              <h2 className="display text-3xl font-bold leading-tight text-teal md:text-[2.5rem]">
                Built by DLF, verified before it&rsquo;s published.
              </h2>
              <p className="text-ink/65">
                Developer and full project particulars remain under review (
                <PendingChip token="VERIFY" />). We show DLF as the named
                developer based on operator confirmation, and replace every
                pending marker with a sourced fact before anything goes live.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* LOCATION */}
      <section className="mx-auto max-w-6xl px-6 py-20 md:py-24">
        <div className="grid gap-12 md:grid-cols-2 md:items-center">
          <Reveal>
            <h2 className="display text-3xl font-bold text-teal md:text-[2.5rem]">
              Andheri West, D.N. Nagar / Link Road
            </h2>
            <p className="mt-5 text-ink/65">
              Positioned in one of Mumbai&rsquo;s most established western
              micro-markets. Exact addressing, distances and connectivity times
              are human-reviewable and stay <PendingChip token="VERIFY" /> until
              confirmed.
            </p>
            <ul className="mt-6 grid gap-2.5 text-sm text-ink/65">
              <li>Commute and metro access <PendingChip token="VERIFY" /></li>
              <li>Schools and institutions <PendingChip token="VERIFY" /></li>
              <li>Retail and lifestyle <PendingChip token="VERIFY" /></li>
            </ul>
          </Reveal>
          <Reveal delay={0.1}>
            <Frame ratio="aspect-[4/3]">
              <Media
                seed="rdh-andheri-west-link-road-locality"
                w={760}
                h={570}
                alt="Andheri West locality around D.N. Nagar and Link Road"
              />
            </Frame>
          </Reveal>
        </div>
      </section>

      {/* AMENITIES */}
      <section className="bg-teal text-white">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <h2 className="display max-w-2xl text-3xl font-bold text-white md:text-[2.5rem]">
              The everyday, considered.
            </h2>
          </Reveal>
          <div className="mt-12 grid gap-px overflow-hidden rounded-2xl bg-white/15 sm:grid-cols-2 lg:grid-cols-3">
            {amenities.map((a, i) => (
              <Reveal key={a.name} delay={i * 0.05}>
                <div className="h-full bg-teal p-7">
                  <div className="font-mono text-xs uppercase tracking-wider text-warm">
                    {a.category}
                  </div>
                  <div className="mt-3 text-lg font-semibold">{a.name}</div>
                  <p className="mt-2 text-sm leading-relaxed text-white/55">
                    <Tokenize text={a.description} />
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* RESIDENCES */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <Label>Residences</Label>
          <h2 className="display text-3xl font-bold text-teal md:text-[2.5rem]">
            Configurations
          </h2>
        </Reveal>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {residences.map((r, i) => (
            <Reveal key={r.config} delay={i * 0.06}>
              <div className="flex h-full flex-col rounded-2xl p-6 ring-1 ring-mist-deep">
                <div className="text-lg font-semibold text-teal">{r.config}</div>
                <dl className="mt-4 space-y-2.5 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <dt className="text-ink/50">Carpet area</dt>
                    <dd><PendingChip token={r.carpetArea} /></dd>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <dt className="text-ink/50">Price</dt>
                    <dd><PendingChip token={r.price} /></dd>
                  </div>
                </dl>
                <a
                  href="#enquiry"
                  className="mt-6 inline-block text-sm font-semibold text-teal underline-offset-4 hover:underline"
                >
                  Request details →
                </a>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* GALLERY */}
      <section className="border-t border-mist-deep bg-mist/40">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <h2 className="display text-3xl font-bold text-teal md:text-[2.5rem]">
              A look around
            </h2>
          </Reveal>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              "facade",
              "interiors",
              "amenity-deck",
              "skyline-views",
              "lobby",
              "landscape",
            ].map((g, i) => (
              <Reveal key={g} delay={(i % 3) * 0.05}>
                <Frame ratio="aspect-[4/3]">
                  <Media
                    seed={`rdh-dlf-westpark-${g}`}
                    w={560}
                    h={420}
                    alt={`DLF Westpark ${g.replace(/-/g, " ")}`}
                  />
                </Frame>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* VERIFIED FACTS LEDGER */}
      <section id="facts" className="mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <Label>Verified facts ledger</Label>
          <h2 className="display max-w-2xl text-3xl font-bold text-teal md:text-[2.5rem]">
            Every claim, with its verification status.
          </h2>
        </Reveal>
        <Reveal>
          <div className="mt-10 divide-y divide-mist overflow-hidden rounded-2xl bg-white ring-1 ring-mist-deep">
            {facts.map((f) => (
              <div
                key={f.key}
                className="grid items-center gap-3 px-6 py-4 md:grid-cols-[1fr_1.4fr_auto]"
              >
                <div className="text-sm font-semibold text-teal">{f.label}</div>
                <div className="text-sm text-ink/70">
                  <Tokenize text={f.value} />
                </div>
                <StatusBadge status={f.status} />
              </div>
            ))}
          </div>
        </Reveal>
        <p className="mt-4 font-mono text-xs text-ink/45">
          Source of truth: local Postgres OS. Website snapshot only. No value
          published until verified.
        </p>
      </section>

      {/* PREVIEW-ONLY ENQUIRY */}
      <section id="enquiry" className="border-y border-mist-deep bg-mist/40">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="grid gap-12 md:grid-cols-[1fr_1.1fr]">
            <Reveal>
              <h2 className="display text-3xl font-bold text-teal md:text-[2.5rem]">
                Request details
              </h2>
              <p className="mt-5 max-w-md text-ink/65">
                This is a staging preview. The form does{" "}
                <strong className="text-teal">not</strong> submit: there is no
                live capture, no automation, and no contact is created. Enquiries
                are manual-review only.
              </p>
              <p className="mt-4 inline-flex rounded-md bg-mist px-3 py-2 font-mono text-xs text-ink/60">
                send_enabled = false · webhook = none · CRM_write = none
              </p>
            </Reveal>

            {/* Preview-only form: no action, submit disabled, consent unchecked */}
            <Reveal delay={0.1}>
              <form
                aria-disabled
                className="rounded-2xl bg-white p-7 ring-1 ring-mist-deep"
              >
                <div className="grid gap-4">
                  <Field label="Name" placeholder="Your name" />
                  <Field label="Contact method" placeholder="Phone or email" />
                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-ink/55">
                      Buying intent
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {["End use", "Investment", "Just exploring"].map((p) => (
                        <span
                          key={p}
                          className="rounded-full border border-mist-deep px-3 py-1.5 text-xs text-ink/65"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                  <Field label="Message" placeholder="Anything specific?" textarea />
                  <label className="flex items-start gap-2.5 text-xs text-ink/65">
                    <input type="checkbox" disabled className="mt-0.5" />
                    I consent to be contacted about this enquiry.
                  </label>
                  <label className="flex items-start gap-2.5 text-xs text-ink/65">
                    <input type="checkbox" disabled className="mt-0.5" />
                    I have read the privacy note.
                  </label>
                  <button
                    type="button"
                    disabled
                    className="mt-1 cursor-not-allowed rounded-full bg-mist-deep px-6 py-3.5 text-sm font-semibold text-ink/50"
                  >
                    Preview only - no live submission
                  </button>
                </div>
              </form>
            </Reveal>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="mx-auto max-w-3xl px-6 py-24">
        <Reveal>
          <h2 className="display text-3xl font-bold text-teal md:text-[2.5rem]">
            Questions, answered honestly.
          </h2>
        </Reveal>
        <div className="mt-10 divide-y divide-mist-deep border-y border-mist-deep">
          {faqs.map((f) => (
            <details key={f.question} className="group py-5">
              <summary className="flex cursor-pointer items-center justify-between gap-4 text-lg font-semibold text-teal marker:content-['']">
                {f.question}
                <span className="font-mono text-ink/40 transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-3 text-ink/65">
                <Tokenize text={f.answer} />
              </p>
            </details>
          ))}
        </div>
      </section>

      <StickyCta />
    </article>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    operator_confirmed: { label: "Confirmed", cls: "bg-teal/10 text-teal" },
    pending_review: { label: "Under review", cls: "bg-warm/10 text-warm" },
    pending: { label: "Pending", cls: "bg-mist text-ink/50" },
  };
  const s = map[status] ?? map.pending;
  return (
    <span
      className={`justify-self-start rounded-full px-2.5 py-1 font-mono text-[11px] font-medium md:justify-self-end ${s.cls}`}
    >
      {s.label}
    </span>
  );
}

function Field({
  label,
  placeholder,
  textarea,
}: {
  label: string;
  placeholder: string;
  textarea?: boolean;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-ink/55">
        {label}
      </label>
      {textarea ? (
        <textarea
          disabled
          rows={3}
          placeholder={placeholder}
          className="w-full resize-none rounded-xl border border-mist-deep bg-mist/40 px-3.5 py-2.5 text-sm text-ink placeholder:text-ink/45 focus:bg-white focus:outline-none"
        />
      ) : (
        <input
          disabled
          placeholder={placeholder}
          className="w-full rounded-xl border border-mist-deep bg-mist/40 px-3.5 py-2.5 text-sm text-ink placeholder:text-ink/45 focus:bg-white focus:outline-none"
        />
      )}
    </div>
  );
}
