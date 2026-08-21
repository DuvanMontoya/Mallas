import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE = process.env.SESSION_COOKIE_NAME ?? "curriculum_session";

/**
 * Fast, optimistic routing guard. A matching cookie only avoids an unnecessary
 * redirect; the protected server components independently validate it against
 * Django before they render any product content.
 */
export function proxy(request: NextRequest) {
  if (request.nextUrl.pathname === "/login" || request.nextUrl.pathname === "/reset-password") {
    return NextResponse.next();
  }
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", `${request.nextUrl.pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!login(?:/|$)|reset-password(?:/|$)|api/v1(?:/|$)|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)"],
};
