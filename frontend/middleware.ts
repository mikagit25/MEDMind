import { NextRequest, NextResponse } from "next/server";

// 'en' is the default locale — no path prefix needed
const LOCALES = ["es", "ru", "ar", "tr", "de", "fr"];
const LOCALE_RE = new RegExp(`^/(${LOCALES.join("|")})(\/|$)`);

// Public paths that should be indexed by search engines
const PUBLIC_PREFIXES = [
  "/articles",
  "/pricing",
  "/how-it-works",
  "/investors",
  "/calculators",
  "/drugs",
  "/imaging",
  "/sitemap",
  "/robots",
  "/opengraph",
  "/llms.txt",
];

function isPublicPath(pathname: string): boolean {
  if (pathname === "/") return true;
  return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

export function middleware(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;

  // ── Case 1: Path-prefixed locale (/es/articles/slug) ──────────────────────
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
  const langParam = searchParams.get("lang");
  if (langParam && LOCALES.includes(langParam)) {
    const url = request.nextUrl.clone();
    url.pathname = `/${langParam}${pathname}`;
    url.searchParams.delete("lang");
    return NextResponse.redirect(url, { status: 301 });
  }

  // ── Case 3: noindex for non-public pages ───────────────────────────────────
  // Authenticated app pages and auth forms have no unique SEO value.
  // The server renders HTML before client-side redirect, so crawlers see them.
  const response = NextResponse.next();
  if (!isPublicPath(pathname)) {
    response.headers.set("X-Robots-Tag", "noindex, nofollow");
  }
  return response;
}

export const config = {
  matcher: [
    // Skip Next.js internals, static assets, and known non-locale paths
    "/((?!_next/static|_next/image|api/|favicon|icon-|manifest\\.json|sitemap|robots|opengraph).*)",
  ],
};
