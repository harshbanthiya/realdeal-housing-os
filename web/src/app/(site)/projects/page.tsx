import Link from "next/link";
import { Reveal } from "@/components/reveal";
import { Media, Frame } from "@/components/media";
import { PageIntro } from "@/components/ui/kit";
import { ProjectCard } from "@/components/cards";
import { projects } from "@/lib/site";

export const metadata = {
  title: "Projects",
  description:
    "Premium Mumbai projects - Imperial Heights, Kalpataru Radiance, Ekta Tripolis (Goregaon West) and Bharat Auravistas (Andheri West).",
};

export default function Page() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20 md:py-24">
      <PageIntro
        eyebrow="Projects"
        title="Premium projects we cover"
        lead="Handpicked towers across Mumbai's Western Suburbs, plus our newest launch preview."
      />

      {/* New launch: image-led feature */}
      <Reveal>
        <Link
          href="/dlf-westpark-andheri-west"
          className="group mt-12 grid overflow-hidden rounded-2xl bg-teal text-white ring-1 ring-teal md:grid-cols-2"
        >
          <Frame ratio="aspect-[16/10] md:aspect-auto md:h-full" className="rounded-none ring-0">
            <Media
              seed="rdh-dlf-westpark-andheri-tower"
              w={760}
              h={520}
              alt="DLF Westpark, Andheri West"
              className="transition-transform duration-500 group-hover:scale-[1.03]"
            />
          </Frame>
          <div className="p-8 md:p-10">
            <span className="rounded-full bg-warm px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider">
              New launch
            </span>
            <h2 className="mt-5 text-2xl font-bold md:text-3xl">
              DLF Westpark, Andheri West
            </h2>
            <p className="mt-3 max-w-md text-white/70">
              A calmer way to evaluate a premium city residence. Preview now, with
              every fact verified before it goes live.
            </p>
            <span className="mt-5 inline-block text-sm font-semibold underline-offset-4 group-hover:underline">
              Open preview →
            </span>
          </div>
        </Link>
      </Reveal>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        {projects.map((p, i) => (
          <ProjectCard key={p.slug} project={p} delay={(i % 2) * 0.08} />
        ))}
      </div>
    </section>
  );
}
