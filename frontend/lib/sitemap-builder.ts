/**
 * Shared sitemap builder for all language-specific sitemaps.
 * Each locale gets its own /sitemap-XX.xml so Google can allocate crawl budget
 * per language and index them in parallel.
 */

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const BACKEND_URL =
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_URL?.replace(/^\//, `${SITE_URL}/`) ??
  "http://localhost:8000/api/v1";

export const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"] as const;
export type Locale = (typeof LOCALES)[number];

export type ArticleSitemapEntry = {
  slug: string;
  updated_at: string | null;
  category: string;
  locales?: string[];
};

export type DrugSitemapEntry = { id: string; available_langs: string[] };

// ── URL helpers ──────────────────────────────────────────────────────────────

export function localizedUrl(path: string, locale: string): string {
  return locale === "en" ? `${SITE_URL}${path}` : `${SITE_URL}/${locale}${path}`;
}

function esc(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Data fetchers ────────────────────────────────────────────────────────────

export async function fetchArticlesSitemapData(): Promise<ArticleSitemapEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/articles/sitemap-data`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchDrugsSitemapData(): Promise<DrugSitemapEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/drugs/sitemap-data`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

// ── XML builders ─────────────────────────────────────────────────────────────

function hreflangTags(path: string, availableLocales: string[]): string {
  const enUrl = localizedUrl(path, "en");
  return [
    `      <xhtml:link rel="alternate" hreflang="x-default" href="${esc(enUrl)}"/>`,
    ...availableLocales.map(
      (l) =>
        `      <xhtml:link rel="alternate" hreflang="${l}" href="${esc(localizedUrl(path, l))}"/>`
    ),
  ].join("\n");
}

function urlEntry({
  url,
  lastmod,
  priority,
  changefreq,
  hreflang,
}: {
  url: string;
  lastmod: string;
  priority: number;
  changefreq: string;
  hreflang?: string;
}): string {
  const inner = [
    `    <loc>${esc(url)}</loc>`,
    `    <lastmod>${lastmod}</lastmod>`,
    `    <changefreq>${changefreq}</changefreq>`,
    `    <priority>${priority.toFixed(1)}</priority>`,
    ...(hreflang ? [hreflang] : []),
  ].join("\n");
  return `  <url>\n${inner}\n  </url>`;
}

// ── Main builder ─────────────────────────────────────────────────────────────

export async function buildLanguageSitemap(locale: Locale): Promise<string> {
  const now = new Date().toISOString().split("T")[0];
  const [articles, drugs] = await Promise.all([
    fetchArticlesSitemapData(),
    fetchDrugsSitemapData(),
  ]);

  const entries: string[] = [];

  // ── Articles index page ─────────────────────────────────────────────────
  entries.push(
    urlEntry({
      url: localizedUrl("/articles", locale),
      lastmod: now,
      priority: 0.9,
      changefreq: "daily",
      hreflang: hreflangTags("/articles", [...LOCALES]),
    })
  );

  // ── Individual articles ─────────────────────────────────────────────────
  for (const article of articles) {
    // Non-English sitemaps only include articles that have that translation
    if (locale !== "en" && !(article.locales ?? []).includes(locale)) continue;

    const path = `/articles/${article.slug}`;
    const articleLocales = ["en", ...(article.locales ?? [])];
    const lastmod = article.updated_at ? article.updated_at.split("T")[0] : now;

    entries.push(
      urlEntry({
        url: localizedUrl(path, locale),
        lastmod,
        priority: 0.8,
        changefreq: "monthly",
        hreflang: hreflangTags(path, articleLocales),
      })
    );
  }

  // ── Category pages ──────────────────────────────────────────────────────
  const categories = [...new Set(articles.map((a) => a.category))];
  for (const cat of categories) {
    const path = `/articles/category/${cat}`;
    entries.push(
      urlEntry({
        url: localizedUrl(path, locale),
        lastmod: now,
        priority: 0.7,
        changefreq: "weekly",
        hreflang: hreflangTags(path, [...LOCALES]),
      })
    );
  }

  // ── Drugs ───────────────────────────────────────────────────────────────
  for (const drug of drugs) {
    if (locale !== "en" && !(drug.available_langs ?? []).includes(locale)) continue;

    const path = `/drugs/${drug.id}`;
    const drugLocales = ["en", ...(drug.available_langs ?? [])];
    entries.push(
      urlEntry({
        url: localizedUrl(path, locale),
        lastmod: now,
        priority: 0.7,
        changefreq: "monthly",
        hreflang: hreflangTags(path, drugLocales),
      })
    );
  }

  // ── Static pages — English only ─────────────────────────────────────────
  if (locale === "en") {
    const statics: { path: string; priority: number; changefreq: string }[] = [
      { path: "/",             priority: 1.0, changefreq: "weekly"  },
      { path: "/how-it-works", priority: 0.9, changefreq: "monthly" },
      { path: "/pricing",      priority: 0.9, changefreq: "monthly" },
      { path: "/investors",    priority: 0.6, changefreq: "monthly" },
      { path: "/register",     priority: 0.7, changefreq: "monthly" },
    ];
    for (const s of statics) {
      entries.push(
        urlEntry({ url: `${SITE_URL}${s.path}`, lastmod: now, priority: s.priority, changefreq: s.changefreq })
      );
    }
  }

  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"`,
    `        xmlns:xhtml="http://www.w3.org/1999/xhtml">`,
    ...entries,
    `</urlset>`,
  ].join("\n");
}

// ── Sitemap index builder ────────────────────────────────────────────────────

export function buildSitemapIndex(): string {
  const now = new Date().toISOString().split("T")[0];
  const sitemaps = LOCALES.map(
    (l) =>
      `  <sitemap>\n    <loc>${SITE_URL}/sitemap-${l}.xml</loc>\n    <lastmod>${now}</lastmod>\n  </sitemap>`
  ).join("\n");
  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">`,
    sitemaps,
    `</sitemapindex>`,
  ].join("\n");
}

export const XML_HEADERS = {
  "Content-Type": "application/xml; charset=utf-8",
  "Cache-Control": "public, max-age=3600, s-maxage=3600",
};
