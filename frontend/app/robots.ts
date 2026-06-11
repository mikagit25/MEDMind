import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

// Public pages with valuable medical content — all search engines should index these
const PUBLIC_ALLOW = [
  "/",
  "/articles",
  "/articles/",
  "/articles/category/",
  "/news",
  "/news/",
  "/drugs",
  "/drugs/",
  "/learn/",
  "/learn/glossary",
  "/learn/glossary/",
  "/learn/topics",
  "/learn/topics/",
  "/learn/drugs",
  "/learn/drugs/",
  "/calculators",
  "/calculators/",
  "/symptoms",
  "/how-it-works",
  "/pricing",
  "/investors",
  "/register",
  "/login",
];

// Private/auth-only pages — never index
const DISALLOW_ALL = [
  "/api/",
  "/admin",
  "/_next/",
  "/dashboard",
  "/modules",
  "/flashcards",
  "/quiz",
  "/cases",
  "/anatomy",
  "/imaging",
  "/ai-tutor",
  "/leaderboard",
  "/progress",
  "/search",
  "/settings",
  "/teacher/",
  "/my-courses",
  "/my-flashcards",
  "/achievements",
  "/bookmarks",
  "/notifications",
  "/simulation",
  "/compliance",
  "/onboarding",
  "/upgrade",
  "/recommendations",
  "/veterinary",
  "/knowledge",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      // ── Standard search engines ─────────────────────────────────────────
      {
        userAgent: "*",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── Google's AI Overviews crawler ───────────────────────────────────
      {
        userAgent: "Googlebot",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── OpenAI / ChatGPT ────────────────────────────────────────────────
      // GPTBot: used by ChatGPT to browse the web and train future models
      // OAI-SearchBot: used for ChatGPT search feature
      {
        userAgent: "GPTBot",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },
      {
        userAgent: "OAI-SearchBot",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },
      {
        userAgent: "ChatGPT-User",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── Perplexity ──────────────────────────────────────────────────────
      // PerplexityBot: indexes content for Perplexity answers
      {
        userAgent: "PerplexityBot",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── Anthropic / Claude ──────────────────────────────────────────────
      {
        userAgent: "anthropic-ai",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },
      {
        userAgent: "Claude-Web",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },
      {
        userAgent: "ClaudeBot",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── Google Gemini / Bard ────────────────────────────────────────────
      {
        userAgent: "Google-Extended",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── Meta AI ─────────────────────────────────────────────────────────
      {
        userAgent: "meta-externalagent",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── Apple ───────────────────────────────────────────────────────────
      {
        userAgent: "Applebot",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },
      {
        userAgent: "Applebot-Extended",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── Microsoft Copilot / Bing ────────────────────────────────────────
      {
        userAgent: "bingbot",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── You.com ─────────────────────────────────────────────────────────
      {
        userAgent: "YouBot",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },

      // ── Cohere ──────────────────────────────────────────────────────────
      {
        userAgent: "cohere-ai",
        allow: PUBLIC_ALLOW,
        disallow: DISALLOW_ALL,
      },
    ],
    // Sitemap index + one sitemap per language so Google allocates crawl budget
    // per language and can index all 7 locales in parallel.
    sitemap: [
      `${SITE_URL}/sitemap.xml`,
      `${SITE_URL}/sitemap-en.xml`,
      `${SITE_URL}/sitemap-ru.xml`,
      `${SITE_URL}/sitemap-ar.xml`,
      `${SITE_URL}/sitemap-tr.xml`,
      `${SITE_URL}/sitemap-de.xml`,
      `${SITE_URL}/sitemap-fr.xml`,
      `${SITE_URL}/sitemap-es.xml`,
    ],
    host: SITE_URL,
  };
}
