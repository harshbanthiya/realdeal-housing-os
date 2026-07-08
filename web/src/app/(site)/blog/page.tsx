import Link from "next/link";
import { getBlogPosts } from "@/lib/cms";

export const revalidate = 300;

// Planned pieces shown as honest drafts until published in the Wix CMS.
const draftPosts = [
  { title: "DLF Westpark Andheri West: A Preview Guide", slug: "dlf-westpark-andheri-west-guide", excerpt: "An honest, verification-first preview of DLF Westpark in Andheri West." },
  { title: "DLF's Debut in Mumbai", slug: "dlf-debut-in-mumbai", excerpt: "Context on DLF entering the Mumbai residential market." },
  { title: "Andheri West Luxury Real Estate: An Overview", slug: "andheri-west-luxury-real-estate", excerpt: "A neutral overview of the Andheri West premium residential market." },
  { title: "D.N. Nagar & Link Road Connectivity", slug: "dn-nagar-link-road-connectivity", excerpt: "How the D.N. Nagar / Link Road micro-market connects across Mumbai." },
  { title: "Questions to Ask Before Buying Luxury Property in Mumbai", slug: "questions-before-buying-luxury-property-mumbai", excerpt: "A practical, buyer-first checklist for evaluating premium Mumbai residences." },
];

export const metadata = {
  title: "Blog",
  description: "Verification-first notes on Mumbai's premium residential market.",
  alternates: { canonical: "/blog" },
};

export default async function Page() {
  const published = await getBlogPosts();
  return (
    <section className="mx-auto max-w-3xl px-6 py-24">
      <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">
        Journal
      </p>
      <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
        Blog
      </h1>
      <div className="mt-10 divide-y divide-mist-deep border-y border-mist-deep">
        {published.map((p) => (
          <article key={p.slug} className="py-7">
            <h2 className="text-xl font-bold text-teal">
              <Link href={`/blog/${p.slug}`} className="hover:underline">
                {p.title}
              </Link>
            </h2>
            <p className="mt-2 text-ink/60">{p.excerpt}</p>
            {p.publishedAt && (
              <span className="mt-3 inline-block font-mono text-xs text-ink/40">
                {new Date(p.publishedAt).toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric" })}
              </span>
            )}
          </article>
        ))}
        {published.length === 0 &&
          draftPosts.map((p) => (
            <article key={p.slug} className="py-7">
              <h2 className="text-xl font-bold text-teal">{p.title}</h2>
              <p className="mt-2 text-ink/60">{p.excerpt}</p>
              <span className="mt-3 inline-block font-mono text-xs text-ink/40">
                draft · staging
              </span>
            </article>
          ))}
      </div>
    </section>
  );
}
