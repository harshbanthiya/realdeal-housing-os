import { Reveal } from "@/components/reveal";
import { Media, Frame } from "@/components/media";
import { Facets } from "@/components/facets";
import { ButtonLink, SectionHead } from "@/components/ui/kit";
import { ProjectCard, ListingCard } from "@/components/cards";
import { company, projects, listings, pillars, testimonial } from "@/lib/site";

const featuredSale = listings.filter((l) => l.type === "sale").slice(0, 4);

export default function Home() {
  return (
    <div>
      {/* Hero - asymmetric split */}
      <section className="mx-auto max-w-6xl px-6 pb-16 pt-16 md:pb-24 md:pt-24">
        <div className="grid items-center gap-10 md:grid-cols-[1.05fr_0.95fr] lg:gap-16">
          <Reveal>
            <p className="mb-6 font-mono text-xs uppercase tracking-[0.2em] text-warm">
              {company.years} years · Mumbai Western Suburbs
            </p>
            <h1 className="display text-balance text-[clamp(2.3rem,4.6vw,3.9rem)] font-extrabold leading-[1.05] text-teal">
              {company.tagline}
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink/65">
              2, 3 and 4 BHK homes for sale and rent across Mumbai&rsquo;s most
              sought-after Western Suburb towers.
            </p>
            <div className="mt-9 flex flex-wrap gap-3.5">
              <ButtonLink href="/buy">View listings →</ButtonLink>
              <ButtonLink href="/dlf-westpark-andheri-west" variant="secondary">
                New launch: DLF Westpark
              </ButtonLink>
            </div>
          </Reveal>

          <Reveal delay={0.12}>
            <div className="relative">
              <Facets className="facet-float absolute -right-4 -top-6 z-10 h-16 w-28 drop-shadow-sm md:-right-6 md:h-20 md:w-36" />
              <Frame ratio="aspect-[4/5]" className="shadow-[0_30px_80px_-40px_rgba(31,61,77,0.55)]">
                <Media
                  seed="rdh-mumbai-skyline-residence-tower"
                  w={720}
                  h={900}
                  alt="A premium residential tower in Mumbai's Western Suburbs"
                  priority
                />
              </Frame>
            </div>
          </Reveal>
        </div>
      </section>

      {/* New launch banner */}
      <section className="bg-teal text-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-7 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-warm px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider">
              New
            </span>
            <span className="text-lg font-semibold">
              DLF Westpark, Andheri West - now previewing
            </span>
          </div>
          <a
            href="/dlf-westpark-andheri-west"
            className="text-sm font-semibold text-white/90 underline-offset-4 hover:underline"
          >
            Explore the launch →
          </a>
        </div>
      </section>

      {/* Featured projects - bento: one large + smaller */}
      <section className="mx-auto max-w-6xl px-6 py-20 md:py-28">
        <SectionHead title="Featured projects" action={{ href: "/projects", label: "All projects →" }} />
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {projects.map((p, i) => (
            <ProjectCard key={p.slug} project={p} delay={(i % 2) * 0.08} />
          ))}
        </div>
      </section>

      {/* Why work with us - editorial, no cards */}
      <section className="border-y border-mist-deep bg-mist/40">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
          <div className="grid gap-12 md:grid-cols-[0.8fr_1.2fr] lg:gap-20">
            <Reveal>
              <h2 className="display text-3xl font-bold leading-[1.1] text-teal md:text-[2.5rem]">
                Why people work with us
              </h2>
              <p className="mt-5 max-w-sm text-ink/60">
                Every building on offer, the room to negotiate, and the paperwork
                handled. Three things we get right.
              </p>
            </Reveal>
            <div className="divide-y divide-mist-deep">
              {pillars.map((p, i) => (
                <div key={p.title} className="py-8 first:pt-0 last:pb-0">
                  <Reveal delay={i * 0.07}>
                    <div className="grid gap-4 sm:grid-cols-[auto_1fr]">
                      <div className="font-mono text-sm text-warm sm:pt-1">
                        0{i + 1}
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-teal">{p.title}</h3>
                        <ul className="mt-3 grid gap-1.5 text-sm text-ink/65">
                          {p.points.map((pt) => (
                            <li key={pt}>{pt}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </Reveal>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Featured properties - uniform image grid */}
      <section className="mx-auto max-w-6xl px-6 py-20 md:py-28">
        <SectionHead title="Featured properties" action={{ href: "/buy", label: "View all →" }} />
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {featuredSale.map((l, i) => (
            <ListingCard key={l.title} listing={l} delay={(i % 4) * 0.05} />
          ))}
        </div>
      </section>

      {/* Testimonial - trimmed pull-quote */}
      <section className="bg-teal text-white">
        <div className="mx-auto max-w-4xl px-6 py-24 text-center">
          <Reveal>
            <Facets className="mx-auto mb-8 h-10 w-20 opacity-90" />
            <blockquote className="mx-auto max-w-3xl text-2xl font-medium leading-snug tracking-tight text-balance md:text-[30px]">
              &ldquo;{testimonial.quote}&rdquo;
            </blockquote>
            <div className="mt-8 text-sm text-white/70">
              <span className="font-semibold text-white">{testimonial.author}</span>
              {" · "}
              {testimonial.role}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="mx-auto max-w-6xl px-6 py-24 text-center">
        <Reveal>
          <h2 className="display mx-auto max-w-2xl text-balance text-3xl font-bold text-teal md:text-[2.5rem] md:leading-[1.1]">
            Let&rsquo;s find the one that fits.
          </h2>
          <p className="mx-auto mt-5 max-w-md text-ink/60">
            Tell us what you are looking for and our team lines up the right
            layouts and floors.
          </p>
          <div className="mt-9 flex justify-center">
            <ButtonLink href="/contact">Talk to our team →</ButtonLink>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
