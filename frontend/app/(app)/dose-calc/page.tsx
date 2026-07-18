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
};

// ── Dose-Calc API ──────────────────────────────────────────────────────────────

const doseCalcApi = {
  getCategories: () => api.get("/dose-calc/categories").then(r => r.data),
  getProblem: (category: Category, seed?: number) =>
    api.get(`/dose-calc/problem/${category}${seed !== undefined ? `?seed=${seed}` : ""}`).then(r => r.data),
  checkAnswer: (category: Category, seed: number, numeric_value: number) =>
    api.post("/dose-calc/check", { category, seed, numeric_value }).then(r => r.data),
};

// ── Step Solution display ──────────────────────────────────────────────────────

function StepSolution({ steps, title }: { steps: string[]; title: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
      <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-3">
        {title}
      </div>
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

// ── Timer display ──────────────────────────────────────────────────────────────

function TimerDisplay({ seconds }: { seconds: number }) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  const label = `${m}:${String(s).padStart(2, "0")}`;
  const cls =
    seconds <= 10 ? "text-red border-red/30 bg-red/10" :
    seconds <= 30 ? "text-amber-600 border-amber-200 bg-amber-50" :
    "text-ink-3 border-border bg-surface";
  return (
    <span className={`flex items-center gap-1 text-xs font-syne font-bold border rounded-full px-2.5 py-0.5 transition-colors ${cls}`}>
      <Timer className="w-3 h-3" />
      {label}
    </span>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

const TIMER_DURATION = 90;

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

  // Timer state
  const [timerEnabled, setTimerEnabled] = useState(false);
  const [timeLeft, setTimeLeft] = useState(TIMER_DURATION);
  const [timerRunning, setTimerRunning] = useState(false);
  const inputValueRef = useRef(inputValue);
  const problemRef = useRef(problem);
  const checkingRef = useRef(false);

  useEffect(() => { inputValueRef.current = inputValue; }, [inputValue]);
  useEffect(() => { problemRef.current = problem; }, [problem]);
  useEffect(() => { checkingRef.current = checking; }, [checking]);

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

  // Stop timer when result arrives
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
        const submitVal = isNaN(raw) ? 0 : raw;
        // Fire-and-forget auto-submit using the actual category stored in the problem
        doseCalcApi.checkAnswer(p.category as BaseCategory, p.seed, submitVal).then((r: CheckResult) => {
          setResult(r);
          setTotal(tot => tot + 1);
          if (r.correct) setStreak(s => s + 1);
          else setStreak(0);
        }).catch(() => {});
      }
      return;
    }
    const id = setTimeout(() => setTimeLeft(t => t - 1), 1000);
    return () => clearTimeout(id);
  }, [timerRunning, timeLeft]);

  const CATEGORIES: { key: Category; icon: string; label: string; description: string }[] = [
    { key: "mixed",          icon: "🎲", label: t("dose_trainer.cat_mixed_label"),     description: t("dose_trainer.cat_mixed_desc") },
    { key: "weight_dose",    icon: "⚖️", label: t("dose_trainer.cat_weight_label"),    description: t("dose_trainer.cat_weight_desc") },
    { key: "infusion_rate",  icon: "💧", label: t("dose_trainer.cat_infusion_label"),  description: t("dose_trainer.cat_infusion_desc") },
    { key: "dilution",       icon: "🧪", label: t("dose_trainer.cat_dilution_label"),  description: t("dose_trainer.cat_dilution_desc") },
    { key: "unit_convert",   icon: "🔄", label: t("dose_trainer.cat_convert_label"),   description: t("dose_trainer.cat_convert_desc") },
    { key: "pediatric_dose", icon: "👶", label: t("dose_trainer.cat_pediatric_label"), description: t("dose_trainer.cat_pediatric_desc") },
  ];

  // Resolve display label for the active problem (mixed mode shows actual category)
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
      setTotal(tot => tot + 1);
      if (r.correct) setStreak(s => s + 1);
      else setStreak(0);
    } catch {
      alert(t("dose_trainer.err_check"));
    } finally {
      setChecking(false);
    }
  }

  function nextProblem() {
    loadProblem(selectedCategory);
  }

  function handleCategoryChange(cat: Category) {
    setSelectedCategory(cat);
    setProblem(null);
    setResult(null);
    setInputValue("");
    setTimerRunning(false);
    setTimeLeft(TIMER_DURATION);
  }

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
            <button
              onClick={() => setTimerEnabled(e => !e)}
              title={timerEnabled ? t("dose_trainer.timer_disable") : t("dose_trainer.timer_enable")}
              className={`flex items-center gap-1.5 text-xs font-syne font-bold px-3 py-1.5 rounded-lg border transition-all ${
                timerEnabled
                  ? "bg-ink text-white border-ink"
                  : "bg-surface text-ink-3 border-border hover:border-ink hover:text-ink"
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

      {/* Stats */}
      {total > 0 && (
        <div className="bg-ink text-white">
          <div className="max-w-3xl mx-auto px-6 py-2 flex gap-6">
            <span className="text-xs font-syne flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              {t("dose_trainer.streak")} <strong>{streak}</strong>
            </span>
            <span className="text-xs font-syne">
              {t("dose_trainer.score")} <strong>{streak}/{total}</strong> ({Math.round((streak / total) * 100)}%)
            </span>
          </div>
        </div>
      )}

      <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
        {/* Category selector */}
        <div>
          <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-3">
            {t("dose_trainer.choose_category")}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat.key}
                onClick={() => handleCategoryChange(cat.key)}
                className={`text-left px-4 py-3 rounded-xl border transition-all ${
                  selectedCategory === cat.key
                    ? "border-ink bg-ink text-white"
                    : "border-border bg-surface text-ink hover:border-ink"
                }`}
              >
                <div className="text-xl mb-1">{cat.icon}</div>
                <div className="font-syne font-bold text-sm leading-snug">{cat.label}</div>
                <div className={`font-serif text-xs mt-0.5 leading-snug ${selectedCategory === cat.key ? "text-white/70" : "text-ink-3"}`}>
                  {cat.description}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Generate button (when no problem) */}
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
            <p className="text-ink-3 font-serif text-xs mt-3">
              {t("dose_trainer.deterministic")}
            </p>
          </div>
        )}

        {/* Problem card */}
        {problem && (
          <div className="space-y-4">
            {/* Question */}
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

              {/* Answer input */}
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

            {/* Result */}
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

            {/* Info */}
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
