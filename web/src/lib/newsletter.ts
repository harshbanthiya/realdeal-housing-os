/**
 * Newsletter plumbing (migration 063: subscribers + email_suppression).
 *
 * Server-only. Unlike lib/db.ts (read-only cockpit reads), this pool WRITES —
 * the same precedent as app/unsubscribe/route.ts: opt-in/opt-out must work at
 * request time. Scope is strictly the subscribers/email_suppression tables.
 * Without DATABASE_URL (Vercel prod today) callers degrade honestly.
 */
import { Pool } from "pg";

let pool: Pool | null = null;

export function newsletterPool(): Pool | null {
  if (!process.env.DATABASE_URL) return null;
  if (!pool) {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 2,
      idleTimeoutMillis: 10_000,
      connectionTimeoutMillis: 4_000,
      statement_timeout: 5_000,
    });
  }
  return pool;
}

export const CONSENT_TEXT =
  "Get new listings and building updates from Real Deal Housing by email. Unsubscribe anytime.";

/** Minimal branded HTML page for GET confirm/unsubscribe outcomes. */
export function htmlPage(msg: string, sub: string): string {
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${msg} — Real Deal Housing</title>
<style>body{font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;padding:0 24px;color:#1F3D4D}
h1{font-size:22px;margin-bottom:12px}p{color:rgba(26,26,26,.6);line-height:1.7;font-size:14px}
a{color:#1F3D4D}</style>
</head><body><h1>${msg}</h1><p>${sub}</p><p><a href="/">← realdealhousing</a></p></body></html>`;
}

/** Send the double-opt-in confirm email via Resend. Returns false when no key. */
export async function sendConfirmEmail(email: string, confirmToken: string, siteUrl: string): Promise<boolean> {
  const key = process.env.RESEND_API_KEY;
  if (!key) return false;
  const from = process.env.EMAIL_FROM ?? "Real Deal Housing <padmini@realdealhousing.com>";
  const url = `${siteUrl}/newsletter/confirm?token=${confirmToken}`;
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from,
      to: [email],
      subject: "Confirm your subscription — Real Deal Housing",
      html: `<p>You asked for new listings and building updates from Real Deal Housing.</p>
<p><a href="${url}">Confirm your email address</a> to start receiving them.</p>
<p style="color:#888;font-size:13px">If this wasn't you, ignore this email — nothing will be sent.</p>`,
    }),
  });
  return res.ok;
}
