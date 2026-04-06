"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { contentApi, progressApi } from "@/lib/api";

type Specialty = { id: string; name: string; module_count: number };
type Module = { id: string; title: string; code: string };
type Case = {
  id: string;
  title: string;
  presentation: string;
  difficulty: string;
  specialty?: string;
};
type CaseDetail = Case & {
  vitals?: Record<string, string | number>;
  diagnosis?: string;
  differential_diagnosis?: string[];
  management?: string[];
  teaching_points?: string[];
};

function CasesInner() {
  const searchParams = useSearchParams();
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState("");
  const [modules, setModules] = useState<Module[]>([]);
  const [moduleId, setModuleId] = useState("");
  const [cases, setCases] = useState<Case[]>([]);
  const [selected, setSelected] = useState<CaseDetail | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const moduleParam = searchParams.get("module");
    contentApi.getSpecialties().then((r) => setSpecialties(r.data ?? []));
    if (moduleParam) {
      // Direct link from module page — load cases for that module immediately
      loadCases(moduleParam);
    }
  }, [searchParams]);

  const loadModules = async (specId: string) => {
    setSelectedSpecialty(specId);
    setModuleId("");
    setCases([]);
    setSelected(null);
    setFeedback(null);
    if (!specId) return;
    const res = await contentApi.getModules(specId);
    setModules(res.data ?? []);
  };

  const loadCases = async (mid: string) => {
    setModuleId(mid);
    setSelected(null);
    setFeedback(null);
    if (!mid) return;
    const res = await contentApi.getCases(mid);
    setCases(res.data ?? []);
  };

  const openCase = async (caseId: string) => {
    const res = await contentApi.getCase(caseId);
    setSelected(res.data);
    setAnswer("");
    setFeedback(null);
  };

  const submit = async () => {
    if (!answer.trim() || !selected) return;
    setLoading(true);
    try {
      const res = await progressApi.completeCase(selected.id, answer);
      setFeedback(res.data);
    } catch {
      setFeedback({ correct: false, explanation: "Could not evaluate answer." });
    } finally {
      setLoading(false);
    }
  };

  const diffColor: Record<string, string> = {
    easy: "bg-green-light text-green",
    medium: "bg-amber-light text-amber",
    hard: "bg-red-light text-red",
  };

  const formatVitals = (vitals: Record<string, string | number>) =>
    Object.entries(vitals)
      .map(([k, v]) => `${k}: ${v}`)
      .join(" · ");

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
      <h1 className="font-syne font-black text-2xl text-ink mb-2">Clinical Cases</h1>
      <p className="font-serif text-ink-3 text-sm mb-6">
        Practice clinical reasoning with realistic patient scenarios
      </p>

      {/* Selectors */}
      <div className="flex gap-3 mb-6 flex-wrap">
        <select
          value={selectedSpecialty}
          onChange={(e) => loadModules(e.target.value)}
          className="px-3 py-2 rounded border border-border bg-surface text-ink font-syne text-sm focus:outline-none focus:border-ink"
        >
          <option value="">Select specialty…</option>
          {specialties.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>

        {modules.length > 0 && (
          <select
            value={moduleId}
            onChange={(e) => loadCases(e.target.value)}
            className="px-3 py-2 rounded border border-border bg-surface text-ink font-syne text-sm focus:outline-none focus:border-ink"
          >
            <option value="">Select module…</option>
            {modules.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title}
              </option>
            ))}
          </select>
        )}
      </div>

      {!selected ? (
        <div className="grid gap-3">
          {cases.length === 0 && moduleId && (
            <p className="font-serif text-ink-3 text-sm">
              No cases available for this module.
            </p>
          )}
          {cases.map((c) => (
            <div
              key={c.id}
              onClick={() => openCase(c.id)}
              className="card p-4 cursor-pointer hover:border-ink transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-syne font-bold text-sm text-ink">{c.title}</div>
                  <div className="font-serif text-ink-3 text-xs mt-0.5 line-clamp-2">
                    {c.presentation}
                  </div>
                </div>
                <span
                  className={`badge text-xs ml-3 flex-shrink-0 ${
                    diffColor[c.difficulty] ?? "bg-surface-2 text-ink-3"
                  }`}
                >
                  {c.difficulty}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-syne font-bold text-lg text-ink">{selected.title}</h2>
            <button
              onClick={() => setSelected(null)}
              className="text-ink-3 font-syne text-xs hover:text-ink"
            >
              ← Back
            </button>
          </div>

          {/* Presentation */}
          <div className="font-serif text-ink text-sm leading-relaxed mb-4">
            {selected.presentation}
          </div>

          {/* Vitals */}
          {selected.vitals && Object.keys(selected.vitals).length > 0 && (
            <div className="bg-bg rounded p-3 mb-4 font-serif text-ink-2 text-xs">
              <span className="font-syne font-bold text-ink text-xs">Vitals: </span>
              {formatVitals(selected.vitals)}
            </div>
          )}

          {/* Differential */}
          {selected.differential_diagnosis && selected.differential_diagnosis.length > 0 && (
            <div className="mb-4">
              <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-1">
                Differential Diagnosis
              </div>
              <ul className="list-disc list-inside font-serif text-ink-2 text-sm space-y-0.5">
                {selected.differential_diagnosis.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </div>
          )}

          {!feedback ? (
            <>
              <div className="font-syne font-bold text-sm text-ink mb-2">
                What is your diagnosis and management plan?
              </div>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={5}
                className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink resize-none mb-3"
                placeholder="Your clinical assessment…"
              />
              <button
                onClick={submit}
                disabled={loading || !answer.trim()}
                className="btn-primary disabled:opacity-40"
              >
                {loading ? "Evaluating…" : "Submit Answer"}
              </button>
            </>
          ) : (
            <div
              className={`rounded p-4 ${feedback.correct ? "bg-green-light" : "bg-red-light"}`}
            >
              <div
                className={`font-syne font-bold text-sm mb-1 ${
                  feedback.correct ? "text-green" : "text-red"
                }`}
              >
                {feedback.correct ? "✓ Correct" : "✗ Review needed"}
              </div>
              <div className="font-serif text-ink text-sm leading-relaxed">
                {feedback.explanation}
              </div>
              {feedback.xp_gained > 0 && (
                <div className="font-syne font-semibold text-xs text-amber-2 mt-2">
                  +{feedback.xp_gained} XP
                </div>
              )}
              <button
                onClick={() => {
                  setSelected(null);
                  setFeedback(null);
                }}
                className="btn-primary mt-3"
              >
                Next Case
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CasesPage() {
  return (
    <Suspense fallback={<div className="flex-1 flex items-center justify-center"><span className="font-serif text-ink-3 text-sm animate-pulse">Loading…</span></div>}>
      <CasesInner />
    </Suspense>
  );
}
