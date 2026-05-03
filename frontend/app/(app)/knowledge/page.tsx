"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";

const CATEGORY_LABELS: Record<string, string> = {
  diseases: "Diseases & Conditions",
  drugs: "Drugs & Medications",
  procedures: "Procedures & Techniques",
  symptoms: "Symptoms & Signs",
  diagnostics: "Diagnostics & Lab Tests",
  emergency: "Emergency Medicine",
  nutrition: "Nutrition & Prevention",
  pediatrics: "Pediatrics",
  cardiology: "Cardiology",
  neurology: "Neurology",
  oncology: "Oncology",
  surgery: "Surgery",
  psychiatry: "Psychiatry",
  endocrinology: "Endocrinology",
  "infectious-diseases": "Infectious Diseases",
  veterinary: "Veterinary Medicine",
};

const CATEGORY_ICONS: Record<string, string> = {
  diseases: "🫀",
  drugs: "💊",
  procedures: "🔬",
  symptoms: "🩺",
  diagnostics: "🧪",
  emergency: "🚑",
  nutrition: "🥗",
  pediatrics: "👶",
  cardiology: "❤️",
  neurology: "🧠",
  oncology: "🎗️",
  surgery: "✂️",
  psychiatry: "🧘",
  endocrinology: "⚗️",
  "infectious-diseases": "🦠",
  veterinary: "🐾",
};

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

  // Load articles when filters change
  const loadArticles = useCallback(async (cat: string, q: string, pg: number) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { limit: LIMIT, page: pg };
      if (cat) params.category = cat;
      if (q) params.search = q;
      const r = await api.get("/articles", { params });
      setArticles(r.data.articles ?? []);
      setTotal(r.data.total ?? 0);
    } catch {
      setArticles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setPage(1);
    loadArticles(activeCategory, debouncedSearch, 1);
  }, [activeCategory, debouncedSearch, loadArticles]);

  useEffect(() => {
    if (page > 1) loadArticles(activeCategory, debouncedSearch, page);
  }, [page, activeCategory, debouncedSearch, loadArticles]);

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="font-syne font-black text-2xl text-ink">Medical Articles</h1>
            <p className="font-serif text-sm text-ink-3 mt-1">{total} evidence-based articles across {categories.length} categories</p>
          </div>
          <a
            href="/articles"
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
          >
            🌐 Public view ↗
          </a>
        </div>

        <div className="flex gap-6">
          {/* Sidebar — Categories */}
          <aside className="w-52 shrink-0">
            <div className="sticky top-4">
              <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-3">Categories</div>
              <button
                onClick={() => { setActiveCategory(""); setPage(1); }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm font-serif mb-1 transition-colors ${
                  activeCategory === "" ? "bg-ink text-white font-semibold" : "hover:bg-surface text-ink-2"
                }`}
              >
                All Articles
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
                  {CATEGORY_LABELS[cat.category] ?? cat.category}
                  <span className="ml-auto float-right text-xs opacity-60">{cat.count}</span>
                </button>
              ))}
            </div>
          </aside>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Search */}
            <div className="mb-5">
              <input
                type="search"
                placeholder="Search articles..."
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1); }}
                className="w-full input-field text-sm"
              />
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
                <div className="font-syne font-semibold text-ink mb-1">No articles found</div>
                <div className="font-serif text-sm text-ink-3">Try a different search or category</div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  {articles.map(article => (
                    <Link
                      key={article.id}
                      href={`/articles/${article.slug}`}
                      target="_blank"
                      rel="noopener"
                      className="card p-4 hover:shadow-md transition-shadow group block"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm">{CATEGORY_ICONS[article.category] ?? "📄"}</span>
                        <span className="font-syne font-semibold text-[10px] text-ink-3 uppercase tracking-wide">
                          {CATEGORY_LABELS[article.category] ?? article.category}
                        </span>
                        {article.reading_time_minutes > 0 && (
                          <span className="ml-auto font-serif text-[10px] text-ink-3">
                            {article.reading_time_minutes} min read
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
                      ← Prev
                    </button>
                    <span className="font-serif text-sm text-ink-3">
                      Page {page} of {totalPages}
                    </span>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="btn-secondary text-xs px-3 py-1.5 disabled:opacity-40"
                    >
                      Next →
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
