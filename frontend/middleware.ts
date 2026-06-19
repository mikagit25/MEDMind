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
  "/learn",
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

  // ── Case 0: Root "/" — redirect to user's preferred locale ────────────────
  // Priority: 1) explicit locale cookie  2) browser Accept-Language header
  // Skip if ?lang= is present (handled by Case 2) to avoid redirect loops.
  if (pathname === "/" && !searchParams.get("lang")) {
    // Cookie set by switchLocale() in I18nProvider — the user's saved choice
    const localeCookie = request.cookies.get("medmind_locale")?.value;
    if (localeCookie && LOCALES.includes(localeCookie)) {
      const url = request.nextUrl.clone();
      url.pathname = `/${localeCookie}`;
      // 302 (not 301) so browsers re-check on every visit in case preference changes
      return NextResponse.redirect(url, { status: 302 });
    }
    // First-time visitor: detect from Accept-Language (e.g. "ru-RU,ru;q=0.9,en;q=0.8")
    const acceptLang = request.headers.get("accept-language") ?? "";
    for (const part of acceptLang.split(",")) {
      const code = part.trim().split(";")[0].trim().split("-")[0].toLowerCase();
      if (LOCALES.includes(code)) {
        const url = request.nextUrl.clone();
        url.pathname = `/${code}`;
        return NextResponse.redirect(url, { status: 302 });
      }
    }
    // No match → serve English (default, fall through)
  }

  // ── Case 1: Path-prefixed locale (/es/articles/slug) ──────────────────────
  const localeMatch = pathname.match(LOCALE_RE);
  if (localeMatch) {
    const locale = localeMatch[1];
    const rest = pathname.slice(locale.length + 1) || "/";
    const url = request.nextUrl.clone();
    url.pathname = rest;
    url.searchParams.set("lang", locale);
    // Forward locale to Server Components via request header (readable via headers())
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-locale", locale);
    return NextResponse.rewrite(url, { request: { headers: requestHeaders } });
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
