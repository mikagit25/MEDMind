import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { getCategoryLabel, CATEGORY_DESCRIPTIONS } from "@/lib/categories";
import { CategoryIcon } from "@/lib/medical-icons";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { getArticlesT } from "@/lib/articles-i18n";
import { PawPrint, Dog, Cat, Rabbit, Bird, Bug } from "lucide-react";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SUPPORTED = ["en", "ru", "ar", "tr", "de", "fr", "es"];
const PAGE_SIZE = 24;

export const dynamic = "force-dynamic";

// ── Veterinary species topics ────────────────────────────────────────────────

type VetSpecies = {
  key: string;
  icon: React.ElementType;
  color: string;        // Tailwind bg/text classes
  labels: Record<string, string>;
  descs: Record<string, string>;
};

const VET_SPECIES: VetSpecies[] = [
  {
    key: "dog",
    icon: Dog,
    color: "bg-amber-50 border-amber-100 text-amber-700 hover:bg-amber-100",
    labels: { en: "Dogs", ru: "Собаки", de: "Hunde", fr: "Chiens", es: "Perros", tr: "Köpekler", ar: "الكلاب" },
    descs:  { en: "Canine diseases & treatment", ru: "Болезни и лечение собак", de: "Hundekrankheiten", fr: "Maladies canines", es: "Enfermedades caninas", tr: "Köpek hastalıkları", ar: "أمراض الكلاب" },
  },
  {
    key: "cat",
    icon: Cat,
    color: "bg-violet-50 border-violet-100 text-violet-700 hover:bg-violet-100",
    labels: { en: "Cats", ru: "Кошки", de: "Katzen", fr: "Chats", es: "Gatos", tr: "Kediler", ar: "القطط" },
    descs:  { en: "Feline diseases & treatment", ru: "Болезни и лечение кошек", de: "Katzenkrankheiten", fr: "Maladies félines", es: "Enfermedades felinas", tr: "Kedi hastalıkları", ar: "أمراض القطط" },
  },
  {
    key: "horse",
    icon: PawPrint,
    color: "bg-brown-50 border-stone-200 text-stone-700 hover:bg-stone-100",
    labels: { en: "Horses", ru: "Лошади", de: "Pferde", fr: "Chevaux", es: "Caballos", tr: "Atlar", ar: "الخيول" },
    descs:  { en: "Equine medicine & surgery", ru: "Болезни и хирургия лошадей", de: "Pferdemedizin", fr: "Médecine équine", es: "Medicina equina", tr: "At sağlığı", ar: "طب الخيول" },
  },
  {
    key: "rabbit",
    icon: Rabbit,
    color: "bg-pink-50 border-pink-100 text-pink-700 hover:bg-pink-100",
    labels: { en: "Rabbits", ru: "Кролики", de: "Kaninchen", fr: "Lapins", es: "Conejos", tr: "Tavşanlar", ar: "الأرانب" },
    descs:  { en: "Rabbit & small mammal care", ru: "Кролики и мелкие млекопитающие", de: "Kaninchenpflege", fr: "Soins lapins", es: "Cuidado de conejos", tr: "Tavşan bakımı", ar: "العناية بالأرانب" },
  },
  {
    key: "bird",
    icon: Bird,
    color: "bg-sky-50 border-sky-100 text-sky-700 hover:bg-sky-100",
    labels: { en: "Birds", ru: "Птицы", de: "Vögel", fr: "Oiseaux", es: "Aves", tr: "Kuşlar", ar: "الطيور" },
    descs:  { en: "Avian medicine & nutrition", ru: "Болезни и питание птиц", de: "Vogelmedizin", fr: "Médecine aviaire", es: "Medicina aviar", tr: "Kuş sağlığı", ar: "طب الطيور" },
  },
  {
    key: "reptile",
    icon: Bug,
    color: "bg-emerald-50 border-emerald-100 text-emerald-700 hover:bg-emerald-100",
    labels: { en: "Reptiles", ru: "Рептилии", de: "Reptilien", fr: "Reptiles", es: "Reptiles", tr: "Sürüngenler", ar: "الزواحف" },
    descs:  { en: "Reptile health & husbandry", ru: "Здоровье и содержание рептилий", de: "Reptiliengesundheit", fr: "Santé des reptiles", es: "Salud de reptiles", tr: "Sürüngen sağlığı", ar: "صحة الزواحف" },
  },
  {
    key: "cattle",
    icon: PawPrint,
    color: "bg-orange-50 border-orange-100 text-orange-700 hover:bg-orange-100",
    labels: { en: "Cattle", ru: "КРС", de: "Rinder", fr: "Bovins", es: "Bovinos", tr: "Sığırlar", ar: "الأبقار" },
    descs:  { en: "Bovine medicine & production", ru: "Болезни и продуктивность КРС", de: "Rindermedizin", fr: "Médecine bovine", es: "Medicina bovina", tr: "Sığır sağlığı", ar: "طب الأبقار" },
  },
];

// ── Types & fetchers ─────────────────────────────────────────────────────────

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

