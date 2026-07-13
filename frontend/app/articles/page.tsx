import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { getCategoryLabel } from "@/lib/categories";
import { CategoryIcon } from "@/lib/medical-icons";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { ReadBadge } from "@/components/ui/ReadBadge";
import { getArticlesT } from "@/lib/articles-i18n";
import { ArticlesFooterCTA } from "./FooterCTA";
import { PawPrint } from "lucide-react";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SUPPORTED = ["en", "ru", "ar", "tr", "de", "fr", "es"];

const ARTICLES_TITLES: Record<string, string> = {
  en: "Medical Articles — Evidence-Based Health Information",
  ru: "Медицинские статьи — доказательная информация",
  de: "Medizinische Artikel — Evidenzbasierte Gesundheitsinformation",
  fr: "Articles médicaux — Information de santé fondée sur des preuves",
  es: "Artículos médicos — Información de salud basada en evidencia",
  tr: "Tıbbi Makaleler — Kanıta Dayalı Sağlık Bilgisi",
  ar: "المقالات الطبية — معلومات صحية قائمة على الأدلة",
};

export const dynamic = "force-dynamic";

export async function generateMetadata({
  searchParams,
}: {
  searchParams?: { search?: string; lang?: string };
}): Promise<Metadata> {
  const rawLocale = searchParams?.lang;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const search = searchParams?.search;

  if (search) {
    return {
      title: `Search: ${search} — Medical Articles — MedMind AI`,
      robots: { index: false, follow: true },
    };
  }

  const canonical = locale !== "en" ? `${SITE_URL}/${locale}/articles` : `${SITE_URL}/articles`;

  return {
    title: ARTICLES_TITLES[locale] ?? ARTICLES_TITLES.en,
    description:
      "Comprehensive evidence-based medical articles on diseases, drugs, procedures, and clinical guidelines. Written for doctors, students, and healthcare professionals.",
    alternates: {
      canonical,
      languages: Object.fromEntries(
        SUPPORTED.map((l) => [l, l === "en" ? `${SITE_URL}/articles` : `${SITE_URL}/${l}/articles`])
      ),
    },
    openGraph: {
      title: "Medical Articles — MedMind AI",
      description: "Evidence-based medical content: diseases, drugs, procedures, diagnostics.",
      url: canonical,
      siteName: "MedMind AI",
      type: "website",
    },
  };
}

type Article = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  keywords: string[];
  reading_time_minutes: number;
  published_at: string | null;
  cover_image: string | null;
};

type CategoryStat = { category: string; count: number };

