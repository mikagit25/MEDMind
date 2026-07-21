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

const GULF_EXAM_SLUGS = ["snle", "dha", "qchp", "omsb", "nhra", "mohuae", "haad"] as const;
type GulfSlug = typeof GULF_EXAM_SLUGS[number];

const GULF_EXAM_INFO: Record<GulfSlug, { name: string; country: string; flag: string; full: string }> = {
  snle:   { name: "SNLE",    country: "Saudi Arabia",  flag: "🇸🇦", full: "Saudi Nursing Licensure Exam" },
  dha:    { name: "DHA",     country: "Dubai",         flag: "🇦🇪", full: "Dubai Health Authority" },
  qchp:   { name: "QCHP",   country: "Qatar",         flag: "🇶🇦", full: "Qatar Council for Healthcare Practitioners" },
  omsb:   { name: "OMSB",   country: "Oman",          flag: "🇴🇲", full: "Oman Medical Specialty Board" },
  nhra:   { name: "NHRA",   country: "Bahrain",       flag: "🇧🇭", full: "National Health Regulatory Authority" },
  mohuae: { name: "MOH UAE", country: "UAE",           flag: "🇦🇪", full: "Ministry of Health UAE" },
  haad:   { name: "HAAD",   country: "Abu Dhabi",     flag: "🇦🇪", full: "Health Authority Abu Dhabi" },
};

