import { NextRequest, NextResponse } from "next/server";
import { newsletterPool, htmlPage } from "@/lib/newsletter";

const html = (msg: string, sub: string, status = 200) =>
  new NextResponse(htmlPage(msg, sub), { status, headers: { "Content-Type": "text/html" } });

export async function GET(req: NextRequest) {
  const token = req.nextUrl.searchParams.get("token");
  if (!token) return html("Invalid link", "This unsubscribe link is missing its token.", 400);

  const pool = newsletterPool();
  if (!pool) return html("Not available", "Subscription management isn't live on this preview yet.", 503);

  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      `UPDATE subscribers
       SET status = 'unsubscribed', unsubscribed_at = NOW(),
           unsub_token = encode(gen_random_bytes(16), 'hex')
       WHERE unsub_token = $1
       RETURNING email`,
      [token],
    );
    if (!rows.length) {
      return html("Link expired or invalid", "This unsubscribe link has already been used or is no longer valid.", 400);
    }
    await client.query(
      `INSERT INTO email_suppression (email, reason, source) VALUES ($1, 'unsubscribed', 'newsletter')
       ON CONFLICT (email) DO NOTHING`,
      [rows[0].email],
    );
    return html("You've been unsubscribed", "You won't receive further newsletter emails from Real Deal Housing. Resubscribe on the site anytime.");
  } finally {
    client.release();
  }
}