async function fetchArticles(search?: string, locale = "en"): Promise<Article[]> {
  try {
    const params = new URLSearchParams({ limit: "24" });
    if (search) params.set("search", search);
    if (locale && locale !== "en") params.set("locale", locale);
    const res = await fetch(`${API_URL}/articles?${params}`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.articles ?? [];
  } catch {
    return [];
  }
}

async function fetchCategories(): Promise<CategoryStat[]> {
  try {
    const res = await fetch(`${API_URL}/articles/categories`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export default async function ArticlesPage({
  searchParams,
}: {
  searchParams?: { search?: string; lang?: string };
}) {
  const search = searchParams?.search;
  const cookieLocale = cookies().get("medmind_locale")?.value;
  const rawLocale = searchParams?.lang || cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const t = getArticlesT(locale);

  const [articles, categories] = await Promise.all([
    fetchArticles(search, locale),
    fetchCategories(),
  ]);

  return (
    <div className="min-h-screen bg-bg" dir={t.dir}>
      <ArticleNav />

      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-10">
          <h1 className="font-syne font-black text-4xl text-ink mb-3">{t.heading}</h1>
          <p className="text-ink-2 font-serif text-lg max-w-2xl">{t.page_desc}</p>

          {/* Search bar */}
          <form method="GET" action="/articles" className="mt-6 flex gap-2 max-w-lg">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none">🔍</span>
              <input
                name="search"
                defaultValue={search ?? ""}
                placeholder={t.search_placeholder}
                className="w-full bg-surface border border-border rounded-xl pl-9 pr-4 py-2.5 text-ink text-sm font-serif focus:outline-none focus:border-ink transition-colors"
              />
            </div>
            <button
              type="submit"
              className="bg-ink text-white font-syne font-semibold text-sm px-5 py-2.5 rounded-xl hover:bg-ink-2 transition-colors shrink-0"
            >
              {t.search_btn}
            </button>
            {search && (
              <Link
                href="/articles"
                className="flex items-center px-3 py-2.5 border border-border rounded-xl text-ink-3 text-sm hover:border-ink-3 transition-colors font-serif shrink-0"
              >
                ✕
              </Link>
            )}
          </form>
        </div>

        {/* ── Veterinary section banner ── */}
        {!search && (() => {
          const vetCount = categories.find(c => c.category === "veterinary")?.count ?? 0;
          if (vetCount === 0) return null;
          const VET_LABEL: Record<string, string> = {
            en: "Veterinary Medicine",
            ru: "Ветеринарная медицина",
            de: "Veterinärmedizin",
            fr: "Médecine vétérinaire",
            es: "Medicina Veterinaria",
            tr: "Veteriner Hekimlik",
            ar: "الطب البيطري",
          };
          const VET_DESC: Record<string, string> = {
            en: "Evidence-based articles on canine, feline, equine and exotic animal diseases — covering diagnosis, treatment protocols, pharmacology and clinical guidelines.",
            ru: "Доказательные статьи по болезням собак, кошек, лошадей и экзотических животных — диагностика, протоколы лечения, фармакология.",
            de: "Evidenzbasierte Artikel zu Erkrankungen bei Hunden, Katzen, Pferden und Exoten — Diagnostik, Therapieprotokolle und klinische Leitlinien.",
            fr: "Articles fondés sur des preuves sur les maladies canines, félines, équines et exotiques — diagnostic, protocoles de traitement et pharmacologie.",
            es: "Artículos basados en evidencia sobre enfermedades caninas, felinas, equinas y animales exóticos — diagnóstico, protocolos de tratamiento y farmacología.",
            tr: "Köpek, kedi, at ve egzotik hayvan hastalıklarına dair kanıta dayalı makaleler — tanı, tedavi protokolleri ve farmakoloji.",
            ar: "مقالات مبنية على الأدلة حول أمراض الكلاب والقطط والخيول والحيوانات الغريبة — التشخيص وبروتوكولات العلاج والصيدلة.",
          };
          const VET_CTA: Record<string, string> = {
            en: "Browse veterinary articles",
            ru: "Перейти к ветеринарным статьям",
            de: "Veterinärmedizinische Artikel",
            fr: "Voir les articles vétérinaires",
            es: "Ver artículos veterinarios",
            tr: "Veteriner makalelerine göz at",
            ar: "تصفح المقالات البيطرية",
          };
          const label = VET_LABEL[locale] ?? VET_LABEL.en;
          const desc  = VET_DESC[locale]  ?? VET_DESC.en;
          const cta   = VET_CTA[locale]   ?? VET_CTA.en;
          const href  = locale && locale !== "en"
            ? `/${locale}/articles/category/veterinary`
            : "/articles/category/veterinary";
          return (
            <section className="mb-10">
              <Link
                href={href}
                className="group flex items-start sm:items-center gap-5 p-6 bg-surface border border-border rounded-2xl hover:border-ink hover:shadow-md transition-all"
              >
                <div className="w-14 h-14 shrink-0 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 group-hover:bg-emerald-100 transition-colors">
                  <PawPrint size={26} strokeWidth={1.75} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="font-syne font-bold text-lg text-ink">{label}</span>
                    <span className="text-xs font-syne font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full px-2.5 py-0.5">
                      {t.n_articles.replace("{n}", String(vetCount))}
                    </span>
                  </div>
                  <p className="text-ink-2 font-serif text-sm leading-relaxed line-clamp-2">{desc}</p>
                </div>
                <span className="shrink-0 hidden sm:flex items-center gap-1.5 font-syne font-semibold text-sm text-ink-2 group-hover:text-ink transition-colors whitespace-nowrap">
                  {cta}
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </span>
              </Link>
            </section>
          );
        })()}

        {/* Category grid */}
        {!search && categories.length > 0 && (
          <section className="mb-12">
            <h2 className="font-syne font-bold text-sm text-ink-3 uppercase tracking-wider mb-4">
              {t.browse_by_cat}
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {categories.map(({ category, count }) => (
                <Link
                  key={category}
                  href={`/articles/category/${category}`}
                  className="flex flex-col items-center gap-1 p-4 bg-surface border border-border rounded-xl hover:border-ink hover:shadow-sm transition-all text-center"
                >
                  <div className="w-10 h-10 rounded-xl bg-bg flex items-center justify-center text-ink-3 group-hover:text-ink transition-colors">
                    <CategoryIcon category={category} size={20} strokeWidth={1.75} />
                  </div>
                  <span className="font-syne font-semibold text-xs text-ink">
                    {getCategoryLabel(category, locale)}
                  </span>
                  <span className="text-ink-3 text-[10px] font-serif">
                    {t.n_articles.replace("{n}", String(count))}
                  </span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Article grid */}
        {articles.length > 0 ? (
          <section>
            <h2 className="font-syne font-bold text-sm text-ink-3 uppercase tracking-wider mb-4">
              {search ? (
                <>
                  {t.results_for.replace("{q}", search)}
                  <Link
                    href="/articles"
                    className="ml-3 text-ink-2 font-normal normal-case text-xs hover:text-ink underline"
                  >
                    {t.clear}
                  </Link>
                </>
              ) : t.latest}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {articles.map((a) => (
                <ArticleCard key={a.id} article={a} locale={locale} t={t} />
              ))}
            </div>
          </section>
        ) : (
          <div className="text-center py-20 text-ink-3 font-serif">{t.no_results}</div>
        )}
      </main>

      {/* Footer CTA */}
      <footer className="border-t border-border mt-20 py-12">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <div className="font-syne font-extrabold text-xl text-ink mb-1">MedMind AI</div>
            <p className="text-ink-3 font-serif text-sm">{t.footer_tagline}</p>
          </div>
          <ArticlesFooterCTA startFreeLabel={t.start_free} viewPricingLabel={t.view_pricing} />
        </div>
      </footer>
    </div>
  );
}

function ArticleCard({
  article,
  locale,
  t,
}: {
  article: Article;
  locale: string;
  t: ReturnType<typeof getArticlesT>;
}) {
  const href =
    locale && locale !== "en"
      ? `/${locale}/articles/${article.slug}`
      : `/articles/${article.slug}`;

  const dateLocale = locale === "ar" ? "ar-SA" : locale === "tr" ? "tr-TR" :
    locale === "ru" ? "ru-RU" : locale === "de" ? "de-DE" :
    locale === "fr" ? "fr-FR" : locale === "es" ? "es-ES" : "en-US";

  return (
    <Link
      href={href}
      className="group flex flex-col bg-surface border border-border rounded-xl overflow-hidden hover:border-ink hover:shadow-md transition-all"
    >
      {article.cover_image ? (
        <div className="relative h-44 overflow-hidden bg-surface-2">
          <img
            src={article.cover_image}
            alt={article.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
          <div className="absolute top-2 left-2">
            <span className="text-xs font-syne font-semibold bg-bg/90 backdrop-blur-sm rounded-full px-2 py-0.5 text-ink-2 flex items-center gap-1">
              <CategoryIcon category={article.category} size={11} strokeWidth={2} />
              <span>{getCategoryLabel(article.category, locale)}</span>
            </span>
          </div>
        </div>
      ) : null}

      <div className="flex flex-col flex-1 p-5">
        {!article.cover_image && (
          <div className="flex items-center gap-2 mb-3">
            <span className="text-ink-3">
              <CategoryIcon category={article.category} size={14} strokeWidth={1.75} />
            </span>
            <span className="text-[11px] font-syne font-semibold text-ink-3 uppercase tracking-wider">
              {getCategoryLabel(article.category, locale)}
            </span>
            <span className="ml-auto">
              <ReadBadge slug={article.slug} />
            </span>
          </div>
        )}
        {article.cover_image && (
          <div className="flex justify-end mb-2">
            <ReadBadge slug={article.slug} />
          </div>
        )}
        <h3 className="font-syne font-bold text-base text-ink mb-2 group-hover:text-accent transition-colors line-clamp-2">
          {article.title}
        </h3>
        <p className="text-ink-2 font-serif text-sm leading-relaxed flex-1 line-clamp-3">
          {article.excerpt}
        </p>
        <div className="flex items-center gap-3 mt-4 pt-3 border-t border-border">
          <span className="text-ink-3 text-xs font-serif">
            {t.read_time.replace("{n}", String(article.reading_time_minutes))}
          </span>
          {article.published_at && (
            <span className="text-ink-3 text-xs font-serif ml-auto">
              {new Date(article.published_at).toLocaleDateString(dateLocale, {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
