import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const BACKEND_URL =
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_URL?.replace(/^\//, `${SITE_URL}/`) ??
  "http://localhost:8000/api/v1";

const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];
const NON_EN   = LOCALES.filter((l) => l !== "en");

type ArticleSitemapEntry = {
  slug: string;
  updated_at: string | null;
  category: string;
  locales?: string[];
};

type DrugSitemapEntry = { id: string; available_langs: string[] };
type ImageSitemapEntry = { id: string; locale?: string };

async function fetchDrugIds(): Promise<DrugSitemapEntry[]> {
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

async function fetchImageIds(): Promise<ImageSitemapEntry[]> {
  try {
    // Fetch all image IDs via browse endpoint (public, no auth)
    const res = await fetch(`${BACKEND_URL}/imaging?limit=100&offset=0`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data || []).map((img: any) => ({ id: img.id }));
  } catch {
    return [];
  }
}

async function fetchArticleSlugs(): Promise<ArticleSitemapEntry[]> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10_000);
    const res = await fetch(`${BACKEND_URL}/articles/sitemap-data`, {
      next: { revalidate: 3600 },
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

/**
 * Build hreflang alternates using path-prefixed URLs (/es/path, /ru/path).
 * Google treats path-prefixed locales as distinct pages; query params (?lang=)
 * are canonicalized to the base URL and never indexed as separate language versions.
 *
 * baseUrl must be the full English URL, e.g. https://medmind.pro/articles/slug
 * The locale prefix is inserted after the origin: https://medmind.pro/es/articles/slug
 */
function langAlternates(baseUrl: string, availableLocales: string[] = LOCALES): Record<string, string> {
  // Extract origin + path separately so we can inject the locale prefix correctly
  const url = new URL(baseUrl);
  const map: Record<string, string> = {
    "x-default": baseUrl,
    en: baseUrl,
  };
  for (const l of availableLocales) {
    if (l !== "en") map[l] = `${url.origin}/${l}${url.pathname}${url.search}`;
  }
  return map;
}

/** Locale-prefixed URL for a given path (empty prefix for English). */
function localizedUrl(path: string, locale: string): string {
  return locale === "en" ? `${SITE_URL}${path}` : `${SITE_URL}/${locale}${path}`;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];
  const now = new Date();

  // ── Static pages (English base only — not localized) ──────────────────────
  const STATIC_PAGES: { path: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"] }[] = [
    { path: "/",             priority: 1.0, changeFrequency: "weekly"  },
    { path: "/how-it-works", priority: 0.9, changeFrequency: "monthly" },
    { path: "/pricing",      priority: 0.9, changeFrequency: "monthly" },
    { path: "/investors",    priority: 0.6, changeFrequency: "monthly" },
    { path: "/register",     priority: 0.7, changeFrequency: "monthly" },
    { path: "/login",        priority: 0.5, changeFrequency: "monthly" },
  ];

  for (const page of STATIC_PAGES) {
    entries.push({
      url: `${SITE_URL}${page.path}`,
      lastModified: now,
      changeFrequency: page.changeFrequency,
      priority: page.priority,
    });
  }

  // ── /articles index — English + one entry per non-English locale ──────────
  entries.push({
    url: `${SITE_URL}/articles`,
    lastModified: now,
    changeFrequency: "daily",
    priority: 0.9,
    alternates: { languages: langAlternates(`${SITE_URL}/articles`) },
  });
  for (const loc of NON_EN) {
    entries.push({
      url: localizedUrl("/articles", loc),
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.8,
      alternates: { languages: langAlternates(`${SITE_URL}/articles`) },
    });
  }

  // ── Drug Database index page ──────────────────────────────────────────────
  entries.push({
    url: `${SITE_URL}/drugs`,
    lastModified: now,
    changeFrequency: "daily",
    priority: 0.9,
    alternates: { languages: langAlternates(`${SITE_URL}/drugs`) },
  });
  for (const loc of NON_EN) {
    entries.push({
      url: localizedUrl("/drugs", loc),
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.8,
      alternates: { languages: langAlternates(`${SITE_URL}/drugs`) },
    });
  }

  // ── Individual drug pages ─────────────────────────────────────────────────
  const drugs = await fetchDrugIds();
  for (const drug of drugs) {
    const basePath = `/drugs/${drug.id}`;
    const baseUrl  = `${SITE_URL}${basePath}`;
    const langs    = drug.available_langs ?? [];
    const langMap: Record<string, string> = { "x-default": baseUrl, en: baseUrl };
    for (const l of langs) {
      if (l !== "en") langMap[l] = localizedUrl(basePath, l);
    }
    entries.push({
      url: baseUrl,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.75,
      alternates: { languages: langMap },
    });
    for (const l of langs) {
      if (l !== "en") {
        entries.push({
          url: localizedUrl(basePath, l),
          lastModified: now,
          changeFrequency: "monthly",
          priority: 0.65,
          alternates: { languages: langMap },
        });
      }
    }
  }

  // ── Medical Imaging index ─────────────────────────────────────────────────
  entries.push({
    url: `${SITE_URL}/imaging`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.85,
    alternates: { languages: langAlternates(`${SITE_URL}/imaging`) },
  });
  for (const loc of NON_EN) {
    entries.push({
      url: localizedUrl("/imaging", loc),
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.75,
      alternates: { languages: langAlternates(`${SITE_URL}/imaging`) },
    });
  }

  // ── Individual imaging pages ──────────────────────────────────────────────
  const images = await fetchImageIds();
  for (const img of images) {
    entries.push({
      url: `${SITE_URL}/imaging/${img.id}`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.7,
      alternates: { languages: langAlternates(`${SITE_URL}/imaging/${img.id}`) },
    });
  }

  // ── Articles ──────────────────────────────────────────────────────────────
  const articles = await fetchArticleSlugs();
  const categoryCount: Record<string, number> = {};

  for (const article of articles) {
    const lastMod  = article.updated_at ? new Date(article.updated_at) : now;
    const basePath = `/articles/${article.slug}`;
    const baseUrl  = `${SITE_URL}${basePath}`;

    const languages: Record<string, string> = {
      "x-default": baseUrl,
      en: baseUrl,
    };
    for (const loc of article.locales ?? []) {
      languages[loc] = localizedUrl(basePath, loc);
    }

    // English canonical
    entries.push({
      url: baseUrl,
      lastModified: lastMod,
      changeFrequency: "monthly",
      priority: 0.8,
      alternates: { languages },
    });

    // One path-prefixed entry per translated locale — Google indexes each as a
    // distinct page rather than a query-param duplicate of the English version.
    for (const loc of article.locales ?? []) {
      entries.push({
        url: localizedUrl(basePath, loc),
        lastModified: lastMod,
        changeFrequency: "monthly",
        priority: 0.7,
        alternates: { languages },
      });
    }

    categoryCount[article.category] = (categoryCount[article.category] ?? 0) + 1;
  }

  // ── Category pages — English + non-English variants ───────────────────────
  for (const [cat, count] of Object.entries(categoryCount)) {
    const catPath = `/articles/category/${cat}`;
    const catBase = `${SITE_URL}${catPath}`;
    const langMap = langAlternates(catBase);

    // English base
    entries.push({
      url: catBase,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.7,
      alternates: { languages: langMap },
    });
    // Non-English variants — path-prefixed so Google indexes them independently
    for (const loc of NON_EN) {
      entries.push({
        url: localizedUrl(catPath, loc),
        lastModified: now,
        changeFrequency: "weekly",
        priority: 0.6,
        alternates: { languages: langMap },
      });
    }
    // Pagination (English only; non-EN pagination adds too many low-value URLs)
    const totalPages = Math.ceil(count / 24);
    for (let p = 2; p <= totalPages; p++) {
      entries.push({
        url: `${catBase}?page=${p}`,
        lastModified: now,
        changeFrequency: "weekly",
        priority: 0.5,
      });
    }
  }

  return entries;
}
