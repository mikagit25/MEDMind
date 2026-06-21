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

export type NewsSitemapEntry = { slug: string; fetched_at: string };

export type LearnGlossaryEntry = { slug: string };
export type LearnTopicEntry = { slug: string };
export type LearnDrugEntry = { slug: string };
export type PublicQuizEntry = { slug: string };
export type LearnPetEntry = { slug: string };
export type LearnLessonEntry = { module_slug: string; lesson_slug: string };

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

export async function fetchNewsSitemapData(): Promise<NewsSitemapEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/news/sitemap-data`, {
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

export async function fetchLearnGlossarySitemapData(): Promise<LearnGlossaryEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/public/glossary?limit=500`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.terms ?? []).map((t: { slug: string }) => ({ slug: t.slug }));
  } catch {
    return [];
  }
}

export async function fetchLearnTopicsSitemapData(): Promise<LearnTopicEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/public/topics?limit=200`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data: { slug: string }[] = await res.json();
    return data.map((t) => ({ slug: t.slug }));
  } catch {
    return [];
  }
}

export async function fetchLearnLessonsSitemapData(): Promise<LearnLessonEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/public/sitemap/lessons`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchLearnDrugsSitemapData(): Promise<LearnDrugEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/public/drugs?limit=200`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data: { slug: string }[] = await res.json();
    return data.map((d) => ({ slug: d.slug }));
  } catch {
    return [];
  }
}

export async function fetchLearnPetsSitemapData(): Promise<LearnPetEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/public/pets`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data: { modules: { slug: string }[] } = await res.json();
    return (data.modules ?? []).map((m) => ({ slug: m.slug }));
  } catch {
    return [];
  }
}

