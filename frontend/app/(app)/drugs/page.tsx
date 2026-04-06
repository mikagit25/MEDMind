"use client";

import { useState, useEffect } from "react";
import { contentApi } from "@/lib/api";

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
};

export default function DrugsPage() {
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Drug | null>(null);
  const [loading, setLoading] = useState(false);

  const doSearch = async (q: string) => {
    if (!q.trim()) { setDrugs([]); return; }
    setLoading(true);
    try {
      const res = await contentApi.searchDrugs(q);
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
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
      <h1 className="font-syne font-black text-2xl text-ink mb-2">Drug Database</h1>
      <p className="font-serif text-ink-3 text-sm mb-6">Search medications, dosages, interactions, and pharmacology</p>

      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search drugs (e.g. metformin, amoxicillin)…"
        className="w-full px-4 py-3 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors mb-6"
      />

      {loading && (
        <div className="text-center py-8 font-serif text-ink-3 text-sm">Searching…</div>
      )}

      {!selected ? (
        <div className="grid gap-3">
          {drugs.map((d) => (
            <div
              key={d.id}
              onClick={() => setSelected(d)}
              className="card p-4 cursor-pointer hover:border-ink transition-colors"
            >
              <div className="font-syne font-bold text-sm text-ink">{d.name}</div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">{d.generic_name} · {d.drug_class}</div>
            </div>
          ))}
          {!loading && search && drugs.length === 0 && (
            <p className="text-center font-serif text-ink-3 text-sm py-8">No drugs found. Try a different search term.</p>
          )}
          {!search && (
            <p className="text-center font-serif text-ink-3 text-sm py-12">Start typing to search the drug database.</p>
          )}
        </div>
      ) : (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="font-syne font-black text-xl text-ink">{selected.name}</h2>
              <div className="font-serif text-ink-3 text-sm">{selected.generic_name}</div>
            </div>
            <button onClick={() => setSelected(null)} className="text-ink-3 font-syne text-xs hover:text-ink">
              ← Back
            </button>
          </div>

          <div className="inline-flex items-center px-2.5 py-1 rounded-full bg-blue-light text-blue font-syne font-semibold text-xs mb-5">
            {selected.drug_class}
          </div>

          <Section title="Mechanism of Action">{selected.mechanism}</Section>

          {selected.dosing && Object.keys(selected.dosing).length > 0 && (
            <Section title="Dosage">
              {Object.entries(selected.dosing).map(([route, dose]) => (
                <div key={route}><strong className="text-ink-2">{route}:</strong> {dose as string}</div>
              ))}
            </Section>
          )}

          {selected.indications && selected.indications.length > 0 && (
            <ListSection title="Indications" items={selected.indications} color="text-green" />
          )}
          {selected.contraindications && selected.contraindications.length > 0 && (
            <ListSection title="Contraindications" items={selected.contraindications} color="text-red" />
          )}
          {selected.adverse_effects && (
            <div className="mb-4">
              <div className="font-syne font-bold text-xs text-ink-2 uppercase mb-1.5">Adverse Effects</div>
              {Object.entries(selected.adverse_effects).map(([category, effects]) => (
                <div key={category} className="mb-1.5">
                  <span className="font-syne font-semibold text-xs text-amber">{category}: </span>
                  <span className="font-serif text-sm text-ink">{(effects as string[]).join(", ")}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="font-syne font-bold text-xs text-ink-2 uppercase mb-1.5">{title}</div>
      <div className="font-serif text-ink text-sm leading-relaxed">{children}</div>
    </div>
  );
}

function ListSection({ title, items, color }: { title: string; items: string[]; color: string }) {
  return (
    <div className="mb-4">
      <div className="font-syne font-bold text-xs text-ink-2 uppercase mb-1.5">{title}</div>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className={`font-serif text-sm ${color} flex gap-2`}>
            <span>•</span><span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
