import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
// Server-side URL — works inside Docker network; falls back to public URL for local dev
const BACKEND_URL =
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_URL?.replace(/^\//, `${SITE_URL}/`) ??
  "http://localhost:8000/api/v1";

const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

// ── Static public pages ───────────────────────────────────────────────────────
const STATIC_PAGES: { path: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"] }[] = [
  { path: "/",              priority: 1.0, changeFrequency: "weekly"  },
  { path: "/how-it-works",  priority: 0.9, changeFrequency: "monthly" },
  { path: "/pricing",       priority: 0.9, changeFrequency: "monthly" },
  { path: "/articles",      priority: 0.9, changeFrequency: "daily"   },
  { path: "/investors",     priority: 0.6, changeFrequency: "monthly" },
  { path: "/register",      priority: 0.7, changeFrequency: "monthly" },
  { path: "/login",         priority: 0.5, changeFrequency: "monthly" },
];

type ArticleSitemapEntry = {
  slug: string;
  updated_at: string | null;
  category: string;
  locales?: string[];
};

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

function hreflang(path: string): Record<string, string> {
  return Object.fromEntries([
    ["x-default", `${SITE_URL}${path}`],
    ...LOCALES.map((l) => [l, `${SITE_URL}/${l}${path}`]),
  ]);
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];
  const now = new Date();

  // ── Static pages ─────────────────────────────────────────────────────────
  for (const page of STATIC_PAGES) {
    entries.push({
      url: `${SITE_URL}${page.path}`,
      lastModified: now,
      changeFrequency: page.changeFrequency,
      priority: page.priority,
      alternates: { languages: hreflang(page.path) },
    });
  }

  // ── Articles ──────────────────────────────────────────────────────────────
  const articles = await fetchArticleSlugs();
  const categoryCount: Record<string, number> = {};

  for (const article of articles) {
    const lastMod = article.updated_at ? new Date(article.updated_at) : now;
    const baseUrl  = `${SITE_URL}/articles/${article.slug}`;

    const languages: Record<string, string> = {
      "x-default": baseUrl,
      en: baseUrl,
    };
    for (const loc of article.locales ?? []) {
      languages[loc] = `${baseUrl}?lang=${loc}`;
    }

    entries.push({
      url: baseUrl,
      lastModified: lastMod,
      changeFrequency: "monthly",
      priority: 0.8,
      alternates: { languages },
    });

    categoryCount[article.category] = (categoryCount[article.category] ?? 0) + 1;
  }

  // ── Article category pages ────────────────────────────────────────────────
  for (const [cat, count] of Object.entries(categoryCount)) {
    entries.push({
      url: `${SITE_URL}/articles/category/${cat}`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.7,
    });
    const totalPages = Math.ceil(count / 24);
    for (let p = 2; p <= totalPages; p++) {
      entries.push({
        url: `${SITE_URL}/articles/category/${cat}?page=${p}`,
        lastModified: now,
        changeFrequency: "weekly",
        priority: 0.5,
      });
    }
  }

  return entries;
}