async function fetchCategory(
  cat: string,
  page = 1,
  locale = "en",
  search?: string,
): Promise<{ articles: Article[]; total: number } | null> {
  try {
    const params = new URLSearchParams({ page: String(page), limit: "24" });
    if (locale && locale !== "en") params.set("locale", locale);
    if (search) params.set("search", search);
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

async function fetchSpeciesCounts(locale: string): Promise<Record<string, number>> {
  const counts: Record<string, number> = {};
  await Promise.all(
    VET_SPECIES.map(async (sp) => {
      try {
        const params = new URLSearchParams({ limit: "1", search: sp.key });
        if (locale && locale !== "en") params.set("locale", locale);
        const res = await fetch(`${API_URL}/articles/category/veterinary?${params}`, {
          cache: "no-store",
        });
        if (res.ok) {
          const d = await res.json();
          counts[sp.key] = d.total ?? 0;
        }
      } catch { /* ignore */ }
    })
  );
  return counts;
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
  searchParams?: { page?: string; lang?: string; species?: string };
}) {
  const cookieLocale = cookies().get("medmind_locale")?.value;
  const rawLocale = searchParams?.lang || cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const t = getArticlesT(locale);

  const label = getCategoryLabel(params.cat, locale);
  if (!label || label === params.cat) notFound();

  const page       = Math.max(1, parseInt(searchParams?.page ?? "1", 10) || 1);
  const speciesKey = searchParams?.species ?? "";
  const isVet      = params.cat === "veterinary";

  const [result, speciesCounts] = await Promise.all([
    fetchCategory(params.cat, page, locale, speciesKey || undefined),
    isVet ? fetchSpeciesCounts(locale) : Promise.resolve({}),
  ]);
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
    const qs = new URLSearchParams();
    if (p > 1) qs.set("page", String(p));
    if (speciesKey) qs.set("species", speciesKey);
    const q = qs.toString();
    return q ? `${base}?${q}` : base;
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

        {/* ── Veterinary species filter ── */}
        {isVet && (
          <section className="mb-10">
            {(() => {
              const VET_SPECIES_HEADING: Record<string, string> = {
                en: "Browse by Species",
                ru: "По виду животного",
                de: "Nach Tierart",
                fr: "Par espèce",
                es: "Por especie",
                tr: "Türe göre",
                ar: "حسب النوع",
              };
              const basePath = locale !== "en"
                ? `/${locale}/articles/category/veterinary`
                : "/articles/category/veterinary";
              return (
                <>
                  <h2 className="font-syne font-bold text-sm text-ink-3 uppercase tracking-wider mb-4">
                    {VET_SPECIES_HEADING[locale] ?? VET_SPECIES_HEADING.en}
                  </h2>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-4">
                    {VET_SPECIES.map((sp) => {
                      const isActive = speciesKey === sp.key;
                      const count = speciesCounts[sp.key] ?? 0;
                      const href  = isActive ? basePath : `${basePath}?species=${sp.key}`;
                      const Icon  = sp.icon;
                      return (
                        <Link
                          key={sp.key}
                          href={href}
                          className={`flex flex-col items-center gap-1.5 p-3.5 border rounded-xl transition-all text-center ${
                            isActive
                              ? sp.color + " ring-2 ring-offset-1 ring-current"
                              : sp.color
                          }`}
                        >
                          <Icon size={22} strokeWidth={1.75} />
                          <span className="font-syne font-bold text-xs">
                            {sp.labels[locale] ?? sp.labels.en}
                          </span>
                          {count > 0 && (
                            <span className="text-[10px] font-serif opacity-70">
                              {count} {t.n_articles.replace("{n}", "").trim() || "articles"}
                            </span>
                          )}
                        </Link>
                      );
                    })}
                  </div>
                  {speciesKey && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-serif text-ink-3">
                        {VET_SPECIES.find(s => s.key === speciesKey)?.descs[locale] ?? ""}
                      </span>
                      <Link
                        href={basePath}
                        className="text-xs font-syne font-semibold text-ink-2 hover:text-ink border border-border rounded-full px-2.5 py-0.5 hover:border-ink-2 transition-colors"
                      >
                        ✕ {locale === "ru" ? "Все" : locale === "de" ? "Alle" : locale === "fr" ? "Tous" : locale === "es" ? "Todos" : locale === "ar" ? "الكل" : locale === "tr" ? "Tümü" : "All"}
                      </Link>
                    </div>
                  )}
                </>
              );
            })()}
          </section>
        )}

        {/* Articles */}
        {articles.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {articles.map((a) => {
              const href = locale !== "en" ? `/${locale}/articles/${a.slug}` : `/articles/${a.slug}`;
              return (
                <Link
                  key={a.id}
                  href={href}
                  className="group flex flex-col bg-surface border border-border rounded-xl overflow-hidden hover:border-ink hover:shadow-md transition-all"
                >
                  {a.cover_image && (
                    <div className="relative h-40 overflow-hidden bg-surface-2">
                      <img
                        src={a.cover_image}
                        alt={a.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    </div>
                  )}
                  <div className="flex flex-col flex-1 p-5">
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
                  </div>
                </Link>
              );
            })}
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
