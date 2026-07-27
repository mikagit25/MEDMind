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
  Info,
  Calendar,
  Flame,
  RefreshCw,
  Trash2,
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

type Readiness = {
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

type PlanTask = {
  date: string;
  task_type: "practice" | "mock_exam" | "review" | "rest" | "exam_day";
  questions: number;
  day_number: number;
  days_to_exam: number;
};

type StudyPlan = {
  id: string;
  exam_type: string;
  exam_date: string;
  daily_minutes: number;
  status: string;
  today_task: PlanTask | null;
  week_tasks: PlanTask[];
  full_plan: PlanTask[];
  completed_dates: string[];
  progress: { total_days: number; completed_days: number; completion_pct: number };
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

// Nursing study modules covering NCLEX Client Needs categories
const NCLEX_STUDY_MODULES = [
  {
    id: "f0913cce-0e39-419f-9b71-e31ee68d7e62",
    title: "Nursing Process & Documentation",
    category: "Management of Care · Safe & Effective Environment",
    icon: "📋", lessons: 2, mcqs: 119,
  },
  {
    id: "3e70e94e-72c2-48ef-a61b-843138f0952a",
    title: "Medication Safety",
    category: "Pharmacological Therapies · Physiological Integrity",
    icon: "💊", lessons: 2, mcqs: 115,
  },
  {
    id: "ea06574b-a01a-4c03-bb32-836179f82698",
    title: "Dose Calculations & Infusion Therapy",
    category: "Pharmacological Therapies — Calculations",
    icon: "🧮", lessons: 2, mcqs: 101,
  },
  {
    id: "89529702-32b1-4f38-bc90-6a4441109000",
    title: "Recognising Patient Deterioration",
    category: "Reduction of Risk Potential · Physiological Integrity",
    icon: "📈", lessons: 2, mcqs: 62,
  },
  {
    id: "a708a327-4246-4448-b739-31c5f61a091e",
    title: "Infection Control & Hand Hygiene",
    category: "Safety & Infection Control · Safe & Effective Environment",
    icon: "🦠", lessons: 2, mcqs: 58,
  },
  {
    id: "30acf5f5-72da-45d6-8277-820d5308fa92",
    title: "Emergency Situations",
    category: "Physiological Adaptation · Physiological Integrity",
    icon: "🚨", lessons: 2, mcqs: 42,
  },
  {
    id: "97b09cd4-f90a-488d-b263-bf37cfad37ef",
    title: "Patient Care: Pressure Injuries & Mobility",
    category: "Basic Care & Comfort · Physiological Integrity",
    icon: "🛏️", lessons: 2, mcqs: 31,
  },
  {
    id: "3785087f-c853-4adb-a717-9ac66df89034",
    title: "Mental Health & Psychiatric Nursing",
    category: "Psychosocial Integrity",
    icon: "🧠", lessons: 0, mcqs: 31,
  },
  {
    id: "43dc8dd3-dab0-4730-932a-c64ddb73709c",
    title: "Patient Communication & SBAR Handoff",
    category: "Management of Care — Communication",
    icon: "💬", lessons: 2, mcqs: 16,
  },
] as const;

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

// ── Readiness Tab Component ────────────────────────────────────────────────────

const LEVEL_CONFIG: Record<string, { color: string; bg: string; border: string }> = {
  high:          { color: "text-green",      bg: "bg-green/5",   border: "border-green/30" },
  passing_range: { color: "text-blue-600",   bg: "bg-blue-50",   border: "border-blue-200" },
  borderline:    { color: "text-amber-600",  bg: "bg-amber-50",  border: "border-amber-200" },
  below_passing: { color: "text-red",        bg: "bg-red/5",     border: "border-red/20" },
};

function ReadinessTab({
  readiness,
  onTrainCategory,
}: {
  readiness: Readiness | null;
  onTrainCategory: (key: string) => void;
}) {
  const [tooltipOpen, setTooltipOpen] = useState(false);

  if (!readiness) {
    return <div className="py-16 text-center text-ink-3 font-serif">Loading…</div>;
  }

  if (!readiness.threshold_met) {
    return (
      <div className="space-y-6">
        <div className="bg-surface border border-border rounded-xl p-8 text-center">
          <Target className="w-12 h-12 mx-auto mb-4 text-ink-3 opacity-40" />
          <h2 className="font-syne font-black text-xl text-ink mb-2">NCLEX Readiness Score</h2>
          <p className="font-serif text-sm text-ink-3 mb-4 max-w-sm mx-auto">
            Answer at least 50 NCLEX practice questions to unlock your readiness estimate.
          </p>
          <div className="inline-flex items-center gap-2 bg-border/40 rounded-full px-4 py-2">
            <div className="h-1.5 w-32 bg-border rounded-full overflow-hidden">
              <div
                className="h-full bg-ink rounded-full transition-all"
                style={{ width: `${Math.min(100, (readiness.questions_answered / 50) * 100)}%` }}
              />
            </div>
            <span className="text-xs font-syne font-bold text-ink-2">
              {readiness.questions_answered} / 50
            </span>
          </div>
          <p className="text-xs font-serif text-ink-3 mt-3">
            {readiness.questions_to_threshold} more questions to go
          </p>
        </div>
      </div>
    );
  }

  const score = readiness.score!;
  const level = readiness.level || "below_passing";
  const lvlCfg = LEVEL_CONFIG[level] ?? LEVEL_CONFIG.below_passing;
  const trendData = readiness.trend;

  return (
    <div className="space-y-6">
      {/* Score card */}
      <div className={`rounded-xl p-6 border ${lvlCfg.bg} ${lvlCfg.border}`}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h2 className="font-syne font-black text-sm text-ink uppercase tracking-wider">
                NCLEX Readiness Score
              </h2>
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
          <div className="text-right">
            <span className="text-xs font-syne text-ink-3">
              {readiness.questions_answered} questions answered
            </span>
          </div>
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

          {/* Mini trend sparkline */}
          {trendData.length > 1 && (
            <div className="flex-1 flex items-end gap-1 h-16 pb-1">
              {trendData.slice(-14).map((pt, i) => {
                const h = Math.max(4, ((pt.score_pct ?? 0) / 100) * 56);
                const color = (pt.score_pct ?? 0) >= 62 ? "bg-green/60" : "bg-red/40";
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

      {/* 30-day trend chart (larger) */}
      {trendData.length > 1 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" /> Performance Trend (last 30 days)
          </h3>
          <div className="flex items-end gap-1.5 h-24">
            {trendData.map((pt, i) => {
              const h = Math.max(4, ((pt.score_pct ?? 0) / 100) * 88);
              const color = (pt.score_pct ?? 0) >= 62 ? "bg-green" : "bg-red/60";
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                  <div className={`w-full rounded-t transition-all ${color}`} style={{ height: `${h}px` }} />
                  <span className="text-[9px] font-syne text-ink-3">
                    {(pt.score_pct ?? 0)}%
                  </span>
                  <div className="absolute -top-6 left-1/2 -translate-x-1/2 hidden group-hover:block bg-ink text-white text-[10px] font-syne rounded px-1.5 py-0.5 whitespace-nowrap z-10">
                    {pt.date}: {pt.correct}/{pt.total}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-[10px] font-syne text-ink-3 mt-1">
            <span>{trendData[0]?.date}</span>
            <span>{trendData[trendData.length - 1]?.date}</span>
          </div>
        </div>
      )}

      {/* Weak categories */}
      {readiness.weak_categories.length > 0 && (
        <div className="bg-red/5 border border-red/20 rounded-xl p-5">
          <h3 className="font-syne font-bold text-sm text-red mb-3 flex items-center gap-2">
            <TrendingDown className="w-4 h-4" /> Focus Areas ({readiness.weak_categories.length})
          </h3>
          <div className="space-y-3">
            {readiness.weak_categories.map(c => (
              <div key={c.key}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-serif text-ink-2 truncate pr-2">{c.label}</span>
                  <span className="text-xs font-syne font-bold text-ink flex-shrink-0">
                    {c.pct}% <span className="text-ink-3 font-normal">({c.count}q)</span>
                  </span>
                </div>
                <div className="h-1.5 bg-border rounded-full overflow-hidden mb-1.5">
                  <div className="h-full bg-red rounded-full" style={{ width: `${c.pct}%` }} />
                </div>
                <button
                  onClick={() => onTrainCategory(c.key)}
                  className="text-xs font-syne text-red hover:underline"
                >
                  Train this category →
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All categories breakdown */}
      {Object.keys(readiness.category_breakdown).length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
            <Layers className="w-4 h-4" /> Category Breakdown
          </h3>
          <div className="space-y-3">
            {Object.entries(readiness.category_breakdown)
              .sort((a, b) => a[1].pct - b[1].pct)
              .map(([key, c]) => {
                const color = c.pct >= 75 ? "bg-green" : c.pct >= 62 ? "bg-amber-400" : "bg-red";
                return (
                  <div key={key}>
                    <div className="flex justify-between items-center mb-1">
                      <button
                        onClick={() => onTrainCategory(key)}
                        className="text-xs font-serif text-ink-2 hover:text-ink transition-colors truncate pr-2 text-left"
                      >
                        {c.label}
                      </button>
                      <span className="text-xs font-syne font-bold text-ink flex-shrink-0">
                        {c.pct}% <span className="text-ink-3 font-normal">({c.count})</span>
                      </span>
                    </div>
                    <div className="h-1.5 bg-border rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${color}`} style={{ width: `${c.pct}%` }} />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <p className="text-xs font-serif text-ink-3 text-center italic px-4">
        {readiness.disclaimer}
      </p>
    </div>
  );
}

// ── Plan Tab Component ────────────────────────────────────────────────────────

const TASK_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  practice:  { label: "Practice",  color: "text-blue-600",  bg: "bg-blue-50",   border: "border-blue-200" },
  mock_exam: { label: "Mock Exam", color: "text-red",       bg: "bg-red/5",     border: "border-red/20" },
  review:    { label: "Review",    color: "text-amber-600", bg: "bg-amber-50",  border: "border-amber-200" },
  rest:      { label: "Rest Day",  color: "text-green",     bg: "bg-green/5",   border: "border-green/20" },
  exam_day:  { label: "Exam Day!", color: "text-ink",       bg: "bg-ink",       border: "border-ink" },
};

function TaskPill({ type, small }: { type: string; small?: boolean }) {
  const cfg = TASK_CONFIG[type] ?? TASK_CONFIG.practice;
  return (
    <span className={`inline-block font-syne font-bold rounded-full border ${small ? "text-[10px] px-2 py-0.5" : "text-xs px-3 py-1"} ${cfg.color} ${cfg.bg} ${cfg.border}`}>
      {cfg.label}
    </span>
  );
}

function PlanTab({
  plan,
  onPlanChange,
}: {
  plan: StudyPlan | null;
  onPlanChange: () => void;
}) {
  const [wizardDate, setWizardDate] = useState("");
  const [wizardMinutes, setWizardMinutes] = useState(30);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const today = new Date().toISOString().split("T")[0];

  async function handleCreate() {
    if (!wizardDate) { setError("Please pick your exam date."); return; }
    setSaving(true);
    setError("");
    try {
      await examApi.createPlan({ exam_date: wizardDate, daily_minutes: wizardMinutes });
      onPlanChange();
    } catch {
      setError("Could not create plan. Try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCompleteToday() {
    if (!plan?.today_task) return;
    setCompleting(true);
    try {
      await examApi.completeTodayTask(plan.today_task.task_type);
      onPlanChange();
    } catch {
      // silently ignore duplicate
    } finally {
      setCompleting(false);
    }
  }

  async function handleDelete() {
    try {
      await examApi.deletePlan();
      onPlanChange();
      setConfirmDelete(false);
    } catch { /* ignore */ }
  }

  // ── No plan yet: wizard ────────────────────────────────────────────────────
  if (!plan) {
    const minDate = new Date();
    minDate.setDate(minDate.getDate() + 2);
    const minDateStr = minDate.toISOString().split("T")[0];

    return (
      <div className="max-w-md mx-auto py-8">
        <div className="text-center mb-8">
          <Calendar className="w-12 h-12 mx-auto mb-4 text-ink-3 opacity-40" />
          <h2 className="font-syne font-black text-2xl text-ink mb-2">Create Your Study Plan</h2>
          <p className="font-serif text-sm text-ink-3">
            Set your exam date and we&apos;ll build a personalised day-by-day schedule.
          </p>
        </div>

        <div className="bg-surface border border-border rounded-xl p-6 space-y-5">
          <div>
            <label className="block font-syne font-bold text-xs text-ink mb-2 uppercase tracking-wider">
              Exam Date
            </label>
            <input
              type="date"
              min={minDateStr}
              value={wizardDate}
              onChange={e => setWizardDate(e.target.value)}
              className="w-full border border-border rounded-lg px-4 py-2.5 font-serif text-sm text-ink bg-bg focus:outline-none focus:ring-2 focus:ring-ink"
            />
          </div>

          <div>
            <label className="block font-syne font-bold text-xs text-ink mb-2 uppercase tracking-wider">
              Daily Study Time
            </label>
            <div className="grid grid-cols-3 gap-2">
              {([15, 30, 60] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setWizardMinutes(m)}
                  className={`py-2.5 rounded-lg border font-syne font-bold text-sm transition-all ${
                    wizardMinutes === m
                      ? "border-ink bg-ink text-white"
                      : "border-border text-ink hover:border-ink"
                  }`}
                >
                  {m} min
                </button>
              ))}
            </div>
            <p className="text-xs font-serif text-ink-3 mt-2">
              {wizardMinutes === 15 ? "10 questions/day"
               : wizardMinutes === 30 ? "20 questions/day"
               : "40 questions/day"}
            </p>
          </div>

          {error && (
            <p className="text-xs font-serif text-red">{error}</p>
          )}

          <button
            onClick={handleCreate}
            disabled={saving || !wizardDate}
            className="w-full font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors disabled:opacity-40"
          >
            {saving ? "Creating…" : "Build My Plan →"}
          </button>
        </div>
      </div>
    );
  }

  // ── Plan exists: calendar view ─────────────────────────────────────────────
  const todayDone = plan.completed_dates.includes(today);
  const daysLeft = plan.today_task?.days_to_exam ?? 0;

  return (
    <div className="space-y-6">
      {/* Header strip */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-syne font-black text-xl text-ink">Study Plan</h2>
          <p className="font-serif text-xs text-ink-3 mt-0.5">
            NCLEX · {plan.exam_date} · {plan.daily_minutes} min/day
            {daysLeft > 0 && <> · <strong className="text-ink">{daysLeft} days to go</strong></>}
          </p>
        </div>
        <button
          onClick={() => setConfirmDelete(true)}
          className="text-ink-3 hover:text-red transition-colors"
          title="Delete plan"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {confirmDelete && (
        <div className="bg-red/5 border border-red/20 rounded-xl p-4 flex items-center gap-4">
          <p className="text-sm font-serif text-ink flex-1">Delete this study plan?</p>
          <button
            onClick={handleDelete}
            className="font-syne font-bold text-xs text-red border border-red/30 px-3 py-1.5 rounded-lg hover:bg-red hover:text-white transition-colors"
          >
            Yes, delete
          </button>
          <button
            onClick={() => setConfirmDelete(false)}
            className="font-syne font-bold text-xs text-ink-3 hover:text-ink"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Progress bar */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <div className="flex justify-between items-center mb-2">
          <span className="font-syne font-bold text-sm text-ink">Overall Progress</span>
          <span className="font-syne font-bold text-sm text-ink">{plan.progress.completion_pct}%</span>
        </div>
        <div className="h-2 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-green rounded-full transition-all"
            style={{ width: `${plan.progress.completion_pct}%` }}
          />
        </div>
        <p className="text-xs font-serif text-ink-3 mt-2">
          {plan.progress.completed_days} of {plan.progress.total_days} days completed
        </p>
      </div>

      {/* Today's task */}
      {plan.today_task && plan.today_task.task_type !== "exam_day" && (
        <div className="bg-surface border-2 border-ink rounded-xl p-5">
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-1">Today</p>
              <TaskPill type={plan.today_task.task_type} />
            </div>
            {todayDone && (
              <div className="flex items-center gap-1 text-green">
                <CheckCircle2 className="w-5 h-5" />
                <span className="text-xs font-syne font-bold">Done!</span>
              </div>
            )}
          </div>
          {plan.today_task.questions > 0 && (
            <p className="font-serif text-sm text-ink-2 mb-4">
              {plan.today_task.questions} questions
              {plan.today_task.task_type === "mock_exam" && " · Full 75-question simulation"}
            </p>
          )}
          {plan.today_task.task_type === "rest" && (
            <p className="font-serif text-sm text-ink-2 mb-4">
              Rest and review your notes. Your exam is tomorrow — you&apos;re ready!
            </p>
          )}
          {!todayDone ? (
            <div className="flex gap-3">
              {plan.today_task.task_type !== "rest" && (
                <button
                  onClick={() => {
                    const modeId = plan.today_task?.task_type === "mock_exam" ? "nclex_rn_75" : "nclex_demo";
                    window.location.href = `/exam?session_mode=${modeId}`;
                  }}
                  className="font-syne font-bold text-sm bg-ink text-white px-5 py-2.5 rounded-lg hover:bg-red transition-colors"
                >
                  Start →
                </button>
              )}
              <button
                onClick={handleCompleteToday}
                disabled={completing}
                className="font-syne font-bold text-sm border border-border text-ink px-5 py-2.5 rounded-lg hover:border-ink transition-colors disabled:opacity-50"
              >
                {completing ? "…" : "Mark Done"}
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-green">
              <Flame className="w-4 h-4" />
              <span className="text-sm font-syne font-bold">Keep the streak going!</span>
            </div>
          )}
        </div>
      )}

      {plan.today_task?.task_type === "exam_day" && (
        <div className="bg-ink rounded-xl p-6 text-center text-white">
          <Trophy className="w-10 h-10 mx-auto mb-3 text-amber-400" />
          <h3 className="font-syne font-black text-xl mb-2">Exam Day!</h3>
          <p className="font-serif text-sm opacity-80">Good luck today. You&apos;ve prepared well.</p>
        </div>
      )}

      {/* This week */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
          <Calendar className="w-4 h-4" /> This Week
        </h3>
        <div className="space-y-2">
          {plan.week_tasks.map(task => {
            const done = plan.completed_dates.includes(task.date);
            const isToday = task.date === today;
            const d = new Date(task.date + "T12:00:00");
            const dayName = d.toLocaleDateString("en-US", { weekday: "short" });
            const dayNum = d.getDate();
            return (
              <div
                key={task.date}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                  isToday ? "bg-ink/5 border border-ink/20" : ""
                }`}
              >
                <div className={`w-10 text-center flex-shrink-0 ${isToday ? "text-ink" : "text-ink-3"}`}>
                  <div className="text-[10px] font-syne font-bold uppercase">{dayName}</div>
                  <div className={`text-lg font-syne font-black leading-none ${isToday ? "text-ink" : "text-ink-3"}`}>{dayNum}</div>
                </div>
                <div className="flex-1">
                  <TaskPill type={task.task_type} small />
                  {task.questions > 0 && (
                    <span className="ml-2 text-[10px] font-serif text-ink-3">{task.questions}q</span>
                  )}
                </div>
                {done ? (
                  <CheckCircle2 className="w-4 h-4 text-green flex-shrink-0" />
                ) : task.days_to_exam < 0 ? (
                  <span className="text-[10px] font-syne text-ink-3">missed</span>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      {/* Reschedule */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="font-syne font-bold text-sm text-ink mb-3 flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Reschedule Exam Date
        </h3>
        <div className="flex gap-3">
          <input
            type="date"
            min={new Date(Date.now() + 2 * 86400000).toISOString().split("T")[0]}
            defaultValue={plan.exam_date}
            id="reschedule-date"
            className="flex-1 border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-bg focus:outline-none focus:ring-2 focus:ring-ink"
          />
          <button
            onClick={async () => {
              const el = document.getElementById("reschedule-date") as HTMLInputElement;
              if (!el?.value) return;
              setSaving(true);
              setError("");
              setSaved(false);
              try {
                await examApi.updatePlan({ exam_date: el.value, daily_minutes: plan.daily_minutes });
                setSaved(true);
                setTimeout(() => setSaved(false), 2000);
                onPlanChange();
              } catch {
                setError("Could not update exam date. Please try again.");
              } finally { setSaving(false); }
            }}
            disabled={saving}
            className={`font-syne font-bold text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-50 ${
              saved ? "bg-green text-white" : "bg-ink text-white hover:bg-red"
            }`}
          >
            {saving ? "…" : saved ? "Saved ✓" : "Update"}
          </button>
        </div>
        {error && (
          <p className="text-xs font-serif text-red mt-2">{error}</p>
        )}
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
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"practice" | "study" | "history" | "analytics" | "readiness" | "plan">("practice");

  const load = useCallback(async () => {
    try {
      const [modeList, catList, hist, analy, rdns, planRes] = await Promise.all([
        examApi.getModes(),
        examApi.getNCLEXCategories(),
        examApi.getHistory(10),
        examApi.getNCLEXAnalytics(),
        examApi.getReadiness(),
        examApi.getPlan(),
      ]);
      setModes(modeList);
      setNclexModes(modeList.filter((m: ExamMode) => NCLEX_MODE_IDS.includes(m.id)));
      setCategories(catList);
      setHistory(hist);
      setAnalytics(analy);
      setReadiness(rdns);
      setPlan(planRes.plan ?? null);
    } catch {
      // silently fail — locked state handled per-card
    } finally {
      setLoading(false);
    }
  }, []);

  async function reloadPlan() {
    try {
      const res = await examApi.getPlan();
      setPlan(res.plan ?? null);
    } catch { /* ignore */ }
  }

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

  const TABS: { id: "practice" | "study" | "history" | "analytics" | "readiness" | "plan"; label: string }[] = [
    { id: "practice",  label: t("nclex_hub.tab_practice") },
    { id: "study",     label: "Study Materials" },
    { id: "plan",      label: "Plan" },
    { id: "readiness", label: t("nclex_hub.tab_readiness") },
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
      {(best_score !== null || (analytics?.sessions_analyzed ?? 0) > 0 || readiness?.threshold_met || plan) && (
        <div className="bg-ink text-white">
          <div className="max-w-5xl mx-auto px-6 py-3 flex flex-wrap gap-6">
            {plan?.today_task && plan.today_task.task_type !== "exam_day" && (
              <button
                onClick={() => setActiveTab("plan")}
                className="flex items-center gap-2 hover:opacity-80 transition-opacity"
              >
                <Calendar className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-syne">
                  Today:{" "}
                  <strong className="text-amber-400">
                    {TASK_CONFIG[plan.today_task.task_type]?.label ?? plan.today_task.task_type}
                    {plan.today_task.questions > 0 && ` (${plan.today_task.questions}q)`}
                  </strong>
                  {plan.completed_dates.includes(new Date().toISOString().split("T")[0]) && (
                    <span className="text-green ml-1">✓</span>
                  )}
                </span>
              </button>
            )}
            {readiness?.threshold_met && readiness.score !== null && (
              <button
                onClick={() => setActiveTab("readiness")}
                className="flex items-center gap-2 hover:opacity-80 transition-opacity"
              >
                <Target className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-syne">
                  {t("nclex_hub.readiness_label")}{" "}
                  <strong className={
                    readiness.score >= 75 ? "text-green" :
                    readiness.score >= 62 ? "text-amber-400" : "text-red"
                  }>{readiness.score}%</strong>
                  {" "}
                  <span className="text-white/50">({readiness.level_label})</span>
                </span>
              </button>
            )}
            {best_score !== null && (
              <div className="flex items-center gap-2">
                <Trophy className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-syne">{t("nclex_hub.best_score")} <strong>{best_score}%</strong></span>
              </div>
            )}
            {last_score !== null && (
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-green" />
                <span className="text-xs font-syne">{t("nclex_hub.last_score")} <strong>{last_score}%</strong></span>
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

        {/* ── Study Materials tab ── */}
        {activeTab === "study" && (
          <div className="space-y-6">
            <div>
              <h2 className="font-syne font-black text-xl text-ink mb-1">Study Materials</h2>
              <p className="font-serif text-sm text-ink-3 leading-relaxed">
                Master each topic before practicing NCLEX-style questions. All modules include
                theory lessons and practice MCQs aligned to NCLEX Client Needs categories.
              </p>
            </div>

            <div>
              <h3 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Nursing Modules</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {NCLEX_STUDY_MODULES.map(mod => (
                  <Link
                    key={mod.id}
                    href={`/modules/${mod.id}`}
                    className="group bg-surface border border-border hover:border-ink rounded-xl p-4 flex items-start gap-3 transition-colors"
                  >
                    <div className="w-9 h-9 rounded-lg bg-ink/5 group-hover:bg-ink group-hover:text-white flex items-center justify-center flex-shrink-0 transition-colors text-lg">
                      {mod.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="font-syne font-bold text-sm text-ink leading-snug group-hover:text-blue-600 transition-colors">
                        {mod.title}
                      </div>
                      <div className="text-xs font-serif text-ink-3 mt-0.5">{mod.category}</div>
                      <div className="flex items-center gap-2 mt-1.5">
                        {mod.lessons > 0 && (
                          <span className="text-[10px] font-syne font-semibold bg-ink/5 text-ink-2 px-2 py-0.5 rounded-full">
                            {mod.lessons} lessons
                          </span>
                        )}
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

            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex gap-3">
              <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <p className="font-serif text-xs text-blue-600 leading-relaxed">
                <span className="font-syne font-bold text-blue-700">Recommended flow: </span>
                Study a module → Practice questions →{" "}
                <button onClick={() => setActiveTab("readiness")} className="underline font-semibold">
                  Check Readiness
                </button>{" "}
                to identify weak spots.
              </p>
            </div>
          </div>
        )}

        {/* ── Plan tab ── */}
        {activeTab === "plan" && (
          <PlanTab plan={plan} onPlanChange={reloadPlan} />
        )}

        {/* ── Readiness tab ── */}
        {activeTab === "readiness" && (
          <ReadinessTab
            readiness={readiness}
            onTrainCategory={(key) => { setSelectedCategory(key); setActiveTab("practice"); }}
          />
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
