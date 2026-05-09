import { NextRequest, NextResponse } from "next/server";

const authEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";
const sessionCookieName = "tradingagents_session";

export function middleware(request: NextRequest) {
  if (!authEnabled) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  const publicPaths = ["/login"];
  const bypassPrefixes = ["/_next", "/favicon.ico"];

  if (
    publicPaths.includes(pathname) ||
    bypassPrefixes.some((prefix) => pathname.startsWith(prefix))
  ) {
    return NextResponse.next();
  }

  const sessionCookie = request.cookies.get(sessionCookieName);
  if (!sessionCookie?.value) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api).*)"],
};
