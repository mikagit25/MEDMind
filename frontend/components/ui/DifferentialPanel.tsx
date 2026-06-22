"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle, List, FlaskConical, ChevronRight, Loader2 } from "lucide-react";
import { API_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import ReactMarkdown from "react-markdown";

interface DifferentialItem {
  diagnosis: string;
  icd?: string;
  reasoning: string;
  next_steps?: string;
}

interface ExpandedItem {
  diagnosis: string;
  icd?: string;
  reasoning: string;
}

interface CantMissItem {
  diagnosis: string;
  icd?: string;
  urgency: "immediate" | "urgent" | "soon";
  red_flags: string;
  action: string;
}

interface DifferentialResult {
  reasoning: string;
  most_likely: DifferentialItem[];
  expanded: ExpandedItem[];
  cant_miss: CantMissItem[];
  recommended_workup: string[];
  pubmed_refs?: { pmid: string; title: string; url: string; year: string }[];
  model?: string;
}

const URGENCY_STYLE: Record<string, string> = {
  immediate: "bg-red/10 border-red text-red",
  urgent:    "bg-amber/10 border-amber text-amber-700",
  soon:      "bg-yellow/10 border-yellow-400 text-yellow-700",
};

export function DifferentialPanel() {
  const { user } = useAuthStore();
  const [caseText, setCaseText]   = useState("");
  const [result,   setResult]     = useState<DifferentialResult | null>(null);
  const [loading,  setLoading]    = useState(false);
  const [error,    setError]      = useState("");
  const isFree = user?.subscription_tier === "free";

  async function handleSubmit() {
    if (!caseText.trim() || loading) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const token = localStorage.getItem("access_token") ?? "";
      const res = await fetch(`${API_URL}/ai/differential`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body:    JSON.stringify({ case_description: caseText }),
      });

      if (res.status === 429) {
        setError("Daily AI limit reached. Upgrade for more access.");
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? "Request failed");
      }
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 h-full overflow-y-auto px-4 py-4">
      {/* Input */}
      <div className="flex flex-col gap-2">
        <label className="font-syne font-semibold text-sm text-ink">
          Clinical case description
        </label>
        <textarea
          value={caseText}
          onChange={e => setCaseText(e.target.value)}
          placeholder="e.g. 52-year-old male, smoker, presenting with 3 weeks of progressive dyspnea, productive cough, low-grade fever. SpO2 94%. CXR shows right lower lobe consolidation…"
          rows={4}
          className="resize-none px-3 py-2.5 rounded-xl border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink-3 transition-colors leading-relaxed"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={handleSubmit}
            disabled={loading || !caseText.trim()}
            className="btn-primary px-5 py-2.5 rounded-xl font-syne font-semibold text-sm flex items-center gap-2 disabled:opacity-40"
          >
            {loading ? (
              <><Loader2 size={15} className="animate-spin" /> Analysing…</>
            ) : (
              <><ChevronRight size={15} /> Generate Differential</>
            )}
          </button>
          {isFree && (
            <span className="text-xs font-syne text-ink-3">
              Free: Haiku · <a href="/upgrade" className="text-blue-2 underline">Upgrade for Sonnet</a>
            </span>
          )}
          {result && !loading && (
            <button
              onClick={() => { setResult(null); setCaseText(""); }}
              className="text-xs font-syne text-ink-3 hover:text-ink ml-auto"
            >
              Clear
            </button>
          )}
        </div>
        {error && (
          <p className="text-xs font-serif text-red bg-red/5 border border-red/20 rounded-lg px-3 py-2">{error}</p>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="flex flex-col gap-5 animate-fade-up">
          {/* Clinical reasoning */}
          <div className="bg-surface border border-border rounded-xl px-4 py-3">
            <p className="text-xs font-syne font-semibold text-ink-3 uppercase tracking-wide mb-1">Clinical Reasoning</p>
            <p className="font-serif text-sm text-ink leading-relaxed">{result.reasoning}</p>
          </div>

          {/* 3 columns */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Most Likely */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <CheckCircle size={15} className="text-green flex-shrink-0" />
                <span className="font-syne font-bold text-sm text-green">Most Likely</span>
              </div>
              {result.most_likely.map((item, i) => (
                <div key={i} className="bg-green/5 border border-green/20 rounded-xl p-3 flex flex-col gap-1">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-syne font-semibold text-sm text-ink">{item.diagnosis}</span>
                    {item.icd && (
                      <span className="text-[10px] font-mono text-ink-3 bg-bg border border-border rounded px-1 py-0.5 flex-shrink-0">
                        {item.icd}
                      </span>
                    )}
                  </div>
                  <p className="font-serif text-xs text-ink-2 leading-relaxed">{item.reasoning}</p>
                  {item.next_steps && (
                    <p className="font-syne text-[11px] text-green font-semibold mt-1">
                      → {item.next_steps}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* Expanded */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <List size={15} className="text-blue-2 flex-shrink-0" />
                <span className="font-syne font-bold text-sm text-blue-2">Expanded</span>
              </div>
              {result.expanded.map((item, i) => (
                <div key={i} className="bg-blue/5 border border-blue/20 rounded-xl p-3 flex flex-col gap-1">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-syne font-semibold text-sm text-ink">{item.diagnosis}</span>
                    {item.icd && (
                      <span className="text-[10px] font-mono text-ink-3 bg-bg border border-border rounded px-1 py-0.5 flex-shrink-0">
                        {item.icd}
                      </span>
                    )}
                  </div>
                  <p className="font-serif text-xs text-ink-2 leading-relaxed">{item.reasoning}</p>
                </div>
              ))}
            </div>

            {/* Can't Miss */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={15} className="text-red flex-shrink-0" />
                <span className="font-syne font-bold text-sm text-red">Can&apos;t Miss</span>
              </div>
              {result.cant_miss.map((item, i) => (
                <div
                  key={i}
                  className={`border rounded-xl p-3 flex flex-col gap-1.5 ${URGENCY_STYLE[item.urgency] ?? "bg-surface border-border text-ink"}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-syne font-semibold text-sm">{item.diagnosis}</span>
                    <span className={`text-[10px] font-syne font-bold uppercase px-1.5 py-0.5 rounded flex-shrink-0 ${
                      item.urgency === "immediate" ? "bg-red text-white" :
                      item.urgency === "urgent"    ? "bg-amber text-white" :
                                                     "bg-yellow-400 text-yellow-900"
                    }`}>
                      {item.urgency}
                    </span>
                  </div>
                  <p className="font-serif text-xs leading-relaxed">
                    <strong>Red flags:</strong> {item.red_flags}
                  </p>
                  <p className="font-syne text-[11px] font-semibold">→ {item.action}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Recommended workup */}
          {result.recommended_workup.length > 0 && (
            <div className="bg-surface border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <FlaskConical size={14} className="text-ink-3" />
                <span className="font-syne font-bold text-sm text-ink">Recommended Workup</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {result.recommended_workup.map((test, i) => (
                  <span key={i} className="bg-bg border border-border rounded-full px-3 py-1 text-xs font-syne text-ink-2">
                    {test}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* PubMed refs */}
          {result.pubmed_refs && result.pubmed_refs.length > 0 && (
            <div className="border-t border-border pt-3">
              <p className="font-syne text-xs font-semibold text-ink-3 mb-2">References (PubMed)</p>
              <div className="space-y-1">
                {result.pubmed_refs.slice(0, 4).map((ref) => (
                  <div key={ref.pmid} className="text-xs font-serif">
                    <a href={ref.url} target="_blank" rel="noopener noreferrer" className="text-blue-2 hover:underline">
                      {ref.title}
                    </a>{" "}
                    <span className="text-ink-3">({ref.year})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-[11px] font-serif text-ink-3 italic border-t border-border pt-3">
            ⚕️ Educational tool only — not for clinical decisions. Always verify with a licensed clinician.
          </p>
        </div>
      )}
    </div>
  );
}
