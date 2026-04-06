"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { contentApi, bookmarksApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

function ModulesInner() {
  const searchParams = useSearchParams();
  const { user } = useAuthStore();
  const [specialties, setSpecialties] = useState<any[]>([]);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [selectedSpecialty, setSelectedSpecialty] = useState<string | null>(
    searchParams.get("specialty")
  );
  const [modules, setModules] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

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

  const isFree = user?.subscription_tier === "free";

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: Specialty list */}
      <div className="w-56 flex-shrink-0 border-r border-border bg-surface overflow-y-auto">
        <div className="p-3 border-b border-border">
          <span className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider">
            Specialties
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
        {!selectedSpecialty ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-4xl mb-3">📚</div>
            <h2 className="font-syne font-bold text-xl text-ink mb-1">Select a specialty</h2>
            <p className="font-serif text-ink-3 text-sm">
              Choose a specialty from the left to browse modules
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
            <p className="font-serif text-ink-3 text-sm">No modules found</p>
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

export default function ModulesPage() {
  return (
    <Suspense fallback={<div className="flex-1 flex items-center justify-center"><span className="font-serif text-ink-3 text-sm animate-pulse">Loading…</span></div>}>
      <ModulesInner />
    </Suspense>
  );
}
