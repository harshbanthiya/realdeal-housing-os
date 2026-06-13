import Link from "next/link";
import { Reveal } from "@/components/reveal";
import { projects } from "@/lib/site";

export const metadata = {
  title: "Projects",
  description:
    "Premium Mumbai projects — Imperial Heights, Kalpataru Radiance, Ekta Tripolis (Goregaon West) and Bharat Auravistas (Andheri West).",
};

export default function Page() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <Reveal>
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">Projects</p>
        <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
          Premium projects we cover
        </h1>
        <p className="mt-5 max-w-2xl text-ink/65">
          Handpicked towers across Mumbai&rsquo;s Western Suburbs, plus our newest
          launch preview.
        </p>
      </Reveal>

      {/* New launch */}
      <Reveal>
        <Link href="/dlf-westpark-andheri-west" className="mt-10 block rounded-2xl border border-teal bg-teal p-7 text-white transition-opacity hover:opacity-95">
          <span className="rounded-full bg-warm px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider">New launch</span>
          <h2 className="mt-4 text-2xl font-bold">DLF Westpark, Andheri West</h2>
          <p className="mt-2 max-w-xl text-white/70">A calmer way to evaluate a premium city residence — preview now, with facts verified before they go live.</p>
          <span className="mt-4 inline-block text-sm font-semibold underline-offset-4 hover:underline">Open preview →</span>
        </Link>
      </Reveal>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        {projects.map((p, i) => (
          <Reveal key={p.slug} delay={i * 0.06}>
            <Link href={`/projects/${p.slug}`} className="group block rounded-2xl border border-mist-deep p-7 transition-colors hover:bg-mist/40">
              <div className="aspect-[16/9] rounded-xl border border-dashed border-mist-deep bg-mist/50" />
              <h2 className="mt-5 text-xl font-bold text-teal">{p.name}</h2>
              <p className="mt-1 text-sm text-ink/55">{p.location} · {p.meta}</p>
              <span className="mt-4 inline-block text-sm font-semibold text-teal group-hover:underline">View project →</span>
            </Link>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
