"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, drugsApi, veterinaryApi } from "@/lib/api";

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
  is_veterinary?: boolean;
};

type Tab = "search" | "interactions" | "dose" | "vet";

export default function DrugsPage() {
  const [tab, setTab] = useState<Tab>("search");

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
      <h1 className="font-syne font-black text-2xl text-ink mb-1">Drug Database</h1>
      <p className="font-serif text-ink-3 text-sm mb-5">Search medications, dosages, interactions, and pharmacology</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-bg-2 p-1 rounded-lg w-fit flex-wrap">
        {(["search", "interactions", "dose", "vet"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded font-syne font-semibold text-sm transition-all capitalize ${
              tab === t ? "bg-white shadow text-ink" : "text-ink-3 hover:text-ink"
            }`}
          >
            {t === "search" ? "🔍 Search" : t === "interactions" ? "⚡ Interactions" : t === "dose" ? "⚖️ Dose Calc" : "🐾 Veterinary"}
          </button>
        ))}
      </div>

      {tab === "search" && <DrugSearch />}
      {tab === "interactions" && <InteractionChecker />}
      {tab === "dose" && <DoseCalculator />}
      {tab === "vet" && <VeterinaryDosing />}
    </div>
  );
}

// ── Drug Search ──────────────────────────────────────────────────────────────

function DrugSearch() {
  const router = useRouter();
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const doSearch = async (q: string) => {
    if (!q.trim()) { setDrugs([]); return; }
    setLoading(true);
    try {
      const res = await drugsApi.search(q);
      setDrugs(res.data ?? []);
    } catch {
      setDrugs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => doSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  return (
    <>
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search drugs (e.g. metformin, amoxicillin)…"
        className="w-full px-4 py-3 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors mb-6"
      />
      {loading && <div className="text-center py-8 font-serif text-ink-3 text-sm">Searching…</div>}
      <div className="grid gap-3">
        {drugs.map((d) => (
          <div
            key={d.id}
            onClick={() => router.push(`/drugs/${d.id}`)}
            className="card p-4 cursor-pointer hover:border-ink transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-syne font-bold text-sm text-ink">{d.name}</div>
                <div className="font-serif text-ink-3 text-xs mt-0.5">{d.generic_name} · {d.drug_class}</div>
              </div>
              <div className="flex gap-1.5 flex-shrink-0">
                {d.is_high_yield && (
                  <span className="inline-block px-2 py-0.5 rounded-full bg-amber-light text-amber font-syne font-semibold text-xs">⭐ HY</span>
                )}
                {d.is_veterinary && (
                  <span className="inline-block px-2 py-0.5 rounded-full bg-green-light text-green font-syne font-semibold text-xs">🐾</span>
                )}
              </div>
            </div>
          </div>
        ))}
        {!loading && search && drugs.length === 0 && (
          <p className="text-center font-serif text-ink-3 text-sm py-8">No drugs found.</p>
        )}
        {!search && (
          <p className="text-center font-serif text-ink-3 text-sm py-12">Start typing to search the drug database.</p>
        )}
      </div>
    </>
  );
}

// ── Interaction Checker ──────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  major: "bg-red-light border-red/30 text-red",
  moderate: "bg-amber-light border-amber/30 text-amber",
  minor: "bg-green-light border-green/20 text-green",
};

function InteractionChecker() {
  const [drugs, setDrugs] = useState<Drug[]>([]);
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
        setSuggestions((res.data ?? []).slice(0, 6));
        setShowSugg(true);
      } catch {
        setSuggestions([]);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  const addDrug = (d: Drug) => {
    if (selected.find((s) => s.id === d.id)) return;
    setSelected((prev) => [...prev, d]);
    setQuery("");
    setSuggestions([]);
    setInteractions([]);
  };

  const removeDrug = (id: string) => {
    setSelected((prev) => prev.filter((d) => d.id !== id));
    setInteractions([]);
  };

  const checkInteractions = async () => {
    if (selected.length < 2) return;
    setChecking(true);
    try {
      const res = await drugsApi.checkInteractions(selected.map((d) => d.id));
      setInteractions(res.data?.interactions ?? []);
    } catch {
      setInteractions([]);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h2 className="font-syne font-bold text-sm text-ink mb-3">Add drugs to check</h2>

        {/* Selected drugs */}
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {selected.map((d) => (
              <span key={d.id} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-ink text-white font-syne font-semibold text-xs">
                {d.name}
                <button onClick={() => removeDrug(d.id)} className="hover:text-red transition-colors">×</button>
              </span>
            ))}
          </div>
        )}

        {/* Search input */}
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setShowSugg(true)}
            placeholder="Type drug name to add…"
            className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink"
          />
          {showSugg && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 z-10 bg-surface border border-border rounded-lg shadow-lg mt-1">
              {suggestions.map((d) => (
                <button
                  key={d.id}
                  onClick={() => { addDrug(d); setShowSugg(false); }}
                  className="w-full text-left px-3 py-2 font-serif text-sm text-ink hover:bg-bg-2 transition-colors first:rounded-t-lg last:rounded-b-lg"
                >
                  <span className="font-syne font-semibold">{d.name}</span>
                  <span className="text-ink-3 ml-2 text-xs">{d.drug_class}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={checkInteractions}
          disabled={selected.length < 2 || checking}
          className="mt-3 btn-primary disabled:opacity-40 text-sm"
        >
          {checking ? "Checking…" : `Check interactions (${selected.length} drugs)`}
        </button>
        {selected.length < 2 && (
          <p className="font-serif text-ink-3 text-xs mt-1.5">Add at least 2 drugs to check</p>
        )}
      </div>

      {/* Results */}
      {interactions.length > 0 ? (
        <div className="space-y-3">
          <h3 className="font-syne font-bold text-sm text-ink">{interactions.length} interaction{interactions.length !== 1 ? "s" : ""} found</h3>
          {interactions.map((ix: any, i: number) => (
            <div key={i} className={`card p-4 border ${SEVERITY_COLORS[ix.severity] ?? "border-border"}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-syne font-bold text-sm">
                  {ix.drug_a_name} + {ix.drug_b_name}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-syne font-bold border ${SEVERITY_COLORS[ix.severity] ?? ""}`}>
                  {ix.severity?.toUpperCase()}
                </span>
              </div>
              {ix.mechanism && <p className="font-serif text-ink-2 text-xs mb-1"><strong>Mechanism:</strong> {ix.mechanism}</p>}
              {ix.clinical_effect && <p className="font-serif text-ink-2 text-xs mb-1"><strong>Effect:</strong> {ix.clinical_effect}</p>}
              {ix.management && <p className="font-serif text-ink text-xs"><strong>Management:</strong> {ix.management}</p>}
            </div>
          ))}
        </div>
      ) : interactions !== null && !checking && selected.length >= 2 ? (
        <div className="card p-6 text-center">
          <div className="text-3xl mb-2">✅</div>
          <p className="font-syne font-bold text-sm text-ink">No significant interactions found</p>
          <p className="font-serif text-ink-3 text-xs mt-1">Always verify with current clinical guidelines</p>
        </div>
      ) : null}

      <p className="font-serif text-ink-3 text-xs text-center">
        ⚕️ For educational use only. Always verify interactions with current references.
      </p>
    </div>
  );
}

// ── Dose Calculator ───────────────────────────────────────────────────────────

function DoseCalculator() {
  const [form, setForm] = useState({
    drug_name: "",
    weight_kg: "",
    age_years: "",
    renal_gfr: "",
    dose_per_kg: "",
    unit: "mg",
    max_dose: "",
  });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const calculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.post("/drugs/calculate-dose", {
        drug_name: form.drug_name,
        weight_kg: parseFloat(form.weight_kg),
        age_years: form.age_years ? parseFloat(form.age_years) : undefined,
        renal_gfr: form.renal_gfr ? parseFloat(form.renal_gfr) : undefined,
        dose_per_kg: form.dose_per_kg ? parseFloat(form.dose_per_kg) : undefined,
        unit: form.unit,
        max_dose: form.max_dose ? parseFloat(form.max_dose) : undefined,
      });
      setResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Calculation failed");
    } finally {
      setLoading(false);
    }
  };

  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((p) => ({ ...p, [key]: e.target.value }));

  return (
    <div className="max-w-lg">
      <form onSubmit={calculate} className="card p-6 space-y-4">
        <h2 className="font-syne font-bold text-base text-ink">Dose Calculator</h2>
        <p className="font-serif text-ink-3 text-xs -mt-2">
          Calculates weight-adjusted dose with optional renal adjustment
        </p>

        <Field label="Drug name *">
          <input
            required
            type="text"
            value={form.drug_name}
            onChange={set("drug_name")}
            placeholder="e.g. Amoxicillin"
            className="input-field"
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Weight (kg) *">
            <input
              required
              type="number"
              min="0.5"
              max="300"
              step="0.1"
              value={form.weight_kg}
              onChange={set("weight_kg")}
              placeholder="70"
              className="input-field"
            />
          </Field>
          <Field label="Age (years)">
            <input
              type="number"
              min="0"
              max="120"
              value={form.age_years}
              onChange={set("age_years")}
              placeholder="optional"
              className="input-field"
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Dose per kg">
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.dose_per_kg}
              onChange={set("dose_per_kg")}
              placeholder="e.g. 25"
              className="input-field"
            />
          </Field>
          <Field label="Unit">
            <select value={form.unit} onChange={set("unit")} className="input-field">
              {["mg", "mcg", "g", "mg/kg", "mcg/kg"].map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Max single dose">
            <input
              type="number"
              min="0"
              step="0.1"
              value={form.max_dose}
              onChange={set("max_dose")}
              placeholder="optional"
              className="input-field"
            />
          </Field>
          <Field label="Renal GFR (mL/min)">
            <input
              type="number"
              min="0"
              max="120"
              value={form.renal_gfr}
              onChange={set("renal_gfr")}
              placeholder="optional"
              className="input-field"
            />
          </Field>
        </div>

        {error && <p className="font-serif text-red text-xs">{error}</p>}
        <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-40">
          {loading ? "Calculating…" : "Calculate dose"}
        </button>
      </form>

      {result && (
        <div className="card p-5 mt-4">
          <h3 className="font-syne font-bold text-sm text-ink mb-3">Result — {result.drug_name}</h3>
          <div className="space-y-2">
            <ResultRow label="Calculated dose" value={`${result.calculated_dose} ${result.unit}`} highlight />
            {result.max_dose_applied && (
              <ResultRow label="Capped at max dose" value={`${result.final_dose} ${result.unit}`} />
            )}
            <ResultRow label="Patient weight" value={`${result.weight_kg} kg`} />
            {result.renal_adjustment && (
              <ResultRow
                label="Renal adjustment"
                value={result.renal_adjustment}
                warn={result.renal_adjustment !== "none"}
              />
            )}
          </div>
          <p className="font-serif text-ink-3 text-xs mt-3">
            ⚕️ Educational estimate only. Verify with current prescribing information.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Veterinary Dosing ─────────────────────────────────────────────────────────

function VeterinaryDosing() {
  const [species, setSpecies] = useState<any[]>([]);
  const [selectedSpecies, setSelectedSpecies] = useState<string>("");
  const [drugQuery, setDrugQuery] = useState("");
  const [drugResults, setDrugResults] = useState<Drug[]>([]);
  const [selectedDrug, setSelectedDrug] = useState<Drug | null>(null);
  const [dosing, setDosing] = useState<any[]>([]);
  const [safety, setSafety] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showSugg, setShowSugg] = useState(false);
  const [zoonoses, setZoonoses] = useState<any[]>([]);
  const [showZoonoses, setShowZoonoses] = useState(false);

  useEffect(() => {
    veterinaryApi.getSpecies().then((s: any) => setSpecies(s ?? [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!drugQuery.trim()) { setDrugResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const res = await drugsApi.search(drugQuery);
        setDrugResults((res.data ?? []).slice(0, 6));
        setShowSugg(true);
      } catch { setDrugResults([]); }
    }, 300);
    return () => clearTimeout(t);
  }, [drugQuery]);

  const selectDrug = async (drug: Drug) => {
    setSelectedDrug(drug);
    setDrugQuery(drug.name);
    setShowSugg(false);
    setDosing([]);
    setSafety(null);
    if (selectedSpecies) fetchDosing(drug.id, selectedSpecies);
  };

  const fetchDosing = async (drugId: string, speciesId: string) => {
    setLoading(true);
    try {
      const [dosingRes, safetyRes] = await Promise.all([
        veterinaryApi.getDrugDosing(drugId, speciesId).catch(() => []),
        veterinaryApi.checkSafety(drugId, speciesId).catch(() => null),
      ]);
      setDosing(dosingRes ?? []);
      setSafety(safetyRes);
    } finally {
      setLoading(false);
    }
  };

  const handleSpeciesChange = (id: string) => {
    setSelectedSpecies(id);
    setSafety(null);
    setDosing([]);
    if (selectedDrug && id) fetchDosing(selectedDrug.id, id);
  };

  const loadZoonoses = async () => {
    if (zoonoses.length) { setShowZoonoses(true); return; }
    try {
      const data = await veterinaryApi.getZoonoses();
      setZoonoses(data.zoonoses ?? []);
      setShowZoonoses(true);
    } catch {}
  };

  return (
    <div className="space-y-5">
      {/* Species selector */}
      <div className="card p-5">
        <h2 className="font-syne font-bold text-sm text-ink mb-3">Veterinary Drug Dosing</h2>
        <div className="space-y-4">
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">Select Species</label>
            <div className="flex flex-wrap gap-2">
              {species.map((s: any) => (
                <button
                  key={s.id}
                  onClick={() => handleSpeciesChange(s.id)}
                  className={`px-3 py-1.5 rounded-lg border font-syne font-semibold text-xs transition-all ${
                    selectedSpecies === s.id
                      ? "border-ink bg-ink text-white"
                      : "border-border text-ink-2 hover:border-ink-3"
                  }`}
                >
                  {s.icon && <span className="mr-1">{s.icon}</span>}{s.name}
                </button>
              ))}
              {species.length === 0 && (
                <div className="flex flex-wrap gap-2">
                  {["🐕 Dog", "🐈 Cat", "🐎 Horse", "🐄 Cattle"].map((s) => (
                    <span key={s} className="px-3 py-1.5 rounded-lg border border-border font-syne font-semibold text-xs text-ink-3">
                      {s}
                    </span>
                  ))}
                  <span className="font-serif text-ink-3 text-xs self-center">(Add species data to database)</span>
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Search Drug</label>
            <div className="relative">
              <input
                type="text"
                value={drugQuery}
                onChange={(e) => { setDrugQuery(e.target.value); setSelectedDrug(null); }}
                onFocus={() => setShowSugg(true)}
                placeholder="Type drug name…"
                className="w-full px-3 py-2 rounded border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink"
              />
              {showSugg && drugResults.length > 0 && (
                <div className="absolute top-full left-0 right-0 z-10 bg-surface border border-border rounded-lg shadow-lg mt-1">
                  {drugResults.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => selectDrug(d)}
                      className="w-full text-left px-3 py-2 font-serif text-sm text-ink hover:bg-bg-2 transition-colors first:rounded-t-lg last:rounded-b-lg"
                    >
                      <span className="font-syne font-semibold">{d.name}</span>
                      <span className="text-ink-3 ml-2 text-xs">{d.drug_class}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Safety banner */}
      {safety && (
        <div className={`card p-4 border ${safety.is_toxic ? "border-red/30 bg-red-light" : "border-green/20 bg-green-light"}`}>
          <div className="flex items-center gap-2">
            <span className="text-xl">{safety.is_toxic ? "⚠️" : "✅"}</span>
            <div>
              <div className={`font-syne font-bold text-sm ${safety.is_toxic ? "text-red" : "text-green"}`}>
                {safety.is_toxic ? "Caution: Potential toxicity" : "Generally safe for this species"}
              </div>
              {safety.toxicity_note && (
                <div className="font-serif text-xs mt-0.5 text-ink-2">{safety.toxicity_note}</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Dosing table */}
      {loading && <div className="text-center py-6 font-serif text-ink-3 text-sm">Loading dosing data…</div>}
      {!loading && dosing.length > 0 && (
        <div className="card p-5">
          <h3 className="font-syne font-bold text-sm text-ink mb-3">
            Dosing: {selectedDrug?.name} in {species.find((s: any) => s.id === selectedSpecies)?.name ?? "selected species"}
          </h3>
          <div className="space-y-3">
            {dosing.map((d: any, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-bg-2 space-y-1">
                <div className="flex items-center gap-3 flex-wrap">
                  {d.route && <span className="px-2 py-0.5 rounded bg-ink text-white font-syne font-bold text-xs">{d.route}</span>}
                  {d.dose && <span className="font-syne font-bold text-sm text-ink">{d.dose}</span>}
                  {d.frequency && <span className="font-serif text-ink-3 text-xs">{d.frequency}</span>}
                </div>
                {d.max_dose && <div className="font-serif text-xs text-ink-2">Max: {d.max_dose}</div>}
                {d.notes && <div className="font-serif text-xs text-ink-3 italic">{d.notes}</div>}
                {d.source && <div className="font-serif text-xs text-ink-3">Source: {d.source}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
      {!loading && selectedDrug && selectedSpecies && dosing.length === 0 && !loading && (
        <div className="card p-6 text-center">
          <p className="font-serif text-ink-3 text-sm">No dosing data available for this combination.</p>
        </div>
      )}

      {/* Zoonoses reference */}
      <div className="card p-4">
        <button
          onClick={loadZoonoses}
          className="w-full flex items-center justify-between font-syne font-bold text-sm text-ink"
        >
          <span>🦠 Zoonotic Disease Reference</span>
          <span className="text-ink-3">{showZoonoses ? "▲" : "▼"}</span>
        </button>
        {showZoonoses && zoonoses.length > 0 && (
          <div className="mt-4 space-y-3">
            {zoonoses.map((z: any, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-bg-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-syne font-bold text-sm text-ink">{z.name}</div>
                    {z.name_ru && <div className="font-serif text-ink-3 text-xs">{z.name_ru}</div>}
                  </div>
                  <span className="font-serif text-xs text-ink-3 shrink-0">{z.pathogen}</span>
                </div>
                <div className="mt-2 space-y-0.5">
                  <div className="font-serif text-xs text-ink-2"><strong>Transmission:</strong> {z.transmission}</div>
                  <div className="font-serif text-xs text-ink-2"><strong>Species:</strong> {z.species?.join(", ")}</div>
                  <div className="font-serif text-xs text-ink-2"><strong>Prevention:</strong> {z.prevention}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="font-serif text-ink-3 text-xs text-center">
        🐾 For educational use only. Always consult current veterinary formularies for clinical dosing.
      </p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">{label}</label>
      {children}
    </div>
  );
}

function ResultRow({ label, value, highlight, warn }: { label: string; value: string; highlight?: boolean; warn?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
      <span className="font-serif text-xs text-ink-3">{label}</span>
      <span className={`font-syne font-bold text-sm ${highlight ? "text-ink text-base" : warn ? "text-amber" : "text-ink-2"}`}>
        {value}
      </span>
    </div>
  );
}

