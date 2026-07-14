"use client";

import { useState } from "react";

/**
 * Double-opt-in newsletter signup (POST /api/subscribe).
 * `dark` fits the teal footer; default fits white sections.
 */
export function NewsletterForm({
  source = "footer",
  buildingInterest = [],
  dark = false,
}: {
  source?: string;
  buildingInterest?: string[];
  dark?: boolean;
}) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<{ kind: "idle" | "busy" | "ok" | "err"; msg?: string }>({ kind: "idle" });

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (state.kind === "busy") return;
    const honeypot = (new FormData(e.currentTarget).get("website") as string) || "";
    setState({ kind: "busy" });
    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source, buildingInterest, website: honeypot }),
      });
      const data = await res.json();
      setState(data.ok ? { kind: "ok", msg: data.message } : { kind: "err", msg: data.error });
      if (data.ok) setEmail("");
    } catch {
      setState({ kind: "err", msg: "Something went wrong — please try again." });
    }
  }

  const border = dark ? "border-white/25" : "border-mist-deep";
  const text = dark ? "text-white placeholder:text-white/40" : "text-teal placeholder:text-ink/40";
  const btn = dark
    ? "bg-white text-teal hover:opacity-90"
    : "bg-teal text-white hover:opacity-90";

  if (state.kind === "ok") {
    return (
      <p className={`text-sm leading-relaxed ${dark ? "text-white/80" : "text-ink/70"}`} role="status">
        ✓ {state.msg}
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="max-w-md">
      <div className={`flex border ${border}`}>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@email.com"
          aria-label="Email address"
          className={`min-w-0 flex-1 bg-transparent px-4 py-3 text-sm outline-none ${text}`}
        />
        {/* honeypot — hidden from humans, tempting to bots */}
        <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
        <button
          type="submit"
          disabled={state.kind === "busy"}
          className={`shrink-0 px-5 py-3 text-sm font-semibold transition-opacity disabled:opacity-60 ${btn}`}
        >
          {state.kind === "busy" ? "…" : "Subscribe"}
        </button>
      </div>
      <p className={`mt-2 text-xs leading-relaxed ${dark ? "text-white/45" : "text-ink/45"}`}>
        New listings and building updates. Double opt-in, unsubscribe anytime.
      </p>
      {state.kind === "err" && (
        <p className="mt-2 text-xs text-warm" role="alert">
          {state.msg}
        </p>
      )}
    </form>
  );
}
