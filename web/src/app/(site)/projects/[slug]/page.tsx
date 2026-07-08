import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Reveal } from "@/components/reveal";
import { RevealImage } from "@/components/reveal-image";
import { ListingGrid } from "@/components/listing-grid";
import { projects, listings } from "@/lib/site";
import { getProject } from "@/lib/cms";

export const revalidate = 300; // re-read CMS content every 5 min once Wix is wired

export function generateStaticParams() {
  return projects.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const p = await getProject(slug);
  if (!p) return { title: "Project" };
  return {
    title: `${p.name} — ${p.location}`,
    description: p.blurb.slice(0, 160),
    alternates: { canonical: `/projects/${slug}` },
  };
}

export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = await getProject(slug);
  if (!p) notFound();

  const related = listings.filter((l) => l.project === p.name);

  return (
    <article>
      <section className="mx-auto max-w-6xl px-6 pt-16 md:pt-24">
        <Reveal>
          <Link href="/projects" className="text-sm font-medium text-ink/50 hover:text-teal">
            ← All projects
          </Link>
          <p className="mt-6 flex items-center gap-2 text-sm font-medium text-ink/55">
            <span className="inline-block h-2 w-2 rounded-full bg-warm" />
            {p.location}
          </p>
          <h1 className="mt-3 text-[clamp(2.4rem,5.5vw,4.5rem)] font-extrabold leading-[1.04] tracking-tight text-teal">
            {p.name}
          </h1>
          <p className="mt-3 font-mono text-sm text-ink/55">{p.meta}</p>
          {p.image ? (
            <RevealImage
              src={p.image.src}
              alt={p.image.alt}
              priority
              sizes="(max-width: 1152px) 100vw, 1152px"
              className="mt-10 aspect-[21/9] w-full rounded-2xl"
            />
          ) : (
            <div className="mt-10 aspect-[21/9] w-full rounded-2xl border border-dashed border-mist-deep bg-mist/50">
              <div className="flex h-full items-center justify-center font-mono text-sm text-ink/40">
                Project imagery — VISUAL_DIRECTION_PENDING
              </div>
            </div>
          )}
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
          <Link href="/contact" className="mt-8 inline-block rounded-full bg-teal px-6 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90">
            Enquire about this property →
          </Link>
        </Reveal>
      </section>
    </article>
  );
}