export async function fetchPublicQuizzesSitemapData(): Promise<PublicQuizEntry[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/public/quiz`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data: { slug: string }[] = await res.json();
    return data.map((q) => ({ slug: q.slug }));
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
  const [articles, drugs, newsItems, learnGlossary, learnTopics, learnLessons, learnDrugs, publicQuizzes, learnPets] = await Promise.all([
    fetchArticlesSitemapData(),
    fetchDrugsSitemapData(),
    fetchNewsSitemapData(),
    fetchLearnGlossarySitemapData(),
    fetchLearnTopicsSitemapData(),
    fetchLearnLessonsSitemapData(),
    fetchLearnDrugsSitemapData(),
    fetchPublicQuizzesSitemapData(),
    fetchLearnPetsSitemapData(),
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

  // ── News pages ──────────────────────────────────────────────────────────────
  entries.push(
    urlEntry({
      url: localizedUrl("/news", locale),
      lastmod: now,
      priority: 0.9,
      changefreq: "hourly",
      hreflang: hreflangTags("/news", [...LOCALES]),
    })
  );
  for (const item of newsItems) {
    const path = `/news/${item.slug}`;
    const lastmod = item.fetched_at ? item.fetched_at.split("T")[0] : now;
    entries.push(
      urlEntry({
        url: localizedUrl(path, locale),
        lastmod,
        priority: 0.75,
        changefreq: "weekly",
        hreflang: hreflangTags(path, [...LOCALES]),
      })
    );
  }

  // ── /learn/* pages — all locales with hreflang ─────────────────────────────
  const LEARN_LOCALES = [...LOCALES]; // en, ru, ar, tr, de, fr, es

  // Hub page
  entries.push(
    urlEntry({
      url: localizedUrl("/learn", locale),
      lastmod: now,
      priority: 0.9,
      changefreq: "weekly",
      hreflang: hreflangTags("/learn", LEARN_LOCALES),
    })
  );

  // Topics index
  entries.push(
    urlEntry({
      url: localizedUrl("/learn/topics", locale),
      lastmod: now,
      priority: 0.8,
      changefreq: "weekly",
      hreflang: hreflangTags("/learn/topics", LEARN_LOCALES),
    })
  );

  // Drugs index
  entries.push(
    urlEntry({
      url: localizedUrl("/learn/drugs", locale),
      lastmod: now,
      priority: 0.8,
      changefreq: "weekly",
      hreflang: hreflangTags("/learn/drugs", LEARN_LOCALES),
    })
  );

  // Glossary index
  entries.push(
    urlEntry({
      url: localizedUrl("/learn/glossary", locale),
      lastmod: now,
      priority: 0.8,
      changefreq: "weekly",
      hreflang: hreflangTags("/learn/glossary", LEARN_LOCALES),
    })
  );

  // Individual glossary term pages (EN canonical; other locales get same content)
  for (const term of learnGlossary) {
    entries.push(
      urlEntry({
        url: localizedUrl(`/learn/glossary/${term.slug}`, locale),
        lastmod: now,
        priority: 0.6,
        changefreq: "monthly",
        hreflang: hreflangTags(`/learn/glossary/${term.slug}`, LEARN_LOCALES),
      })
    );
  }

  // Individual topic pages
  for (const topic of learnTopics) {
    entries.push(
      urlEntry({
        url: localizedUrl(`/learn/topics/${topic.slug}`, locale),
        lastmod: now,
        priority: 0.7,
        changefreq: "monthly",
        hreflang: hreflangTags(`/learn/topics/${topic.slug}`, LEARN_LOCALES),
      })
    );
  }

  // Individual lesson pages — highest priority for content indexing
  for (const lesson of learnLessons) {
    const path = `/learn/topics/${lesson.module_slug}/${lesson.lesson_slug}`;
    entries.push(
      urlEntry({
        url: localizedUrl(path, locale),
        lastmod: now,
        priority: 0.75,
        changefreq: "monthly",
        hreflang: hreflangTags(path, LEARN_LOCALES),
      })
    );
  }

  // Individual public drug pages
  for (const drug of learnDrugs) {
    entries.push(
      urlEntry({
        url: localizedUrl(`/learn/drugs/${drug.slug}`, locale),
        lastmod: now,
        priority: 0.65,
        changefreq: "monthly",
        hreflang: hreflangTags(`/learn/drugs/${drug.slug}`, LEARN_LOCALES),
      })
    );
  }

  // Pet owner module index + individual modules
  entries.push(
    urlEntry({
      url: localizedUrl("/learn/pets", locale),
      lastmod: now,
      priority: 0.85,
      changefreq: "weekly",
      hreflang: hreflangTags("/learn/pets", LEARN_LOCALES),
    })
  );

  // Veterinary professionals page
  entries.push(
    urlEntry({
      url: localizedUrl("/learn/vet", locale),
      lastmod: now,
      priority: 0.85,
      changefreq: "weekly",
      hreflang: hreflangTags("/learn/vet", LEARN_LOCALES),
    })
  );
  for (const pet of learnPets) {
    entries.push(
      urlEntry({
        url: localizedUrl(`/learn/pets/${pet.slug}`, locale),
        lastmod: now,
        priority: 0.75,
        changefreq: "monthly",
        hreflang: hreflangTags(`/learn/pets/${pet.slug}`, LEARN_LOCALES),
      })
    );
  }

  // Public quiz index + individual quizzes (EN only — not localized yet)
  if (locale === "en") {
    entries.push(
      urlEntry({ url: `${SITE_URL}/quiz/public`, lastmod: now, priority: 0.85, changefreq: "weekly" })
    );
    for (const quiz of publicQuizzes) {
      entries.push(
        urlEntry({
          url: `${SITE_URL}/quiz/public/${quiz.slug}`,
          lastmod: now,
          priority: 0.75,
          changefreq: "monthly",
        })
      );
    }
  }

  // ── Calculator pages — client-side i18n, same URL for every locale ─────────
  // Calculators use client-side language switching: the URL is always
  // /calculators/<slug> regardless of locale, so never use localizedUrl() here.
  const ALL_CALC_SLUGS = [
    "cha2ds2-vasc", "has-bled", "heart-score", "wells-dvt", "wells-pe",
    "egfr-ckd-epi", "cockcroft-gault", "aki", "corrected-calcium",
    "sofa", "qsofa", "gcs", "curb-65", "abcd2",
    "meld", "child-pugh", "anion-gap", "bmi",
    "pregnancy-due-date", "ideal-body-weight", "target-heart-rate", "daily-calories",
  ];
  // Only emit once — the EN sitemap is the canonical source; other locales
  // include calculators too so Google can map them per-language hreflang.
  entries.push(
    urlEntry({
      url: `${SITE_URL}/calculators`,
      lastmod: now,
      priority: 0.85,
      changefreq: "monthly",
      hreflang: [
        `      <xhtml:link rel="alternate" hreflang="x-default" href="${esc(`${SITE_URL}/calculators`)}"/>`,
        ...[...LOCALES].map(
          (l) => `      <xhtml:link rel="alternate" hreflang="${l}" href="${esc(`${SITE_URL}/calculators`)}"/>`
        ),
      ].join("\n"),
    })
  );
  for (const slug of ALL_CALC_SLUGS) {
    const calcUrl = `${SITE_URL}/calculators/${slug}`;
    entries.push(
      urlEntry({
        url: calcUrl,
        lastmod: now,
        priority: 0.8,
        changefreq: "monthly",
        hreflang: [
          `      <xhtml:link rel="alternate" hreflang="x-default" href="${esc(calcUrl)}"/>`,
          ...[...LOCALES].map(
            (l) => `      <xhtml:link rel="alternate" hreflang="${l}" href="${esc(calcUrl)}"/>`
          ),
        ].join("\n"),
      })
    );
  }

  // ── Localized landing pages (/ru, /de, /fr, /es, /tr, /ar) ───────────────
  // Only emit the current locale's own landing page (avoid duplicates in each sitemap)
  if (locale !== "en") {
    const lp = localizedUrl("/", locale);
    // Use localizedUrl which produces /<locale> for non-en
    const locLanding = `${SITE_URL}/${locale}`;
    entries.push(
      urlEntry({
        url: locLanding,
        lastmod: now,
        priority: 1.0,
        changefreq: "weekly",
        hreflang: hreflangTags("/", [...LOCALES]),
      })
    );
  }

  // ── Static pages — English only ─────────────────────────────────────────
  if (locale === "en") {
    const statics: { path: string; priority: number; changefreq: string }[] = [
      { path: "/",                   priority: 1.0, changefreq: "weekly"  },
      { path: "/how-it-works",       priority: 0.9, changefreq: "monthly" },
      { path: "/pricing",            priority: 0.9, changefreq: "monthly" },
      { path: "/investors",          priority: 0.6, changefreq: "monthly" },
      { path: "/symptoms",           priority: 0.9, changefreq: "monthly" },
      { path: "/news",               priority: 0.9, changefreq: "hourly"  },
      { path: "/register",           priority: 0.7, changefreq: "monthly" },
      // Trust pages (V4 Phase 3)
      { path: "/about",              priority: 0.7, changefreq: "monthly" },
      { path: "/editorial-policy",   priority: 0.7, changefreq: "monthly" },
      { path: "/medical-disclaimer", priority: 0.6, changefreq: "yearly"  },
      { path: "/contact",            priority: 0.6, changefreq: "monthly" },
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
