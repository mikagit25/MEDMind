"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import {
  Calculator,
  ChevronRight,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Info,
  Zap,
  Timer,
  BarChart3,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

type BaseCategory = "weight_dose" | "infusion_rate" | "dilution" | "unit_convert" | "pediatric_dose";
type Category = BaseCategory | "mixed";

const BASE_CATEGORIES: BaseCategory[] = ["weight_dose", "infusion_rate", "dilution", "unit_convert", "pediatric_dose"];

function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

type Problem = {
  category: string;
  question: string;
  numeric_answer: number;
  numeric_tolerance: number;
  numeric_unit: string;
  steps: string[];
  seed: number;
};

type CheckResult = {
  correct: boolean;
  expected: number;
  tolerance: number;
  unit: string;
  steps: string[];
  diff: number;
  overall_streak: number;
  overall_total: number;
  overall_correct: number;
  cat_total: number;
  cat_correct: number;
};

type CategoryStat = {
  total: number;
  correct: number;
  pct: number;
  streak: number;
  best_streak: number;
};

type StatsMap = Record<string, CategoryStat>;

// ── Dose-Calc API ──────────────────────────────────────────────────────────────

const doseCalcApi = {
  getProblem: (category: BaseCategory, seed?: number) =>
    api.get(`/dose-calc/problem/${category}${seed !== undefined ? `?seed=${seed}` : ""}`).then(r => r.data),
  checkAnswer: (category: BaseCategory, seed: number, numeric_value: number) =>
    api.post("/dose-calc/check", { category, seed, numeric_value }).then(r => r.data),
  getStats: (): Promise<StatsMap> =>
    api.get("/dose-calc/stats").then(r => r.data),
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function StepSolution({ steps, title }: { steps: string[]; title: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
      <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-3">{title}</div>
      {steps.map((step, i) => (
        <div key={i} className="flex gap-3">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-ink text-white text-xs font-syne font-bold flex items-center justify-center">
            {i + 1}
          </span>
          <p className="text-sm font-serif text-ink leading-relaxed">{step}</p>
        </div>
      ))}
    </div>
  );
}

function TimerDisplay({ seconds }: { seconds: number }) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  const cls =
    seconds <= 10 ? "text-red border-red/30 bg-red/10" :
    seconds <= 30 ? "text-amber-600 border-amber-200 bg-amber-50" :
    "text-ink-3 border-border bg-surface";
  return (
    <span className={`flex items-center gap-1 text-xs font-syne font-bold border rounded-full px-2.5 py-0.5 transition-colors ${cls}`}>
      <Timer className="w-3 h-3" />
      {m}:{String(s).padStart(2, "0")}
    </span>
  );
}

