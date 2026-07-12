"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { API_URL } from "@/lib/api";
import { Activity, Search } from "lucide-react";

type LabValue = {
  name: string;
  full_name?: string;
  unit: string;
  ref?: string;
  male?: string;
  female?: string;
  critical_low?: string | null;
  critical_high?: string | null;
};

type LabPanels = Record<string, LabValue[]>;

type LabData = { species: string; panels: LabPanels };

const SPECIES_OPTIONS = [
  { value: "human", label: "Human" },
  { value: "dog",   label: "Dog 🐕" },
  { value: "cat",   label: "Cat 🐈" },
];

function criticalClass(val: string | null | undefined): string {
  if (!val) return "";
  return "text-red font-bold";
}

export default function LabValuesPage() {
  const [species, setSpecies] = useState("human");
  const [data, setData] = useState<LabData | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    setLoading(true);
    const token = localStorage.getItem("access_token");
    fetch(`${API_URL}/practice/lab-values?species=${species}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.ok ? r.json() : null)
      .then(setData)
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [species]);

  const filteredPanels = useMemo(() => {
    if (!data) return {};
    if (!query.trim()) return data.panels;
    const q = query.toLowerCase();
    const out: LabPanels = {};
    for (const [panel, values] of Object.entries(data.panels)) {
      const filtered = values.filter(
        (v) =>
          v.name.toLowerCase().includes(q) ||
          (v.full_name ?? "").toLowerCase().includes(q)
      );
      if (filtered.length > 0) out[panel] = filtered;
    }
    return out;
  }, [data, query]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-5">

        {/* Header */}
        <div className="flex items-center gap-2">
          <Link href="/practice" className="text-ink-3 hover:text-ink text-sm">← Practice</Link>
          <h1 className="font-syne font-black text-2xl text-ink flex items-center gap-2">
            <Activity size={20} /> Lab Reference Values
          </h1>
        </div>

        {/* Controls */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex gap-2">
            {SPECIES_OPTIONS.map((o) => (
              <button
                key={o.value}
                onClick={() => setSpecies(o.value)}
                className={`px-3 py-1.5 rounded-full text-xs font-syne font-semibold border transition-all ${
                  species === o.value
                    ? "bg-ink text-white border-ink"
                    : "border-border text-ink-2 hover:border-ink-3"
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
          <div className="relative flex-1 max-w-xs">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter (e.g. Hgb, Troponin…)"
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-border bg-surface font-syne text-xs text-ink placeholder-ink-3 focus:outline-none focus:border-ink"
            />
          </div>
        </div>

        {/* Tables */}
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 rounded-lg bg-surface-2 animate-pulse" />
            ))}
          </div>
        ) : !data ? (
          <p className="font-serif text-ink-3 text-sm text-center py-8">Failed to load data.</p>
        ) : Object.keys(filteredPanels).length === 0 ? (
          <p className="font-serif text-ink-3 text-sm text-center py-8">No results for &ldquo;{query}&rdquo;</p>
        ) : (
          Object.entries(filteredPanels).map(([panel, values]) => (
            <section key={panel}>
              <h2 className="font-syne font-bold text-sm text-ink mb-2 capitalize">
                {panel.replace(/_/g, " ")}
              </h2>
              <div className="card overflow-x-auto">
                <table className="w-full text-xs font-syne">
                  <thead>
                    <tr className="border-b border-border text-ink-3 text-left">
                      <th className="p-2 font-semibold">Name</th>
                      <th className="p-2 font-semibold">Unit</th>
                      <th className="p-2 font-semibold">Reference Range</th>
                      <th className="p-2 font-semibold text-red">Critical Low</th>
                      <th className="p-2 font-semibold text-red">Critical High</th>
                    </tr>
                  </thead>
                  <tbody>
                    {values.map((v) => {
                      const range = v.ref
                        ? v.ref
                        : v.male && v.female
                        ? `M: ${v.male} / F: ${v.female}`
                        : v.male ?? v.female ?? "—";
                      return (
                        <tr key={v.name} className="border-b border-border hover:bg-surface-2 transition-colors">
                          <td className="p-2">
                            <div className="font-bold text-ink">{v.name}</div>
                            {v.full_name && v.full_name !== v.name && (
                              <div className="text-ink-3 text-xs font-serif">{v.full_name}</div>
                            )}
                          </td>
                          <td className="p-2 font-mono text-ink-3">{v.unit}</td>
                          <td className="p-2 text-ink-2">{range}</td>
                          <td className={`p-2 ${criticalClass(v.critical_low)}`}>
                            {v.critical_low ?? "—"}
                          </td>
                          <td className={`p-2 ${criticalClass(v.critical_high)}`}>
                            {v.critical_high ?? "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          ))
        )}

        {/* Source */}
        {data && (
          <p className="font-serif text-xs text-ink-3/70">
            Source: Harrison&apos;s Principles of Internal Medicine 21st Ed.; Merck Veterinary Manual 2023.
            Values are approximate — verify with your institution&apos;s reference ranges.
          </p>
        )}
      </div>
    </div>
  );
}
