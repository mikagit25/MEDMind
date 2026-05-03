"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { bookmarksApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

type FilterType = "all" | "lesson" | "module" | "drug" | "case";

interface Bookmark {
  id: string;
  resource_type: string;
  resource_id: string;
  title: string | null;
  created_at: string;
}

const TYPE_META: Record<string, { icon: string; label: string; color: string; href: (id: string) => string }> = {
  lesson: { icon: "📖", label: "Lessons", color: "bg-blue-light text-blue",   href: (id) => `/modules/${id}` },
  module: { icon: "📚", label: "Modules", color: "bg-red-light text-red",     href: (id) => `/modules/${id}` },
  drug:   { icon: "💊", label: "Drugs",   color: "bg-amber-light text-amber", href: (id) => `/drugs/${id}` },
  case:   { icon: "🩺", label: "Cases",   color: "bg-green-light text-green", href: (id) => `/cases?id=${id}` },
};

const FILTER_LABELS: Record<FilterType, string> = {
  all: "All",
  lesson: "Lessons",
  module: "Modules",
  drug: "Drugs",
  case: "Cases",
};

export default function BookmarksPage() {
  const t = useT();
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [filter, setFilter] = useState<FilterType>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    bookmarksApi.list()
      .then((data: any) => setBookmarks(data ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const remove = async (b: Bookmark) => {
    await bookmarksApi.remove(b.resource_type, b.resource_id).catch(() => {});
    setBookmarks((prev) => prev.filter((x) => x.id !== b.id));
  };

  const counts: Record<string, number> = { all: bookmarks.length };
  for (const b of bookmarks) {
    counts[b.resource_type] = (counts[b.resource_type] ?? 0) + 1;
  }

  const filtered = filter === "all"
    ? bookmarks
    : bookmarks.filter((b) => b.resource_type === filter);

  // Group by week
  const now = Date.now();
  const recent = filtered.filter((b) => now - new Date(b.created_at).getTime() < 7 * 86400_000);
  const older = filtered.filter((b) => now - new Date(b.created_at).getTime() >= 7 * 86400_000);

  const filters: FilterType[] = ["all", "lesson", "module", "drug", "case"];
  const activeFilters = filters.filter((f) => f === "all" || counts[f]);

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-2xl mx-auto w-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("bookmarks.title")}</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">{bookmarks.length} {t("bookmarks.subtitle")}</p>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1.5 flex-wrap mb-6">
        {activeFilters.map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`px-3 py-1.5 rounded-full font-syne font-semibold text-xs transition-all border ${
              filter === t
                ? "bg-ink text-white border-ink"
                : "border-border text-ink-3 hover:border-ink hover:text-ink"
            }`}
          >
            {t !== "all" && TYPE_META[t]?.icon} {FILTER_LABELS[t]}
            {counts[t] ? ` (${counts[t]})` : ""}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-16 font-serif text-ink-3 text-sm">{t("common.loading")}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3">🔖</div>
          <p className="font-syne font-bold text-sm text-ink">{t("bookmarks.empty")}</p>
          <p className="font-serif text-ink-3 text-xs mt-1">{t("bookmarks.empty_hint")}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {recent.length > 0 && (
            <section>
              {older.length > 0 && (
                <h2 className="font-syne font-bold text-xs text-ink-3 uppercase mb-2">This week</h2>
              )}
              <div className="space-y-2">
                {recent.map((b) => <BookmarkCard key={b.id} bookmark={b} onRemove={remove} />)}
              </div>
            </section>
          )}
          {older.length > 0 && (
            <section>
              {recent.length > 0 && (
                <h2 className="font-syne font-bold text-xs text-ink-3 uppercase mb-2">Older</h2>
              )}
              <div className="space-y-2">
                {older.map((b) => <BookmarkCard key={b.id} bookmark={b} onRemove={remove} />)}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

function BookmarkCard({ bookmark: b, onRemove }: { bookmark: Bookmark; onRemove: (b: Bookmark) => void }) {
  const meta = TYPE_META[b.resource_type];
  const href = meta?.href(b.resource_id) ?? "#";
  const date = new Date(b.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

  return (
    <div className="card flex items-center gap-3 px-4 py-3">
      <div className={`w-9 h-9 rounded-lg ${meta?.color ?? "bg-bg-2 text-ink-3"} flex items-center justify-center text-lg flex-shrink-0`}>
        {meta?.icon ?? "📌"}
      </div>
      <div className="flex-1 min-w-0">
        <Link
          href={href}
          className="font-syne font-bold text-sm text-ink hover:underline truncate block"
        >
          {b.title || b.resource_id}
        </Link>
        <div className="font-serif text-xs text-ink-3 mt-0.5 capitalize">
          {meta?.label.slice(0, -1) ?? b.resource_type} · saved {date}
        </div>
      </div>
      <Link
        href={href}
        className="font-syne font-semibold text-xs text-ink-3 hover:text-ink flex-shrink-0"
      >
        Open →
      </Link>
      <button
        onClick={() => onRemove(b)}
        className="text-ink-3 hover:text-red transition-colors text-xl flex-shrink-0 leading-none"
        title="Remove"
      >
        ×
      </button>
    </div>
  );
}
