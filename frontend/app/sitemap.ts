import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.ai";
const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

// Static pages available without login (public SEO pages)
const STATIC_PAGES = [
  { path: "/", priority: 1.0, changeFrequency: "weekly" as const },
  { path: "/pricing", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/login", priority: 0.5, changeFrequency: "monthly" as const },
  { path: "/register", priority: 0.6, changeFrequency: "monthly" as const },
];

// App sections (indexed after login but still useful for Google to discover)
const APP_SECTIONS = [
  { path: "/dashboard", priority: 0.8 },
  { path: "/modules", priority: 0.9 },
  { path: "/flashcards", priority: 0.8 },
  { path: "/quiz", priority: 0.8 },
  { path: "/cases", priority: 0.8 },
  { path: "/drugs", priority: 0.8 },
  { path: "/anatomy", priority: 0.7 },
  { path: "/imaging", priority: 0.7 },
  { path: "/leaderboard", priority: 0.6 },
  { path: "/progress", priority: 0.6 },
];

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

  // App sections — one entry per locale
  for (const section of APP_SECTIONS) {
    for (const locale of LOCALES) {
      entries.push({
        url: `${SITE_URL}/${locale}${section.path}`,
        lastModified: now,
        changeFrequency: "weekly",
        priority: section.priority * (locale === "en" ? 1 : 0.85), // en is canonical
      });
    }
  }

  return entries;
}
