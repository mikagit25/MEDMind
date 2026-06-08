import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { getCategoryLabel, CATEGORY_DESCRIPTIONS } from "@/lib/categories";
import { CategoryIcon } from "@/lib/medical-icons";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { getArticlesT } from "@/lib/articles-i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SUPPORTED = ["en", "ru", "ar", "tr", "de", "fr", "es"];
const PAGE_SIZE = 24;

export const dynamic = "force-dynamic";

type Article = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  keywords: string[];
  reading_time_minutes: number;
  published_at: string | null;
};

async function fetchCategory(
  cat: string,
  page = 1,
  locale = "en"
): Promise<{ articles: Article[]; total: number } | null> {
  try {
    const params = new URLSearchParams({ page: String(page), limit: "24" });
    if (locale && locale !== "en") params.set("locale", locale);
    const res = await fetch(`${API_URL}/articles/category/${cat}?${params}`, {
      cache: "no-store",
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    const data = await res.json();
    return { articles: data.articles ?? [], total: data.total ?? 0 };
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: { cat: string };
  searchParams?: { page?: string; lang?: string };
}): Promise<Metadata> {
  const cookieLocale = cookies().get("medmind_locale")?.value;
  const rawLocale = searchParams?.lang || cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const label = getCategoryLabel(params.cat, locale);
  if (!label || label === params.cat) return { title: "Category not found" };

  const page = Math.max(1, parseInt(searchParams?.page ?? "1", 10) || 1);
  const description =
    CATEGORY_DESCRIPTIONS[params.cat] ??
    `Evidence-based medical articles in ${label}. Comprehensive content for healthcare professionals.`;
  const basePath = `/articles/category/${params.cat}`;
  const baseUrl  = `${SITE_URL}${basePath}`;
  const localBase = locale !== "en" ? `${SITE_URL}/${locale}${basePath}` : baseUrl;
  const canonical = page > 1 ? `${localBase}?page=${page}` : localBase;

  return {
    title: page > 1
      ? `${label} — Page ${page} — Medical Articles`
      : `${label} — Medical Articles`,
    description,
    alternates: {
      canonical,
      languages: Object.fromEntries(
        ["en", "ru", "ar", "tr", "de", "fr", "es"].map((l) => [
          l,
          l === "en" ? baseUrl : `${SITE_URL}/${l}${basePath}`,
        ])
      ),
    },
    openGraph: {
      title: `${label} — MedMind AI Articles`,
      description,
      url: canonical,
      siteName: "MedMind AI",
      type: "website",
    },
  };
}

export default async function CategoryPage({
  params,
  searchParams,
}: {
  params: { cat: string };
  searchParams?: { page?: string; lang?: string };
}) {
  const cookieLocale = cookies().get("medmind_locale")?.value;
  const rawLocale = searchParams?.lang || cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const t = getArticlesT(locale);

  const label = getCategoryLabel(params.cat, locale);
  if (!label || label === params.cat) notFound();

  const page = Math.max(1, parseInt(searchParams?.page ?? "1", 10) || 1);
  const result = await fetchCategory(params.cat, page, locale);
  if (!result) notFound();

  const { articles, total } = result;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: t.nav_articles, item: `${SITE_URL}/articles` },
      { "@type": "ListItem", position: 3, name: label, item: `${SITE_URL}/articles/category/${params.cat}` },
    ],
  };

  const dateLocale =
    locale === "ar" ? "ar-SA" : locale === "tr" ? "tr-TR" :
    locale === "ru" ? "ru-RU" : locale === "de" ? "de-DE" :
    locale === "fr" ? "fr-FR" : locale === "es" ? "es-ES" : "en-US";

  const catHref = (p: number) => {
    const base = locale !== "en"
      ? `/${locale}/articles/category/${params.cat}`
      : `/articles/category/${params.cat}`;
    return p > 1 ? `${base}?page=${p}` : base;
  };

  return (
    <div className="min-h-screen bg-bg" dir={t.dir}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />

      <ArticleNav />

      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Breadcrumb */}
        <nav
          className="flex items-center gap-1.5 text-xs font-serif text-ink-3 mb-8"
          aria-label="Breadcrumb"
        >
          <Link href="/articles" className="hover:text-ink">{t.nav_articles}</Link>
          <span>/</span>
          <span className="text-ink-2">{label}</span>
        </nav>

        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center text-ink-2">
              <CategoryIcon category={params.cat} size={26} strokeWidth={1.5} />
            </div>
            <h1 className="font-syne font-black text-3xl text-ink">{label}</h1>
          </div>
          <p className="text-ink-2 font-serif text-base max-w-2xl">
            {CATEGORY_DESCRIPTIONS[params.cat]}
          </p>
          <p className="text-ink-3 font-serif text-sm mt-2">
            {t.n_articles.replace("{n}", String(total))}
          </p>
        </div>

        {/* Articles */}
        {articles.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {articles.map((a) => (
              <Link
                key={a.id}
                href={locale !== "en" ? `/${locale}/articles/${a.slug}` : `/articles/${a.slug}`}
                className="group flex flex-col bg-surface border border-border rounded-xl p-5 hover:border-ink hover:shadow-md transition-all"
              >
                <h2 className="font-syne font-bold text-base text-ink mb-2 group-hover:text-accent transition-colors line-clamp-2">
                  {a.title}
                </h2>
                <p className="text-ink-2 font-serif text-sm leading-relaxed flex-1 line-clamp-3">
                  {a.excerpt}
                </p>
                <div className="flex items-center gap-3 mt-4 pt-3 border-t border-border">
                  <span className="text-ink-3 text-xs font-serif">
                    {t.read_time.replace("{n}", String(a.reading_time_minutes))}
                  </span>
                  {a.published_at && (
                    <span className="text-ink-3 text-xs font-serif ml-auto">
                      {new Date(a.published_at).toLocaleDateString(dateLocale, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-20 text-ink-3 font-serif">
            {t.no_results_cat}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <nav
            className="mt-12 pt-8 border-t border-border flex items-center justify-between gap-3"
            aria-label="Pagination"
          >
            <div>
              {page > 1 && (
                <Link
                  href={catHref(page - 1)}
                  className="inline-flex items-center gap-1.5 font-syne font-semibold text-sm text-ink-2 hover:text-ink border border-border rounded-lg px-4 py-2 hover:border-ink transition-all"
                >
                  {t.prev}
                </Link>
              )}
            </div>
            <span className="font-serif text-xs text-ink-3">
              {t.page_of.replace("{page}", String(page)).replace("{total}", String(totalPages))}
              {" — "}
              {t.n_articles.replace("{n}", String(total))}
            </span>
            <div>
              {page < totalPages && (
                <Link
                  href={catHref(page + 1)}
                  className="inline-flex items-center gap-1.5 font-syne font-semibold text-sm text-ink-2 hover:text-ink border border-border rounded-lg px-4 py-2 hover:border-ink transition-all"
                >
                  {t.next}
                </Link>
              )}
            </div>
          </nav>
        )}

        {/* Back link */}
        <div className="mt-6 pt-4">
          <Link href="/articles" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink">
            {t.all_articles}
          </Link>
        </div>
      </main>
    </div>
  );
}
