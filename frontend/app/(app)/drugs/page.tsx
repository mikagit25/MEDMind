"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { drugsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

type Drug = {
  id: string;
  name: string;
  generic_name?: string;
  drug_class?: string;
  mechanism?: string;
  indications?: string[];
  contraindications?: string[];
  adverse_effects?: Record<string, string[]>;
  dosing?: Record<string, string>;
  is_high_yield?: boolean;
  is_nti?: boolean;
  is_veterinary?: boolean;
  image_url?: string;
};

type BrowseResult = {
  items: Drug[];
  total: number;
  page: number;
  pages: number;
  limit: number;
};

type Tab = "browse" | "interactions" | "dose" | "vet";

export default function DrugsPage() {
  const t = useT();
  const [tab, setTab] = useState<Tab>("browse");

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-6xl mx-auto w-full">
      <h1 className="font-syne font-black text-2xl text-ink mb-1">{t("drugs.title")}</h1>
      <p className="font-serif text-ink-3 text-sm mb-5">{t("drugs.subtitle")}</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-bg-2 p-1 rounded-lg w-fit flex-wrap">
        {(["browse", "interactions", "dose", "vet"] as Tab[]).map((tabKey) => (
          <button
            key={tabKey}
            onClick={() => setTab(tabKey)}
            className={`px-4 py-1.5 rounded font-syne font-semibold text-sm transition-all ${
              tab === tabKey ? "bg-white shadow text-ink" : "text-ink-3 hover:text-ink"
            }`}
          >
            {tabKey === "browse"
              ? "💊 Browse"
              : tabKey === "interactions"
              ? "⚡ Interactions"
              : tabKey === "dose"
              ? "⚖️ Dose Calc"
              : "🐾 Veterinary"}
          </button>
        ))}
      </div>

      {tab === "browse" && <DrugBrowser />}
      {tab === "interactions" && <InteractionChecker />}
      {tab === "dose" && <DoseCalculator />}
      {tab === "vet" && <VeterinaryDosing />}
    </div>
  );
}

// ── Drug image with RxImage fallback ─────────────────────────────────────────

function DrugImage({ drug, size = "sm" }: { drug: Drug; size?: "sm" | "lg" }) {
  const [imgSrc, setImgSrc] = useState<string | null>(drug.image_url || null);
  const [tried, setTried] = useState(false);

  useEffect(() => {
    if (!imgSrc && !tried) {
      setTried(true);
      drugsApi.fetchRxImage(drug.generic_name || drug.name).then((url) => {
        if (url) setImgSrc(url);
      });
    }
  }, [drug.name, drug.generic_name, imgSrc, tried]);

  const dim = size === "lg" ? "h-40 w-full" : "h-20 w-full";

  if (!imgSrc) {
    return (
      <div className={`${dim} rounded-lg bg-bg-2 flex items-center justify-center`}>
        <span className="text-3xl">💊</span>
      </div>
    );
  }

  return (
    <div className={`${dim} rounded-lg overflow-hidden bg-bg-2 relative`}>
      <img
        src={imgSrc}
        alt={drug.name}
        className="w-full h-full object-contain"
        onError={() => setImgSrc(null)}
      />
    </div>
  );
}

// ── Main Browser ──────────────────────────────────────────────────────────────

