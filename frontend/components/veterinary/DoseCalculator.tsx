"use client";

import { useState } from "react";
import { drugsApi } from "@/lib/api";
import { SpeciesSelector } from "./SpeciesSelector";
import { useT } from "@/lib/i18n";

interface DoseResult {
  drug_name: string;
  species: string;
  weight_kg: number;
  dose_per_kg: number;
  total_dose: number;
  unit: string;
  frequency: string;
  warnings: string[];
}

interface Props {
  drugId?: string;
  drugName?: string;
}

export function DoseCalculator({ drugId, drugName }: Props) {
  const [weight, setWeight]     = useState<string>("");
  const [species, setSpecies]   = useState<string | null>(null);
  const [age, setAge]           = useState<string>("");
  const [result, setResult]     = useState<DoseResult | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const calculate = async () => {
    if (!weight || !species || !drugId) {
      setError("Please select a species and enter weight.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await drugsApi.calculateDose({
        drug_id: drugId,
        species_id: species,
        weight_kg: parseFloat(weight),
        age_years: age ? parseFloat(age) : undefined,
      });
      setResult(res);
    } catch (e: any) {
      setError(e?.message ?? "Calculation failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-5 space-y-5">
      <h3 className="font-syne font-bold text-base text-ink">
        Dose Calculator {drugName ? `— ${drugName}` : ""}
      </h3>

      <div>
        <label className="text-xs font-semibold text-ink-3 uppercase tracking-wide mb-2 block">Species</label>
        <SpeciesSelector value={species} onChange={setSpecies} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-semibold text-ink-3 mb-1 block">Weight (kg)</label>
          <input
            type="number"
            value={weight}
            onChange={e => setWeight(e.target.value)}
            placeholder="e.g. 25"
            min="0.1"
            step="0.1"
            className="input w-full"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-ink-3 mb-1 block">Age (years, optional)</label>
          <input
            type="number"
            value={age}
            onChange={e => setAge(e.target.value)}
            placeholder="e.g. 3"
            min="0"
            step="0.5"
            className="input w-full"
          />
        </div>
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}

      <button onClick={calculate} disabled={loading || !drugId} className="btn-primary w-full">
        {loading ? "Calculating…" : "Calculate Dose"}
      </button>

      {result && (
        <div className="bg-surface-2 rounded-xl p-4 space-y-2">
          <div className="font-syne font-bold text-ink">{result.drug_name}</div>
          <div className="text-sm text-ink">
            <span className="text-2xl font-bold text-accent">{result.total_dose} {result.unit}</span>
            <span className="text-ink-3 ml-2">({result.frequency})</span>
          </div>
          <div className="text-xs text-ink-3">
            Based on {result.dose_per_kg} {result.unit}/kg × {result.weight_kg} kg
          </div>
          {result.warnings?.length > 0 && (
            <div className="mt-3 space-y-1">
              {result.warnings.map((w, i) => (
                <div key={i} className="text-xs text-amber-700 bg-amber-50 dark:bg-amber-950 dark:text-amber-300 rounded px-3 py-1.5">
                  ⚠️ {w}
                </div>
              ))}
            </div>
          )}
          <div className="text-xs text-ink-3 mt-2 italic">
            For educational purposes only. Always verify with current guidelines.
          </div>
        </div>
      )}
    </div>
  );
}