function StatBar({ label, stat }: { label: string; stat: CategoryStat }) {
  const pct = stat.pct;
  const color = pct >= 75 ? "bg-green" : pct >= 50 ? "bg-amber-400" : "bg-red";
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-serif text-ink-2 truncate pr-2">{label}</span>
        <span className="text-xs font-syne font-bold text-ink flex-shrink-0">
          {pct}% <span className="text-ink-3 font-normal">({stat.correct}/{stat.total})</span>
        </span>
      </div>
      <div className="h-1.5 bg-border rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Timer logic ────────────────────────────────────────────────────────────────

const TIMER_DURATION = 90;

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function DoseCalcPage() {
  const t = useT();
  const [selectedCategory, setSelectedCategory] = useState<Category>("weight_dose");
  const [problem, setProblem] = useState<Problem | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [result, setResult] = useState<CheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [streak, setStreak] = useState(0);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<StatsMap>({});
  const [showStats, setShowStats] = useState(false);

  // Timer
  const [timerEnabled, setTimerEnabled] = useState(false);
  const [timeLeft, setTimeLeft] = useState(TIMER_DURATION);
  const [timerRunning, setTimerRunning] = useState(false);
  const inputValueRef = useRef(inputValue);
  const problemRef = useRef(problem);
  const checkingRef = useRef(false);

  useEffect(() => { inputValueRef.current = inputValue; }, [inputValue]);
  useEffect(() => { problemRef.current = problem; }, [problem]);
  useEffect(() => { checkingRef.current = checking; }, [checking]);

  // Load persisted stats on mount (Task 7)
  useEffect(() => {
    doseCalcApi.getStats().then(s => {
      setStats(s);
      const overall = s["_overall"];
      if (overall) {
        setStreak(overall.streak);
        setTotal(overall.total);
      }
    }).catch(() => {});
  }, []);

  // Reset/start timer when problem changes or timer toggled
  useEffect(() => {
    if (timerEnabled && problem && !result) {
      setTimeLeft(TIMER_DURATION);
      setTimerRunning(true);
    } else {
      setTimerRunning(false);
      setTimeLeft(TIMER_DURATION);
    }
  }, [problem?.seed, timerEnabled]); // eslint-disable-line react-hooks/exhaustive-deps

  // Stop timer on result
  useEffect(() => {
    if (result) setTimerRunning(false);
  }, [result]);

  // Countdown tick
  useEffect(() => {
    if (!timerRunning) return;
    if (timeLeft <= 0) {
      setTimerRunning(false);
      const p = problemRef.current;
      if (p && !checkingRef.current) {
        const raw = parseFloat(inputValueRef.current.replace(",", "."));
        doseCalcApi.checkAnswer(p.category as BaseCategory, p.seed, isNaN(raw) ? 0 : raw)
          .then((r: CheckResult) => {
            setResult(r);
            setStreak(r.overall_streak);
            setTotal(r.overall_total);
            setStats(prev => updateStatsFromResult(prev, p.category as BaseCategory, r));
          }).catch(() => {});
      }
      return;
    }
    const id = setTimeout(() => setTimeLeft(t => t - 1), 1000);
    return () => clearTimeout(id);
  }, [timerRunning, timeLeft]);

  function updateStatsFromResult(prev: StatsMap, cat: BaseCategory, r: CheckResult): StatsMap {
    return {
      ...prev,
      [cat]: { total: r.cat_total, correct: r.cat_correct, pct: r.cat_total ? Math.round(r.cat_correct / r.cat_total * 100) : 0, streak: 0, best_streak: 0 },
      "_overall": { total: r.overall_total, correct: r.overall_correct, pct: r.overall_total ? Math.round(r.overall_correct / r.overall_total * 100) : 0, streak: r.overall_streak, best_streak: prev["_overall"]?.best_streak ?? 0 },
    };
  }

  const CATEGORIES: { key: Category; icon: string; label: string; description: string }[] = [
    { key: "mixed",          icon: "🎲", label: t("dose_trainer.cat_mixed_label"),     description: t("dose_trainer.cat_mixed_desc") },
    { key: "weight_dose",    icon: "⚖️", label: t("dose_trainer.cat_weight_label"),    description: t("dose_trainer.cat_weight_desc") },
    { key: "infusion_rate",  icon: "💧", label: t("dose_trainer.cat_infusion_label"),  description: t("dose_trainer.cat_infusion_desc") },
    { key: "dilution",       icon: "🧪", label: t("dose_trainer.cat_dilution_label"),  description: t("dose_trainer.cat_dilution_desc") },
    { key: "unit_convert",   icon: "🔄", label: t("dose_trainer.cat_convert_label"),   description: t("dose_trainer.cat_convert_desc") },
    { key: "pediatric_dose", icon: "👶", label: t("dose_trainer.cat_pediatric_label"), description: t("dose_trainer.cat_pediatric_desc") },
  ];

  const activeCategoryLabel = problem
    ? (CATEGORIES.find(c => c.key === problem.category)?.label ?? CATEGORIES.find(c => c.key === selectedCategory)?.label)
    : CATEGORIES.find(c => c.key === selectedCategory)?.label;

  const loadProblem = useCallback(async (cat: Category, seed?: number) => {
    setLoading(true);
    setResult(null);
    setInputValue("");
    try {
      const actualCat: BaseCategory = cat === "mixed" ? pickRandom(BASE_CATEGORIES) : cat;
      const p = await doseCalcApi.getProblem(actualCat, seed);
      setProblem(p);
    } catch {
      alert(t("dose_trainer.err_load"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  async function checkAnswer() {
    if (!problem || !inputValue.trim()) return;
    const val = parseFloat(inputValue.replace(",", "."));
    if (isNaN(val)) { alert(t("dose_trainer.err_number")); return; }

    setChecking(true);
    try {
      const r: CheckResult = await doseCalcApi.checkAnswer(problem.category as BaseCategory, problem.seed, val);
      setResult(r);
      setStreak(r.overall_streak);
      setTotal(r.overall_total);
      setStats(prev => updateStatsFromResult(prev, problem.category as BaseCategory, r));
    } catch {
      alert(t("dose_trainer.err_check"));
    } finally {
      setChecking(false);
    }
  }

  function nextProblem() { loadProblem(selectedCategory); }

  function handleCategoryChange(cat: Category) {
    setSelectedCategory(cat);
    setProblem(null);
    setResult(null);
    setInputValue("");
    setTimerRunning(false);
    setTimeLeft(TIMER_DURATION);
  }

  const overallPct = total > 0 ? Math.round((stats["_overall"]?.correct ?? 0) / total * 100) : 0;
  const hasStats = Object.keys(stats).some(k => k !== "_overall" && stats[k].total > 0);

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <div className="border-b border-border bg-surface px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calculator className="w-5 h-5 text-ink" />
            <div>
              <h1 className="font-syne font-black text-lg text-ink leading-none">{t("dose_trainer.title")}</h1>
              <p className="text-ink-3 font-serif text-xs mt-0.5">{t("dose_trainer.sub")}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {hasStats && (
              <button
                onClick={() => setShowStats(s => !s)}
                title={t("dose_trainer.stats_toggle")}
                className={`flex items-center gap-1.5 text-xs font-syne font-bold px-3 py-1.5 rounded-lg border transition-all ${
                  showStats ? "bg-ink text-white border-ink" : "bg-surface text-ink-3 border-border hover:border-ink hover:text-ink"
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                {t("dose_trainer.stats_btn")}
              </button>
            )}
            <button
              onClick={() => setTimerEnabled(e => !e)}
              title={timerEnabled ? t("dose_trainer.timer_disable") : t("dose_trainer.timer_enable")}
              className={`flex items-center gap-1.5 text-xs font-syne font-bold px-3 py-1.5 rounded-lg border transition-all ${
                timerEnabled ? "bg-ink text-white border-ink" : "bg-surface text-ink-3 border-border hover:border-ink hover:text-ink"
              }`}
            >
              <Timer className="w-3.5 h-3.5" />
              {timerEnabled ? t("dose_trainer.timer_on") : t("dose_trainer.timer_off")}
            </button>
            <Link href="/nurses/nclex" className="text-xs font-syne text-ink-3 hover:text-ink transition-colors">
              {t("dose_trainer.back")}
            </Link>
          </div>
        </div>
      </div>

      {/* Stats strip */}
      {total > 0 && (
        <div className="bg-ink text-white">
          <div className="max-w-3xl mx-auto px-6 py-2 flex gap-6">
            <span className="text-xs font-syne flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              {t("dose_trainer.streak")} <strong>{streak}</strong>
            </span>
            <span className="text-xs font-syne">
              {t("dose_trainer.score")} <strong>{stats["_overall"]?.correct ?? 0}/{total}</strong> ({overallPct}%)
            </span>
          </div>
        </div>
      )}

      <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
        {/* Per-category stats panel (Task 6) */}
        {showStats && hasStats && (
          <div className="bg-surface border border-border rounded-xl p-5">
            <h2 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" /> {t("dose_trainer.stats_title")}
            </h2>
            <div className="space-y-3">
              {BASE_CATEGORIES.map(cat => {
                const s = stats[cat];
                if (!s || s.total === 0) return null;
                const label = CATEGORIES.find(c => c.key === cat)?.label ?? cat;
                return <StatBar key={cat} label={label} stat={s} />;
              })}
            </div>
          </div>
        )}

        {/* Category selector */}
        <div>
          <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-3">
            {t("dose_trainer.choose_category")}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {CATEGORIES.map(cat => {
              const catStat = cat.key !== "mixed" ? stats[cat.key] : undefined;
              return (
                <button
                  key={cat.key}
                  onClick={() => handleCategoryChange(cat.key)}
                  className={`text-left px-4 py-3 rounded-xl border transition-all ${
                    selectedCategory === cat.key
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-surface text-ink hover:border-ink"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="text-xl mb-1">{cat.icon}</div>
                    {catStat && catStat.total > 0 && (
                      <span className={`text-[10px] font-syne font-bold ${
                        selectedCategory === cat.key ? "text-white/70" :
                        catStat.pct >= 75 ? "text-green" : catStat.pct >= 50 ? "text-amber-500" : "text-red"
                      }`}>
                        {catStat.pct}%
                      </span>
                    )}
                  </div>
                  <div className="font-syne font-bold text-sm leading-snug">{cat.label}</div>
                  <div className={`font-serif text-xs mt-0.5 leading-snug ${selectedCategory === cat.key ? "text-white/70" : "text-ink-3"}`}>
                    {cat.description}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Generate button */}
        {!problem && (
          <div className="text-center py-8">
            <button
              onClick={() => loadProblem(selectedCategory)}
              disabled={loading}
              className="font-syne font-bold text-sm bg-ink text-white px-8 py-3.5 rounded-xl hover:bg-red transition-colors disabled:opacity-50 flex items-center gap-2 mx-auto"
            >
              <Calculator className="w-4 h-4" />
              {loading ? t("dose_trainer.generating") : t("dose_trainer.generate")}
            </button>
            <p className="text-ink-3 font-serif text-xs mt-3">{t("dose_trainer.deterministic")}</p>
          </div>
        )}

        {/* Problem card */}
        {problem && (
          <div className="space-y-4">
            <div className="bg-surface border border-border rounded-xl p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider">
                    {activeCategoryLabel}
                  </div>
                  {timerEnabled && !result && <TimerDisplay seconds={timeLeft} />}
                </div>
                <button
                  onClick={nextProblem}
                  disabled={loading}
                  className="text-xs font-syne text-ink-3 hover:text-ink transition-colors flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" /> {t("dose_trainer.new_problem")}
                </button>
              </div>

              <p className="font-serif text-base text-ink leading-relaxed mb-6">{problem.question}</p>

              {!result && (
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <input
                      type="number"
                      step="any"
                      value={inputValue}
                      onChange={e => setInputValue(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && checkAnswer()}
                      placeholder={t("dose_trainer.enter_answer")}
                      className="w-full bg-bg border border-border rounded-xl px-4 py-3 font-mono text-sm text-ink focus:outline-none focus:border-ink transition-colors"
                    />
                    {problem.numeric_unit && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-syne text-ink-3 font-bold pointer-events-none">
                        {problem.numeric_unit}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={checkAnswer}
                    disabled={checking || !inputValue.trim()}
                    className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors disabled:opacity-40"
                  >
                    {checking ? t("dose_trainer.checking") : t("common.submit")}
                  </button>
                </div>
              )}
            </div>

            {result && (
              <div className={`rounded-xl border p-5 ${result.correct ? "bg-green/5 border-green/30" : "bg-red/5 border-red/30"}`}>
                <div className="flex items-center gap-2 mb-3">
                  {result.correct ? (
                    <CheckCircle2 className="w-5 h-5 text-green" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red" />
                  )}
                  <span className={`font-syne font-bold text-sm ${result.correct ? "text-green" : "text-red"}`}>
                    {result.correct ? t("dose_trainer.correct") : t("dose_trainer.incorrect")}
                  </span>
                  {!result.correct && (
                    <span className="text-ink-2 font-serif text-sm">
                      — {t("dose_trainer.correct_answer")} <strong>{result.expected} {result.unit}</strong>
                      <span className="text-ink-3 text-xs"> (±{result.tolerance})</span>
                    </span>
                  )}
                </div>

                <StepSolution steps={result.steps} title={t("dose_trainer.steps_title")} />

                <button
                  onClick={nextProblem}
                  className="mt-4 font-syne font-bold text-sm bg-ink text-white px-6 py-2.5 rounded-xl hover:bg-red transition-colors flex items-center gap-2"
                >
                  {t("dose_trainer.next_problem")} <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}

            <div className="flex items-start gap-2 text-xs font-serif text-ink-3">
              <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>{t("dose_trainer.formula_note")}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
