import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

// Static pages available without login (public SEO pages)
const STATIC_PAGES = [
  { path: "/", priority: 1.0, changeFrequency: "weekly" as const },
  { path: "/pricing", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/articles", priority: 0.9, changeFrequency: "daily" as const },
  { path: "/login", priority: 0.5, changeFrequency: "monthly" as const },
  { path: "/register", priority: 0.6, changeFrequency: "monthly" as const },
];

// Note: authenticated app sections (/dashboard, /modules, etc.) are intentionally
// excluded from the sitemap — they require login and are disallowed in robots.txt.

type ArticleSitemapEntry = {
  slug: string;
  updated_at: string | null;
  category: string;
  locales?: string[];  // available translation locales
};

async function fetchArticleSlugs(): Promise<ArticleSitemapEntry[]> {
  try {
    const res = await fetch(`${API_URL}/articles/sitemap-data`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];
  const now = new Date();

  // Static pages — one entry per locale
  for (const page of STATIC_PAGES) {
    entries.push({
      url: `${SITE_URL}${page.path}`,
      lastModified: now,
      changeFrequency: page.changeFrequency,
      priority: page.priority,
      alternates: {
        languages: Object.fromEntries(
          LOCALES.map((l) => [l, `${SITE_URL}/${l}${page.path}`])
        ),
      },
    });
  }

  // Dynamic article pages
  const articles = await fetchArticleSlugs();
  for (const article of articles) {
    const lastMod = article.updated_at ? new Date(article.updated_at) : now;
    const baseUrl = `${SITE_URL}/articles/${article.slug}`;

    // Build hreflang alternates: en is canonical, translated locales use ?lang=xx
    const languages: Record<string, string> = {
      "x-default": baseUrl,
      en: baseUrl,
    };
    if (article.locales?.length) {
      for (const loc of article.locales) {
        languages[loc] = `${baseUrl}?lang=${loc}`;
      }
    }

    entries.push({
      url: baseUrl,
      lastModified: lastMod,
      changeFrequency: "monthly",
      priority: 0.8,
      alternates: { languages },
    });
  }

  // Unique category pages
  const categories = [...new Set(articles.map((a) => a.category))];
  for (const cat of categories) {
    entries.push({
      url: `${SITE_URL}/articles/category/${cat}`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.7,
    });
  }

  return entries;
}
