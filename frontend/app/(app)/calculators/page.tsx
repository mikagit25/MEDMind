"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useT } from "@/lib/i18n";
import { calculatorsApi } from "@/lib/api";
import { Calculator, Trash2, ExternalLink, ChevronRight } from "lucide-react";

type SavedResult = {
  id: string;
  slug: string;
  inputs: Record<string, unknown>;
  score: string | null;
  risk_level: string | null;
  note: string | null;
  created_at: string;
};

const SLUG_NAMES: Record<string, { name: string; icon: string }> = {
  "cha2ds2-vasc":       { name: "CHA₂DS₂-VASc",         icon: "💓" },
  "has-bled":           { name: "HAS-BLED",                         icon: "🩸" },
  "wells-dvt":          { name: "Wells Criteria (DVT)",             icon: "🦵" },
  "wells-pe":           { name: "Wells Criteria (PE)",              icon: "🪱" },
  "heart-score":        { name: "HEART Score",                      icon: "🏥" },
  "target-heart-rate":  { name: "Target Heart Rate",                icon: "💓" },
  "egfr-ckd-epi":       { name: "eGFR (CKD-EPI 2021)",             icon: "🪲" },
  "cockcroft-gault":    { name: "Cockcroft-Gault CrCl",            icon: "💊" },
  "aki":                { name: "AKI Staging (KDIGO)",              icon: "🚨" },
  "corrected-calcium":  { name: "Corrected Calcium",                icon: "🧪" },
  "anion-gap":          { name: "Anion Gap",                        icon: "⚗️" },
  "meld":               { name: "MELD / MELD-Na",                   icon: "🫀" },
  "child-pugh":         { name: "Child-Pugh Score",                 icon: "🫀" },
  "sofa":               { name: "SOFA Score",                       icon: "🏥" },
  "qsofa":              { name: "qSOFA",                            icon: "⚠️" },
  "curb-65":            { name: "CURB-65",                          icon: "🪱" },
  "gcs":                { name: "Glasgow Coma Scale",               icon: "🧠" },
  "abcd2":              { name: "ABCD² Score",                 icon: "🧠" },
  "bmi":                { name: "BMI Calculator",                   icon: "⚖️" },
  "ideal-body-weight":  { name: "Ideal Body Weight",                icon: "⚖️" },
  "daily-calories":     { name: "Daily Calorie Needs",              icon: "🍎" },
  "pregnancy-due-date": { name: "Pregnancy Due Date",               icon: "🤰" },
};

const RISK_COLOR: Record<string, string> = {
  low:      "text-green-600 bg-green-50",
  moderate: "text-amber-600 bg-amber-50",
  high:     "text-red-600 bg-red-50",
  very_high:"text-red-700 bg-red-100",
};

function riskClass(level: string | null) {
  if (!level) return "text-ink-2 bg-surface";
  const k = level.toLowerCase().replace(/\s+/g, "_");
  return RISK_COLOR[k] ?? "text-ink-2 bg-surface";
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function CalcHistoryPage() {
  const t = useT();
  const [results, setResults] = useState<SavedResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<Record<string, boolean>>({});
  const [filterSlug, setFilterSlug] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await calculatorsApi.getHistory(filterSlug || undefined);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [filterSlug]);

  useEffect(() => { load(); }, [load]);

  async function handleDelete(id: string) {
    setDeleting(prev => ({ ...prev, [id]: true }));
    try {
      await calculatorsApi.deleteResult(id);
      setResults(prev => prev.filter(r => r.id !== id));
    } catch {
      // leave in place on error
    } finally {
      setDeleting(prev => ({ ...prev, [id]: false }));
    }
  }

  const slugOptions = [...new Set(results.map(r => r.slug))].sort();

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary/10 rounded-xl">
          <Calculator size={22} className="text-primary" strokeWidth={1.75} />
        </div>
        <div>
          <h1 className="font-syne font-bold text-xl text-ink">{t("calc_history.title")}</h1>
          <p className="text-sm text-ink-2">{t("calc_history.subtitle")}</p>
        </div>
      </div>

      {/* Browse public calculators link */}
      <Link
        href="/calculators"
        className="flex items-center gap-2 text-sm text-primary hover:underline"
      >
        <ExternalLink size={14} />
        {t("calc_history.browse_link")}
      </Link>

      {/* Filter */}
      {slugOptions.length > 1 && (
        <select
          value={filterSlug}
          onChange={e => setFilterSlug(e.target.value)}
          className="text-sm bg-surface border border-border rounded-lg px-3 py-1.5 text-ink focus:outline-none focus:border-primary"
        >
          <option value="">{t("calc_history.all_calculators")}</option>
          {slugOptions.map(s => (
            <option key={s} value={s}>{SLUG_NAMES[s]?.name ?? s}</option>
          ))}
        </select>
      )}

      {/* List */}
      {loading ? (
        <div className="text-center py-16 text-ink-2">{t("calc_history.loading")}</div>
      ) : results.length === 0 ? (
        <div className="text-center py-16 space-y-3">
          <p className="text-ink-2">{t("calc_history.empty")}</p>
          <Link
            href="/calculators"
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            {t("calc_history.go_calculate")} <ChevronRight size={14} />
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {results.map(r => {
            const meta = SLUG_NAMES[r.slug];
            return (
              <div key={r.id} className="bg-surface border border-border rounded-xl p-4 space-y-3">
                {/* Top row */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xl leading-none" aria-hidden>{meta?.icon ?? "🔢"}</span>
                    <div className="min-w-0">
                      <Link
                        href={`/calculators/${r.slug}`}
                        className="font-syne font-semibold text-sm text-ink hover:text-primary truncate block"
                      >
                        {meta?.name ?? r.slug}
                      </Link>
                      <p className="text-xs text-ink-3">{formatDate(r.created_at)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {r.score && (
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${riskClass(r.risk_level)}`}>
                        {r.score}{r.risk_level ? ` · ${r.risk_level}` : ""}
                      </span>
                    )}
                    <button
                      onClick={() => handleDelete(r.id)}
                      disabled={deleting[r.id]}
                      aria-label={t("calc_history.delete")}
                      className="p-1.5 text-ink-3 hover:text-red-500 transition-colors disabled:opacity-40"
                    >
                      <Trash2 size={15} strokeWidth={1.75} />
                    </button>
                  </div>
                </div>

                {/* Note */}
                {r.note && (
                  <p className="text-xs text-ink-2 italic border-t border-border pt-2">{r.note}</p>
                )}

                {/* Inputs */}
                <details className="group">
                  <summary className="text-xs text-ink-3 cursor-pointer select-none group-open:text-ink-2">
                    {t("calc_history.show_inputs")}
                  </summary>
                  <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
                    {Object.entries(r.inputs).map(([k, v]) => (
                      <div key={k} className="flex gap-1 text-xs">
                        <span className="text-ink-3 capitalize">{k.replace(/_/g, " ")}:</span>
                        <span className="text-ink font-medium">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
