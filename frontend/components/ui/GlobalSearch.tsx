"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { Search, X, Loader2 } from "lucide-react";
import { api, drugsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface SearchResult {
  id: string;
  type: "module" | "lesson" | "drug" | "article";
  title: string;
  module_id?: string;
  subtitle?: string;
  slug?: string;
}

const TYPE_ICON: Record<string, string> = {
  module: "📚",
  lesson: "📖",
  drug: "💊",
  article: "📄",
};

const TYPE_COLOR: Record<string, string> = {
  module: "text-blue-400",
  lesson: "text-green-400",
  drug: "text-purple-400",
  article: "text-amber-400",
};

export function GlobalSearch() {
  const t = useT();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(0);
  const [mounted, setMounted] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => { setMounted(true); }, []);

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(o => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // Custom event: open from Sidebar / MobileNav search click
  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener("search:open", onOpen);
    return () => window.removeEventListener("search:open", onOpen);
  }, []);

  // Focus input when modal opens
  useEffect(() => {
    if (open) {
      const id = setTimeout(() => inputRef.current?.focus(), 60);
      return () => clearTimeout(id);
    } else {
      setQuery("");
      setResults([]);
      setSelected(0);
    }
  }, [open]);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); return; }
    setLoading(true);
    try {
      const [contentRes, drugRes] = await Promise.all([
        api.get("/search", { params: { q, limit: 20 } }).then(r => r.data).catch(() => ({})),
        drugsApi.search(q).catch(() => []),
      ]);
      const flat: SearchResult[] = [
        ...(contentRes.modules ?? []).map((m: any) => ({
          id: m.id, type: "module" as const,
          title: m.title,
          subtitle: m.module_code ?? m.specialty ?? "",
        })),
        ...(contentRes.lessons ?? []).map((l: any) => ({
          id: l.id, type: "lesson" as const,
          title: l.title,
          module_id: l.module_id,
          subtitle: l.module_title ?? "",
        })),
        ...(Array.isArray(drugRes) ? drugRes : (drugRes as any)?.drugs ?? []).map((d: any) => ({
          id: d.id, type: "drug" as const,
          title: d.name ?? d.generic_name ?? d.title,
          subtitle: d.drug_class ?? d.category ?? "",
        })),
        ...(contentRes.articles ?? []).map((a: any) => ({
          id: a.id, type: "article" as const,
          title: a.title,
          subtitle: a.category ?? "",
          slug: a.slug,
        })),
      ];
      setResults(flat.slice(0, 25));
      setSelected(0);
    } finally {
      setLoading(false);
    }
  }, []);

  const onChange = (val: string) => {
    setQuery(val);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(val), 300);
  };

  const hrefOf = (r: SearchResult) => {
    if (r.type === "module")  return `/modules/${r.id}`;
    if (r.type === "lesson")  return `/modules/${r.module_id ?? ""}`;
    if (r.type === "drug")    return `/drugs?highlight=${r.id}`;
    if (r.type === "article") return `/articles/${r.slug ?? r.id}`;
    return "/search";
  };

  const navigate = (r: SearchResult) => {
    setOpen(false);
    router.push(hrefOf(r));
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected(s => Math.min(s + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected(s => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && results.length > 0) {
      e.preventDefault();
      navigate(results[selected]);
    }
  };

  if (!mounted || !open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center pt-[10vh] bg-black/60 backdrop-blur-sm"
      onMouseDown={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl mx-4 bg-surface rounded-2xl shadow-2xl border border-border overflow-hidden"
        onMouseDown={e => e.stopPropagation()}
      >
        {/* Input row */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-border">
          {loading
            ? <Loader2 size={16} className="text-ink-3 animate-spin flex-shrink-0" />
            : <Search size={16} className="text-ink-3 flex-shrink-0" />
          }
          <input
            ref={inputRef}
            value={query}
            onChange={e => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={t("search.placeholder")}
            className="flex-1 bg-transparent text-ink placeholder:text-ink-3 text-base focus:outline-none font-serif"
          />
          {query && (
            <button
              onMouseDown={e => { e.preventDefault(); setQuery(""); setResults([]); inputRef.current?.focus(); }}
              className="text-ink-3 hover:text-ink transition-colors"
            >
              <X size={14} />
            </button>
          )}
          <kbd className="hidden sm:inline text-[10px] text-ink-3 border border-border rounded px-1.5 py-0.5 font-mono flex-shrink-0">
            Esc
          </kbd>
        </div>

        {/* Results list */}
        {results.length > 0 && (
          <ul className="max-h-[55vh] overflow-y-auto divide-y divide-border/40">
            {results.map((r, i) => (
              <li key={`${r.type}-${r.id}`}>
                <button
                  onMouseDown={() => navigate(r)}
                  onMouseEnter={() => setSelected(i)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                    selected === i ? "bg-surface-2" : "hover:bg-surface-2"
                  }`}
                >
                  <span className="text-lg w-6 text-center flex-shrink-0">{TYPE_ICON[r.type]}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-ink font-medium truncate">{r.title}</div>
                    {r.subtitle && (
                      <div className="text-xs text-ink-3 truncate mt-0.5">{r.subtitle}</div>
                    )}
                  </div>
                  <span className={`text-[10px] font-syne font-bold uppercase flex-shrink-0 ${TYPE_COLOR[r.type]}`}>
                    {r.type}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Empty state */}
        {!loading && query.trim() && results.length === 0 && (
          <div className="px-4 py-10 text-center">
            <div className="text-2xl mb-2">🔍</div>
            <div className="text-sm text-ink-3">
              {t("search.no_results")} «{query}»
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-2 border-t border-border flex items-center gap-4 text-[10px] text-ink-3 font-mono">
          <span>↑↓ navigate</span>
          <span>↵ open</span>
          <span>Esc close</span>
        </div>
      </div>
    </div>,
    document.body
  );
}
