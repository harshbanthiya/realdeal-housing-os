import Link from "next/link";

export function ComingSoon({
  title,
  blurb,
}: {
  title: string;
  blurb: string;
}) {
  return (
    <section className="mx-auto max-w-3xl px-6 py-28 text-center">
      <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">
        Staging — section pending
      </p>
      <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
        {title}
      </h1>
      <p className="mx-auto mt-5 max-w-md text-ink/60">{blurb}</p>
      <Link
        href="/dlf-westpark-andheri-west"
        className="mt-9 inline-block rounded-full bg-teal px-6 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
      >
        View DLF Westpark preview →
      </Link>
    </section>
  );
}
