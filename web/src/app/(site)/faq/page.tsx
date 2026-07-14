import { Reveal } from "@/components/reveal";
import { siteFaqs } from "@/lib/site";

export const metadata = {
  alternates: { canonical: "/faq" },
  title: "FAQ",
  description:
    "Common questions about buying and renting premium apartments in Mumbai's Western Suburbs with Real Deal Housing.",
};

export default function Page() {
  return (
    <section className="mx-auto max-w-3xl px-6 py-24">
      <Reveal>
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">FAQ</p>
        <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
          Frequently asked questions
        </h1>
      </Reveal>
      <div className="mt-10 divide-y divide-mist-deep border-y border-mist-deep">
        {siteFaqs.map((f) => (
          <details key={f.q} className="group py-5">
            <summary className="flex cursor-pointer items-center justify-between gap-4 text-lg font-semibold text-teal marker:content-['']">
              {f.q}
              <span className="font-mono text-ink/40 transition-transform group-open:rotate-45">+</span>
            </summary>
            <p className="mt-3 text-ink/65">{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
