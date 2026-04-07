"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { bookmarksApi } from "@/lib/api";

type FilterType = "all" | "lesson" | "module" | "drug";

interface Bookmark {
  id: string;
  resource_type: string;
  resource_id: string;
  title: string | null;
  created_at: string;
}

const TYPE_ICONS: Record<string, string> = {
  lesson: "📖",
  module: "📚",
  drug:   "💊",
};

const TYPE_HREF: Record<string, (id: string) => string> = {
  lesson: (id) => `/lessons/${id}`,
  module: (id) => `/modules/${id}`,
  drug:   (id) => `/drugs?highlight=${id}`,
};

export default function BookmarksPage() {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [filter, setFilter]       = useState<FilterType>("all");
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    bookmarksApi.list()
      .then((data: any) => setBookmarks(data ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const remove = async (b: Bookmark) => {
    await bookmarksApi.remove(b.resource_type, b.resource_id);
    setBookmarks(prev => prev.filter(x => x.id !== b.id));
  };

  const filtered = filter === "all"
    ? bookmarks
    : bookmarks.filter(b => b.resource_type === filter);

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-syne font-black text-2xl text-ink">Bookmarks</h1>
        <span className="text-ink-3 text-sm">{bookmarks.length} saved</span>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6 bg-surface-2 rounded-lg p-1 w-fit">
        {(["all", "lesson", "module", "drug"] as FilterType[]).map(t => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition-colors ${
              filter === t ? "bg-accent text-white" : "text-ink-3 hover:text-ink"
            }`}
          >
            {t === "all" ? "All" : `${TYPE_ICONS[t] || ""} ${t}s`}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-16 text-ink-3">Loading…</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-ink-3">
          <div className="text-4xl mb-3">🔖</div>
          <div>No bookmarks {filter !== "all" ? `in "${filter}"` : "yet"}</div>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(b => {
            const href = TYPE_HREF[b.resource_type]?.(b.resource_id) ?? "#";
            return (
              <div key={b.id} className="card flex items-center gap-4 px-4 py-3">
                <div className="text-2xl">{TYPE_ICONS[b.resource_type] ?? "📌"}</div>
                <div className="flex-1 min-w-0">
                  <Link href={href} className="font-semibold text-sm text-ink hover:text-accent truncate block">
                    {b.title || b.resource_id}
                  </Link>
                  <div className="text-xs text-ink-3 mt-0.5 capitalize">
                    {b.resource_type} · {new Date(b.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={() => remove(b)}
                  className="text-ink-3 hover:text-red-500 text-lg transition-colors"
                  title="Remove bookmark"
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
