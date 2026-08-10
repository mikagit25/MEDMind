"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { examApi } from "@/lib/api";
import {
  Star, Clock, CheckCircle2, AlertTriangle, BarChart3,
  Target, Layers, TrendingUp, TrendingDown, Trophy, Info,
  ChevronRight, Globe,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

type GulfAnalytics = {
  sessions_analyzed: number;
  difficulty_performance: Record<string, { label: string; pct: number; total: number; correct: number }>;
  exam_performance: Record<string, { label: string; sessions: number; passed: number; avg_score: number }>;
  weak_areas: Array<{ key: string; label: string; pct: number; total: number }>;
  overall_trend: Array<{ session_id: string; date: string; score_pct: number | null; mode: string; passed: boolean | null }>;
};

type PlanTask = { task_type: string; topic: string; days_to_exam: number };
type GulfStudyPlan = {
  exam_type: string;
  exam_date: string;
  daily_minutes: number;
  completed_dates: string[];
  today_task: PlanTask | null;
  week_tasks: PlanTask[];
};

type ExamMode = {
  id: string;
  name: string;
  description: string;
  questions: number;
  duration_min: number;
  locked: boolean;
  lock_reason: string | null;
};

type SessionHistory = {
  session_id: string;
  mode: string;
  mode_id: string;
  started_at: string;
  score_pct: number | null;
  passed: boolean | null;
  correct: number | null;
  total_questions: number;
  time_taken_min: number | null;
};

type GulfReadiness = {
  score: number | null;
  level: string | null;
  level_label: string | null;
  threshold_met: boolean;
  questions_answered: number;
  questions_to_threshold: number;
  category_breakdown: Record<string, { label: string; pct: number; count: number }>;
  weak_categories: Array<{ key: string; label: string; pct: number; count: number }>;
  trend: Array<{ date: string; score_pct: number | null; correct: number; total: number }>;
  disclaimer: string;
};

// ── Constants ──────────────────────────────────────────────────────────────────

const GULF_EXAM_SLUGS = ["snle", "dha", "qchp", "omsb", "nhra", "mohuae", "haad", "moh_kw"] as const;
type GulfSlug = typeof GULF_EXAM_SLUGS[number];

const GULF_EXAM_INFO: Record<GulfSlug, { name: string; country: string; flag: string; full: string }> = {
  snle:   { name: "SNLE",    country: "Saudi Arabia",  flag: "🇸🇦", full: "Saudi Nursing Licensure Exam" },
  dha:    { name: "DHA",     country: "Dubai",         flag: "🇦🇪", full: "Dubai Health Authority" },
  qchp:   { name: "QCHP",   country: "Qatar",         flag: "🇶🇦", full: "Qatar Council for Healthcare Practitioners" },
  omsb:   { name: "OMSB",   country: "Oman",          flag: "🇴🇲", full: "Oman Medical Specialty Board" },
  nhra:   { name: "NHRA",   country: "Bahrain",       flag: "🇧🇭", full: "National Health Regulatory Authority" },
  mohuae: { name: "MOH UAE", country: "UAE",           flag: "🇦🇪", full: "Ministry of Health UAE" },
  haad:   { name: "HAAD",   country: "Abu Dhabi",     flag: "🇦🇪", full: "Health Authority Abu Dhabi" },
  moh_kw: { name: "MOH-KW", country: "Kuwait",        flag: "🇰🇼", full: "Ministry of Health Kuwait" },
};

// Nursing study modules linked to Gulf exam question banks
const NURSING_STUDY_MODULES = [
  {
    id: "f0913cce-0e39-419f-9b71-e31ee68d7e62",
    title: "Nursing Process & Documentation",
    desc: "Assessment, diagnosis, planning, intervention, evaluation + legal documentation",
    icon: "📋", lessons: 2, mcqs: 119,
  },
  {
    id: "3e70e94e-72c2-48ef-a61b-843138f0952a",
    title: "Medication Safety",
    desc: "Five Rights, administration errors, high-alert medications",
    icon: "💊", lessons: 2, mcqs: 115,
  },
  {
    id: "ea06574b-a01a-4c03-bb32-836179f82698",
    title: "Dose Calculations & Infusion Therapy",
    desc: "Core formulas, IV drip rates, weight-based dosing",
    icon: "🧮", lessons: 2, mcqs: 101,
  },
  {
    id: "89529702-32b1-4f38-bc90-6a4441109000",
    title: "Recognising Patient Deterioration",
    desc: "Early warning signs, NEWS2 scoring, rapid response",
    icon: "📈", lessons: 2, mcqs: 62,
  },
  {
    id: "a708a327-4246-4448-b739-31c5f61a091e",
    title: "Infection Control & Hand Hygiene",
    desc: "Standard precautions, transmission-based isolation, PPE",
    icon: "🦠", lessons: 2, mcqs: 58,
  },
  {
    id: "30acf5f5-72da-45d6-8277-820d5308fa92",
    title: "Emergency Situations",
    desc: "Nurse's role before the doctor arrives — BLS, triage, deterioration",
    icon: "🚨", lessons: 2, mcqs: 42,
  },
  {
    id: "97b09cd4-f90a-488d-b263-bf37cfad37ef",
    title: "Patient Care: Pressure Injuries & Mobility",
    desc: "Braden scale, repositioning, wound staging, falls prevention",
    icon: "🛏️", lessons: 2, mcqs: 31,
  },
  {
    id: "3785087f-c853-4adb-a717-9ac66df89034",
    title: "Mental Health & Psychiatric Nursing",
    desc: "Psychopathology, therapeutic communication, crisis intervention",
    icon: "🧠", lessons: 0, mcqs: 31,
  },
  {
    id: "43dc8dd3-dab0-4730-932a-c64ddb73709c",
    title: "Patient Communication & SBAR Handoff",
    desc: "Therapeutic communication, family engagement, structured handoff",
    icon: "💬", lessons: 2, mcqs: 16,
  },
] as const;

const GULF_MODE_IDS = [
  "snle_practice",  "dha_practice",  "qchp_practice", "omsb_practice",
  "nhra_practice",  "mohuae_practice", "haad_practice", "moh_kw_practice",
  "snle_full",      "dha_full",      "qchp_full",     "omsb_full",
  "nhra_full",      "mohuae_full",   "haad_full",     "moh_kw_full",
];

const LEVEL_CONFIG: Record<string, { color: string; bg: string; border: string }> = {
  high:          { color: "text-green",     bg: "bg-green/5",  border: "border-green/30" },
  passing_range: { color: "text-blue-600",  bg: "bg-blue-50",  border: "border-blue-200" },
  borderline:    { color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-200" },
  below_passing: { color: "text-red",       bg: "bg-red/5",    border: "border-red/20" },
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function ScoreBadge({ pct }: { pct: number }) {
  const color = pct >= 75 ? "text-green bg-green/10 border-green/30"
    : pct >= 60 ? "text-amber-600 bg-amber-50 border-amber-200"
    : "text-red bg-red/10 border-red/30";
  return (
    <span className={`inline-block text-xs font-syne font-bold border rounded-full px-2 py-0.5 ${color}`}>
      {pct}%
    </span>
  );
}

function CategoryBar({ label, pct, count }: { label: string; pct: number; count: number }) {
  const color = pct >= 75 ? "bg-green" : pct >= 60 ? "bg-amber-400" : "bg-red";
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-serif text-ink-2 truncate pr-2">{label}</span>
        <span className="text-xs font-syne font-bold text-ink flex-shrink-0">
          {pct}% <span className="text-ink-3 font-normal">({count})</span>
        </span>
      </div>
      <div className="h-1.5 bg-border rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Readiness Panel ────────────────────────────────────────────────────────────

function ReadinessPanel({
  readiness,
  examSlug,
  paywalled,
  loading: isLoading,
}: {
  readiness: GulfReadiness | null;
  examSlug: GulfSlug;
  paywalled: boolean;
  loading: boolean;
}) {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const info = GULF_EXAM_INFO[examSlug];

  if (isLoading) {
    return <div className="py-12 text-center text-ink-3 font-serif">Loading readiness…</div>;
  }

  if (paywalled) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="max-w-sm w-full text-center space-y-5">
          <div className="w-16 h-16 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-3xl">🔒</div>
          <div>
            <h2 className="font-syne font-black text-xl text-ink mb-2">Upgrade to unlock Readiness Score</h2>
            <p className="font-serif text-sm text-ink-3 leading-relaxed">
              Gulf Readiness tracking is available on Student and Pro plans.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <a href="/pricing" className="btn-primary font-syne font-bold text-sm px-6 py-2.5 rounded-lg inline-block">View plans →</a>
          </div>
        </div>
      </div>
    );
  }

  if (!readiness) {
    return <div className="py-12 text-center text-ink-3 font-serif">Could not load readiness data.</div>;
  }

  if (!readiness.threshold_met) {
    return (
      <div className="bg-surface border border-border rounded-xl p-8 text-center">
        <Target className="w-12 h-12 mx-auto mb-4 text-ink-3 opacity-40" />
        <h3 className="font-syne font-black text-lg text-ink mb-2">
          {info.flag} {info.name} Readiness Score
        </h3>
        <p className="font-serif text-sm text-ink-3 mb-4 max-w-sm mx-auto">
          Answer at least 30 {info.name} practice questions to unlock your readiness estimate.
        </p>
        <div className="inline-flex items-center gap-2 bg-border/40 rounded-full px-4 py-2">
          <div className="h-1.5 w-32 bg-border rounded-full overflow-hidden">
            <div
              className="h-full bg-ink rounded-full transition-all"
              style={{ width: `${Math.min(100, (readiness.questions_answered / 30) * 100)}%` }}
            />
          </div>
          <span className="text-xs font-syne font-bold text-ink-2">
            {readiness.questions_answered} / 30
          </span>
        </div>
        <p className="text-xs font-serif text-ink-3 mt-3">
          {readiness.questions_to_threshold} more questions to go
        </p>
      </div>
    );
  }

  const score = readiness.score!;
  const level = readiness.level || "below_passing";
  const lvlCfg = LEVEL_CONFIG[level] ?? LEVEL_CONFIG.below_passing;

  return (
    <div className="space-y-4">
      {/* Score card */}
      <div className={`rounded-xl p-6 border ${lvlCfg.bg} ${lvlCfg.border}`}>
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">{info.flag}</span>
              <h3 className="font-syne font-black text-sm text-ink uppercase tracking-wider">
                {info.name} Readiness Score
              </h3>
              <button
                onClick={() => setTooltipOpen(o => !o)}
                className="text-ink-3 hover:text-ink transition-colors"
              >
                <Info className="w-3.5 h-3.5" />
              </button>
            </div>
            {tooltipOpen && (
              <div className="bg-ink text-white rounded-xl px-4 py-3 text-xs font-serif max-w-sm mb-3 leading-relaxed">
                {readiness.disclaimer}
              </div>
            )}
          </div>
          <span className="text-xs font-syne text-ink-3">
            {readiness.questions_answered} questions
          </span>
        </div>

        <div className="flex items-end gap-6">
          <div>
            <div className={`font-syne font-black text-7xl leading-none mb-1 ${lvlCfg.color}`}>
              {score}%
            </div>
            <div className={`font-syne font-bold text-sm ${lvlCfg.color}`}>
              {readiness.level_label}
            </div>
          </div>

          {readiness.trend.length > 1 && (
            <div className="flex-1 flex items-end gap-1 h-16 pb-1">
              {readiness.trend.slice(-14).map((pt, i) => {
                const h = Math.max(4, ((pt.score_pct ?? 0) / 100) * 56);
                const color = (pt.score_pct ?? 0) >= 60 ? "bg-green/60" : "bg-red/40";
                return (
                  <div key={i} className="flex-1 flex flex-col justify-end">
                    <div className={`rounded-sm ${color}`} style={{ height: `${h}px` }} />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Weak categories */}
      {readiness.weak_categories.length > 0 && (
        <div className="bg-red/5 border border-red/20 rounded-xl p-4">
          <h4 className="font-syne font-bold text-sm text-red mb-3 flex items-center gap-2">
            <TrendingDown className="w-4 h-4" /> Focus Areas
          </h4>
          <div className="space-y-3">
            {readiness.weak_categories.map(c => (
              <CategoryBar key={c.key} label={c.label} pct={c.pct} count={c.count} />
            ))}
          </div>
        </div>
      )}

      {/* All categories */}
      {Object.keys(readiness.category_breakdown).length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-4">
          <h4 className="font-syne font-bold text-sm text-ink mb-3 flex items-center gap-2">
            <Layers className="w-4 h-4" /> Blueprint Performance
          </h4>
          <div className="space-y-3">
            {Object.entries(readiness.category_breakdown)
              .sort((a, b) => a[1].pct - b[1].pct)
              .map(([key, c]) => (
                <CategoryBar key={key} label={c.label} pct={c.pct} count={c.count} />
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function GulfHubPage() {
  const [modes, setModes] = useState<ExamMode[]>([]);
  const [history, setHistory] = useState<SessionHistory[]>([]);
  const [readiness, setReadiness] = useState<GulfReadiness | null>(null);
  const [readinessPaywalled, setReadinessPaywalled] = useState(false);
  const [readinessLoading, setReadinessLoading] = useState(true);
  const [selectedSlug, setSelectedSlug] = useState<GulfSlug>("snle");
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<GulfAnalytics | null>(null);
  const [plan, setPlan] = useState<GulfStudyPlan | null>(null);
  const [planSaving, setPlanSaving] = useState(false);
  const [planWizardDate, setPlanWizardDate] = useState("");
  const [planWizardMinutes, setPlanWizardMinutes] = useState(45);
  const [starting, setStarting] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"practice" | "study" | "readiness" | "history" | "analytics" | "plan">("practice");

  const loadReadiness = useCallback(async (slug: GulfSlug) => {
    setReadinessLoading(true);
    setReadinessPaywalled(false);
    try {
      const r = await examApi.getGulfReadiness(slug);
      setReadiness(r);
    } catch (e: any) {
      setReadiness(null);
      if (e?.response?.status === 403) setReadinessPaywalled(true);
    } finally {
      setReadinessLoading(false);
    }
  }, []);

  const reloadPlan = useCallback(async () => {
    try {
      const res = await examApi.getPlan("gulf");
      setPlan(res.plan ?? null);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    Promise.all([
      examApi.getModes(),
      examApi.getHistory(30),
      examApi.getGulfAnalytics(),
      examApi.getPlan("gulf"),
    ])
      .then(([modeList, hist, anal, planRes]) => {
        const gulfModes = modeList.filter((m: ExamMode) => GULF_MODE_IDS.includes(m.id));
        setModes(gulfModes);
        setHistory(hist.filter((s: SessionHistory) => GULF_MODE_IDS.includes(s.mode_id)));
        setAnalytics(anal);
        setPlan(planRes.plan ?? null);
      })
      .finally(() => setLoading(false));
    loadReadiness("snle");
  }, [loadReadiness, reloadPlan]);

  function handleSlugChange(slug: GulfSlug) {
    setSelectedSlug(slug);
    setReadiness(null);
    setReadinessPaywalled(false);
    loadReadiness(slug);
  }

  async function startSession(modeId: string) {
    setStarting(modeId);
    try {
      const session = await examApi.createSession(modeId);
      window.location.href = `/exam?session=${session.session_id}`;
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || "Failed to start session";
      alert(msg);
    } finally {
      setStarting(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="text-ink-3 font-serif">Loading…</div>
      </div>
    );
  }

  const gulfHistory = history;
  const bestScore = gulfHistory.length ? Math.max(...gulfHistory.map(s => s.score_pct ?? 0)) : null;

  const fullSimModes = modes.filter(m => m.id.endsWith("_full"));
  const practiceByExam = modes.filter(m => m.id.endsWith("_practice"));

  const TABS: { id: "practice" | "study" | "plan" | "readiness" | "history" | "analytics"; label: string }[] = [
    { id: "practice",  label: "Exam Simulations" },
    { id: "study",     label: "Study Materials" },
    { id: "plan",      label: "Plan" },
    { id: "readiness", label: "Readiness Score" },
    { id: "history",   label: `History (${gulfHistory.length})` },
    { id: "analytics", label: "Analytics" },
  ];

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <div className="border-b border-border bg-surface px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Globe className="w-5 h-5 text-ink" />
            <div>
              <h1 className="font-syne font-black text-lg text-ink leading-none">Gulf Nursing Exams</h1>
              <p className="text-ink-3 font-serif text-xs mt-0.5">
                SNLE · DHA · QCHP · OMSB · NHRA · MOH UAE · HAAD
              </p>
            </div>
          </div>
          <Link href="/nurses" className="text-xs font-syne text-ink-3 hover:text-ink transition-colors">
            ← Nurses Hub
          </Link>
        </div>
      </div>

      {/* Stats strip */}
      {(bestScore !== null || readiness?.threshold_met) && (
        <div className="bg-ink text-white">
          <div className="max-w-5xl mx-auto px-6 py-3 flex flex-wrap gap-6">
            {readiness?.threshold_met && readiness.score !== null && (
              <button
                onClick={() => setActiveTab("readiness")}
                className="flex items-center gap-2 hover:opacity-80 transition-opacity"
              >
                <Target className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-syne">
                  {GULF_EXAM_INFO[selectedSlug].name} Readiness{" "}
                  <strong className={
                    readiness.score >= 75 ? "text-green" :
                    readiness.score >= 60 ? "text-amber-400" : "text-red"
                  }>{readiness.score}%</strong>
                  {" "}
                  <span className="text-white/50">({readiness.level_label})</span>
                </span>
              </button>
            )}
            {bestScore !== null && (
              <div className="flex items-center gap-2">
                <Trophy className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-syne">Best score <strong>{bestScore}%</strong></span>
              </div>
            )}
            {gulfHistory.length > 0 && (
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-green" />
                <span className="text-xs font-syne">{gulfHistory.length} sessions completed</span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="max-w-5xl mx-auto px-6 py-6">
        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-border">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-syne font-semibold transition-colors border-b-2 -mb-px ${
                activeTab === tab.id
                  ? "border-ink text-ink"
                  : "border-transparent text-ink-3 hover:text-ink"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Practice tab ── */}
        {activeTab === "practice" && (
          <div className="space-y-8">
            {/* Info banner */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-3">
              <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-syne font-bold text-xs text-amber-700 mb-0.5">Gulf Question Banks — Early Access</p>
                <p className="font-serif text-xs text-amber-600 leading-relaxed">
                  Gulf-specific question banks are actively expanding. Practice and simulation modes require a Student or Pro plan.{" "}
                  <a href="/pricing" className="underline font-semibold">See plans →</a>
                </p>
              </div>
            </div>

            {/* Exam selector */}
            <div>
              <h2 className="font-syne font-black text-xl text-ink mb-3">Select Your Exam</h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {GULF_EXAM_SLUGS.map(slug => {
                  const info = GULF_EXAM_INFO[slug];
                  return (
                    <button
                      key={slug}
                      onClick={() => handleSlugChange(slug)}
                      className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-syne font-semibold transition-all ${
                        selectedSlug === slug
                          ? "border-ink bg-ink text-white"
                          : "border-border text-ink hover:border-ink"
                      }`}
                    >
                      <span>{info.flag}</span>
                      <span>{info.name}</span>
                    </button>
                  );
                })}
              </div>
              {selectedSlug && (
                <p className="text-xs font-serif text-ink-3 mt-2">
                  {GULF_EXAM_INFO[selectedSlug].full} — {GULF_EXAM_INFO[selectedSlug].country}
                </p>
              )}
            </div>

            {/* Practice + Full Simulation for selected exam */}
            {(() => {
              const info = GULF_EXAM_INFO[selectedSlug];
              const practiceMode = practiceByExam.find(m => m.id === `${selectedSlug}_practice`);
              const fullMode = fullSimModes.find(m => m.id === `${selectedSlug}_full`);
              return (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Practice card */}
                  {practiceMode && (
                    <div className={`bg-surface border border-border rounded-xl p-5 flex flex-col gap-4 ${practiceMode.locked ? "opacity-60" : ""}`}>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-syne font-bold bg-green/10 text-green border border-green/30 rounded-full px-2 py-0.5">Practice</span>
                        </div>
                        <div className="font-syne font-bold text-sm text-ink">{info.name} Practice</div>
                        <div className="font-serif text-xs text-ink-3 mt-0.5">With explanations after each answer</div>
                      </div>
                      <div className="flex gap-4 text-xs font-syne text-ink-3">
                        <span className="flex items-center gap-1"><Star className="w-3 h-3" /> {practiceMode.questions} questions</span>
                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {practiceMode.duration_min} min</span>
                      </div>
                      {practiceMode.locked ? (
                        <div className="text-xs font-serif text-ink-3 italic">{practiceMode.lock_reason}</div>
                      ) : (
                        <button
                          onClick={() => startSession(practiceMode.id)}
                          disabled={starting === practiceMode.id}
                          className="font-syne font-bold text-sm border-2 border-ink text-ink px-5 py-2.5 rounded-xl hover:bg-ink hover:text-white transition-colors disabled:opacity-50"
                        >
                          {starting === practiceMode.id ? "Starting…" : "Start Practice →"}
                        </button>
                      )}
                    </div>
                  )}

                  {/* Full Simulation card */}
                  {fullMode && (
                    <div className={`bg-ink text-white rounded-xl p-5 flex flex-col gap-4 ${fullMode.locked ? "opacity-60" : ""}`}>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-syne font-bold bg-white/10 text-white/80 border border-white/20 rounded-full px-2 py-0.5">Official Format</span>
                        </div>
                        <div className="font-syne font-bold text-sm text-white">{info.name} Full Simulation</div>
                        <div className="font-serif text-xs text-white/60 mt-0.5">No explanations until review — real exam conditions</div>
                      </div>
                      <div className="flex gap-4 text-xs font-syne text-white/60">
                        <span className="flex items-center gap-1"><Star className="w-3 h-3" /> {fullMode.questions} questions</span>
                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {fullMode.duration_min} min</span>
                        <span className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Pass: 65%</span>
                      </div>
                      {fullMode.locked ? (
                        <div className="text-xs font-serif text-white/60 italic">{fullMode.lock_reason}</div>
                      ) : (
                        <button
                          onClick={() => startSession(fullMode.id)}
                          disabled={starting === fullMode.id}
                          className="font-syne font-bold text-sm bg-white text-ink px-5 py-2.5 rounded-xl hover:bg-amber-50 transition-colors disabled:opacity-50"
                        >
                          {starting === fullMode.id ? "Starting…" : `Start ${info.name} Simulation →`}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })()}

            {/* All exams quick launch */}
            <section>
              <h2 className="font-syne font-black text-xl text-ink mb-3">All Gulf Exams</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {GULF_EXAM_SLUGS.map(slug => {
                  const info = GULF_EXAM_INFO[slug];
                  const practiceMode = practiceByExam.find(m => m.id === `${slug}_practice`);
                  const fullMode = fullSimModes.find(m => m.id === `${slug}_full`);
                  return (
                    <div key={slug} className="bg-surface border border-border rounded-xl p-4">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-xl flex-shrink-0">{info.flag}</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-syne font-bold text-sm text-ink">{info.name}</div>
                          <div className="font-serif text-xs text-ink-3 truncate">{info.country}</div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {practiceMode && !practiceMode.locked && (
                          <button
                            onClick={() => startSession(practiceMode.id)}
                            disabled={!!starting}
                            className="flex-1 font-syne font-bold text-xs border border-ink text-ink px-2 py-1.5 rounded-lg hover:bg-ink hover:text-white transition-colors disabled:opacity-50"
                          >
                            {starting === practiceMode.id ? "…" : `Practice (${practiceMode.questions}Q)`}
                          </button>
                        )}
                        {fullMode && !fullMode.locked && (
                          <button
                            onClick={() => startSession(fullMode.id)}
                            disabled={!!starting}
                            className="flex-1 font-syne font-bold text-xs bg-ink text-white px-2 py-1.5 rounded-lg hover:bg-red transition-colors disabled:opacity-50"
                          >
                            {starting === fullMode.id ? "…" : `Full Sim (${fullMode.questions}Q)`}
                          </button>
                        )}
                        {!practiceMode && !fullMode && (
                          <ChevronRight className="w-4 h-4 text-ink-3" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        )}

        {/* ── Readiness tab ── */}
        {activeTab === "readiness" && (
          <div className="space-y-6">
            {/* Exam selector */}
            <div>
              <p className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-2">
                Select exam
              </p>
              <div className="flex flex-wrap gap-2">
                {GULF_EXAM_SLUGS.map(slug => {
                  const info = GULF_EXAM_INFO[slug];
                  return (
                    <button
                      key={slug}
                      onClick={() => handleSlugChange(slug)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-syne font-semibold transition-all ${
                        selectedSlug === slug
                          ? "border-ink bg-ink text-white"
                          : "border-border text-ink hover:border-ink"
                      }`}
                    >
                      <span>{info.flag}</span>
                      <span>{info.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <ReadinessPanel readiness={readiness} examSlug={selectedSlug} paywalled={readinessPaywalled} loading={readinessLoading} />

            {/* Trend chart */}
            {readiness?.threshold_met && (readiness.trend?.length ?? 0) > 1 && (
              <div className="bg-surface border border-border rounded-xl p-5">
                <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" /> Performance Trend
                </h3>
                <div className="flex items-end gap-1.5 h-24">
                  {readiness.trend.map((pt, i) => {
                    const h = Math.max(4, ((pt.score_pct ?? 0) / 100) * 88);
                    const color = (pt.score_pct ?? 0) >= 60 ? "bg-green" : "bg-red/60";
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                        <div className={`w-full rounded-t transition-all ${color}`} style={{ height: `${h}px` }} />
                        <span className="text-[9px] font-syne text-ink-3">{pt.score_pct ?? 0}%</span>
                        <div className="absolute -top-6 left-1/2 -translate-x-1/2 hidden group-hover:block bg-ink text-white text-[10px] font-syne rounded px-1.5 py-0.5 whitespace-nowrap z-10">
                          {pt.date}: {pt.correct}/{pt.total}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="flex justify-between text-[10px] font-syne text-ink-3 mt-1">
                  <span>{readiness.trend[0]?.date}</span>
                  <span>{readiness.trend[readiness.trend.length - 1]?.date}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── History tab ── */}
        {/* ── Study Materials tab ── */}
        {activeTab === "study" && (
          <div className="space-y-6">
            <div>
              <h2 className="font-syne font-black text-xl text-ink mb-1">Study Before You Practice</h2>
              <p className="font-serif text-sm text-ink-3 leading-relaxed">
                These modules cover every topic tested on Gulf nursing licensing exams.
                Work through the lessons, then return here to practice questions.
              </p>
            </div>

            {/* Core nursing modules */}
            <div>
              <h3 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Core Nursing Modules</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {NURSING_STUDY_MODULES.map(mod => (
                  <Link
                    key={mod.id}
                    href={`/modules/${mod.id}`}
                    className="group bg-surface border border-border hover:border-ink rounded-xl p-4 flex items-start gap-3 transition-colors"
                  >
                    <div className="w-9 h-9 rounded-lg bg-ink/5 group-hover:bg-ink group-hover:text-white flex items-center justify-center flex-shrink-0 transition-colors text-lg">
                      {mod.icon}
                    </div>
                    <div className="min-w-0">
                      <div className="font-syne font-bold text-sm text-ink leading-snug group-hover:text-blue-600 transition-colors">
                        {mod.title}
                      </div>
                      <div className="text-xs font-serif text-ink-3 mt-0.5">{mod.desc}</div>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="text-[10px] font-syne font-semibold bg-ink/5 text-ink-2 px-2 py-0.5 rounded-full">
                          {mod.lessons} lessons
                        </span>
                        <span className="text-[10px] font-syne font-semibold bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                          {mod.mcqs} MCQs
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-ink-3 group-hover:text-ink flex-shrink-0 mt-1 transition-colors" />
                  </Link>
                ))}
              </div>
            </div>

            {/* Study tip */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex gap-3">
              <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-syne font-bold text-xs text-blue-700 mb-0.5">Recommended study flow</p>
                <p className="font-serif text-xs text-blue-600 leading-relaxed">
                  Study a module → Practice its questions in{" "}
                  <button onClick={() => setActiveTab("practice")} className="underline font-semibold">Exam Simulations</button>
                  {" "}→ Check your{" "}
                  <button onClick={() => setActiveTab("readiness")} className="underline font-semibold">Readiness Score</button>
                  {" "}to see which topics need more work.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── Plan tab ── */}
        {activeTab === "plan" && (
          <div className="space-y-6">
            {!plan ? (
              /* Plan wizard */
              <div className="max-w-md mx-auto bg-surface border border-border rounded-xl p-6">
                <h2 className="font-syne font-black text-xl text-ink mb-1">Create Your Study Plan</h2>
                <p className="font-serif text-sm text-ink-3 mb-5">
                  Set your Gulf exam date and daily study goal. We&apos;ll build a personalised schedule.
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-syne font-bold text-ink-2 uppercase tracking-wider block mb-1">
                      Exam Date
                    </label>
                    <input
                      type="date"
                      value={planWizardDate}
                      min={new Date().toISOString().split("T")[0]}
                      onChange={e => setPlanWizardDate(e.target.value)}
                      className="w-full border border-border rounded-lg px-3 py-2 text-sm font-syne bg-bg focus:outline-none focus:border-ink"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-syne font-bold text-ink-2 uppercase tracking-wider block mb-1">
                      Daily Study Time
                    </label>
                    <div className="flex gap-2 flex-wrap">
                      {[30, 45, 60, 90].map(m => (
                        <button
                          key={m}
                          onClick={() => setPlanWizardMinutes(m)}
                          className={`px-3 py-1.5 rounded-lg border text-xs font-syne font-semibold transition-all ${
                            planWizardMinutes === m ? "border-ink bg-ink text-white" : "border-border text-ink hover:border-ink"
                          }`}
                        >
                          {m} min
                        </button>
                      ))}
                    </div>
                  </div>
                  <button
                    disabled={!planWizardDate || planSaving}
                    onClick={async () => {
                      if (!planWizardDate) return;
                      setPlanSaving(true);
                      try {
                        await examApi.createPlan({ exam_date: planWizardDate, daily_minutes: planWizardMinutes, exam_type: "gulf" });
                        await reloadPlan();
                      } catch { /* ignore */ } finally { setPlanSaving(false); }
                    }}
                    className="w-full bg-ink text-white rounded-xl py-3 font-syne font-bold text-sm hover:opacity-90 transition-opacity disabled:opacity-40"
                  >
                    {planSaving ? "Creating…" : "Build My Plan →"}
                  </button>
                </div>
              </div>
            ) : (
              /* Plan exists */
              <div className="space-y-4">
                <div className="bg-surface border border-border rounded-xl p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h2 className="font-syne font-black text-xl text-ink">Study Plan</h2>
                      <p className="text-xs font-syne text-ink-3 mt-0.5">
                        Gulf Exams · {plan.exam_date} · {plan.daily_minutes} min/day
                      </p>
                    </div>
                    <button
                      onClick={async () => {
                        if (!confirm("Delete this study plan?")) return;
                        await examApi.deletePlan("gulf");
                        setPlan(null);
                      }}
                      className="text-xs text-ink-3 hover:text-red transition-colors font-syne"
                    >
                      Delete
                    </button>
                  </div>
                  {plan.today_task && (
                    <div className="bg-ink/5 rounded-xl p-4 flex items-center justify-between">
                      <div>
                        <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-0.5">
                          Today&apos;s Task
                        </div>
                        <div className="font-syne font-bold text-sm text-ink">{plan.today_task.topic}</div>
                        <div className="text-xs font-serif text-ink-3 mt-0.5">
                          {plan.today_task.days_to_exam} days to exam
                        </div>
                      </div>
                      {plan.completed_dates.includes(new Date().toISOString().split("T")[0]) ? (
                        <CheckCircle2 className="w-6 h-6 text-green flex-shrink-0" />
                      ) : (
                        <button
                          onClick={async () => {
                            await examApi.completeTodayTask(plan.today_task!.task_type, "gulf");
                            await reloadPlan();
                          }}
                          className="flex-shrink-0 bg-ink text-white text-xs font-syne font-bold px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity"
                        >
                          Mark Done
                        </button>
                      )}
                    </div>
                  )}
                  {/* Week calendar */}
                  {plan.week_tasks.length > 0 && (
                    <div className="mt-4">
                      <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-2">This Week</div>
                      <div className="grid grid-cols-7 gap-1">
                        {plan.week_tasks.map((t, i) => {
                          const d = new Date(); d.setDate(d.getDate() + i);
                          const dStr = d.toISOString().split("T")[0];
                          const done = plan.completed_dates.includes(dStr);
                          return (
                            <div key={i} className={`rounded-lg p-1.5 text-center ${done ? "bg-green/10 border border-green/30" : "bg-border/30"}`}>
                              <div className="text-[10px] font-syne text-ink-3">{["S","M","T","W","T","F","S"][d.getDay()]}</div>
                              <div className={`text-[10px] font-syne font-bold mt-0.5 ${done ? "text-green" : "text-ink-2"}`}>
                                {done ? "✓" : d.getDate()}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex gap-3">
                  <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                  <p className="font-serif text-xs text-blue-600 leading-relaxed">
                    Follow the plan daily, then check your{" "}
                    <button onClick={() => setActiveTab("readiness")} className="underline font-semibold">Readiness Score</button>
                    {" "}to track progress toward your exam goal.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Analytics tab ── */}
        {activeTab === "analytics" && (
          <div className="space-y-6">
            {!analytics || analytics.sessions_analyzed === 0 ? (
              <div className="text-center py-16 text-ink-3 font-serif">
                <BarChart3 className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>Complete at least one Gulf exam simulation to see analytics.</p>
              </div>
            ) : (
              <>
                {/* Score trend */}
                {analytics.overall_trend.length > 1 && (
                  <div className="bg-surface border border-border rounded-xl p-5">
                    <h3 className="font-syne font-bold text-sm text-ink mb-3 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" /> Score Trend
                    </h3>
                    <div className="flex items-end gap-2 h-20">
                      {analytics.overall_trend.map((pt, i) => (
                        <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                          <div
                            className={`w-full rounded-t transition-all ${(pt.score_pct ?? 0) >= 60 ? "bg-green" : "bg-red/60"}`}
                            style={{ height: `${Math.max(8, ((pt.score_pct ?? 0) / 100) * 72)}px` }}
                          />
                          <span className="text-[10px] font-syne text-ink-3">{pt.score_pct ?? 0}%</span>
                          <div className="absolute -top-7 left-1/2 -translate-x-1/2 hidden group-hover:block bg-ink text-white text-[10px] font-syne rounded px-1.5 py-0.5 whitespace-nowrap z-10">
                            {pt.date} · {pt.mode}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Performance by difficulty */}
                {Object.keys(analytics.difficulty_performance).length > 0 && (
                  <div className="bg-surface border border-border rounded-xl p-5">
                    <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
                      <Layers className="w-4 h-4" /> Performance by Difficulty
                    </h3>
                    <div className="space-y-3">
                      {Object.entries(analytics.difficulty_performance)
                        .sort((a, b) => (a[1].pct) - (b[1].pct))
                        .map(([key, c]) => (
                          <div key={key}>
                            <div className="flex justify-between items-center mb-1">
                              <span className="text-xs font-syne font-semibold text-ink">{c.label}</span>
                              <span className={`text-xs font-syne font-bold ${c.pct >= 60 ? "text-green" : "text-red"}`}>
                                {c.pct}% <span className="text-ink-3 font-normal">({c.correct}/{c.total})</span>
                              </span>
                            </div>
                            <div className="h-2 bg-border rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${c.pct >= 60 ? "bg-green" : "bg-red/60"}`}
                                style={{ width: `${c.pct}%` }}
                              />
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Per-exam breakdown */}
                {Object.keys(analytics.exam_performance).length > 0 && (
                  <div className="bg-surface border border-border rounded-xl p-5">
                    <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
                      <Globe className="w-4 h-4" /> Results by Exam
                    </h3>
                    <div className="space-y-2">
                      {Object.entries(analytics.exam_performance).map(([slug, e]) => {
                        const info = GULF_EXAM_INFO[slug as GulfSlug];
                        return (
                          <div key={slug} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                            <div className="flex items-center gap-2">
                              <span className="text-base">{info?.flag ?? "🌍"}</span>
                              <span className="font-syne font-semibold text-sm text-ink">{e.label}</span>
                            </div>
                            <div className="flex items-center gap-4 text-xs font-syne">
                              <span className="text-ink-3">{e.sessions} session{e.sessions !== 1 ? "s" : ""}</span>
                              <span className={`font-bold ${e.avg_score >= 60 ? "text-green" : "text-red"}`}>
                                avg {e.avg_score}%
                              </span>
                              <span className="text-ink-3">
                                {e.passed}/{e.sessions} passed
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Weak areas */}
                {analytics.weak_areas.length > 0 && (
                  <div className="bg-red/5 border border-red/20 rounded-xl p-5">
                    <h3 className="font-syne font-bold text-sm text-red mb-3 flex items-center gap-2">
                      <TrendingDown className="w-4 h-4" /> Needs Work
                    </h3>
                    <div className="space-y-2">
                      {analytics.weak_areas.map(w => (
                        <div key={w.key} className="flex items-center justify-between">
                          <span className="text-sm font-syne text-ink">{w.label}</span>
                          <span className="text-xs font-syne font-bold text-red">{w.pct}%</span>
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={() => setActiveTab("practice")}
                      className="mt-3 text-xs font-syne font-semibold text-red hover:underline"
                    >
                      Practice weak areas →
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === "history" && (
          <div>
            <h2 className="font-syne font-black text-xl text-ink mb-4">Session History</h2>
            {gulfHistory.length === 0 ? (
              <div className="text-center py-16 text-ink-3 font-serif">
                <Globe className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>No Gulf exam sessions yet. Start a simulation above!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {gulfHistory.map(s => (
                  <div key={s.session_id} className="bg-surface border border-border rounded-xl p-4 flex items-center gap-4">
                    <div className="flex-shrink-0">
                      {s.passed === true ? (
                        <CheckCircle2 className="w-6 h-6 text-green" />
                      ) : s.passed === false ? (
                        <AlertTriangle className="w-6 h-6 text-red" />
                      ) : (
                        <Clock className="w-6 h-6 text-ink-3" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-syne font-bold text-sm text-ink truncate">{s.mode}</div>
                      <div className="text-ink-3 font-serif text-xs">
                        {new Date(s.started_at).toLocaleDateString()} · {s.total_questions} questions
                        {s.time_taken_min != null ? ` · ${s.time_taken_min} min` : ""}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {s.score_pct != null ? (
                        <>
                          <ScoreBadge pct={s.score_pct} />
                          <div className="text-ink-3 font-serif text-xs mt-1">
                            {s.correct ?? "?"}/{s.total_questions}
                          </div>
                        </>
                      ) : (
                        <span className="text-xs text-ink-3">—</span>
                      )}
                    </div>
                    <Link
                      href={`/exam?session=${s.session_id}&results=1`}
                      className="flex-shrink-0 text-xs font-syne font-semibold text-ink-3 hover:text-ink transition-colors"
                    >
                      Review
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
