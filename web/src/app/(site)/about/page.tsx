import { Reveal } from "@/components/reveal";
import { company, testimonial } from "@/lib/site";

export const metadata = {
  alternates: { canonical: "/about" },
  title: "About",
  description:
    "15 years in Mumbai's real estate market — specialists in Imperial Heights, Ekta Tripolis & Kalpataru Radiance across the Western Suburbs.",
};

export default function Page() {
  return (
    <div>
      <section className="mx-auto max-w-4xl px-6 py-24">
        <Reveal>
          <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">About us</p>
          <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
            {company.legalName}
          </h1>
          <p className="mt-7 text-xl leading-relaxed text-ink/70">{company.about}</p>
          <div className="mt-10 grid grid-cols-3 gap-6 border-t border-mist-deep pt-8">
            <Stat n={`${company.years}+`} label="Years in Mumbai" />
            <Stat n="4" label="Premium projects" />
            <Stat n="3" label="Suburbs covered" />
          </div>
        </Reveal>
      </section>

      {/* Manifesto — "We publish facts, not promises" promoted to brand level (UX plan §5) */}
      <section className="border-t border-mist-deep">
        <div className="mx-auto max-w-4xl px-6 py-24">
          <Reveal>
            <p className="inline-flex items-center gap-2 border border-mist-deep px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-ink/60">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-warm" />
              How we publish
            </p>
            <h2 className="mt-8 text-[clamp(2rem,4vw,3rem)] font-extrabold uppercase leading-[1.08] tracking-tight text-teal">
              We publish facts,
              <br />
              not promises.
            </h2>
          </Reveal>
          <div className="mt-12">
            {[
              {
                title: "Verified before published",
                body: "Every figure on this site traces to a source — RERA filings, registration records, or the developer's own documents. Anything unverified renders as a visible pending placeholder, never a guess.",
              },
              {
                title: "Few buildings, total depth",
                body: "Depth over breadth: a handful of buildings in Goregaon and Andheri West, known floor by floor — registrations, layouts, who's selling and what it last traded at.",
              },
              {
                title: "A person, not a portal",
                body: "Launch pricing moves weekly and every flat has a story. The site gets you the facts; a phone call gets you the rest.",
              },
            ].map((row, i) => (
              <Reveal key={row.title} delay={i * 0.05}>
                <div className="grid gap-3 border-t border-mist-deep py-8 md:grid-cols-[80px_1fr_1.6fr] md:gap-8 md:py-10">
                  <div className="font-mono text-sm text-warm">0{i + 1}</div>
                  <h3 className="text-xl font-bold text-teal">{row.title}</h3>
                  <p className="text-[15px] leading-relaxed text-ink/65">{row.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-mist-deep bg-teal text-white">
        <div className="mx-auto max-w-4xl px-6 py-24 text-center">
          <Reveal>
            <blockquote className="text-2xl font-medium leading-snug tracking-tight md:text-[28px]">
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

function Stat({ n, label }: { n: string; label: string }) {
  return (
    <div>
      <div className="text-3xl font-extrabold text-teal md:text-4xl">{n}</div>
      <div className="mt-1 text-sm text-ink/55">{label}</div>
    </div>
  );
}
