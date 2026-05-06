"use client";

import { useState, useEffect } from "react";
import { contentApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

type PubMedRef = {
  pmid: string;
  title: string;
  authors?: string[];
  journal?: string;
  year?: string | number;
  abstract?: string;
  url?: string;
};

interface Props {
  /** Pre-loaded refs from AI response (optional) */
  initialRefs?: PubMedRef[];
  onClose?: () => void;
}

export default function PubMedPanel({ initialRefs = [], onClose }: Props) {
  const t = useT();
  const [query, setQuery] = useState("");
  const [refs, setRefs] = useState<PubMedRef[]>(initialRefs);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [open, setOpen] = useState(initialRefs.length > 0);

  // Sync incoming AI refs
  useEffect(() => {
    if (initialRefs.length > 0) {
      setRefs(initialRefs);
      setOpen(true);
    }
  }, [initialRefs]);

  const search = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const res = await contentApi.searchPubMed(q, 8);
      setRefs(res.data?.results ?? res.data ?? []);
    } catch {
      setRefs([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") search(query);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-10 border-l border-border bg-surface flex-shrink-0 flex flex-col items-center justify-start pt-4 gap-2 hover:bg-bg-2 transition-colors"
        title="Open PubMed search"
      >
        <span className="text-xs font-syne font-bold text-ink-3 rotate-90 whitespace-nowrap" style={{ writingMode: "vertical-rl" }}>
          PubMed
        </span>
        <span className="text-base">📄</span>
      </button>
    );
  }

  return (
    <div className="w-72 border-l border-border bg-surface flex-shrink-0 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-border flex-shrink-0">
        <h3 className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider">
          📄 PubMed
        </h3>
        <button
          onClick={() => { setOpen(false); onClose?.(); }}
          className="text-ink-3 hover:text-ink text-sm transition-colors"
        >
          ×
        </button>
      </div>

      {/* Search bar */}
      <div className="px-3 py-2 border-b border-border flex-shrink-0">
        <div className="flex gap-1.5">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("pubmed_panel.search_placeholder")}
            className="flex-1 px-2.5 py-1.5 rounded border border-border bg-bg text-ink font-serif text-xs focus:outline-none focus:border-ink transition-colors"
          />
          <button
            onClick={() => search(query)}
            disabled={loading || !query.trim()}
            className="px-2.5 py-1.5 rounded bg-ink text-white font-syne font-semibold text-xs hover:bg-red transition-colors disabled:opacity-40"
          >
            {loading ? "…" : "→"}
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="p-4 space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-1">
                <div className="h-3 bg-bg-2 rounded animate-pulse" style={{ width: "90%" }} />
                <div className="h-2.5 bg-bg-2 rounded animate-pulse" style={{ width: "60%" }} />
              </div>
            ))}
          </div>
        )}

        {!loading && refs.length === 0 && (
          <div className="p-4 text-center">
            <p className="font-serif text-ink-3 text-xs">
              {query ? t("pubmed_panel.no_results") : t("pubmed_panel.empty_hint")}
            </p>
          </div>
        )}

        {!loading && refs.length > 0 && (
          <div className="divide-y divide-border">
            {refs.map((ref) => (
              <div key={ref.pmid} className="p-3">
                <a
                  href={ref.url ?? `https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-syne font-semibold text-xs text-blue hover:text-blue-2 transition-colors leading-tight block mb-1"
                >
                  {ref.title}
                </a>
                <p className="font-serif text-ink-3 text-xs">
                  {ref.authors?.[0]}{ref.authors && ref.authors.length > 1 ? " et al." : ""}{ref.journal ? ` · ${ref.journal}` : ""}{ref.year ? `, ${ref.year}` : ""}
                </p>
                {ref.abstract && (
                  <>
                    <button
                      onClick={() => setExpanded(expanded === ref.pmid ? null : ref.pmid)}
                      className="font-syne text-xs text-ink-3 hover:text-ink mt-1 transition-colors"
                    >
                      {expanded === ref.pmid ? t("pubmed_panel.hide") : t("pubmed_panel.abstract")}
                    </button>
                    {expanded === ref.pmid && (
                      <p className="font-serif text-xs text-ink-2 leading-relaxed mt-1.5 line-clamp-6">
                        {ref.abstract}
                      </p>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="px-3 py-2 border-t border-border flex-shrink-0">
        <p className="font-serif text-ink-3 text-xs text-center">
          {t("pubmed_panel.powered_by")}
        </p>
      </div>
    </div>
  );
}
