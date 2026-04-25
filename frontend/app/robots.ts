import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        // Public pages — crawl and index
        userAgent: "*",
        allow: ["/", "/pricing", "/login", "/register"],
        disallow: [
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
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
