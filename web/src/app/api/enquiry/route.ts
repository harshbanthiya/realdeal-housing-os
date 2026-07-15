import { NextRequest, NextResponse } from "next/server";

/**
 * Public enquiry endpoint — the site's lead capture.
 *
 * Every submission is (1) inserted into the Wix `EnquiriesPreview` collection
 * (the CRM-visible lead inbox on the premium site; insert-only for visitors,
 * reads stay privileged) and (2) emailed to the operator via Resend with
 * reply-to set to the enquirer. Either sink alone counts as success so a
 * single outage never drops a lead; both failing returns 500 so the form can
 * tell the visitor to WhatsApp instead.
 */

const LEAD_EMAIL = "PadminiJain1@gmail.com";

interface EnquiryBody {
  name?: string;
  email?: string;
  phone?: string;
  message?: string;
  source?: string;
  company?: string; // honeypot — real users never fill this
}

async function insertWixLead(b: EnquiryBody): Promise<boolean> {
  try {
    const [{ createClient, OAuthStrategy }, { items }] = await Promise.all([
      import("@wix/sdk"),
      import("@wix/data"),
    ]);
    const client = createClient({
      modules: { items },
      auth: OAuthStrategy({ clientId: process.env.WIX_CLIENT_ID! }),
    });
    await client.items.insert("EnquiriesPreview", {
      name: b.name,
      email: b.email ?? "",
      phone: b.phone ?? "",
      message: b.message ?? "",
      source: b.source ?? "website",
      submittedAt: new Date().toISOString(),
    });
    return true;
  } catch {
    return false;
  }
}

async function emailLead(b: EnquiryBody): Promise<boolean> {
  const key = process.env.RESEND_API_KEY;
  if (!key) return false;
  const from = process.env.EMAIL_FROM ?? "Real Deal Housing <padmini@realdealhousing.com>";
  const esc = (s: string) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from,
        to: [LEAD_EMAIL],
        reply_to: b.email || undefined,
        subject: `New enquiry — ${b.name}${b.source ? ` (${b.source})` : ""}`,
        html: `<div style="font-family:system-ui,sans-serif;max-width:520px">
<h2 style="color:#1F3D4D">New website enquiry</h2>
<table style="font-size:14px;line-height:1.8">
<tr><td style="color:#888;padding-right:16px">Name</td><td><b>${esc(b.name ?? "")}</b></td></tr>
<tr><td style="color:#888;padding-right:16px">Email</td><td>${esc(b.email ?? "—")}</td></tr>
<tr><td style="color:#888;padding-right:16px">Phone</td><td>${esc(b.phone ?? "—")}</td></tr>
<tr><td style="color:#888;padding-right:16px">Page</td><td>${esc(b.source ?? "website")}</td></tr>
</table>
<p style="font-size:14px;white-space:pre-wrap;border-left:3px solid #C97B4A;padding-left:12px">${esc(b.message ?? "")}</p>
<p style="font-size:12px;color:#999">Reply to this email to answer ${esc(b.name ?? "the enquirer")} directly.</p>
</div>`,
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function POST(req: NextRequest) {
  let body: EnquiryBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  // Honeypot: pretend success so bots learn nothing.
  if (body.company) return NextResponse.json({ ok: true });

  const name = (body.name ?? "").trim().slice(0, 200);
  const email = (body.email ?? "").trim().slice(0, 200);
  const phone = (body.phone ?? "").trim().slice(0, 40);
  const message = (body.message ?? "").trim().slice(0, 4000);
  if (!name || (!email && !phone)) {
    return NextResponse.json(
      { ok: false, error: "name and email or phone required" },
      { status: 400 }
    );
  }
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ ok: false, error: "invalid email" }, { status: 400 });
  }

  const lead = { name, email, phone, message, source: (body.source ?? "website").slice(0, 100) };
  const [stored, mailed] = await Promise.all([insertWixLead(lead), emailLead(lead)]);
  if (!stored && !mailed) {
    return NextResponse.json({ ok: false, error: "delivery_failed" }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
