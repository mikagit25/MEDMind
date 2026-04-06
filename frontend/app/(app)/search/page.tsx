"use client";
import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

interface SearchResult {
  id: string;
  type: "module" | "lesson";
  title: string;
  module_id?: string;   // for lessons — navigate to /modules/{module_id}
}

function SearchInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const q = searchParams.get("q") ?? "";
  const [query, setQuery] = useState(q);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = useCallback(async (term: string) => {
    if (!term.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await api.get("/search", { params: { q: term, limit: 30 } });
      // Backend returns {modules: [...], lessons: [...], total: N}
      const data = res.data ?? {};
      const flat: SearchResult[] = [
        ...(data.modules ?? []).map((m: any) => ({ id: m.id, type: "module" as const, title: m.title })),
        ...(data.lessons ?? []).map((l: any) => ({ id: l.id, type: "lesson" as const, title: l.title, module_id: l.module_id })),
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

  const typeIcon: Record<string, string> = {
    module: "📚",
    lesson: "📖",
  };

  const typeHref = (r: SearchResult) => {
    if (r.type === "module") return `/modules/${r.id}`;
    if (r.type === "lesson") return `/modules/${r.module_id ?? ""}`;
    return "/modules";
  };

  return (
    <div className="flex-1 overflow-y-auto bg-bg p-6">
      <div className="max-w-2xl mx-auto">
        {/* Search input */}
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-3">🔍</span>
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search modules, lessons, flashcards..."
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

        {/* Loading */}
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
              {results.length === 0
                ? `No results for "${q}"`
                : `${results.length} result${results.length !== 1 ? "s" : ""} for "${q}"`}
            </div>
            <div className="space-y-2">
              {results.map((r) => (
                <Link
                  key={`${r.type}-${r.id}`}
                  href={typeHref(r)}
                  className="block bg-surface border border-border rounded-lg p-4 hover:border-ink-3 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg mt-0.5">{typeIcon[r.type]}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-syne font-semibold text-ink text-sm mb-0.5">
                        {r.title}
                      </div>
                      <div className="text-xs text-ink-3 flex items-center gap-1.5">
                        <span className="capitalize bg-bg-2 px-1.5 py-0.5 rounded font-syne font-semibold">
                          {r.type}
                        </span>
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
            <div className="font-syne font-semibold text-base">Search across all content</div>
            <div className="text-sm mt-2">Modules, lessons, flashcards — all in one place</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="flex-1 flex items-center justify-center"><span className="font-serif text-ink-3 text-sm animate-pulse">Loading…</span></div>}>
      <SearchInner />
    </Suspense>
  );
}
