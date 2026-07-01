import { NextRequest, NextResponse } from "next/server";
import { Pool } from "pg";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

const PAGE = (msg: string, sub: string) => `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${msg} — Real Deal Housing</title>
<style>body{font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;padding:0 24px;color:#1F3D4D}
h1{font-size:22px;margin-bottom:12px}p{color:rgba(26,26,26,.6);line-height:1.7;font-size:14px}</style>
</head><body><h1>${msg}</h1><p>${sub}</p></body></html>`;

export async function GET(req: NextRequest) {
  const contact = req.nextUrl.searchParams.get("contact");
  const token   = req.nextUrl.searchParams.get("token");

  if (!contact || !token) {
    return new NextResponse(PAGE("Invalid link", "This unsubscribe link is missing required parameters."), {
      status: 400, headers: { "Content-Type": "text/html" },
    });
  }

  const client = await pool.connect();
  try {
    // verify token matches contact
    const { rows } = await client.query(
      "SELECT id FROM contacts WHERE id = $1 AND unsub_token = $2",
      [contact, token],
    );
    if (!rows.length) {
      return new NextResponse(PAGE("Link expired or invalid", "This unsubscribe link has already been used or is no longer valid."), {
        status: 400, headers: { "Content-Type": "text/html" },
      });
    }

    // mark unsubscribed in drip state (all templates)
    await client.query(`
      INSERT INTO email_drip_state (contact_id, template_key, unsubscribed_at)
      SELECT $1, template_key, NOW()
      FROM (VALUES ('dlf-westpark'),('drip-1-variant-a'),('drip-1-variant-b')) t(template_key)
      ON CONFLICT (contact_id, template_key) DO UPDATE SET unsubscribed_at = NOW()
    `, [contact]);

    // rotate token so link can't be replayed
    await client.query(
      "UPDATE contacts SET unsub_token = encode(gen_random_bytes(16),'hex') WHERE id = $1",
      [contact],
    );

    return new NextResponse(
      PAGE("You've been unsubscribed", "You won't receive further emails from Real Deal Housing. If this was a mistake, reply to any previous email and we'll re-add you."),
      { status: 200, headers: { "Content-Type": "text/html" } },
    );
  } finally {
    client.release();
  }
}
