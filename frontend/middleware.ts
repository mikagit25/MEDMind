import { NextRequest, NextResponse } from "next/server";

// 'en' is the default locale — no path prefix needed
const LOCALES = ["es", "ru", "ar", "tr", "de", "fr"];
const LOCALE_RE = new RegExp(`^/(${LOCALES.join("|")})(\/|$)`);

export function middleware(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;

  // ── Case 1: Path-prefixed locale (/es/articles/slug) ──────────────────────
  // Rewrite to internal query-param form so existing page code works unchanged
  const localeMatch = pathname.match(LOCALE_RE);
  if (localeMatch) {
    const locale = localeMatch[1];
    const rest = pathname.slice(locale.length + 1) || "/";
    const url = request.nextUrl.clone();
    url.pathname = rest;
    url.searchParams.set("lang", locale);
    return NextResponse.rewrite(url);
  }

  // ── Case 2: ?lang= query param → 301 redirect to path-prefixed URL ────────
  // Moves language selector from query param to path so Google indexes each
  // language version as a distinct URL rather than a query-param duplicate.
  const langParam = searchParams.get("lang");
  if (langParam && LOCALES.includes(langParam)) {
    const url = request.nextUrl.clone();
    url.pathname = `/${langParam}${pathname}`;
    url.searchParams.delete("lang");
    return NextResponse.redirect(url, { status: 301 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Skip Next.js internals, static assets, and known non-locale paths
    "/((?!_next/static|_next/image|api/|favicon|icon-|manifest\\.json|sitemap|robots|opengraph).*)",
  ],
};
