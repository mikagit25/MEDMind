"use client";

import { useState } from "react";
import { Printer, Heart, Stethoscope, Pill, AlertTriangle, Phone, Loader2, ChevronRight, Lightbulb } from "lucide-react";
import { API_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

interface HandoutData {
  condition: string;
  what_is_it: string;
  how_common?: string;
  causes: string[];
  symptoms: string[];
  diagnosis?: string;
  treatment_overview: string;
  lifestyle_tips: string[];
  when_to_see_doctor: string[];
  warning_signs: string[];
  model?: string;
}

function Section({ icon, title, color, children }: {
  icon: React.ReactNode;
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className={`flex items-center gap-2 pb-1 border-b ${color}`}>
        {icon}
        <span className="font-syne font-bold text-sm">{title}</span>
      </div>
      {children}
    </div>
  );
}

function BulletList({ items, accent }: { items: string[]; accent?: string }) {
  return (
    <ul className="space-y-1">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2 text-sm font-serif text-ink-2 leading-relaxed">
          <span className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${accent ?? "bg-ink-3"}`} />
          {item}
        </li>
      ))}
    </ul>
  );
}

export function PatientHandout() {
  const { user } = useAuthStore();
  const [condition, setCondition] = useState("");
  const [result,    setResult]    = useState<HandoutData | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");

  async function handleGenerate() {
    if (!condition.trim() || loading) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const token = localStorage.getItem("access_token") ?? "";
      const res = await fetch(`${API_URL}/ai/handout`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body:    JSON.stringify({ condition: condition.trim() }),
      });

      if (res.status === 429) { setError("Daily AI limit reached."); return; }
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

  function handlePrint() {
    window.print();
  }

  return (
    <div className="flex flex-col gap-5 h-full overflow-y-auto px-4 py-4">
      {/* Input */}
      <div className="flex flex-col gap-2">
        <label className="font-syne font-semibold text-sm text-ink">
          Medical condition or topic
        </label>
        <div className="flex gap-2">
          <input
            value={condition}
            onChange={e => setCondition(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleGenerate()}
            placeholder="e.g. Type 2 Diabetes, Hypertension, Asthma, GERD…"
            className="flex-1 px-3 py-2.5 rounded-xl border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink-3 transition-colors"
          />
          <button
            onClick={handleGenerate}
            disabled={loading || !condition.trim()}
            className="btn-primary px-4 py-2.5 rounded-xl font-syne font-semibold text-sm flex items-center gap-1.5 disabled:opacity-40 flex-shrink-0"
          >
            {loading ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <ChevronRight size={15} />
            )}
            {loading ? "Creating…" : "Create Handout"}
          </button>
        </div>
        {error && (
          <p className="text-xs font-serif text-red bg-red/5 border border-red/20 rounded-lg px-3 py-2">{error}</p>
        )}
      </div>

      {/* Handout */}
      {result && (
        <div className="flex flex-col gap-5 animate-fade-up print:gap-4" id="patient-handout">
          {/* Title bar */}
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-syne font-black text-xl text-ink">{result.condition}</h2>
              <p className="text-xs font-syne text-ink-3 mt-0.5">Patient Education Handout · MedMind AI</p>
            </div>
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 text-xs font-syne text-ink-3 hover:text-ink border border-border rounded-lg px-3 py-1.5 transition-colors print:hidden"
            >
              <Printer size={13} /> Print
            </button>
          </div>

          {/* What is it */}
          <Section
            icon={<Heart size={14} className="text-red" />}
            title="What is it?"
            color="border-red/30 text-ink"
          >
            <p className="font-serif text-sm text-ink-2 leading-relaxed">{result.what_is_it}</p>
            {result.how_common && (
              <p className="font-serif text-xs text-ink-3 italic">{result.how_common}</p>
            )}
          </Section>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Causes */}
            <Section
              icon={<Stethoscope size={14} className="text-blue-2" />}
              title="Common Causes"
              color="border-blue/30 text-ink"
            >
              <BulletList items={result.causes} accent="bg-blue-2" />
            </Section>

            {/* Symptoms */}
            <Section
              icon={<Stethoscope size={14} className="text-amber-600" />}
              title="Symptoms to Watch For"
              color="border-amber/30 text-ink"
            >
              <BulletList items={result.symptoms} accent="bg-amber-500" />
            </Section>
          </div>

          {/* Diagnosis */}
          {result.diagnosis && (
            <Section
              icon={<FlaskIcon />}
              title="How Is It Diagnosed?"
              color="border-border text-ink"
            >
              <p className="font-serif text-sm text-ink-2 leading-relaxed">{result.diagnosis}</p>
            </Section>
          )}

          {/* Treatment */}
          <Section
            icon={<Pill size={14} className="text-green" />}
            title="Treatment Overview"
            color="border-green/30 text-ink"
          >
            <p className="font-serif text-sm text-ink-2 leading-relaxed">{result.treatment_overview}</p>
          </Section>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Lifestyle */}
            {result.lifestyle_tips.length > 0 && (
              <Section
                icon={<Lightbulb size={14} className="text-green" />}
                title="Lifestyle Tips"
                color="border-green/30 text-ink"
              >
                <BulletList items={result.lifestyle_tips} accent="bg-green" />
              </Section>
            )}

            {/* When to see doctor */}
            <Section
              icon={<Phone size={14} className="text-blue-2" />}
              title="When to See a Doctor"
              color="border-blue/30 text-ink"
            >
              <BulletList items={result.when_to_see_doctor} accent="bg-blue-2" />
            </Section>
          </div>

          {/* Warning signs */}
          {result.warning_signs.length > 0 && (
            <div className="bg-red/5 border border-red/30 rounded-xl p-4 flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <AlertTriangle size={15} className="text-red flex-shrink-0" />
                <span className="font-syne font-bold text-sm text-red">Emergency Warning Signs — Call 112/911</span>
              </div>
              <ul className="space-y-1.5">
                {result.warning_signs.map((sign, i) => (
                  <li key={i} className="flex gap-2 text-sm font-serif text-red/80 leading-relaxed">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red flex-shrink-0" />
                    {sign}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Disclaimer */}
          <p className="text-[11px] font-serif text-ink-3 italic border-t border-border pt-3">
            ℹ️ This handout is for educational purposes only and does not replace professional medical advice.
            Always consult a qualified doctor or healthcare provider for diagnosis and treatment.
          </p>

          {/* New handout button */}
          <button
            onClick={() => { setResult(null); setCondition(""); }}
            className="text-xs font-syne text-ink-3 hover:text-ink self-start print:hidden"
          >
            ← Create another handout
          </button>
        </div>
      )}
    </div>
  );
}

function FlaskIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-ink-3">
      <path d="M9 3h6M9 3v7.5L4.5 18A2 2 0 0 0 6.34 21h11.32a2 2 0 0 0 1.84-3L15 10.5V3" />
    </svg>
  );
}
