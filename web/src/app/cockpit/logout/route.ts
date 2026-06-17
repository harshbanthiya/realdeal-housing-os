import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Clears the cockpit session cookie and returns to the login page.
export async function GET(req: NextRequest) {
  const res = NextResponse.redirect(new URL("/cockpit/login", req.url));
  res.cookies.set("cockpit_auth", "", { path: "/", maxAge: 0 });
  return res;
}
