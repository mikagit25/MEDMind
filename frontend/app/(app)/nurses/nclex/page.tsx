"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { examApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import {
  HeartPulse,
  BookOpen,
  Calculator,
  BarChart3,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  Trophy,
  Target,
  Zap,
  Layers,
  TrendingUp,
  TrendingDown,
  Gift,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

type ExamMode = {
  id: string;
  name: string;
  description: string;
  questions: number;
  duration_min: number;
  nursing_only: boolean;
  cat: boolean;
  locked: boolean;
  lock_reason: string | null;
  icon: string;
  pass_threshold: number;
  demo?: boolean;
};

type NCLEXCategory = {
  key: string;
  label: string;
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
  cat_enabled: boolean;
};

type Analytics = {
  sessions_analyzed: number;
  category_performance: Record<string, { total: number; correct: number; pct: number; label: string }>;
  cjmm_performance: Record<string, { total: number; correct: number; pct: number; label: string }>;
  weak_categories: Array<{ key: string; label: string; pct: number; total: number }>;
  overall_trend: Array<{ session_id: string; date: string; score_pct: number; mode: string }>;
};

// ── Icon map ───────────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  "heart-pulse": HeartPulse,
  "stethoscope": BookOpen,
  "hospital": BookOpen,
  "layers": Layers,
  "flag": Target,
  "zap": Zap,
};

const NCLEX_MODE_IDS = ["nclex_rn_75", "nclex_rn_85", "nclex_rn_145", "nclex_category", "nclex_demo"];

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

