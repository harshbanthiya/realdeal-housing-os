import Link from "next/link";
import Image from "next/image";
import { Reveal } from "@/components/reveal";
import { RevealImage } from "@/components/reveal-image";
import { MapHero } from "@/components/map-hero";
import { CountUp } from "@/components/count-up";
import { AmbientVideo } from "@/components/ambient-video";
import { company, projects, projectImages, listings, pillars, testimonial } from "@/lib/site";

const featuredSale = listings.filter((l) => l.type === "sale" && l.featured).slice(0, 4);
const imageForListing = (l: (typeof listings)[number]) =>
  l.image ?? projects.find((p) => p.name === l.project)?.image;

/** The focus four: three Goregaon West towers + the DLF Westpark launch. */
const chapters = [
  ...projects
    .filter((p) => p.slug !== "bharat-auravistas")
    .map((p) => ({
      href: `/projects/${p.slug}`,
      name: p.name,
      meta: `${p.location} · ${p.meta}`,
      image:
        p.slug === "ekta-tripolis"
          ? { src: "/ekta-towers-night.jpg", alt: "The three Ekta Tripolis towers lit at night over the Goregaon West skyline" }
          : p.image,
    })),
  {
    href: "/dlf-westpark-andheri-west",
    name: "DLF Westpark",
    meta: "Andheri West · 4 towers · 3–5 BHK · now previewing",
    image: projectImages["dlf-westpark-andheri-west"],
  },
];

export const metadata = {
  alternates: { canonical: "/" },
};

/** Mono eyebrow chip — editorial section marker (design system: mono = data/labels). */
function Eyebrow({ n, label }: { n?: string; label: string }) {
  return (
    <p className="inline-flex items-center gap-2 border border-mist-deep px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-ink/60">
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-warm" />
      {n ? `${n} — ${label}` : label}
    </p>
  );
}

