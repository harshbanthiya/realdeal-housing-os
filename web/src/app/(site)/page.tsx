import Link from "next/link";
import Image from "next/image";
import { Reveal } from "@/components/reveal";
import { RevealImage } from "@/components/reveal-image";
import { company, projects, projectImages, listings, pillars, testimonial } from "@/lib/site";

const featuredSale = listings.filter((l) => l.type === "sale" && l.featured).slice(0, 4);
const imageForListing = (l: (typeof listings)[number]) =>
  l.image ?? projects.find((p) => p.name === l.project)?.image;

export default function Home() {
  return (
    <div>
      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pb-20 pt-20 md:pt-28">
        <Reveal>
          <p className="mb-6 flex items-center gap-2 text-sm font-medium text-ink/50">
            <span className="inline-block h-2 w-2 rounded-full bg-warm" />
            {company.years} years · Mumbai Western Suburbs
          </p>
          <h1 className="max-w-4xl text-[clamp(2.6rem,6.5vw,5.5rem)] font-extrabold leading-[1.02] tracking-tight text-teal">
            {company.tagline}
          </h1>
          <p className="mt-7 max-w-xl text-lg leading-relaxed text-ink/65">
            2, 3 &amp; 4 BHK apartments for sale and rent in Mumbai&rsquo;s most
            sought-after towers — Imperial Heights, Kalpataru Radiance, Ekta
            Tripolis and more across Goregaon, Andheri &amp; Malad.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link href="/buy" className="rounded-full bg-teal px-6 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90">
              View listings →
            </Link>
            <Link href="/dlf-westpark-andheri-west" className="rounded-full border border-mist-deep px-6 py-3.5 text-sm font-semibold text-teal transition-colors hover:bg-mist">
              New launch · DLF Westpark
            </Link>
          </div>
        </Reveal>
        <RevealImage
          src={projectImages["ekta-tripolis"].src}
          alt={projectImages["ekta-tripolis"].alt}
          priority
          sizes="(max-width: 1152px) 100vw, 1152px"
          className="mt-14 aspect-[21/9] w-full rounded-2xl"
        />
      </section>

      {/* New launch banner */}
      <section className="border-y border-mist-deep bg-teal text-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-7 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-warm px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider">New</span>
            <span className="text-lg font-semibold">DLF Westpark, Andheri West — now previewing</span>
          </div>
          <Link href="/dlf-westpark-andheri-west" className="text-sm font-semibold text-white/90 underline-offset-4 hover:underline">
            Explore the launch →
          </Link>
        </div>
      </section>

      {/* Featured projects */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <Reveal>
          <div className="flex items-end justify-between">
            <h2 className="text-3xl font-bold tracking-tight text-teal md:text-4xl">Featured projects</h2>
            <Link href="/projects" className="text-sm font-semibold text-teal hover:underline">All projects →</Link>
          </div>
        </Reveal>
        <div className="mt-10 grid gap-6 sm:grid-cols-2">
          {projects.map((p, i) => (
            <Reveal key={p.slug} delay={i * 0.06}>
              <Link href={`/projects/${p.slug}`} className="group block rounded-2xl border border-mist-deep p-7 transition-colors hover:bg-mist/40">
                {p.image ? (
                  <RevealImage src={p.image.src} alt={p.image.alt} zoom className="aspect-[16/9] rounded-xl" />
                ) : (
                  <div className="aspect-[16/9] rounded-xl border border-dashed border-mist-deep bg-mist/50" />
                )}
                <h3 className="mt-5 text-xl font-bold text-teal">{p.name}</h3>
                <p className="mt-1 text-sm text-ink/55">{p.location} · {p.meta}</p>
                <span className="mt-4 inline-block text-sm font-semibold text-teal group-hover:underline">View project →</span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Featured properties */}
      <section className="border-t border-mist-deep bg-mist/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <Reveal>
            <div className="flex items-end justify-between">
              <h2 className="text-3xl font-bold tracking-tight text-teal md:text-4xl">Featured properties</h2>
              <Link href="/buy" className="text-sm font-semibold text-teal hover:underline">View all →</Link>
            </div>
          </Reveal>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {featuredSale.map((l, i) => (
              <Reveal key={l.slug} delay={i * 0.05}>
                <Link
                  href={`/listings/${l.slug}`}
                  className="group flex h-full flex-col rounded-2xl border border-mist-deep bg-white p-5 transition-colors hover:bg-mist/30"
                >
                  {imageForListing(l) ? (
                    <div className="rdh-zoom relative aspect-[4/3] overflow-hidden rounded-lg">
                      <Image
                        src={imageForListing(l)!.src}
                        alt={imageForListing(l)!.alt}
                        fill
                        sizes="(max-width: 640px) 100vw, 25vw"
                        className="object-cover"
                      />
                    </div>
                  ) : (
                    <div className="aspect-[4/3] rounded-lg border border-dashed border-mist-deep bg-mist/50" />
                  )}
                  <h3 className="mt-4 text-base font-semibold leading-snug text-teal group-hover:underline">{l.title}</h3>
                  <p className="mt-1 text-xs text-ink/50">{l.location} · {l.config} · {l.sqft} sqft</p>
                  <p className="mt-3 text-lg font-bold text-teal">{l.price}</p>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Why work with us */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <Reveal>
          <h2 className="text-3xl font-bold tracking-tight text-teal md:text-4xl">Why work with us?</h2>
        </Reveal>
        <div className="mt-10 grid gap-8 md:grid-cols-3">
          {pillars.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.07}>
              <div className="rounded-2xl border border-mist-deep p-7">
                <div className="font-mono text-sm text-warm">0{i + 1}</div>
                <h3 className="mt-3 text-xl font-bold text-teal">{p.title}</h3>
                <ul className="mt-4 space-y-2 text-sm text-ink/65">
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

      {/* Testimonial */}
      <section className="border-t border-mist-deep bg-teal text-white">
        <div className="mx-auto max-w-4xl px-6 py-24 text-center">
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
