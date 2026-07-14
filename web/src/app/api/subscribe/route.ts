import { NextRequest, NextResponse } from "next/server";
import { newsletterPool, sendConfirmEmail, CONSENT_TEXT } from "@/lib/newsletter";
import { SITE_URL } from "@/lib/seo";
import { company } from "@/lib/site";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (body?.website) return NextResponse.json({ ok: true, message: "Check your inbox." }); // honeypot

  const email = String(body?.email ?? "").trim().toLowerCase();
  const source = String(body?.source ?? "footer").slice(0, 80);
  const interest = Array.isArray(body?.buildingInterest)
    ? body.buildingInterest.slice(0, 8).map((s: unknown) => String(s).slice(0, 80))
    : [];
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return NextResponse.json({ ok: false, error: "Please enter a valid email address." }, { status: 400 });
  }

  const pool = newsletterPool();
  if (!pool) {
    // ponytail: prod has no DB yet — honest fallback until launch storage is decided
    return NextResponse.json(
      { ok: false, error: `Signups aren't live on this preview yet — email ${company.email} and we'll add you.` },
      { status: 503 },
    );
  }

  const client = await pool.connect();
  try {
    const blocked = await client.query(
      "SELECT reason FROM email_suppression WHERE email = $1 AND reason IN ('bounced','complained')",
      [email],
    );
    if (blocked.rows.length) {
      return NextResponse.json(
        { ok: false, error: `We couldn't deliver to this address before — email ${company.email} and we'll sort it out.` },
        { status: 400 },
      );
    }

    const { rows } = await client.query(
      `INSERT INTO subscribers (email, source, building_interest, consent_text)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (email) DO UPDATE SET
         building_interest = ARRAY(SELECT DISTINCT unnest(subscribers.building_interest || EXCLUDED.building_interest)),
         status       = CASE WHEN subscribers.status = 'unsubscribed' THEN 'pending' ELSE subscribers.status END,
         requested_at = CASE WHEN subscribers.status = 'unsubscribed' THEN NOW() ELSE subscribers.requested_at END
       RETURNING status, confirm_token`,
      [email, source, interest, CONSENT_TEXT],
    );
    const sub = rows[0];

    if (sub.status === "confirmed") {
      return NextResponse.json({ ok: true, message: "You're already subscribed." });
    }
    const sent = await sendConfirmEmail(email, sub.confirm_token, SITE_URL).catch(() => false);
    return NextResponse.json({
      ok: true,
      message: sent
        ? "Almost there — check your inbox for a confirmation link."
        : "You're on the list. We'll confirm your address before anything is sent.",
    });
  } finally {
    client.release();
  }
}