function CategoryBar({ label, pct, total }: { label: string; pct: number; total: number }) {
  const color = pct >= 75 ? "bg-green" : pct >= 60 ? "bg-amber-400" : "bg-red";
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-serif text-ink-2 truncate pr-2">{label}</span>
        <span className="text-xs font-syne font-bold text-ink flex-shrink-0">{pct}% <span className="text-ink-3 font-normal">({total})</span></span>
      </div>
      <div className="h-1.5 bg-border rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function NCLEXHubPage() {
  const t = useT();
  const [modes, setModes] = useState<ExamMode[]>([]);
  const [nclex_modes, setNclexModes] = useState<ExamMode[]>([]);
  const [categories, setCategories] = useState<NCLEXCategory[]>([]);
  const [history, setHistory] = useState<SessionHistory[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"practice" | "history" | "analytics">("practice");

  const load = useCallback(async () => {
    try {
      const [modeList, catList, hist, analy] = await Promise.all([
        examApi.getModes(),
        examApi.getNCLEXCategories(),
        examApi.getHistory(10),
        examApi.getNCLEXAnalytics(),
      ]);
      setModes(modeList);
      setNclexModes(modeList.filter((m: ExamMode) => NCLEX_MODE_IDS.includes(m.id)));
      setCategories(catList);
      setHistory(hist);
      setAnalytics(analy);
    } catch {
      // silently fail — locked state handled per-card
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function startSession(modeId: string) {
    setStarting(modeId);
    try {
      const opts: { nclex_category?: string } = {};
      if (modeId === "nclex_category" && selectedCategory) {
        opts.nclex_category = selectedCategory;
      }
      const session = await examApi.createSession(modeId, undefined, opts);
      window.location.href = `/exam?session=${session.session_id}`;
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || t("nclex_hub.session_error");
      alert(msg);
    } finally {
      setStarting(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="text-ink-3 font-serif">{t("nclex_hub.loading")}</div>
      </div>
    );
  }

  const nclex_history = history.filter(s => NCLEX_MODE_IDS.includes(s.mode_id));
  const best_score = nclex_history.length
    ? Math.max(...nclex_history.map(s => s.score_pct ?? 0))
    : null;
  const last_score = nclex_history[0]?.score_pct ?? null;

  const TABS: { id: "practice" | "history" | "analytics"; label: string }[] = [
    { id: "practice",  label: t("nclex_hub.tab_practice") },
    { id: "history",   label: t("nclex_hub.tab_history") },
    { id: "analytics", label: t("nclex_hub.tab_analytics") },
  ];

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <div className="border-b border-border bg-surface px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <HeartPulse className="w-5 h-5 text-red" />
            <div>
              <h1 className="font-syne font-black text-lg text-ink leading-none">{t("nclex_hub.title")}</h1>
              <p className="text-ink-3 font-serif text-xs mt-0.5">{t("nclex_hub.sub")}</p>
            </div>
          </div>
          <Link href="/nurses" className="text-xs font-syne text-ink-3 hover:text-ink transition-colors">
            {t("nclex_hub.back")}
          </Link>
        </div>
      </div>

      {/* Stats strip */}
      {(best_score !== null || (analytics?.sessions_analyzed ?? 0) > 0) && (
        <div className="bg-ink text-white">
          <div className="max-w-5xl mx-auto px-6 py-3 flex flex-wrap gap-6">
            {best_score !== null && (
              <div className="flex items-center gap-2">
                <Trophy className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-syne">{t("nclex_hub.best_score")} <strong>{best_score}%</strong></span>
              </div>
            )}
            {last_score !== null && (
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-syne">{t("nclex_hub.last_score")} <strong>{last_score}%</strong></span>
              </div>
            )}
            {analytics && analytics.sessions_analyzed > 0 && (
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-green" />
                <span className="text-xs font-syne">{analytics.sessions_analyzed} {t("nclex_hub.sessions_analyzed")}</span>
              </div>
            )}
            {analytics?.weak_categories?.[0] && (
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-syne">{t("nclex_hub.weakest")} <strong>{analytics.weak_categories[0].label}</strong> ({analytics.weak_categories[0].pct}%)</span>
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
            {/* Free Demo banner */}
            {(() => {
              const demo = modes.find(m => m.id === "nclex_demo");
              if (!demo) return null;
              return (
                <div className="bg-green/5 border border-green/30 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-green/10 flex items-center justify-center flex-shrink-0">
                      <Gift className="w-5 h-5 text-green" />
                    </div>
                    <div>
                      <div className="font-syne font-black text-base text-ink leading-snug">{t("nclex_hub.demo_title")}</div>
                      <p className="text-ink-2 font-serif text-xs mt-0.5">{t("nclex_hub.demo_sub")}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => startSession("nclex_demo")}
                    disabled={starting === "nclex_demo"}
                    className="sm:ml-auto font-syne font-bold text-sm bg-green text-white px-6 py-2.5 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 flex-shrink-0"
                  >
                    {starting === "nclex_demo" ? t("nclex_hub.starting") : t("nclex_hub.demo_cta")}
                  </button>
                </div>
              );
            })()}

            {/* NCLEX Simulation modes */}
            <section>
              <div className="mb-4">
                <h2 className="font-syne font-black text-xl text-ink">{t("nclex_hub.sim_title")}</h2>
                <p className="text-ink-2 font-serif text-sm mt-1">{t("nclex_hub.sim_sub")}</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {nclex_modes.filter(m => m.id !== "nclex_category").map(mode => {
                  const Icon = ICON_MAP[mode.icon] ?? HeartPulse;
                  return (
                    <div
                      key={mode.id}
                      className={`bg-surface border rounded-xl p-5 transition-all ${
                        mode.locked ? "opacity-60 border-border" : "border-border hover:border-ink hover:shadow-sm"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <Icon className="w-5 h-5 text-red" />
                        {mode.cat && (
                          <span className="text-xs font-syne font-bold bg-blue-50 text-blue-600 border border-blue-200 rounded-full px-2 py-0.5">
                            {t("nclex_hub.cat_badge")}
                          </span>
                        )}
                      </div>
                      <h3 className="font-syne font-bold text-sm text-ink mb-1">
                        {t(`nclex_hub.modes.${mode.id}.name`) !== `nclex_hub.modes.${mode.id}.name` ? t(`nclex_hub.modes.${mode.id}.name`) : mode.name}
                      </h3>
                      <p className="text-ink-3 font-serif text-xs leading-relaxed mb-3">
                        {t(`nclex_hub.modes.${mode.id}.desc`) !== `nclex_hub.modes.${mode.id}.desc` ? t(`nclex_hub.modes.${mode.id}.desc`) : mode.description}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-ink-3 font-serif mb-4">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {mode.duration_min} {t("common.minutes")}
                        </span>
                        <span className="flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> {t("nclex_hub.pass_label")}{mode.pass_threshold}%
                        </span>
                      </div>
                      {mode.locked ? (
                        <div className="text-xs font-serif text-ink-3 italic">{t("nclex_hub.lock_reason")}</div>
                      ) : (
                        <button
                          onClick={() => startSession(mode.id)}
                          disabled={starting === mode.id}
                          className="w-full font-syne font-bold text-xs bg-ink text-white px-4 py-2.5 rounded-lg hover:bg-red transition-colors disabled:opacity-50"
                        >
                          {starting === mode.id ? t("nclex_hub.starting") : t("nclex_hub.start_sim")}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Category practice */}
            <section>
              <div className="mb-4">
                <h2 className="font-syne font-black text-xl text-ink">{t("nclex_hub.cat_prac_title")}</h2>
                <p className="text-ink-2 font-serif text-sm mt-1">{t("nclex_hub.cat_prac_sub")}</p>
              </div>
              <div className="bg-surface border border-border rounded-xl p-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 mb-4">
                  {categories.map(cat => {
                    const weakPct = analytics?.category_performance?.[cat.key]?.pct;
                    const isWeak = weakPct !== undefined && weakPct < 60;
                    return (
                      <button
                        key={cat.key}
                        onClick={() => setSelectedCategory(selectedCategory === cat.key ? "" : cat.key)}
                        className={`text-left px-3 py-2.5 rounded-lg border text-xs font-syne transition-all ${
                          selectedCategory === cat.key
                            ? "border-ink bg-ink text-white"
                            : isWeak
                            ? "border-red/40 bg-red/5 text-ink hover:border-red"
                            : "border-border text-ink hover:border-ink"
                        }`}
                      >
                        <span className="font-semibold">{cat.label}</span>
                        {weakPct !== undefined && (
                          <span className={`ml-2 font-normal ${selectedCategory === cat.key ? "text-white/70" : isWeak ? "text-red" : "text-ink-3"}`}>
                            {weakPct}%
                          </span>
                        )}
                        {isWeak && selectedCategory !== cat.key && (
                          <AlertTriangle className="inline w-3 h-3 ml-1 text-red" />
                        )}
                      </button>
                    );
                  })}
                </div>
                {(() => {
                  const catMode = nclex_modes.find(m => m.id === "nclex_category");
                  if (!catMode) return null;
                  return catMode.locked ? (
                    <div className="text-xs font-serif text-ink-3 italic">{catMode.lock_reason}</div>
                  ) : (
                    <button
                      onClick={() => startSession("nclex_category")}
                      disabled={!selectedCategory || starting === "nclex_category"}
                      className="font-syne font-bold text-sm bg-ink text-white px-6 py-2.5 rounded-lg hover:bg-red transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {selectedCategory
                        ? `${t("nclex_hub.practice_cat")} ${categories.find(c => c.key === selectedCategory)?.label} →`
                        : t("nclex_hub.select_cat")}
                    </button>
                  );
                })()}
              </div>
            </section>

            {/* Quick links */}
            <section>
              <h2 className="font-syne font-black text-xl text-ink mb-4">{t("nclex_hub.other_tools")}</h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Link
                  href="/learn"
                  className="flex items-center gap-3 bg-surface border border-border rounded-xl p-4 hover:border-ink hover:shadow-sm transition-all group"
                >
                  <BookOpen className="w-5 h-5 text-ink-3 group-hover:text-ink transition-colors" />
                  <div>
                    <div className="font-syne font-bold text-sm text-ink">{t("nclex_hub.modules_title")}</div>
                    <div className="text-ink-3 font-serif text-xs">{t("nclex_hub.modules_sub")}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-ink-3 ml-auto" />
                </Link>
                <Link
                  href="/dose-calc"
                  className="flex items-center gap-3 bg-surface border border-border rounded-xl p-4 hover:border-ink hover:shadow-sm transition-all group"
                >
                  <Calculator className="w-5 h-5 text-ink-3 group-hover:text-ink transition-colors" />
                  <div>
                    <div className="font-syne font-bold text-sm text-ink">{t("nclex_hub.dose_title")}</div>
                    <div className="text-ink-3 font-serif text-xs">{t("nclex_hub.dose_sub")}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-ink-3 ml-auto" />
                </Link>
                <Link
                  href="/quiz"
                  className="flex items-center gap-3 bg-surface border border-border rounded-xl p-4 hover:border-ink hover:shadow-sm transition-all group"
                >
                  <Zap className="w-5 h-5 text-ink-3 group-hover:text-ink transition-colors" />
                  <div>
                    <div className="font-syne font-bold text-sm text-ink">{t("nclex_hub.quiz_title")}</div>
                    <div className="text-ink-3 font-serif text-xs">{t("nclex_hub.quiz_sub")}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-ink-3 ml-auto" />
                </Link>
              </div>
            </section>
          </div>
        )}

        {/* ── History tab ── */}
        {activeTab === "history" && (
          <div>
            <h2 className="font-syne font-black text-xl text-ink mb-4">{t("nclex_hub.history_title")}</h2>
            {nclex_history.length === 0 ? (
              <div className="text-center py-16 text-ink-3 font-serif">
                <HeartPulse className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>{t("nclex_hub.history_empty")}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {nclex_history.map(s => (
                  <div
                    key={s.session_id}
                    className="bg-surface border border-border rounded-xl p-4 flex items-center gap-4"
                  >
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
                        {new Date(s.started_at).toLocaleDateString()} ·{" "}
                        {s.total_questions} {t("common.questions")} ·{" "}
                        {s.time_taken_min != null ? `${s.time_taken_min} ${t("common.minutes")}` : "—"}
                        {s.cat_enabled && ` · ${t("nclex_hub.cat_badge")}`}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {s.score_pct != null ? (
                        <>
                          <ScoreBadge pct={s.score_pct} />
                          <div className="text-ink-3 font-serif text-xs mt-1">
                            {s.correct}/{s.total_questions}
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
                      {t("nclex_hub.review")}
                    </Link>
                  </div>
                ))}
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
                <p>{t("nclex_hub.analytics_empty")}</p>
              </div>
            ) : (
              <>
                {/* Score trend */}
                {analytics.overall_trend.length > 1 && (
                  <div className="bg-surface border border-border rounded-xl p-5">
                    <h3 className="font-syne font-bold text-sm text-ink mb-3 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" /> {t("nclex_hub.score_trend")}
                    </h3>
                    <div className="flex items-end gap-2 h-20">
                      {analytics.overall_trend.slice().reverse().map((trend, i) => (
                        <div key={i} className="flex-1 flex flex-col items-center gap-1">
                          <div
                            className={`w-full rounded-t transition-all ${
                              (trend.score_pct ?? 0) >= 62 ? "bg-green" : "bg-red/60"
                            }`}
                            style={{ height: `${Math.max(8, ((trend.score_pct ?? 0) / 100) * 72)}px` }}
                          />
                          <span className="text-[10px] font-syne text-ink-3">
                            {trend.score_pct ?? 0}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Weak categories */}
                {analytics.weak_categories.length > 0 && (
                  <div className="bg-red/5 border border-red/20 rounded-xl p-5">
                    <h3 className="font-syne font-bold text-sm text-red mb-3 flex items-center gap-2">
                      <TrendingDown className="w-4 h-4" /> {t("nclex_hub.weak_areas")}
                    </h3>
                    <div className="space-y-3">
                      {analytics.weak_categories.map(c => (
                        <div key={c.key}>
                          <CategoryBar label={c.label} pct={c.pct} total={c.total} />
                          <button
                            onClick={() => {
                              setSelectedCategory(c.key);
                              setActiveTab("practice");
                            }}
                            className="mt-1 text-xs font-syne text-red hover:underline"
                          >
                            {t("nclex_hub.practice_this")}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* All categories */}
                <div className="bg-surface border border-border rounded-xl p-5">
                  <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
                    <Layers className="w-4 h-4" /> {t("nclex_hub.all_categories")}
                  </h3>
                  <div className="space-y-3">
                    {Object.entries(analytics.category_performance)
                      .sort((a, b) => a[1].pct - b[1].pct)
                      .map(([key, c]) => (
                        <CategoryBar key={key} label={c.label} pct={c.pct} total={c.total} />
                      ))}
                  </div>
                </div>

                {/* CJMM skills */}
                {Object.keys(analytics.cjmm_performance).length > 0 && (
                  <div className="bg-surface border border-border rounded-xl p-5">
                    <h3 className="font-syne font-bold text-sm text-ink mb-4">
                      {t("nclex_hub.cjmm_title")}
                    </h3>
                    <div className="space-y-3">
                      {Object.entries(analytics.cjmm_performance)
                        .sort((a, b) => a[1].pct - b[1].pct)
                        .map(([key, c]) => (
                          <CategoryBar key={key} label={c.label} pct={c.pct} total={c.total} />
                        ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