export default function Home() {
  return (
    <div>
      {/* ——— 1 · HERO — interactive map of the focus four ——— */}
      <MapHero />

      {/* ——— 2 · PROOF ——— */}
      <section className="mx-auto max-w-6xl px-6 py-16 md:py-24">
        <Reveal>
          <Eyebrow n="01" label="Track record" />
        </Reveal>
        <div className="mt-8 grid grid-cols-2 gap-x-8 md:grid-cols-4">
          {[
            { n: `${company.years}+`, label: "Years in Mumbai" },
            { n: `${chapters.length}`, label: "Focus buildings" },
            { n: "2", label: "Micro-markets — Goregaon & Andheri West" },
            { n: `${listings.length}`, label: "Homes on our books" },
          ].map((s, i) => (
            <Reveal key={s.label} delay={i * 0.05}>
              <div className="border-t border-mist-deep py-6 md:py-8">
                <CountUp value={s.n} className="block text-5xl font-extrabold tracking-tight text-teal md:text-6xl" />
                <div className="mt-2 font-mono text-[11px] uppercase tracking-[0.15em] text-ink/55">{s.label}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ——— 2b · FULL-BLEED — ambient loop, the view from an Ekta flat (Wix CDN) ——— */}
      <AmbientVideo
        src="https://video.wixstatic.com/video/77ab1a_de8956e8c8674debad018e978b834df1/file"
        poster="https://static.wixstatic.com/media/77ab1a_d965c181dcb1416f823e2738604950c1~mv2.jpg"
        caption="The view from Ekta Tripolis · Goregaon West"
        className="h-[52vh] md:h-[70vh]"
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "VideoObject",
            name: "The view from Ekta Tripolis, Goregaon West",
            description:
              "Looping aerial view over Goregaon West from an apartment in Ekta Tripolis: the metro flyover and surrounding towers of Mumbai's Western Suburbs.",
            contentUrl: "https://video.wixstatic.com/video/77ab1a_de8956e8c8674debad018e978b834df1/file",
            thumbnailUrl: "https://static.wixstatic.com/media/77ab1a_d965c181dcb1416f823e2738604950c1~mv2.jpg",
            uploadDate: "2026-07-14",
            duration: "PT5S",
          }),
        }}
      />

      {/* ——— 3 · THE BUILDINGS — full-bleed chapters ——— */}
      <section>
        <div className="mx-auto max-w-6xl px-6">
          <Reveal>
            <Eyebrow n="02" label="The buildings" />
            <h2 className="mt-6 max-w-3xl text-3xl font-bold tracking-tight text-teal md:text-5xl">
              Four buildings, known floor by floor.
            </h2>
            <p className="mt-4 max-w-2xl text-lg leading-relaxed text-ink/65">
              Apartments for sale and rent in Goregaon West and Andheri West —
              tracked registration by registration, floor by floor.
            </p>
          </Reveal>
        </div>
        <div className="mt-12">
          {chapters.map((c) => (
            <Link key={c.href} href={c.href} className="group relative block">
              {c.image ? (
                <RevealImage
                  src={c.image.src}
                  alt={c.image.alt}
                  zoom
                  sizes="100vw"
                  className="h-[48vh] w-full md:h-[64vh]"
                />
              ) : (
                <div className="flex h-[40vh] w-full items-center justify-center border-y border-dashed border-mist-deep bg-mist/50 font-mono text-xs text-ink/40">
                  PHOTOGRAPHY_PENDING
                </div>
              )}
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink/45 via-transparent to-transparent" />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 px-6 pb-6 md:px-10 md:pb-9">
                <div className="mb-4 h-px w-full bg-white/30" />
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <h3 className="text-3xl font-extrabold uppercase tracking-tight text-white md:text-5xl">
                      {c.name}
                    </h3>
                    <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.18em] text-white/80">
                      {c.meta}
                    </p>
                  </div>
                  <span className="hidden text-sm font-semibold text-white underline-offset-4 group-hover:underline md:inline">
                    View building →
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ——— 4 · AVAILABLE NOW ——— */}
      <section className="mx-auto max-w-6xl px-6 py-16 md:py-24">
        <Reveal>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <Eyebrow n="03" label="Available now" />
              <h2 className="mt-6 text-3xl font-bold tracking-tight text-teal md:text-4xl">
                Flats for sale in Goregaon West &amp; Andheri West
              </h2>
            </div>
            <Link href="/buy" className="text-sm font-semibold text-teal hover:underline">
              All listings →
            </Link>
          </div>
        </Reveal>
        <div className="mt-10 grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {featuredSale.map((l, i) => (
            <Reveal key={l.slug} delay={i * 0.05} className="h-full">
              <Link href={`/listings/${l.slug}`} className="group flex h-full flex-col border-t border-mist-deep pt-5">
                {imageForListing(l) ? (
                  <div className="rdh-zoom relative aspect-[4/3] overflow-hidden">
                    <Image
                      src={imageForListing(l)!.src}
                      alt={imageForListing(l)!.alt}
                      fill
                      sizes="(max-width: 640px) 100vw, 25vw"
                      className="object-cover"
                    />
                  </div>
                ) : (
                  <div className="aspect-[4/3] border border-dashed border-mist-deep bg-mist/50" />
                )}
                <p className="mt-4 text-xl font-extrabold tracking-tight text-teal">{l.price}</p>
                <h3 className="mt-1.5 text-[15px] font-semibold leading-snug text-teal group-hover:underline">{l.title}</h3>
                <p className="mt-2 font-mono text-[11px] uppercase tracking-wide text-ink/50">{l.location} · {l.config} · {l.sqft} sqft</p>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ——— 5 · NEW LAUNCH chapter ——— */}
      <section className="bg-teal text-white">
        <div className="mx-auto max-w-6xl px-6 py-16 md:py-24">
          <Reveal>
            <p className="inline-flex items-center gap-2 border border-white/25 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-white/75">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-warm" />
              04 — New launch
            </p>
            <div className="mt-8 flex flex-wrap items-end justify-between gap-8">
              <div>
                <h2 className="text-4xl font-extrabold uppercase tracking-tight md:text-6xl">
                  DLF Westpark
                </h2>
                <p className="mt-4 max-w-xl text-lg leading-relaxed text-white/70">
                  Andheri West, now previewing. Every fact verified before we publish it —
                  pricing and RERA shown as pending until confirmed.
                </p>
              </div>
              <Link
                href="/dlf-westpark-andheri-west"
                className="rounded-full bg-white px-7 py-3.5 text-sm font-semibold text-teal transition-opacity hover:opacity-90"
              >
                Explore the launch →
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ——— 6 · METHOD — editorial rows, no boxes ——— */}
      <section className="mx-auto max-w-6xl px-6 py-16 md:py-24">
        <Reveal>
          <Eyebrow n="05" label="How we work" />
          <h2 className="mt-6 text-3xl font-bold tracking-tight text-teal md:text-4xl">Why work with us?</h2>
        </Reveal>
        <div className="mt-10">
          {pillars.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.05}>
              <div className="grid gap-4 border-t border-mist-deep py-8 md:grid-cols-[80px_1fr_1.4fr] md:gap-8 md:py-10">
                <div className="font-mono text-sm text-warm">0{i + 1}</div>
                <h3 className="text-xl font-bold text-teal md:text-2xl">{p.title}</h3>
                <ul className="space-y-2 text-[15px] leading-relaxed text-ink/65">
                  {p.points.map((pt) => (
                    <li key={pt} className="flex gap-2">
                      <span className="text-warm">·</span> {pt}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ——— 7 · Testimonial — Marine Drive night skyline backdrop (Pixabay, free license) ——— */}
      <section className="relative overflow-hidden border-t border-mist-deep bg-teal text-white">
        <Image
          src="/mumbai-skyline-night.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover opacity-40"
        />
        <div className="absolute inset-0 bg-teal/60" />
        <div className="relative mx-auto max-w-4xl px-6 py-24 text-center">
          <Reveal>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-white/45">What our clients say</p>
            <blockquote className="mx-auto mt-6 max-w-3xl text-2xl font-medium leading-snug tracking-tight md:text-[28px]">
              &ldquo;{testimonial.quote}&rdquo;
            </blockquote>
            <div className="mt-7 text-sm text-white/70">
              <span className="font-semibold text-white">{testimonial.author}</span> · {testimonial.role}
            </div>
          </Reveal>
        </div>
      </section>
    </div>
  );
}
