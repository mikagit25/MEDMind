import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

// Static pages available without login (public SEO pages)
const STATIC_PAGES = [
  { path: "/", priority: 1.0, changeFrequency: "weekly" as const },
  { path: "/pricing", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/login", priority: 0.5, changeFrequency: "monthly" as const },
  { path: "/register", priority: 0.6, changeFrequency: "monthly" as const },
];

// Note: authenticated app sections (/dashboard, /modules, etc.) are intentionally
// excluded from the sitemap — they require login and are disallowed in robots.txt.

export default function sitemap(): MetadataRoute.Sitemap {
  const entries: MetadataRoute.Sitemap = [];
  const now = new Date();

  // Static pages — one entry per locale
  for (const page of STATIC_PAGES) {
    entries.push({
      url: `${SITE_URL}${page.path}`,
      lastModified: now,
      changeFrequency: page.changeFrequency,
      priority: page.priority,
      // Google's multi-language sitemap alternates
      alternates: {
        languages: Object.fromEntries(
          LOCALES.map((l) => [l, `${SITE_URL}/${l}${page.path}`])
        ),
      },
    });
  }

  return entries;
}
