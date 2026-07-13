import type { Metadata } from "next";
import Link from "next/link";
import { Reveal } from "@/components/reveal";
import { ZoomImage } from "@/components/zoom-image";
import { NeighborhoodMap } from "@/components/neighborhood-map";
import { PendingChip, Tokenize } from "@/components/placeholder";
import { RevealImage } from "@/components/reveal-image";
import { projectImages } from "@/lib/site";
import { StickyCta } from "@/components/sticky-cta";
import { project, facts, residences, amenities, faqs } from "@/lib/content";

export const metadata: Metadata = {
  title: project.seoTitle,
  description: project.seoDescription,
};

function Eyebrow({ n, label }: { n: string; label: string }) {
  return (
    <p className="mb-5 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-ink/45">
      <span className="font-mono text-warm">{n}</span>
      <span className="h-px w-8 bg-mist-deep" />
      {label}
    </p>
  );
}

export default function DlfWestparkPage() {
  return (
    <article>
      {/* 01 — HERO */}
      <section className="mx-auto max-w-6xl px-6 pb-20 pt-16 md:pt-24">
        <Reveal>
          <p className="mb-6 flex items-center gap-2 text-sm font-medium text-ink/55">
            <span className="inline-block h-2 w-2 rounded-full bg-warm" />
            {project.developer} · {project.locality}
          </p>
          <h1 className="max-w-4xl text-[clamp(2.5rem,6.5vw,5.25rem)] font-extrabold leading-[1.03] tracking-tight text-teal">
            {project.name}
          </h1>
          <p className="mt-7 max-w-2xl text-xl leading-relaxed text-ink/70">
            {project.heroTagline}
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-ink/60">
            <span>Pricing on request</span>
            <span>MahaRERA PR1181012500079 · Phase 1 complete</span>
            <span>Micro-market · {project.microMarket}</span>
          </div>
          <div className="mt-10 flex flex-wrap gap-4">
            <a
              href="#enquiry"
              className="rounded-full bg-teal px-6 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              Request details
            </a>
            <Link
              href="/dlf-westpark-andheri-west/plans"
              className="rounded-full border border-mist-deep px-6 py-3.5 text-sm font-semibold text-teal transition-colors hover:bg-mist"
            >
              Explore floor plans →
            </Link>
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <figure className="mt-14">
            <RevealImage
              src={projectImages["dlf-westpark-andheri-west"].src}
              alt={projectImages["dlf-westpark-andheri-west"].alt}
              priority
              sizes="(max-width: 1152px) 100vw, 1152px"
              className="aspect-[21/9] w-full rounded-2xl"
            />
            <figcaption className="mt-2 text-right font-mono text-[11px] text-ink/40">
              Artist&rsquo;s impression — from the official project brochure
            </figcaption>
          </figure>
        </Reveal>
      </section>

      {/* 02 — PROJECT OVERVIEW */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <Reveal>
          <Eyebrow n="02" label="Project overview" />
          <p className="max-w-3xl text-2xl font-medium leading-snug tracking-tight text-teal md:text-3xl">
            {project.overview}
          </p>
        </Reveal>
      </section>

      {/* 03 — DLF TRUST / DEVELOPER */}
      <section className="border-y border-mist-deep bg-mist/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <Reveal>
            <Eyebrow n="03" label="Developer context" />
            <div className="grid gap-10 md:grid-cols-[1.2fr_1fr]">
              <h2 className="text-3xl font-bold leading-tight tracking-tight text-teal md:text-4xl">
                Built by DLF — verified before it&rsquo;s published.
              </h2>
              <p className="self-end text-ink/65">
                Phase 1 is developed by Peegen Builders and Developers Pvt. Ltd. —
                a DLF and Trident Realty joint venture — under MahaRERA
                PR1181012500079, per the official brochure. Pricing and
                possession remain marked <PendingChip token="VERIFY" /> until
                individually confirmed.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* 04 — LOCATION */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <Reveal>
          <Eyebrow n="04" label="Location" />
          <div className="grid gap-12 md:grid-cols-2">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-teal md:text-4xl">
                Andheri West · D.N. Nagar / Link Road
              </h2>
              <p className="mt-5 text-ink/65">
                Positioned in one of Mumbai&rsquo;s most established western
                micro-markets. Everything below sits within ~1.5 km of the
                project (OpenStreetMap data — explore it on the map). Exact
                project addressing stays <PendingChip token="VERIFY" /> until
                confirmed.
              </p>
              <ul className="mt-6 space-y-2 text-sm text-ink/60">
                <li>· Commute &amp; metro — D.N. Nagar &amp; Versova (Line 1) and Lower Oshiwara (Line 2A) metro stations; Link Road on the doorstep</li>
                <li>· Schools &amp; institutions — Holy Cross Convent, A.H. Wadia High School, Cosmopolitan Education Society</li>
                <li>· Retail &amp; lifestyle — Infinity Mall and Crystal Plaza, with Versova&rsquo;s café belt close by</li>
              </ul>
            </div>
            <figure>
              <ZoomImage
                src="/dlf/building-connectivity-map-p4.jpg"
                alt="DLF Westpark connectivity map, Andheri West"
                sizes="(max-width: 768px) 100vw, 50vw"
                className="aspect-square overflow-hidden rounded-2xl border border-mist-deep bg-white"
                imgClassName="object-contain"
              />
              <figcaption className="mt-2 text-right font-mono text-[11px] text-ink/40">
                Connectivity map — official brochure, not to scale · click to enlarge
              </figcaption>
            </figure>
          </div>
        </Reveal>
        <div className="mt-14">
          <NeighborhoodMap
            slug="dlf-westpark"
            buildingName="DLF Westpark"
            lat={19.1298}
            lng={72.8262}
          />
        </div>
      </section>

      {/* 05 — LIFESTYLE & AMENITIES */}
      <section className="border-t border-mist-deep bg-teal text-white">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <p className="mb-5 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-white/45">
              <span className="font-mono text-warm">05</span>
              <span className="h-px w-8 bg-white/25" />
              Lifestyle &amp; amenities
            </p>
            <h2 className="max-w-2xl text-3xl font-bold tracking-tight md:text-4xl">
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

      {/* 06 — RESIDENCES */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <Eyebrow n="06" label="Residences" />
          <div className="flex flex-wrap items-end justify-between gap-4">
            <h2 className="text-3xl font-bold tracking-tight text-teal md:text-4xl">
              Configurations
            </h2>
            <Link href="/dlf-westpark-andheri-west/plans" className="text-sm font-semibold text-teal hover:underline">
              Floor-by-floor explorer →
            </Link>
          </div>
        </Reveal>
        <div className="mt-10 divide-y divide-mist-deep border-y border-mist-deep">
          {residences.map((r, i) => (
            <Reveal key={r.config} delay={i * 0.05}>
              <div className="grid items-center gap-4 py-6 md:grid-cols-[1fr_1.1fr_1.4fr_auto]">
                <div className="text-lg font-semibold text-teal">{r.config}</div>
                <div className="text-sm text-ink/60">
                  Carpet area · <Tokenize text={r.carpetArea} />
                </div>
                <div className="text-sm text-ink/55">{r.description}</div>
                <a
                  href="#enquiry"
                  className="justify-self-start rounded-full border border-mist-deep px-4 py-2 text-xs font-semibold text-teal transition-colors hover:bg-mist md:justify-self-end"
                >
                  Pricing on request
                </a>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* 07 — GALLERY / VIDEO */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <Reveal>
          <Eyebrow n="07" label="Gallery" />
        </Reveal>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { src: "/dlf/building-building-exterior-all-towers-p2.jpg", alt: "DLF Westpark — all four towers, exterior render", label: "Façade — all towers" },
            { src: "/dlf/building-pool-and-landscape-overview-p3.jpg", alt: "DLF Westpark pool and landscape overview render", label: "Pool & landscape" },
            { src: "/dlf/building-eco-deck-pool-p46.jpg", alt: "DLF Westpark eco-deck swimming pool render", label: "Eco-deck pool" },
            { src: "/dlf/show-apartment-living-1.jpg", alt: "DLF Westpark show apartment living room", label: "Show apartment — living" },
            { src: "/dlf/show-apartment-master-bedroom.jpg", alt: "DLF Westpark show apartment master bedroom", label: "Show apartment — master bedroom" },
            { src: "/dlf/show-apartment-kitchen-1.jpg", alt: "DLF Westpark show apartment kitchen", label: "Show apartment — kitchen" },
          ].map((g, i) => (
            <Reveal key={g.src} delay={i * 0.04}>
              <figure>
                <ZoomImage
                  src={g.src}
                  alt={g.alt}
                  sizes="(max-width: 640px) 100vw, 33vw"
                  className="aspect-[4/3] overflow-hidden rounded-xl border border-mist-deep"
                />
                <figcaption className="mt-2 font-mono text-[10px] uppercase tracking-wide text-ink/40">
                  {g.label} · brochure / show flat · click to enlarge
                </figcaption>
              </figure>
            </Reveal>
          ))}
        </div>
      </section>

      {/* 08 — VERIFIED FACTS LEDGER */}
      <section id="facts" className="border-y border-mist-deep bg-mist/40">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <Eyebrow n="08" label="Verified facts ledger" />
            <h2 className="max-w-2xl text-3xl font-bold tracking-tight text-teal md:text-4xl">
              Every claim, with its verification status.
            </h2>
          </Reveal>
          <div className="mt-10 overflow-hidden rounded-2xl border border-mist-deep bg-white">
            {facts.map((f, i) => (
              <Reveal key={f.key} delay={i * 0.03}>
                <div className="grid items-center gap-3 border-b border-mist px-6 py-4 last:border-0 md:grid-cols-[1fr_1.4fr_auto]">
                  <div className="text-sm font-semibold text-teal">{f.label}</div>
                  <div className="text-sm text-ink/70">
                    <Tokenize text={f.value} />
                  </div>
                  <StatusBadge status={f.status} />
                </div>
              </Reveal>
            ))}
          </div>
          <p className="mt-4 font-mono text-xs text-ink/45">
            Source of truth: local Postgres OS · website snapshot only · no value
            published until verified.
          </p>
        </div>
      </section>

      {/* 09 — ENQUIRY */}
      <section id="enquiry" className="mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <Eyebrow n="09" label="Get in touch" />
          <div className="grid gap-12 md:grid-cols-[1fr_1.1fr]">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-teal md:text-4xl">
                Request the full brief.
              </h2>
              <p className="mt-5 max-w-md text-ink/65">
                Price list, floor plans and brochure — and a private presentation
                if you&rsquo;d like to go deeper. No commitment, no lock-in.
              </p>
              <div className="mt-8 space-y-3">
                <a
                  href="https://wa.me/918291293889?text=Hi%20Padmini%2C%20I%27m%20interested%20in%20DLF%20Westpark%20Phase%202%20%E2%80%94%20can%20you%20share%20the%20price%20list%20and%20floor%20plans%3F"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 rounded-full bg-warm px-6 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 w-fit"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.117.549 4.107 1.51 5.84L.057 23.428a.5.5 0 0 0 .614.614l5.588-1.453A11.95 11.95 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.885 0-3.65-.52-5.16-1.426l-.37-.22-3.818.993.993-3.818-.22-.37A9.956 9.956 0 0 1 2 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"/></svg>
                  WhatsApp Padmini
                </a>
                <a
                  href={`mailto:PadminiJain1@gmail.com?subject=${encodeURIComponent("DLF Westpark — request for details")}&body=${encodeURIComponent("Hi Padmini,\n\nI'd like the price list, floor plans and brochure for DLF Westpark Phase 2.\n\nName: \nPhone: \nConfiguration interest (3 / 4 BHK): \n\nThank you.")}`}
                  className="flex items-center gap-3 rounded-full border border-mist-deep px-6 py-3.5 text-sm font-semibold text-teal transition-colors hover:bg-mist w-fit"
                >
                  Email instead →
                </a>
              </div>
              <p className="mt-6 font-mono text-xs text-ink/40">
                +91 82912 93889 · Director, Real Deal Housing
              </p>
            </div>

            <div className="rounded-2xl border border-mist-deep bg-mist/30 p-8">
              <p className="font-mono text-xs uppercase tracking-wider text-ink/40 mb-5">What to expect</p>
              <ul className="space-y-4 text-sm text-ink/65">
                {[
                  "Price list and carpet area schedule for 3 & 4 BHK",
                  "Floor plans for Towers 6 & 7 (Phase 2)",
                  "Full brochure — DLF & Trident Realty",
                  "Private presentation if you want to go deeper",
                  "No lock-in, no brokerage pressure",
                ].map((item) => (
                  <li key={item} className="flex gap-3">
                    <span className="text-warm font-bold mt-0.5">—</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Reveal>
      </section>

      {/* 10 — FAQ (native disclosures, SEO text in DOM) */}
      <section className="border-t border-mist-deep bg-mist/30">
        <div className="mx-auto max-w-3xl px-6 py-24">
          <Reveal>
            <Eyebrow n="10" label="FAQ" />
            <h2 className="text-3xl font-bold tracking-tight text-teal md:text-4xl">
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
        </div>
      </section>

      <StickyCta />
    </article>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    operator_confirmed: { label: "Confirmed", cls: "bg-teal/10 text-teal" },
    brochure_verified: { label: "Brochure-verified", cls: "bg-teal/10 text-teal" },
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

