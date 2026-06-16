import { Reveal } from "@/components/reveal";
import { company, testimonial } from "@/lib/site";

export const metadata = {
  title: "About",
  description:
    "15 years in Mumbai's real estate market - specialists in Imperial Heights, Ekta Tripolis & Kalpataru Radiance across the Western Suburbs.",
};

export default function Page() {
  return (
    <div>
      <section className="mx-auto max-w-4xl px-6 py-24">
        <Reveal>
          <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">About us</p>
          <h1 className="display text-balance text-[clamp(2.1rem,4.8vw,3.6rem)] font-extrabold leading-[1.05] text-teal">
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
