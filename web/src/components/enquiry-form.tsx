"use client";

import { useState } from "react";

/**
 * Live enquiry form → POST /api/enquiry (Wix EnquiriesPreview + email to the
 * operator). `variant="sell"` adds property fields, serialized into the
 * message so the API and inbox stay one shape.
 */
export function EnquiryForm({
  source,
  variant = "contact",
}: {
  source: string;
  variant?: "contact" | "sell";
}) {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const get = (k: string) => String(fd.get(k) ?? "").trim();

    let message = get("message");
    if (variant === "sell") {
      const props = [
        ["Neighbourhood", get("neighbourhood")],
        ["Address", get("address")],
        ["Floor", get("floor")],
        ["Bedrooms", get("bedrooms")],
      ]
        .filter(([, v]) => v)
        .map(([k, v]) => `${k}: ${v}`)
        .join("\n");
      message = [props, message].filter(Boolean).join("\n\n");
    }

    setState("sending");
    try {
      const res = await fetch("/api/enquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: get("name"),
          email: get("email"),
          phone: get("phone"),
          message,
          source,
          company: get("company"), // honeypot
        }),
      });
      setState(res.ok ? "sent" : "error");
    } catch {
      setState("error");
    }
  }

  if (state === "sent") {
    return (
      <div className="rounded-2xl border border-mist-deep bg-white p-10 text-center">
        <p className="text-2xl font-bold text-teal">Thank you — message received.</p>
        <p className="mt-3 text-sm text-ink/60">
          A real person reads every enquiry. We usually reply within a few hours.
        </p>
      </div>
    );
  }

  const inputCls =
    "w-full rounded-lg border border-mist-deep bg-white px-3.5 py-2.5 text-sm text-ink placeholder:text-ink/35 focus:border-teal focus:outline-none";
  const labelCls = "mb-1.5 block text-xs font-semibold uppercase tracking-wider text-ink/50";

  return (
    <form onSubmit={onSubmit} className="rounded-2xl border border-mist-deep bg-white p-7">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label htmlFor={`${source}-name`} className={labelCls}>Name</label>
          <input id={`${source}-name`} name="name" required placeholder="Your name" className={inputCls} />
        </div>
        <div>
          <label htmlFor={`${source}-email`} className={labelCls}>Email</label>
          <input id={`${source}-email`} name="email" type="email" placeholder="you@example.com" className={inputCls} />
        </div>
        <div>
          <label htmlFor={`${source}-phone`} className={labelCls}>Phone</label>
          <input id={`${source}-phone`} name="phone" type="tel" placeholder="+91" className={inputCls} />
        </div>
        {variant === "sell" && (
          <>
            <div>
              <label htmlFor={`${source}-neighbourhood`} className={labelCls}>Neighbourhood</label>
              <input id={`${source}-neighbourhood`} name="neighbourhood" placeholder="e.g. Goregaon West" className={inputCls} />
            </div>
            <div>
              <label htmlFor={`${source}-address`} className={labelCls}>Building / address</label>
              <input id={`${source}-address`} name="address" placeholder="Building name" className={inputCls} />
            </div>
            <div>
              <label htmlFor={`${source}-floor`} className={labelCls}>Floor</label>
              <input id={`${source}-floor`} name="floor" placeholder="e.g. 14" className={inputCls} />
            </div>
            <div>
              <label htmlFor={`${source}-bedrooms`} className={labelCls}>Bedrooms</label>
              <input id={`${source}-bedrooms`} name="bedrooms" placeholder="e.g. 3 BHK" className={inputCls} />
            </div>
          </>
        )}
        <div className="sm:col-span-2">
          <label htmlFor={`${source}-message`} className={labelCls}>Message</label>
          <textarea
            id={`${source}-message`}
            name="message"
            rows={3}
            placeholder={variant === "sell" ? "Anything else we should know" : "Type your message here"}
            className={`${inputCls} resize-none`}
          />
        </div>
        {/* honeypot — hidden from real users */}
        <input name="company" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
      </div>
      <button
        type="submit"
        disabled={state === "sending"}
        className="mt-5 rounded-full bg-teal px-6 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {state === "sending" ? "Sending…" : "Send message"}
      </button>
      <p className="mt-3 text-xs text-ink/45">
        {state === "error"
          ? "Something went wrong — please WhatsApp us on +91 82912 93889 instead."
          : "Goes straight to our team — a real person replies."}
      </p>
    </form>
  );
}
