"use server";

/**
 * Cockpit login (Phase 8.3). Validates the shared password (COCKPIT_PASSWORD)
 * with a timing-safe compare and, on success, sets the httpOnly session cookie
 * to COCKPIT_AUTH_TOKEN — which the edge middleware checks on every /cockpit route.
 *
 * Runs in the Node runtime (server action), so node:crypto is available.
 */
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { timingSafeEqual } from "node:crypto";

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}

export async function authenticate(formData: FormData): Promise<void> {
  const password = String(formData.get("password") ?? "");
  const next = String(formData.get("next") ?? "/cockpit") || "/cockpit";
  const expected = process.env.COCKPIT_PASSWORD ?? "";
  const token = process.env.COCKPIT_AUTH_TOKEN ?? "";

  if (!expected || !token || !safeEqual(password, expected)) {
    redirect(`/cockpit/login?error=1${next !== "/cockpit" ? `&next=${encodeURIComponent(next)}` : ""}`);
  }

  const jar = await cookies();
  jar.set("cockpit_auth", token, {
    httpOnly: true,
    sameSite: "lax",
    secure: false, // served over http on LAN/Tailscale; the tailnet encrypts transport
    path: "/",
    maxAge: 60 * 60 * 24 * 30, // 30 days
  });
  // Only allow redirecting to internal cockpit paths.
  redirect(next.startsWith("/cockpit") ? next : "/cockpit");
}
