import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

// Pages with valuable public medical content — AI crawlers should index these
const PUBLIC_ALLOW = [
  "/",
  "/how-it-works",
  "/pricing",
  "/articles",
  "/articles/",
  "/articles/category/",
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
  "/drugs",
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
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
