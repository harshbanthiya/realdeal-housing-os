import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Reveal } from "@/components/reveal";
import { ListingGrid } from "@/components/listing-grid";
import { Media, Frame } from "@/components/media";
import { ButtonLink } from "@/components/ui/kit";
import { projects, listings } from "@/lib/site";

export function generateStaticParams() {
  return projects.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const p = projects.find((x) => x.slug === slug);
  if (!p) return { title: "Project" };
  return { title: `${p.name} - ${p.location}`, description: p.blurb.slice(0, 160) };
}

export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = projects.find((x) => x.slug === slug);
  if (!p) notFound();

  const related = listings.filter((l) => l.project === p.name);

  return (
    <article>
      <section className="mx-auto max-w-6xl px-6 pt-16 md:pt-24">
        <Reveal>
          <Link href="/projects" className="text-sm font-medium text-ink/50 hover:text-teal">
            ← All projects
          </Link>
          <p className="mt-6 font-mono text-xs uppercase tracking-[0.2em] text-warm">
            {p.location}
          </p>
          <h1 className="display mt-3 text-balance text-[clamp(2.2rem,5vw,4rem)] font-extrabold leading-[1.05] text-teal">
            {p.name}
          </h1>
          <p className="mt-3 font-mono text-sm text-ink/55">{p.meta}</p>
          <Frame ratio="aspect-[21/9]" className="mt-10 shadow-[0_30px_80px_-50px_rgba(31,61,77,0.5)]">
            <Media
              seed={`rdh-${p.slug}-hero`}
              w={1400}
              h={600}
              alt={`${p.name} in ${p.location}`}
              priority
            />
          </Frame>
        </Reveal>
      </section>

      {/* About the property */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-12 md:grid-cols-[1.4fr_1fr]">
          <Reveal>
            <h2 className="text-2xl font-bold tracking-tight text-teal">About the property</h2>
            <p className="mt-5 text-lg leading-relaxed text-ink/70">{p.blurb}</p>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="rounded-2xl border border-mist-deep bg-mist/40 p-7">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-ink/50">Building info</h3>
              <ul className="mt-4 space-y-3 text-sm text-ink/70">
                {p.highlights.map((h) => (
                  <li key={h} className="flex gap-2">
                    <span className="text-warm">·</span> {h}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Related listings */}
      {related.length > 0 && (
        <section className="border-t border-mist-deep bg-mist/40">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <Reveal>
              <h2 className="text-2xl font-bold tracking-tight text-teal">
                Available in {p.name}
              </h2>
            </Reveal>
            <ListingGrid items={related} />
          </div>
        </section>
      )}

      {/* Interested */}
      <section className="mx-auto max-w-3xl px-6 py-24 text-center">
        <Reveal>
          <h2 className="text-3xl font-bold tracking-tight text-teal">
            Interested in {p.name}?
          </h2>
          <p className="mx-auto mt-4 max-w-md text-ink/65">
            Our team will line up the best layouts and floors and handle the rest.
          </p>
          <div className="mt-8 flex justify-center">
            <ButtonLink href="/contact">Enquire about this property →</ButtonLink>
          </div>
        </Reveal>
      </section>
    </article>
  );
}