function DrugBrowser() {
  const router = useRouter();
  const [result, setResult] = useState<BrowseResult | null>(null);
  const [classes, setClasses] = useState<{ drug_class: string; count: number }[]>([]);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Drug[]>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [filterVet, setFilterVet] = useState<boolean | undefined>();
  const [filterHY, setFilterHY] = useState<boolean | undefined>();
  const [loading, setLoading] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout>>();

  const loadBrowse = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const data = await drugsApi.browse(p, 24, selectedClass || undefined, filterVet, filterHY);
      setResult(data);
      setPage(p);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [selectedClass, filterVet, filterHY]);

  // Initial load + filter changes
  useEffect(() => {
    if (!search) loadBrowse(1);
  }, [loadBrowse, search]);

  // Search with debounce
  useEffect(() => {
    clearTimeout(searchTimer.current);
    if (!search.trim()) {
      setSearchResults([]);
      return;
    }
    searchTimer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await drugsApi.search(search);
        setSearchResults(data ?? []);
      } catch {
        setSearchResults([]);
      } finally {
        setLoading(false);
      }
    }, 350);
  }, [search]);

  // Load drug classes for filter
  useEffect(() => {
    drugsApi.getClasses().then((d) => setClasses(d ?? [])).catch(() => {});
  }, []);

  const displayDrugs = search.trim() ? searchResults : result?.items ?? [];
  const isSearch = !!search.trim();

  return (
    <div>
      {/* Search + filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, class, generic name…"
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors"
          />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3 text-base">🔍</span>
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink text-lg leading-none"
            >
              ×
            </button>
          )}
        </div>

        {/* Class filter */}
        <select
          value={selectedClass}
          onChange={(e) => { setSelectedClass(e.target.value); setPage(1); }}
          className="px-3 py-2.5 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink min-w-[180px]"
        >
          <option value="">All classes</option>
          {classes.slice(0, 20).map((c) => (
            <option key={c.drug_class} value={c.drug_class}>
              {c.drug_class} ({c.count})
            </option>
          ))}
        </select>
      </div>

      {/* Quick filters */}
      <div className="flex gap-2 mb-5 flex-wrap">
        <button
          onClick={() => { setFilterHY(filterHY ? undefined : true); setPage(1); }}
          className={`px-3 py-1 rounded-full font-syne font-semibold text-xs border transition-all ${
            filterHY ? "bg-amber-light border-amber text-amber" : "border-border text-ink-3 hover:border-ink-3"
          }`}
        >
          ⭐ High Yield
        </button>
        <button
          onClick={() => { setFilterVet(filterVet ? undefined : true); setPage(1); }}
          className={`px-3 py-1 rounded-full font-syne font-semibold text-xs border transition-all ${
            filterVet ? "bg-green-light border-green text-green" : "border-border text-ink-3 hover:border-ink-3"
          }`}
        >
          🐾 Veterinary
        </button>
        {(selectedClass || filterHY || filterVet) && (
          <button
            onClick={() => { setSelectedClass(""); setFilterHY(undefined); setFilterVet(undefined); setPage(1); }}
            className="px-3 py-1 rounded-full font-syne font-semibold text-xs border border-red/30 text-red hover:bg-red-light transition-all"
          >
            ✕ Clear filters
          </button>
        )}
        {!isSearch && result && (
          <span className="ml-auto font-serif text-ink-3 text-xs self-center">
            {result.total} drugs
          </span>
        )}
      </div>

      {/* Drug grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="card p-3 animate-pulse">
              <div className="h-20 bg-bg-2 rounded-lg mb-3" />
              <div className="h-3 bg-bg-2 rounded mb-1.5 w-3/4" />
              <div className="h-2.5 bg-bg-2 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : displayDrugs.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3">💊</div>
          <p className="font-syne font-bold text-ink text-sm">
            {isSearch ? `No results for "${search}"` : "No drugs found"}
          </p>
          <p className="font-serif text-ink-3 text-xs mt-1">Try adjusting filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
          {displayDrugs.map((drug) => (
            <DrugCard key={drug.id} drug={drug} onClick={() => router.push(`/drugs/${drug.id}`)} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isSearch && result && result.pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <button
            onClick={() => loadBrowse(page - 1)}
            disabled={page <= 1 || loading}
            className="px-3 py-1.5 rounded-lg border border-border font-syne font-semibold text-sm text-ink-2 hover:border-ink disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            ←
          </button>

          {/* Page numbers */}
          {Array.from({ length: Math.min(result.pages, 7) }, (_, i) => {
            let p: number;
            if (result.pages <= 7) {
              p = i + 1;
            } else if (page <= 4) {
              p = i + 1;
            } else if (page >= result.pages - 3) {
              p = result.pages - 6 + i;
            } else {
              p = page - 3 + i;
            }
            return (
              <button
                key={p}
                onClick={() => loadBrowse(p)}
                disabled={loading}
                className={`w-8 h-8 rounded-lg font-syne font-semibold text-sm transition-all ${
                  p === page
                    ? "bg-ink text-white"
                    : "border border-border text-ink-2 hover:border-ink disabled:opacity-40"
                }`}
              >
                {p}
              </button>
            );
          })}

          <button
            onClick={() => loadBrowse(page + 1)}
            disabled={page >= result.pages || loading}
            className="px-3 py-1.5 rounded-lg border border-border font-syne font-semibold text-sm text-ink-2 hover:border-ink disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            →
          </button>

          <span className="font-serif text-ink-3 text-xs ml-2">
            Page {page} of {result.pages}
          </span>
        </div>
      )}
    </div>
  );
}

