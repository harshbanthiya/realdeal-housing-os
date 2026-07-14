import { NextRequest, NextResponse } from "next/server";
import { newsletterPool, htmlPage } from "@/lib/newsletter";

const html = (msg: string, sub: string, status = 200) =>
  new NextResponse(htmlPage(msg, sub), { status, headers: { "Content-Type": "text/html" } });

export async function GET(req: NextRequest) {
  const token = req.nextUrl.searchParams.get("token");
  if (!token) return html("Invalid link", "This confirmation link is missing its token.", 400);

  const pool = newsletterPool();
  if (!pool) return html("Not available", "Subscription management isn't live on this preview yet.", 503);

  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      `UPDATE subscribers
       SET status = 'confirmed', confirmed_at = NOW(),
           confirm_token = encode(gen_random_bytes(16), 'hex')
       WHERE confirm_token = $1 AND status <> 'unsubscribed'
       RETURNING email`,
      [token],
    );
    if (!rows.length) {
      return html("Link expired or invalid", "This confirmation link has already been used or is no longer valid.", 400);
    }
    // explicit re-opt-in clears a previous unsubscribe suppression
    await client.query(
      "DELETE FROM email_suppression WHERE email = $1 AND reason = 'unsubscribed'",
      [rows[0].email],
    );
    return html("Subscription confirmed", "You'll be the first to hear about new listings in the buildings we cover. Unsubscribe anytime from any email.");
  } finally {
    client.release();
  }
}
