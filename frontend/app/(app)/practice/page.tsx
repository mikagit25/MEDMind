"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { API_URL } from "@/lib/api";
import {
  Search,
  Pill,
  Zap,
  Calculator,
  GitBranch,
  Activity,
  ChevronRight,
} from "lucide-react";

type SearchResult = {
  type: "drug" | "algorithm" | "module";
  id: string;
  title: string;
  subtitle: string;
  href: string;
};

type SearchResponse = {
  query: string;
  results: SearchResult[];
  counts: { drugs: number; algorithms: number; modules: number };
};

const TYPE_BADGE: Record<string, string> = {
  drug:      "bg-blue-100 text-blue-700",
  algorithm: "bg-amber-100 text-amber-700",
  module:    "bg-surface-2 text-ink-3",
};

const TILES = [
  { label: "Drugs",         icon: Pill,       href: "/drugs",                  color: "bg-blue-50 border-blue-200 hover:border-blue-400",   textColor: "text-blue-700" },
  { label: "Interactions",  icon: Zap,        href: "/drug-checker",            color: "bg-amber-50 border-amber-200 hover:border-amber-400", textColor: "text-amber-700" },
  { label: "Calculators",   icon: Calculator, href: "/calculator-history",      color: "bg-green/10 border-green/30 hover:border-green",      textColor: "text-green" },
  { label: "Algorithms",    icon: GitBranch,  href: "/practice/algorithms",     color: "bg-purple-50 border-purple-200 hover:border-purple-400",textColor: "text-purple-700" },
  { label: "Lab Values",    icon: Activity,   href: "/practice/lab-values",     color: "bg-rose-50 border-rose-200 hover:border-rose-400",   textColor: "text-rose-700" },
];

export default function PracticePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) { setResults(null); return; }
    setLoading(true);
    try {
      const token = localStorage.getItem("access_token");
      const r = await fetch(`${API_URL}/practice/search?q=${encodeURIComponent(q)}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (r.ok) {
        const data: SearchResponse = await r.json();
        setResults(data.results);
      }
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(query), 250);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [query, doSearch]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-6">

        {/* Header */}
        <div>
          <h1 className="font-syne font-black text-2xl text-ink mb-1">Practice</h1>
          <p className="font-serif text-ink-3 text-sm">Point-of-care clinical reference — answer in seconds.</p>
        </div>

        {/* Search bar */}
        <div className="relative">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3">
            <Search size={18} />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search drugs, algorithms, interactions…"
            className="w-full pl-10 pr-4 py-3 rounded-lg border border-border bg-surface font-syne text-sm text-ink placeholder-ink-3 focus:outline-none focus:border-ink transition-colors"
            autoFocus
          />
          {loading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-ink-3 border-t-transparent rounded-full animate-spin" />
          )}
        </div>

        {/* Search results */}
        {results !== null && (
          <div className="card overflow-hidden divide-y divide-border">
            {results.length === 0 ? (
              <div className="p-6 text-center font-serif text-ink-3 text-sm">
                No results for &ldquo;{query}&rdquo;
              </div>
            ) : (
              results.map((r, i) => (
                <Link
                  key={i}
                  href={r.href}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-surface-2 transition-colors"
                >
                  <span className={`text-xs font-syne font-bold px-2 py-0.5 rounded-full ${TYPE_BADGE[r.type]}`}>
                    {r.type}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-syne font-semibold text-sm text-ink truncate">{r.title}</div>
                    {r.subtitle && (
                      <div className="font-serif text-xs text-ink-3 truncate">{r.subtitle}</div>
                    )}
                  </div>
                  <ChevronRight size={14} className="text-ink-3 shrink-0" />
                </Link>
              ))
            )}
          </div>
        )}

        {/* Category tiles */}
        {results === null && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {TILES.map(({ label, icon: Icon, href, color, textColor }) => (
                <Link
                  key={label}
                  href={href}
                  className={`flex flex-col items-center gap-2 p-5 rounded-xl border transition-all ${color}`}
                >
                  <Icon size={24} className={textColor} />
                  <span className={`font-syne font-bold text-sm ${textColor}`}>{label}</span>
                </Link>
              ))}
            </div>

            {/* Quick links */}
            <div>
              <h2 className="font-syne font-bold text-sm text-ink mb-3">Common lookups</h2>
              <div className="space-y-2">
                {[
                  { label: "Anaphylaxis management", href: "/practice/algorithms/anaphylaxis" },
                  { label: "Cardiac arrest BLS",     href: "/practice/algorithms/cardiac-arrest-bls" },
                  { label: "Sepsis — qSOFA bundle",  href: "/practice/algorithms/sepsis-qsofa" },
                  { label: "Human lab reference",    href: "/practice/lab-values" },
                  { label: "Drug interactions",      href: "/drug-checker" },
                ].map(({ label, href }) => (
                  <Link
                    key={href}
                    href={href}
                    className="flex items-center justify-between px-4 py-2.5 rounded-lg border border-border bg-surface hover:bg-surface-2 transition-colors"
                  >
                    <span className="font-syne text-sm text-ink-2">{label}</span>
                    <ChevronRight size={14} className="text-ink-3" />
                  </Link>
                ))}
              </div>
            </div>
          </>
        )}

      </div>
    </div>
  );
}