// ── Drug Card ─────────────────────────────────────────────────────────────────

function DrugCard({ drug, onClick }: { drug: Drug; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      className="card p-3 cursor-pointer hover:border-ink transition-all hover:shadow-md group"
    >
      <DrugImage drug={drug} size="sm" />
      <div className="mt-2.5">
        <div className="font-syne font-bold text-xs text-ink leading-tight group-hover:text-ink line-clamp-2">
          {drug.name}
        </div>
        {drug.generic_name && drug.generic_name !== drug.name && (
          <div className="font-serif text-ink-3 text-xs mt-0.5 line-clamp-1">{drug.generic_name}</div>
        )}
        {drug.drug_class && (
          <div className="font-serif text-ink-3 text-xs mt-1 line-clamp-1 leading-tight">{drug.drug_class}</div>
        )}
        <div className="flex gap-1 mt-1.5 flex-wrap">
          {drug.is_high_yield && (
            <span className="px-1.5 py-0.5 rounded-full bg-amber-light text-amber font-syne font-bold text-xs">⭐ HY</span>
          )}
          {drug.is_nti && (
            <span className="px-1.5 py-0.5 rounded-full bg-red-light text-red font-syne font-bold text-xs">NTI</span>
          )}
          {drug.is_veterinary && (
            <span className="px-1.5 py-0.5 rounded-full bg-green-light text-green font-syne font-bold text-xs">🐾</span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Interaction Checker ───────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  major: "bg-red-light border-red/30 text-red",
  moderate: "bg-amber-light border-amber/30 text-amber",
  minor: "bg-green-light border-green/20 text-green",
};

function InteractionChecker() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Drug[]>([]);
  const [selected, setSelected] = useState<Drug[]>([]);
  const [interactions, setInteractions] = useState<any[]>([]);
  const [checking, setChecking] = useState(false);
  const [showSugg, setShowSugg] = useState(false);

  useEffect(() => {
    if (!query.trim()) { setSuggestions([]); return; }
    const t = setTimeout(async () => {
      try {
        const res = await drugsApi.search(query);
        setSuggestions((res ?? []).slice(0, 6));
        setShowSugg(true);
      } catch { setSuggestions([]); }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  const addDrug = (d: Drug) => {
    if (selected.find((s) => s.id === d.id)) return;
    setSelected((prev) => [...prev, d]);
    setQuery(""); setSuggestions([]); setInteractions([]);
  };

  const checkInteractions = async () => {
    if (selected.length < 2) return;
    setChecking(true);
    try {
      const res = await drugsApi.checkInteractions(selected.map((d) => d.id));
      setInteractions(res?.interactions ?? []);
    } catch { setInteractions([]); }
    finally { setChecking(false); }
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="card p-5">
        <h2 className="font-syne font-bold text-sm text-ink mb-3">Drug Interaction Checker</h2>
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {selected.map((d) => (
              <span key={d.id} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-ink text-white font-syne font-semibold text-xs">
                {d.name}
                <button onClick={() => setSelected((p) => p.filter((x) => x.id !== d.id))} className="hover:text-red">×</button>
              </span>
            ))}
          </div>
        )}
        <div className="relative">
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} onFocus={() => setShowSugg(true)}
            placeholder="Type drug name to add…"
            className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink" />
          {showSugg && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 z-10 bg-surface border border-border rounded-lg shadow-lg mt-1">
              {suggestions.map((d) => (
                <button key={d.id} onClick={() => { addDrug(d); setShowSugg(false); }}
                  className="w-full text-left px-3 py-2 font-serif text-sm text-ink hover:bg-bg-2 transition-colors first:rounded-t-lg last:rounded-b-lg">
                  <span className="font-syne font-semibold">{d.name}</span>
                  <span className="text-ink-3 ml-2 text-xs">{d.drug_class}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <button onClick={checkInteractions} disabled={selected.length < 2 || checking} className="mt-3 btn-primary disabled:opacity-40 text-sm">
          {checking ? "Checking…" : `Check interactions (${selected.length} drugs)`}
        </button>
      </div>
      {interactions.length > 0 ? (
        <div className="space-y-3">
          <h3 className="font-syne font-bold text-sm text-ink">{interactions.length} interaction{interactions.length !== 1 ? "s" : ""} found</h3>
          {interactions.map((ix: any, i: number) => (
            <div key={i} className={`card p-4 border ${SEVERITY_COLORS[ix.severity] ?? "border-border"}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-syne font-bold text-sm">{ix.drug_a_name} + {ix.drug_b_name}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-syne font-bold border ${SEVERITY_COLORS[ix.severity] ?? ""}`}>{ix.severity?.toUpperCase()}</span>
              </div>
              {ix.mechanism && <p className="font-serif text-ink-2 text-xs mb-1"><strong>Mechanism:</strong> {ix.mechanism}</p>}
              {ix.clinical_effect && <p className="font-serif text-ink-2 text-xs mb-1"><strong>Effect:</strong> {ix.clinical_effect}</p>}
              {ix.management && <p className="font-serif text-xs text-ink"><strong>Management:</strong> {ix.management}</p>}
            </div>
          ))}
        </div>
      ) : !checking && selected.length >= 2 ? (
        <div className="card p-6 text-center">
          <div className="text-3xl mb-2">✅</div>
          <p className="font-syne font-bold text-sm text-ink">No significant interactions found</p>
          <p className="font-serif text-ink-3 text-xs mt-1">Always verify with current clinical guidelines</p>
        </div>
      ) : null}
      <p className="font-serif text-ink-3 text-xs text-center">⚕️ For educational use only.</p>
    </div>
  );
}

// ── Dose Calculator ───────────────────────────────────────────────────────────

function DoseCalculator() {
  const [form, setForm] = useState({ drug_name: "", weight_kg: "", age_years: "", renal_gfr: "", dose_per_kg: "", unit: "mg", max_dose: "" });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm((p) => ({ ...p, [key]: e.target.value }));

  const calculate = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setError(""); setResult(null);
    try {
      const res = await drugsApi.calculateDose({ drug_name: form.drug_name, weight_kg: parseFloat(form.weight_kg), age_years: form.age_years ? parseFloat(form.age_years) : undefined, renal_gfr: form.renal_gfr ? parseFloat(form.renal_gfr) : undefined, dose_per_kg: form.dose_per_kg ? parseFloat(form.dose_per_kg) : undefined, unit: form.unit, max_dose: form.max_dose ? parseFloat(form.max_dose) : undefined });
      setResult(res);
    } catch (err: any) { setError(err.response?.data?.detail ?? "Calculation failed"); }
    finally { setLoading(false); }
  };

  return (
    <div className="max-w-lg">
      <form onSubmit={calculate} className="card p-6 space-y-4">
        <h2 className="font-syne font-bold text-base text-ink">Dose Calculator</h2>
        <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Drug name *</label><input required type="text" value={form.drug_name} onChange={set("drug_name")} placeholder="e.g. Amoxicillin" className="input-field" /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Weight (kg) *</label><input required type="number" min="0.5" max="300" step="0.1" value={form.weight_kg} onChange={set("weight_kg")} placeholder="70" className="input-field" /></div>
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Age (years)</label><input type="number" min="0" max="120" value={form.age_years} onChange={set("age_years")} placeholder="optional" className="input-field" /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Dose per kg</label><input type="number" min="0" step="0.01" value={form.dose_per_kg} onChange={set("dose_per_kg")} placeholder="e.g. 25" className="input-field" /></div>
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Unit</label><select value={form.unit} onChange={set("unit")} className="input-field">{["mg","mcg","g","mg/kg","mcg/kg"].map((u) => <option key={u} value={u}>{u}</option>)}</select></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Max single dose</label><input type="number" min="0" step="0.1" value={form.max_dose} onChange={set("max_dose")} placeholder="optional" className="input-field" /></div>
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Renal GFR (mL/min)</label><input type="number" min="0" max="120" value={form.renal_gfr} onChange={set("renal_gfr")} placeholder="optional" className="input-field" /></div>
        </div>
        {error && <p className="font-serif text-red text-xs">{error}</p>}
        <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-40">{loading ? "Calculating…" : "Calculate dose"}</button>
      </form>
      {result && (
        <div className="card p-5 mt-4">
          <h3 className="font-syne font-bold text-sm text-ink mb-3">Result — {result.drug_name}</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between py-1.5 border-b border-border"><span className="font-serif text-xs text-ink-3">Calculated dose</span><span className="font-syne font-bold text-base text-ink">{result.calculated_dose} {result.unit}</span></div>
            {result.renal_adjustment && result.renal_adjustment !== "none" && <div className="flex items-center justify-between py-1.5 border-b border-border"><span className="font-serif text-xs text-ink-3">Renal adjustment</span><span className="font-syne font-bold text-sm text-amber">{result.renal_adjustment}</span></div>}
          </div>
          <p className="font-serif text-ink-3 text-xs mt-3">⚕️ Educational estimate only.</p>
        </div>
      )}
    </div>
  );
}

// ── Veterinary Dosing ─────────────────────────────────────────────────────────

function VeterinaryDosing() {
  const [species, setSpecies] = useState<any[]>([]);
  const [selectedSpecies, setSelectedSpecies] = useState("");
  const [drugQuery, setDrugQuery] = useState("");
  const [drugResults, setDrugResults] = useState<Drug[]>([]);
  const [selectedDrug, setSelectedDrug] = useState<Drug | null>(null);
  const [dosing, setDosing] = useState<any[]>([]);
  const [safety, setSafety] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showSugg, setShowSugg] = useState(false);

  useEffect(() => {
    import("@/lib/api").then(({ veterinaryApi }) =>
      veterinaryApi.getSpecies().then((s: any) => setSpecies(s ?? [])).catch(() => {})
    );
  }, []);

  useEffect(() => {
    if (!drugQuery.trim()) { setDrugResults([]); return; }
    const t = setTimeout(async () => {
      try { const res = await drugsApi.search(drugQuery); setDrugResults((res ?? []).slice(0, 6)); setShowSugg(true); }
      catch { setDrugResults([]); }
    }, 300);
    return () => clearTimeout(t);
  }, [drugQuery]);

  const selectDrug = async (drug: Drug) => {
    setSelectedDrug(drug); setDrugQuery(drug.name); setShowSugg(false);
    if (selectedSpecies) {
      setLoading(true);
      try {
        const { veterinaryApi } = await import("@/lib/api");
        const [d, s] = await Promise.all([
          veterinaryApi.getDrugDosing(drug.id, selectedSpecies).catch(() => []),
          veterinaryApi.checkSafety(drug.id, selectedSpecies).catch(() => null),
        ]);
        setDosing(d ?? []); setSafety(s);
      } finally { setLoading(false); }
    }
  };

  return (
    <div className="space-y-5 max-w-2xl">
      <div className="card p-5">
        <h2 className="font-syne font-bold text-sm text-ink mb-4">Veterinary Drug Dosing</h2>
        <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">Species</label>
        <div className="flex flex-wrap gap-2 mb-4">
          {species.length > 0 ? species.map((s: any) => (
            <button key={s.id} onClick={() => setSelectedSpecies(s.id)}
              className={`px-3 py-1.5 rounded-lg border font-syne font-semibold text-xs transition-all ${selectedSpecies === s.id ? "border-ink bg-ink text-white" : "border-border text-ink-2 hover:border-ink-3"}`}>
              {s.icon && <span className="mr-1">{s.icon}</span>}{s.name}
            </button>
          )) : ["🐕 Dog","🐈 Cat","🐎 Horse","🐄 Cattle"].map((s) => (
            <span key={s} className="px-3 py-1.5 rounded-lg border border-border font-syne font-semibold text-xs text-ink-3">{s}</span>
          ))}
        </div>
        <div className="relative">
          <input type="text" value={drugQuery} onChange={(e) => { setDrugQuery(e.target.value); setSelectedDrug(null); }} onFocus={() => setShowSugg(true)}
            placeholder="Search drug…" className="w-full px-3 py-2 rounded border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink" />
          {showSugg && drugResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 z-10 bg-surface border border-border rounded-lg shadow-lg mt-1">
              {drugResults.map((d) => (
                <button key={d.id} onClick={() => selectDrug(d)}
                  className="w-full text-left px-3 py-2 font-serif text-sm text-ink hover:bg-bg-2 transition-colors first:rounded-t-lg last:rounded-b-lg">
                  <span className="font-syne font-semibold">{d.name}</span>
                  <span className="text-ink-3 ml-2 text-xs">{d.drug_class}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      {safety && (
        <div className={`card p-4 border ${safety.is_toxic ? "border-red/30 bg-red-light" : "border-green/20 bg-green-light"}`}>
          <div className="flex items-center gap-2">
            <span className="text-xl">{safety.is_toxic ? "⚠️" : "✅"}</span>
            <div>
              <div className={`font-syne font-bold text-sm ${safety.is_toxic ? "text-red" : "text-green"}`}>{safety.is_toxic ? "Caution: Potential toxicity" : "Generally safe"}</div>
              {safety.toxicity_note && <div className="font-serif text-xs mt-0.5 text-ink-2">{safety.toxicity_note}</div>}
            </div>
          </div>
        </div>
      )}
      {loading && <div className="text-center py-6 font-serif text-ink-3 text-sm">Loading dosing data…</div>}
      {!loading && dosing.length > 0 && (
        <div className="card p-5">
          <h3 className="font-syne font-bold text-sm text-ink mb-3">Dosing: {selectedDrug?.name}</h3>
          <div className="space-y-3">
            {dosing.map((d: any, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-bg-2 space-y-1">
                <div className="flex items-center gap-3 flex-wrap">
                  {d.route && <span className="px-2 py-0.5 rounded bg-ink text-white font-syne font-bold text-xs">{d.route}</span>}
                  {d.dose && <span className="font-syne font-bold text-sm text-ink">{d.dose}</span>}
                  {d.frequency && <span className="font-serif text-ink-3 text-xs">{d.frequency}</span>}
                </div>
                {d.notes && <div className="font-serif text-xs text-ink-3 italic">{d.notes}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
      <p className="font-serif text-ink-3 text-xs text-center">🐾 For educational use only.</p>
    </div>
  );
}
