import { Reveal } from "@/components/reveal";
import { company } from "@/lib/site";

export const metadata = {
  title: "Contact",
  description: "Get in touch with Real Deal Housing — Goregaon West, Mumbai.",
};

export default function Page() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-24">
      <Reveal>
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">Contact</p>
        <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
          Leave us a message
        </h1>
      </Reveal>
      <div className="mt-12 grid gap-12 md:grid-cols-[1fr_1.1fr]">
        <Reveal>
          <div className="space-y-6 text-sm">
            <Detail label="Phone" value={company.phone} href={company.phoneHref} />
            <Detail label="Email" value={company.email} href={`mailto:${company.email}`} />
            <Detail label="Office" value={company.address} />
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <form aria-disabled className="rounded-2xl border border-mist-deep bg-white p-7">
            <div className="grid gap-4">
              {["First name", "Last name", "Email", "Phone"].map((f) => (
                <div key={f}>
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-ink/50">{f}</label>
                  <input disabled placeholder={f} className="w-full rounded-lg border border-mist-deep bg-mist/40 px-3.5 py-2.5 text-sm text-ink placeholder:text-ink/35" />
                </div>
              ))}
              <textarea disabled rows={3} placeholder="Type your message here" className="w-full resize-none rounded-lg border border-mist-deep bg-mist/40 px-3.5 py-2.5 text-sm text-ink placeholder:text-ink/35" />
              <button type="button" disabled className="mt-1 cursor-not-allowed rounded-full bg-mist-deep px-6 py-3.5 text-sm font-semibold text-ink/50">
                Preview only — no live submission
              </button>
            </div>
          </form>
        </Reveal>
      </div>
    </section>
  );
}

function Detail({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink/45">{label}</div>
      {href ? (
        <a href={href} className="text-lg font-medium text-teal hover:underline">{value}</a>
      ) : (
        <div className="text-lg font-medium text-teal">{value}</div>
      )}
    </div>
  );
}
