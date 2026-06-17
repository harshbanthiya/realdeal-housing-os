import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Cockpit shared-password gate (Phase 8.3).
 *
 * Protects every /cockpit route. A valid session is the cookie `cockpit_auth`
 * equal to COCKPIT_AUTH_TOKEN (set by the login server action after the shared
 * password matches). The login page itself is public.
 *
 * If COCKPIT_AUTH_TOKEN is unset (e.g. local dev), the gate is OPEN so nobody
 * gets locked out — the serve script warns loudly when that happens before
 * exposing the app on the network.
 *
 * Edge-safe: only cookie read + env compare + redirect. No Node APIs.
 */
const COOKIE = "cockpit_auth";

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname === "/cockpit/login") return NextResponse.next();

  const token = process.env.COCKPIT_AUTH_TOKEN;
  if (!token) return NextResponse.next(); // gate not configured -> open (dev)

  if (req.cookies.get(COOKIE)?.value === token) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/cockpit/login";
  url.search = pathname && pathname !== "/cockpit" ? `?next=${encodeURIComponent(pathname)}` : "";
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/cockpit", "/cockpit/:path*"],
};
