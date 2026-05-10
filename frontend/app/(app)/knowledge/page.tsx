"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useT, useI18n } from "@/lib/i18n";
import { CATEGORY_ICONS, CATEGORY_KEY } from "@/lib/categories";

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

type CategoryStat = { category: string; count: number };

export default function ArticlesPage() {
  const t = useT();
  const { locale } = useI18n();
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<CategoryStat[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const LIMIT = 20;

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 400);
    return () => clearTimeout(t);
  }, [search]);

  // Load categories once
  useEffect(() => {
    api.get("/articles/categories").then(r => setCategories(r.data ?? [])).catch(() => {});
  }, []);

  // Load articles when filters or locale change
  const loadArticles = useCallback(async (cat: string, q: string, pg: number) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { limit: LIMIT, page: pg };
      if (cat) params.category = cat;
      if (q) params.search = q;
      if (locale && locale !== "en") params.locale = locale;
      const r = await api.get("/articles", { params });
      setArticles(r.data.articles ?? []);
      setTotal(r.data.total ?? 0);
    } catch {
      setArticles([]);
    } finally {
      setLoading(false);
    }
  }, [locale]); // locale in deps — new closure when language changes

  useEffect(() => {
    setPage(1);
    loadArticles(activeCategory, debouncedSearch, 1);
  }, [activeCategory, debouncedSearch, loadArticles, locale]);

  useEffect(() => {
    if (page > 1) loadArticles(activeCategory, debouncedSearch, page);
  }, [page, activeCategory, debouncedSearch, loadArticles]);

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-3 sm:px-6 py-4 sm:py-8">
        {/* Header */}
        <div className="mb-4 sm:mb-6 flex items-center justify-between gap-3">
          <div>
            <h1 className="font-syne font-black text-xl sm:text-2xl text-ink">{t("articles.title")}</h1>
            <p className="font-serif text-xs sm:text-sm text-ink-3 mt-0.5">{t("articles.subtitle", { count: String(total), cats: String(categories.length) })}</p>
          </div>
          <a
            href="/articles"
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1"
          >
            🌐 <span className="hidden sm:inline">{t("articles.public_view")}</span>
          </a>
        </div>

        <div className="flex gap-6">
          {/* Sidebar — Categories: hidden on mobile */}
          <aside className="hidden md:block w-52 shrink-0">
            <div className="sticky top-4">
              <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-3">{t("articles.categories")}</div>
              <button
                onClick={() => { setActiveCategory(""); setPage(1); }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm font-serif mb-1 transition-colors ${
                  activeCategory === "" ? "bg-ink text-white font-semibold" : "hover:bg-surface text-ink-2"
                }`}
              >
                {t("articles.all")}
                <span className="ml-auto float-right text-xs opacity-60">{total}</span>
              </button>
              {categories.map(cat => (
                <button
                  key={cat.category}
                  onClick={() => { setActiveCategory(cat.category); setPage(1); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-serif mb-1 transition-colors ${
                    activeCategory === cat.category ? "bg-ink text-white font-semibold" : "hover:bg-surface text-ink-2"
                  }`}
                >
                  <span className="mr-1.5">{CATEGORY_ICONS[cat.category] ?? "📄"}</span>
                  {CATEGORY_KEY[cat.category] ? t(`articles.${CATEGORY_KEY[cat.category]}` as any) : cat.category}
                  <span className="ml-auto float-right text-xs opacity-60">{cat.count}</span>
                </button>
              ))}
            </div>
          </aside>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Search */}
            <div className="mb-3">
              <input
                type="search"
                placeholder={t("articles.search_placeholder")}
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1); }}
                className="w-full input-field text-sm"
              />
            </div>

            {/* Mobile category pills (hidden on md+) */}
            <div className="md:hidden flex gap-2 mb-4 overflow-x-auto pb-1 -mx-1 px-1">
              <button
                onClick={() => { setActiveCategory(""); setPage(1); }}
                className={`shrink-0 px-3 py-1.5 rounded-full font-syne text-xs border transition-colors ${activeCategory === "" ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}
              >
                All ({total})
              </button>
              {categories.map(cat => (
                <button
                  key={cat.category}
                  onClick={() => { setActiveCategory(cat.category); setPage(1); }}
                  className={`shrink-0 px-3 py-1.5 rounded-full font-syne text-xs border transition-colors ${activeCategory === cat.category ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}
                >
                  {CATEGORY_ICONS[cat.category] ?? "📄"} {CATEGORY_KEY[cat.category] ? t(`articles.${CATEGORY_KEY[cat.category]}` as any) : cat.category}
                </button>
              ))}
            </div>

            {/* Articles grid */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="card p-4 animate-pulse">
                    <div className="h-3 bg-surface rounded w-1/4 mb-3" />
                    <div className="h-4 bg-surface rounded w-3/4 mb-2" />
                    <div className="h-3 bg-surface rounded w-full mb-1" />
                    <div className="h-3 bg-surface rounded w-2/3" />
                  </div>
                ))}
              </div>
            ) : articles.length === 0 ? (
              <div className="text-center py-16">
                <div className="text-4xl mb-3">📭</div>
                <div className="font-syne font-semibold text-ink mb-1">{t("articles.no_results")}</div>
                <div className="font-serif text-sm text-ink-3">{t("articles.no_results_hint")}</div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  {articles.map(article => (
                    <Link
                      key={article.id}
                      href={locale && locale !== "en" ? `/articles/${article.slug}?lang=${locale}` : `/articles/${article.slug}`}
                      target="_blank"
                      rel="noopener"
                      className="card p-4 hover:shadow-md transition-shadow group block"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm">{CATEGORY_ICONS[article.category] ?? "📄"}</span>
                        <span className="font-syne font-semibold text-[10px] text-ink-3 uppercase tracking-wide">
                          {CATEGORY_KEY[article.category] ? t(`articles.${CATEGORY_KEY[article.category]}` as any) : article.category}
                        </span>
                        {article.reading_time_minutes > 0 && (
                          <span className="ml-auto font-serif text-[10px] text-ink-3">
                            {t("articles.read_time", { n: String(article.reading_time_minutes) })}
                          </span>
                        )}
                      </div>
                      <h3 className="font-syne font-bold text-sm text-ink mb-1.5 group-hover:underline line-clamp-2">
                        {article.title}
                      </h3>
                      {article.excerpt && (
                        <p className="font-serif text-xs text-ink-3 line-clamp-2">{article.excerpt}</p>
                      )}
                      {article.keywords?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {article.keywords.slice(0, 3).map(kw => (
                            <span key={kw} className="bg-surface text-ink-3 font-serif text-[10px] px-1.5 py-0.5 rounded">
                              {kw}
                            </span>
                          ))}
                        </div>
                      )}
                    </Link>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="btn-secondary text-xs px-3 py-1.5 disabled:opacity-40"
                    >
                      {t("articles.prev")}
                    </button>
                    <span className="font-serif text-sm text-ink-3">
                      {t("articles.page_of", { page: String(page), total: String(totalPages) })}
                    </span>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="btn-secondary text-xs px-3 py-1.5 disabled:opacity-40"
                    >
                      {t("articles.next")}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