const GULF_MODE_IDS = [
  "snle_full", "dha_full", "qchp_full", "omsb_full",
  "nhra_full", "mohuae_full", "haad_full",
  "gulf_practice",
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
}: {
  readiness: GulfReadiness | null;
  examSlug: GulfSlug;
}) {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const info = GULF_EXAM_INFO[examSlug];

  if (!readiness) {
    return <div className="py-12 text-center text-ink-3 font-serif">Loading readiness…</div>;
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
  const [selectedSlug, setSelectedSlug] = useState<GulfSlug>("snle");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"practice" | "readiness" | "history">("practice");

  const loadReadiness = useCallback(async (slug: GulfSlug) => {
    try {
      const r = await examApi.getGulfReadiness(slug);
      setReadiness(r);
    } catch {
      setReadiness(null);
    }
  }, []);

  useEffect(() => {
    Promise.all([examApi.getModes(), examApi.getHistory(30)])
      .then(([modeList, hist]) => {
        const gulfModes = modeList.filter((m: ExamMode) => GULF_MODE_IDS.includes(m.id));
        setModes(gulfModes);
        setHistory(hist.filter((s: SessionHistory) => GULF_MODE_IDS.includes(s.mode_id)));
      })
      .finally(() => setLoading(false));
    loadReadiness("snle");
  }, [loadReadiness]);

  function handleSlugChange(slug: GulfSlug) {
    setSelectedSlug(slug);
    setReadiness(null);
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

  // Separate full-simulation modes from general practice
  const fullSimModes = modes.filter(m => m.id !== "gulf_practice");
  const practiceModes = modes.filter(m => m.id === "gulf_practice");

  const TABS = [
    { id: "practice" as const, label: "Exam Simulations" },
    { id: "readiness" as const, label: "Readiness Score" },
    { id: "history" as const, label: `History (${gulfHistory.length})` },
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
                <p className="font-syne font-bold text-xs text-amber-700 mb-0.5">Content in Progress</p>
                <p className="font-serif text-xs text-amber-600 leading-relaxed">
                  Gulf-specific question banks are being generated automatically. More questions are added every 30 minutes.
                  Meanwhile, practice using the general Gulf Practice mode which uses our full NCLEX bank.
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

            {/* Full simulation for selected exam */}
            {(() => {
              const modeId = `${selectedSlug}_full`;
              const mode = fullSimModes.find(m => m.id === modeId);
              if (!mode) return null;
              const info = GULF_EXAM_INFO[selectedSlug];
              return (
                <div className="bg-surface border-2 border-ink rounded-xl p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{info.flag}</span>
                      <div>
                        <div className="font-syne font-black text-base text-ink">{info.name} Full Simulation</div>
                        <div className="text-ink-3 font-serif text-xs">{info.full}</div>
                      </div>
                    </div>
                    <span className="text-xs font-syne font-bold bg-ink/5 border border-ink/20 rounded-full px-2 py-0.5 text-ink">
                      Official Format
                    </span>
                  </div>
                  <div className="flex gap-6 text-xs font-syne text-ink-3 mb-5">
                    <span className="flex items-center gap-1">
                      <Star className="w-3 h-3" /> {mode.questions} questions
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {mode.duration_min} minutes
                    </span>
                    <span className="flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Pass: 60%
                    </span>
                  </div>
                  {mode.locked ? (
                    <div className="text-xs font-serif text-ink-3 italic">{mode.lock_reason}</div>
                  ) : (
                    <button
                      onClick={() => startSession(mode.id)}
                      disabled={starting === mode.id}
                      className="font-syne font-bold text-sm bg-ink text-white px-8 py-3 rounded-xl hover:bg-red transition-colors disabled:opacity-50"
                    >
                      {starting === mode.id ? "Starting…" : `Start ${info.name} Simulation →`}
                    </button>
                  )}
                </div>
              );
            })()}

            {/* General Gulf Practice */}
            {practiceModes.length > 0 && (
              <section>
                <h2 className="font-syne font-black text-xl text-ink mb-3">Gulf Practice</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {practiceModes.map(mode => (
                    <div key={mode.id} className={`bg-surface border border-border rounded-xl p-5 ${mode.locked ? "opacity-60" : ""}`}>
                      <div className="font-syne font-bold text-sm text-ink mb-1">{mode.name}</div>
                      <div className="font-serif text-xs text-ink-3 leading-relaxed mb-3">{mode.description}</div>
                      <div className="flex gap-4 text-xs font-syne text-ink-3 mb-4">
                        <span>{mode.questions} questions</span>
                        <span>{mode.duration_min} min</span>
                      </div>
                      {mode.locked ? (
                        <div className="text-xs font-serif text-ink-3 italic">{mode.lock_reason}</div>
                      ) : (
                        <button
                          onClick={() => startSession(mode.id)}
                          disabled={starting === mode.id}
                          className="font-syne font-bold text-sm bg-ink text-white px-5 py-2 rounded-lg hover:bg-red transition-colors disabled:opacity-50"
                        >
                          {starting === mode.id ? "Starting…" : "Start Practice"}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* All exams quick launch */}
            <section>
              <h2 className="font-syne font-black text-xl text-ink mb-3">All Gulf Exams</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {GULF_EXAM_SLUGS.map(slug => {
                  const info = GULF_EXAM_INFO[slug];
                  const modeId = `${slug}_full`;
                  const mode = fullSimModes.find(m => m.id === modeId);
                  return (
                    <div key={slug} className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
                      <span className="text-xl flex-shrink-0">{info.flag}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-syne font-bold text-sm text-ink">{info.name}</div>
                        <div className="font-serif text-xs text-ink-3 truncate">{info.full}</div>
                        {mode && (
                          <div className="text-[10px] font-syne text-ink-3 mt-0.5">
                            {mode.questions}Q · {mode.duration_min}min
                          </div>
                        )}
                      </div>
                      {mode && !mode.locked ? (
                        <button
                          onClick={() => startSession(modeId)}
                          disabled={starting === modeId}
                          className="flex-shrink-0 font-syne font-bold text-xs bg-ink text-white px-3 py-2 rounded-lg hover:bg-red transition-colors disabled:opacity-50"
                        >
                          {starting === modeId ? "…" : "Start"}
                        </button>
                      ) : (
                        <ChevronRight className="w-4 h-4 text-ink-3 flex-shrink-0" />
                      )}
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

            <ReadinessPanel readiness={readiness} examSlug={selectedSlug} />

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
