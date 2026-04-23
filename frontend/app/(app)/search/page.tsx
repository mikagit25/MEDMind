"use client";
import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, drugsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

type FilterType = "all" | "module" | "lesson" | "drug";

interface SearchResult {
  id: string;
  type: "module" | "lesson" | "drug";
  title: string;
  module_id?: string;   // for lessons
  subtitle?: string;    // drug category / module code
}

const TYPE_ICON: Record<string, string> = {
  module: "📚",
  lesson: "📖",
  drug: "💊",
};

const TYPE_LABEL: Record<string, string> = {
  module: "Module",
  lesson: "Lesson",
  drug: "Drug",
};

function SearchInner() {
  const t = useT();
  const searchParams = useSearchParams();
  const router = useRouter();
  const q = searchParams.get("q") ?? "";

  const [query, setQuery] = useState(q);
  const [filter, setFilter] = useState<FilterType>("all");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = useCallback(async (term: string) => {
    if (!term.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const [contentRes, drugRes] = await Promise.all([
        api.get("/search", { params: { q: term, limit: 30 } }).then(r => r.data).catch(() => ({})),
        drugsApi.search(term).catch(() => []),
      ]);

      const flat: SearchResult[] = [
        ...(contentRes.modules ?? []).map((m: any) => ({
          id: m.id,
          type: "module" as const,
          title: m.title,
          subtitle: m.module_code ?? m.specialty ?? "",
        })),
        ...(contentRes.lessons ?? []).map((l: any) => ({
          id: l.id,
          type: "lesson" as const,
          title: l.title,
          module_id: l.module_id,
          subtitle: l.module_title ?? "",
        })),
        ...(Array.isArray(drugRes) ? drugRes : drugRes?.drugs ?? []).map((d: any) => ({
          id: d.id,
          type: "drug" as const,
          title: d.name ?? d.generic_name ?? d.title,
          subtitle: d.drug_class ?? d.category ?? "",
        })),
      ];
      setResults(flat);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (q) {
      setQuery(q);
      doSearch(q);
    }
  }, [q, doSearch]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  const typeHref = (r: SearchResult) => {
    if (r.type === "module") return `/modules/${r.id}`;
    if (r.type === "lesson") return `/modules/${r.module_id ?? ""}`;
    if (r.type === "drug") return `/drugs?highlight=${r.id}`;
    return "/modules";
  };

  const filtered = filter === "all" ? results : results.filter((r) => r.type === filter);

  const counts: Record<FilterType, number> = {
    all: results.length,
    module: results.filter((r) => r.type === "module").length,
    lesson: results.filter((r) => r.type === "lesson").length,
    drug: results.filter((r) => r.type === "drug").length,
  };

  return (
    <div className="flex-1 overflow-y-auto bg-bg p-6">
      <div className="max-w-2xl mx-auto">
        {/* Search input */}
        <form onSubmit={handleSubmit} className="mb-6">
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-3">🔍</span>
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("search.placeholder")}
              className="w-full bg-surface border border-border rounded-xl pl-11 pr-4 py-3 text-ink focus:outline-none focus:border-ink transition-colors font-serif text-base"
            />
            {query && (
              <button
                type="button"
                onClick={() => { setQuery(""); setResults([]); setSearched(false); }}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink text-sm"
              >
                ✕
              </button>
            )}
          </div>
        </form>

        {/* Filter tabs — only show after search */}
        {searched && !loading && results.length > 0 && (
          <div className="flex gap-1.5 mb-5">
            {(["all", "module", "lesson", "drug"] as FilterType[]).map((t) => (
              <button
                key={t}
                onClick={() => setFilter(t)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-syne text-xs font-semibold transition-colors ${
                  filter === t
                    ? "bg-ink text-white"
                    : "bg-surface border border-border text-ink-3 hover:border-ink-3"
                }`}
              >
                {t === "all" ? "All" : TYPE_ICON[t]}
                {t !== "all" && TYPE_LABEL[t]}
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                  filter === t ? "bg-white/20 text-white" : "bg-border text-ink-3"
                }`}>
                  {counts[t]}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-surface border border-border rounded-lg p-4 animate-pulse">
                <div className="h-4 bg-bg-2 rounded w-2/3 mb-2" />
                <div className="h-3 bg-bg-2 rounded w-1/3" />
              </div>
            ))}
          </div>
        )}

        {/* Results */}
        {!loading && searched && (
          <>
            <div className="text-sm text-ink-3 font-syne mb-4">
              {filtered.length === 0
                ? `No ${filter === "all" ? "" : filter + " "}results for "${q}"`
                : `${filtered.length} result${filtered.length !== 1 ? "s" : ""}${filter !== "all" ? ` (${filter}s)` : ""} for "${q}"`}
            </div>
            <div className="space-y-2">
              {filtered.map((r) => (
                <Link
                  key={`${r.type}-${r.id}`}
                  href={typeHref(r)}
                  className="block bg-surface border border-border rounded-lg p-4 hover:border-ink-3 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg mt-0.5 shrink-0">{TYPE_ICON[r.type]}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-syne font-semibold text-ink text-sm mb-0.5 truncate">
                        {r.title}
                      </div>
                      <div className="text-xs text-ink-3 flex items-center gap-1.5">
                        <span className="capitalize bg-bg-2 px-1.5 py-0.5 rounded font-syne font-semibold">
                          {TYPE_LABEL[r.type]}
                        </span>
                        {r.subtitle && (
                          <>
                            <span className="text-border">·</span>
                            <span className="truncate">{r.subtitle}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}

        {/* Empty state */}
        {!loading && !searched && (
          <div className="text-center py-16 text-ink-3">
            <div className="text-5xl mb-4">🔍</div>
            <div className="font-syne font-semibold text-base text-ink">{t("search.title")}</div>
            <div className="font-serif text-sm mt-2 text-ink-3">
              {t("search.placeholder")}
            </div>
            <div className="flex justify-center gap-3 mt-6">
              {[
                { icon: "📚", labelKey: "nav.items.modules", href: "/modules" },
                { icon: "💊", labelKey: "nav.items.drugs", href: "/drugs" },
                { icon: "🩺", labelKey: "cases.title", href: "/cases" },
              ].map((l) => (
                <Link key={l.href} href={l.href}
                  className="flex items-center gap-2 bg-surface border border-border rounded-lg px-4 py-2 font-syne text-sm text-ink hover:border-ink-3 transition-colors">
                  <span>{l.icon}</span>
                  {t(l.labelKey as Parameters<typeof t>[0])}
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex items-center justify-center">
        <span className="font-serif text-ink-3 text-sm animate-pulse">Loading…</span>
      </div>
    }>
      <SearchInner />
    </Suspense>
  );
}
