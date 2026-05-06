"use client";

import { useState } from "react";
import { drugsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface Drug {
  id: string;
  name: string;
}

interface Interaction {
  drug_a: string;
  drug_b: string;
  severity: "mild" | "moderate" | "severe" | "contraindicated";
  mechanism: string;
  clinical_effect: string;
  management: string;
}

const SEVERITY_STYLES: Record<string, string> = {
  mild:             "bg-green-50 border-green-200 text-green-800 dark:bg-green-950 dark:border-green-800 dark:text-green-300",
  moderate:         "bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-300",
  severe:           "bg-red-50 border-red-200 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-300",
  contraindicated:  "bg-red-100 border-red-400 text-red-900 dark:bg-red-900 dark:border-red-600 dark:text-red-200",
};

export function InteractionChecker() {
  const t = useT();
  const [query, setQuery]             = useState("");
  const [suggestions, setSuggestions] = useState<Drug[]>([]);
  const [selected, setSelected]       = useState<Drug[]>([]);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [checked, setChecked]         = useState(false);
  const [loading, setLoading]         = useState(false);

  const search = async (q: string) => {
    setQuery(q);
    if (q.length < 2) { setSuggestions([]); return; }
    const res = await drugsApi.search(q).catch(() => []);
    setSuggestions((res?.drugs ?? res ?? []).slice(0, 6));
  };

  const add = (drug: Drug) => {
    if (!selected.find(d => d.id === drug.id) && selected.length < 8) {
      setSelected(prev => [...prev, drug]);
    }
    setQuery("");
    setSuggestions([]);
    setInteractions([]);
    setChecked(false);
  };

  const remove = (id: string) => {
    setSelected(prev => prev.filter(d => d.id !== id));
    setInteractions([]);
    setChecked(false);
  };

  const check = async () => {
    if (selected.length < 2) return;
    setLoading(true);
    try {
      const res = await drugsApi.checkInteractions(selected.map(d => d.id));
      setInteractions(res?.interactions ?? []);
      setChecked(true);
    } catch {
      alert("Failed to check interactions.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-5 space-y-4">
      <h3 className="font-syne font-bold text-base text-ink">{t("drugs.interaction_checker")}</h3>

      {/* Search */}
      <div className="relative">
        <input
          value={query}
          onChange={e => search(e.target.value)}
          placeholder={t("drugs.interaction_placeholder")}
          className="input w-full"
        />
        {suggestions.length > 0 && (
          <div className="absolute top-full left-0 right-0 z-10 bg-surface border border-border rounded-xl shadow-lg mt-1 overflow-hidden">
            {suggestions.map(d => (
              <button
                key={d.id}
                onClick={() => add(d)}
                className="w-full text-left px-4 py-2 text-sm text-ink hover:bg-surface-2 transition-colors"
              >
                {d.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected drugs */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selected.map(d => (
            <span key={d.id} className="flex items-center gap-1.5 bg-accent/10 text-accent text-xs px-3 py-1 rounded-full font-semibold">
              {d.name}
              <button onClick={() => remove(d.id)} className="hover:text-red-500 ml-1">×</button>
            </span>
          ))}
        </div>
      )}

      <button
        onClick={check}
        disabled={selected.length < 2 || loading}
        className="btn-primary w-full disabled:opacity-50"
      >
        {loading ? t("drugs.interaction_checking") : `${t("drugs.interaction_check")} (${selected.length})`}
      </button>

      {/* Results */}
      {checked && (
        interactions.length === 0 ? (
          <div className="text-center py-4 text-green-600 dark:text-green-400 font-semibold text-sm">
            ✓ {t("drugs.interaction_no_found")}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="text-sm font-semibold text-ink">{interactions.length} {t("drugs.interaction_found")}:</div>
            {interactions.map((ix, i) => (
              <div key={i} className={`border rounded-xl p-4 text-sm space-y-2 ${SEVERITY_STYLES[ix.severity] ?? ""}`}>
                <div className="font-bold capitalize">{ix.severity}: {ix.drug_a} + {ix.drug_b}</div>
                {ix.mechanism && <div><span className="font-semibold">{t("drugs.mechanism")}:</span> {ix.mechanism}</div>}
                {ix.clinical_effect && <div><span className="font-semibold">{t("drugs.interaction_effect")}:</span> {ix.clinical_effect}</div>}
                {ix.management && <div><span className="font-semibold">{t("drugs.interaction_management")}:</span> {ix.management}</div>}
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
