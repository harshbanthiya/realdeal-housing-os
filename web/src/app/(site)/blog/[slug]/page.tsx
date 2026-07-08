import type { Metadata } from "next";
import Image from "next/image";
import { notFound } from "next/navigation";
import { getBlogPosts } from "@/lib/cms";

export const revalidate = 300;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = (await getBlogPosts()).find((p) => p.slug === slug);
  if (!post) return { title: "Post" };
  return {
    title: post.seoTitle,
    description: post.seoDescription,
    alternates: { canonical: `/blog/${slug}` },
    openGraph: {
      title: post.seoTitle,
      description: post.seoDescription,
      type: "article",
      publishedTime: post.publishedAt || undefined,
      images: post.heroImageUrl ? [post.heroImageUrl] : undefined,
    },
  };
}

export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = (await getBlogPosts()).find((p) => p.slug === slug);
  if (!post) notFound();

  return (
    <article className="mx-auto max-w-3xl px-6 py-24">
      <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">
        Journal
      </p>
      <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
        {post.title}
      </h1>
      {post.publishedAt && (
        <time
          dateTime={post.publishedAt}
          className="mt-4 block font-mono text-xs text-ink/40"
        >
          {new Date(post.publishedAt).toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric" })}
        </time>
      )}
      {post.heroImageUrl && (
        <Image
          src={post.heroImageUrl}
          alt={post.title}
          width={1200}
          height={675}
          className="mt-10 rounded-2xl border border-mist-deep"
          priority
        />
      )}
      {/* Body is trusted editor content from our own Wix CMS. */}
      <div
        className="prose-rdh mt-10 space-y-5 leading-relaxed text-ink/80"
        dangerouslySetInnerHTML={{ __html: post.body }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            headline: post.title,
            description: post.seoDescription,
            datePublished: post.publishedAt || undefined,
            image: post.heroImageUrl || undefined,
            author: { "@type": "Organization", name: "Real Deal Housing" },
          }),
        }}
      />
    </article>
  );
}
