"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { API_URL } from "@/lib/api";
import { GitBranch, ArrowRight, AlertCircle, Info, CheckCircle, Loader } from "lucide-react";

type Step = {
  id: string;
  type: "start" | "action" | "decision" | "info";
  text: string;
  note?: string;
  children?: { label: string; next: string }[];
};

type AlgorithmDetail = {
  id: string;
  slug: string;
  title: string;
  specialty: string;
  description: string;
  steps: Step[];
  tags: string[];
  source: string;
  is_veterinary: boolean;
};

const STEP_STYLES: Record<string, { border: string; bg: string; icon: JSX.Element }> = {
  start:    { border: "border-ink",    bg: "bg-ink text-white",       icon: <span className="font-bold text-xs">START</span> },
  action:   { border: "border-blue-400", bg: "bg-blue-50",             icon: <ArrowRight size={14} className="text-blue-600" /> },
  decision: { border: "border-amber-400", bg: "bg-amber-50",           icon: <AlertCircle size={14} className="text-amber-600" /> },
  info:     { border: "border-border",  bg: "bg-surface-2",            icon: <Info size={14} className="text-ink-3" /> },
};

export default function AlgorithmPage() {
  const { slug } = useParams<{ slug: string }>();
  const [algo, setAlgo] = useState<AlgorithmDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [activeStep, setActiveStep] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    fetch(`${API_URL}/practice/algorithms/${slug}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then(setAlgo)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader size={20} className="animate-spin text-ink-3" />
      </div>
    );
  }

  if (error || !algo) {
    return (
      <div className="flex-1 flex items-center justify-center flex-col gap-3 p-8">
        <p className="font-serif text-ink-3">Algorithm not found.</p>
        <Link href="/practice/algorithms" className="btn-secondary text-sm px-4 py-1.5">← Back</Link>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">

        {/* Header */}
        <div className="flex items-center gap-2 text-sm">
          <Link href="/practice" className="text-ink-3 hover:text-ink">Practice</Link>
          <span className="text-ink-3">/</span>
          <Link href="/practice/algorithms" className="text-ink-3 hover:text-ink">Algorithms</Link>
        </div>

        <div>
          <div className="flex items-start gap-3 mb-2">
            <GitBranch size={20} className="text-ink-3 shrink-0 mt-1" />
            <div>
              <h1 className="font-syne font-black text-xl text-ink">{algo.title}</h1>
              {algo.description && (
                <p className="font-serif text-ink-3 text-sm mt-0.5">{algo.description}</p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {algo.specialty && (
              <span className="text-xs font-syne font-semibold bg-surface-2 border border-border text-ink-2 px-2 py-0.5 rounded-full">
                {algo.specialty}
              </span>
            )}
            {algo.tags.map((t) => (
              <span key={t} className="text-xs font-mono text-ink-3 bg-surface-2 px-2 py-0.5 rounded-full">{t}</span>
            ))}
            {algo.is_veterinary && (
              <span className="text-xs font-syne font-bold bg-green/10 text-green px-2 py-0.5 rounded-full">🐾 Veterinary</span>
            )}
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {algo.steps.map((step, idx) => {
            const style = STEP_STYLES[step.type] ?? STEP_STYLES.info;
            const isActive = activeStep === step.id;
            return (
              <div
                key={step.id}
                className={`rounded-lg border-2 p-4 transition-all cursor-pointer ${
                  isActive ? style.border + " shadow-md" : "border-border"
                } ${isActive ? style.bg : "bg-surface"}`}
                onClick={() => setActiveStep(isActive ? null : step.id)}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    isActive ? "bg-ink/10" : "bg-surface-2"
                  }`}>
                    {style.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-syne text-ink-3 uppercase">{step.type}</span>
                      <span className="text-xs font-mono text-ink-3/50">#{idx + 1}</span>
                    </div>
                    <p className="font-serif text-sm text-ink leading-relaxed">{step.text}</p>

                    {step.note && (
                      <div className="mt-2 bg-amber-50 border border-amber-200 rounded p-2 text-xs font-serif text-amber-800">
                        ⚠️ {step.note}
                      </div>
                    )}

                    {step.children && step.children.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {step.children.map((c, ci) => (
                          <button
                            key={ci}
                            onClick={(e) => { e.stopPropagation(); setActiveStep(c.next); }}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-ink-3 bg-surface hover:bg-ink hover:text-white hover:border-ink transition-all text-xs font-syne font-semibold text-ink-2"
                          >
                            {c.label}
                            <ArrowRight size={11} />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Source */}
        {algo.source && (
          <div className="border-t border-border pt-4">
            <p className="font-serif text-xs text-ink-3">
              <strong>Source:</strong> {algo.source}
            </p>
            <p className="font-serif text-xs text-ink-3/70 mt-1">
              For emergency use only. Always apply clinical judgment. This tool does not replace professional medical training.
            </p>
          </div>
        )}

        <Link href="/practice/algorithms" className="inline-block text-sm text-ink-3 hover:text-ink font-syne">
          ← All algorithms
        </Link>
      </div>
    </div>
  );
}
