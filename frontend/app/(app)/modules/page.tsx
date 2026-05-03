"use client";

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { contentApi, bookmarksApi, api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

function ModulesInner() {
  const searchParams = useSearchParams();
  const { user } = useAuthStore();
  const t = useT();
  const [specialties, setSpecialties] = useState<any[]>([]);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [selectedSpecialty, setSelectedSpecialty] = useState<string | null>(
    searchParams.get("specialty")
  );
  const [modules, setModules] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    contentApi.getSpecialties().then((r) => {
      setSpecialties(r.data ?? []);
    });
    // Load existing module bookmarks
    bookmarksApi.list("module").then((r) => {
      const ids = new Set<string>((r.data ?? []).map((b: any) => String(b.content_id)));
      setBookmarkedIds(ids);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedSpecialty) return;
    setLoading(true);
    contentApi
      .getModules(selectedSpecialty)
      .then((r) => setModules(r.data ?? []))
      .catch(() => setModules([]))
      .finally(() => setLoading(false));
  }, [selectedSpecialty]);

  const toggleBookmark = useCallback(async (modId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const wasBookmarked = bookmarkedIds.has(modId);
    // Optimistic update
    setBookmarkedIds((prev) => {
      const next = new Set(prev);
      if (wasBookmarked) next.delete(modId); else next.add(modId);
      return next;
    });
    try {
      if (wasBookmarked) {
        await bookmarksApi.remove("module", modId);
      } else {
        await bookmarksApi.add("module", modId);
      }
    } catch {
      // Rollback on error
      setBookmarkedIds((prev) => {
        const next = new Set(prev);
        if (wasBookmarked) next.add(modId); else next.delete(modId);
        return next;
      });
    }
  }, [bookmarkedIds]);

  // Debounced search across all modules
  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!searchQ.trim()) { setSearchResults([]); return; }
    searchTimer.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await api.get("/search", { params: { q: searchQ.trim(), limit: 30 } });
        setSearchResults(res.data?.modules ?? []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }, [searchQ]);

  const isFree = user?.subscription_tier === "free";
  const isSearching = searchQ.trim().length >= 2;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: Specialty list */}
      <div className="w-56 flex-shrink-0 border-r border-border bg-surface overflow-y-auto">
        <div className="p-3 border-b border-border">
          <span className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider">
            {t("modules.filter_specialty")}
          </span>
        </div>
        {specialties.map((sp) => (
          <button
            key={sp.id}
            onClick={() => setSelectedSpecialty(String(sp.id))}
            className={`nav-item w-full ${
              selectedSpecialty === String(sp.id) ? "active" : "text-ink-2 bg-transparent hover:bg-bg-2 hover:text-ink"
            }`}
          >
            <span className="text-sm">{sp.name}</span>
            <span className="ml-auto text-xs opacity-60">{sp.module_count ?? 0}</span>
          </button>
        ))}
      </div>

      {/* Right: Module list */}
      <div className="flex-1 overflow-y-auto p-5">
        {/* Search bar */}
        <div className="relative mb-5">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none">🔍</span>
          <input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder={t("modules.search_placeholder")}
            className="w-full bg-surface border border-border rounded-xl pl-9 pr-9 py-2.5 text-ink text-sm font-serif focus:outline-none focus:border-ink transition-colors"
          />
          {searchQ && (
            <button
              onClick={() => setSearchQ("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink text-sm"
            >
              ✕
            </button>
          )}
        </div>

        {isSearching ? (
          searchLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <div key={i} className="card h-20 animate-pulse bg-bg-2" />)}
            </div>
          ) : searchResults.length === 0 ? (
            <div className="text-center py-16 text-ink-3 font-serif text-sm">No modules found for &ldquo;{searchQ}&rdquo;</div>
          ) : (
            <div className="space-y-2.5">
              <p className="font-syne text-xs text-ink-3 mb-3">{searchResults.length} result{searchResults.length !== 1 ? "s" : ""} for &ldquo;{searchQ}&rdquo;</p>
              {searchResults.map((mod: any) => {
                const locked = isFree && !mod.is_fundamental;
                return (
                  <div key={mod.id} className={`card transition-all ${locked ? "opacity-60" : "hover:border-ink-3 hover:shadow-sm"}`}>
                    <div className="flex items-start gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-syne font-bold text-sm text-ink">{mod.title}</h3>
                          {mod.is_fundamental && <span className="badge bg-blue-light text-blue text-[10px]">Free</span>}
                          {locked && <span className="badge bg-amber-light text-amber text-[10px]">🔒 Pro</span>}
                        </div>
                        {mod.description && <p className="font-serif text-ink-3 text-xs line-clamp-2">{mod.description}</p>}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {!locked ? (
                          <Link href={`/modules/${mod.id}`} className="btn-primary text-xs px-3 py-1.5">Open →</Link>
                        ) : (
                          <Link href="/settings?tab=billing" className="btn-secondary text-xs px-3 py-1.5">Upgrade</Link>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )
        ) : !selectedSpecialty ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-4xl mb-3">📚</div>
            <h2 className="font-syne font-bold text-xl text-ink mb-1">{t("modules.filter_specialty")}</h2>
            <p className="font-serif text-ink-3 text-sm">
              {t("modules.all_specialties")}
            </p>
          </div>
        ) : loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="card h-20 animate-pulse bg-bg-2" />
            ))}
          </div>
        ) : modules.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <p className="font-serif text-ink-3 text-sm">{t("modules.no_modules")}</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {modules.map((mod: any) => {
              const locked = isFree && !mod.is_fundamental;
              return (
                <div
                  key={mod.id}
                  className={`card transition-all ${locked ? "opacity-60" : "hover:border-ink-3 hover:shadow-sm"}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-syne font-bold text-sm text-ink">{mod.title}</h3>
                        {mod.is_fundamental && (
                          <span className="badge bg-blue-light text-blue text-[10px]">Free</span>
                        )}
                        {locked && (
                          <span className="badge bg-amber-light text-amber text-[10px]">🔒 Pro</span>
                        )}
                      </div>
                      {mod.description && (
                        <p className="font-serif text-ink-3 text-xs line-clamp-2">{mod.description}</p>
                      )}
                      <div className="flex gap-3 mt-2 text-xs font-syne text-ink-3">
                        {mod.lesson_count > 0 && <span>📖 {mod.lesson_count} lessons</span>}
                        {mod.flashcard_count > 0 && <span>🃏 {mod.flashcard_count} cards</span>}
                        {mod.mcq_count > 0 && <span>❓ {mod.mcq_count} MCQs</span>}
                      </div>
                    </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={(e) => toggleBookmark(String(mod.id), e)}
                      title={bookmarkedIds.has(String(mod.id)) ? "Remove bookmark" : "Bookmark"}
                      className={`text-lg leading-none transition-transform hover:scale-110 ${
                        bookmarkedIds.has(String(mod.id)) ? "opacity-100" : "opacity-30 hover:opacity-70"
                      }`}
                    >
                      🔖
                    </button>
                    {!locked && (
                      <Link
                        href={`/modules/${mod.id}`}
                        className="btn-primary text-xs px-3 py-1.5"
                      >
                        Open →
                      </Link>
                    )}
                    {locked && (
                      <Link
                        href="/settings?tab=billing"
                        className="btn-secondary text-xs px-3 py-1.5"
                      >
                        Upgrade
                      </Link>
                    )}
                  </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ModulesPageFallback() {
  const t = useT();
  return (
    <div className="flex-1 flex items-center justify-center">
      <span className="font-serif text-ink-3 text-sm animate-pulse">{t("common.loading")}</span>
    </div>
  );
}

export default function ModulesPage() {
  return (
    <Suspense fallback={<ModulesPageFallback />}>
      <ModulesInner />
    </Suspense>
  );
}
