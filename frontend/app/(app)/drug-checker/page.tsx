"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { drugsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface DrugItem {
  id: string;
  name: string;
  generic_name?: string | null;
  drug_class?: string | null;
}

interface Interaction {
  drug_a: string;
  drug_b: string;
  severity: "major" | "moderate" | "minor" | string;
  mechanism: string | null;
  clinical_effect: string | null;
  management: string | null;
  evidence_level: string | null;
}

const SEVERITY_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  major:    { bg: "bg-red/10",    text: "text-red",       border: "border-red/30" },
  moderate: { bg: "bg-amber-2/10", text: "text-amber-600", border: "border-amber-2/30" },
  minor:    { bg: "bg-green/10",  text: "text-green",     border: "border-green/30" },
};

function SeverityBadge({ severity, t }: { severity: string; t: (k: string) => string }) {
  const s = SEVERITY_STYLE[severity] ?? SEVERITY_STYLE.minor;
  const labelKey = `drugs.severity_${severity}`;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-syne font-bold border ${s.bg} ${s.text} ${s.border}`}>
      {t(labelKey) || severity}
    </span>
  );
}

function DrugSearchInput({
  onAdd,
  disabled,
}: {
  onAdd: (drug: DrugItem) => void;
  disabled?: boolean;
}) {
  const t = useT();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DrugItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setOpen(false); return; }
    setLoading(true);
    try {
      const data = await drugsApi.search(q);
      const items: DrugItem[] = Array.isArray(data) ? data : (data?.items ?? []);
      setResults(items.slice(0, 8));
      setOpen(items.length > 0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (v: string) => {
    setQuery(v);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => search(v), 300);
  };

  const handleSelect = (drug: DrugItem) => {
    onAdd(drug);
    setQuery("");
    setResults([]);
    setOpen(false);
  };

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={wrapRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={e => handleChange(e.target.value)}
        disabled={disabled}
        placeholder={t("drugs.interaction_placeholder")}
        className="w-full bg-bg-2 border border-stroke rounded px-3 py-2 font-serif text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-red/30 disabled:opacity-50"
      />
      {loading && (
        <span className="absolute right-3 top-2.5 font-serif text-xs text-ink-3">{t("common.loading")}</span>
      )}
      {open && results.length > 0 && (
        <ul className="absolute z-20 left-0 right-0 top-full mt-1 bg-bg border border-stroke rounded shadow-lg max-h-56 overflow-y-auto">
          {results.map(d => (
            <li key={d.id}>
              <button
                type="button"
                onClick={() => handleSelect(d)}
                className="w-full text-left px-3 py-2 hover:bg-bg-2 transition-colors"
              >
                <span className="font-syne font-semibold text-sm text-ink">{d.name}</span>
                {d.generic_name && d.generic_name !== d.name && (
                  <span className="font-serif text-xs text-ink-3 ml-2">{d.generic_name}</span>
                )}
                {d.drug_class && (
                  <span className="font-serif text-xs text-ink-3 block">{d.drug_class}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function DrugCheckerPage() {
  const t = useT();
  const [selected, setSelected] = useState<DrugItem[]>([]);
  const [interactions, setInteractions] = useState<Interaction[] | null>(null);
  const [pairsChecked, setPairsChecked] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const addDrug = useCallback((drug: DrugItem) => {
    setSelected(prev => {
      if (prev.some(d => d.id === drug.id)) return prev;
      return [...prev, drug];
    });
    setInteractions(null);
    setError("");
  }, []);

  const removeDrug = (id: string) => {
    setSelected(prev => prev.filter(d => d.id !== id));
    setInteractions(null);
    setError("");
  };

  const handleCheck = async () => {
    if (selected.length < 2) return;
    setLoading(true);
    setError("");
    setInteractions(null);
    try {
      const data = await drugsApi.checkInteractions(selected.map(d => d.id));
      setInteractions(data.interactions ?? []);
      setPairsChecked(data.pairs_checked ?? 0);
    } catch {
      setError(t("common.error_retry"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-3xl">
      <div className="mb-1 flex items-center gap-2">
        <Link href="/drugs" className="text-ink-3 hover:text-ink font-syne text-sm">
          ← {t("nav.items.drugs")}
        </Link>
      </div>
      <h1 className="font-syne font-black text-2xl text-ink mb-1">{t("drugs.interaction_checker")}</h1>
      <p className="font-serif text-ink-3 text-sm mb-6">{t("drugs.interaction_subtitle")}</p>

      {/* Drug search input */}
      <div className="card p-4 mb-4">
        <label className="font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider block mb-2">
          {t("drugs.interaction_add")}
        </label>
        <DrugSearchInput onAdd={addDrug} disabled={loading} />
      </div>

      {/* Selected drug chips */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {selected.map(drug => (
            <span
              key={drug.id}
              className="inline-flex items-center gap-1.5 bg-blue-light text-blue font-syne font-semibold text-sm px-3 py-1.5 rounded-full"
            >
              {drug.name}
              <button
                onClick={() => removeDrug(drug.id)}
                className="hover:text-red transition-colors ml-0.5 font-normal leading-none"
                aria-label={`Remove ${drug.name}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Hint or Check button */}
      {selected.length < 2 ? (
        <p className="font-serif text-xs text-ink-3 mb-6">{t("drugs.interaction_min_hint")}</p>
      ) : (
        <button
          onClick={handleCheck}
          disabled={loading}
          className="btn-primary px-6 py-2 rounded font-syne font-semibold text-sm mb-6 disabled:opacity-60"
        >
          {loading ? t("drugs.interaction_checking") : t("drugs.interaction_check")}
        </button>
      )}

      {/* Error */}
      {error && <p className="font-serif text-sm text-red mb-4">{error}</p>}

      {/* Results */}
      {interactions !== null && (
        <div>
          {interactions.length === 0 ? (
            <div className="card p-6 text-center">
              <div className="text-4xl mb-3">✅</div>
              <p className="font-syne font-bold text-base text-ink mb-1">{t("drugs.interaction_no_found")}</p>
              <p className="font-serif text-xs text-ink-3">
                {pairsChecked} {t("drugs.pairs_checked")}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="font-syne font-bold text-sm text-ink">
                {interactions.length} {t("drugs.interaction_found")} · {pairsChecked} {t("drugs.pairs_checked")}
              </p>
              {interactions.map((ix, i) => {
                const sty = SEVERITY_STYLE[ix.severity] ?? SEVERITY_STYLE.minor;
                return (
                  <div key={i} className={`card p-4 border-l-4 ${sty.border}`}>
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <p className="font-syne font-bold text-sm text-ink">
                        {ix.drug_a} ↔ {ix.drug_b}
                      </p>
                      <SeverityBadge severity={ix.severity} t={t} />
                    </div>
                    {ix.clinical_effect && (
                      <div className="mb-2">
                        <span className="font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">{t("drugs.interaction_effect")}: </span>
                        <span className="font-serif text-sm text-ink">{ix.clinical_effect}</span>
                      </div>
                    )}
                    {ix.mechanism && (
                      <div className="mb-2">
                        <span className="font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">{t("drugs.mechanism_label")}: </span>
                        <span className="font-serif text-sm text-ink">{ix.mechanism}</span>
                      </div>
                    )}
                    {ix.management && (
                      <div className="mb-2">
                        <span className="font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">{t("drugs.interaction_management")}: </span>
                        <span className="font-serif text-sm text-ink">{ix.management}</span>
                      </div>
                    )}
                    {ix.evidence_level && (
                      <span className="font-serif text-xs text-ink-3">Evidence: {ix.evidence_level}</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Disclaimer */}
          <div className="mt-6 p-3 rounded bg-amber-light/20 border border-amber-2/30">
            <p className="font-serif text-xs text-ink-3">
              ⚠️ {t("drugs.interaction_disclaimer")}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
