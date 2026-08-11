"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { adaptivePlanApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

const EXAM_LABELS: Record<string, string> = {
  usmle_step1: "USMLE Step 1",
  usmle_step2: "USMLE Step 2 CK",
  usmle_step3: "USMLE Step 3",
  nclex_rn:    "NCLEX-RN",
  nclex_pn:    "NCLEX-PN",
  ukmla:       "UKMLA",
  plab:        "PLAB",
  // Gulf licensing exams
  snle:        "SNLE (Saudi)",
  dha:         "DHA (Dubai)",
  haad:        "HAAD (Abu Dhabi)",
  qchp:        "QCHP (Qatar)",
  nhra:        "NHRA (Bahrain)",
  omsb:        "OMSB (Oman)",
  mohuae:      "MOH UAE",
  moh_kw:      "MOH Kuwait",
  custom:      "Board Exam",
};

type ModuleItem = { module_id: string; title: string; sessions: number };
type Week = { week: number; theme: string; modules: ModuleItem[]; daily_hours: number; milestone: string };
type Plan = {
  exam_type: string; exam_label: string; exam_date: string; days_remaining: number;
  total_weeks: number; daily_hours: number; generated_at: string; weeks: Week[]; tip: string;
};

function Countdown({ days }: { days: number }) {
  const color = days <= 30 ? "text-red" : days <= 90 ? "text-amber" : "text-green";
  return (
    <div className="text-center py-5">
      <p className={`font-syne font-black text-5xl ${color}`}>{days}</p>
      <p className="font-serif text-ink-3 text-sm mt-1">days remaining</p>
    </div>
  );
}

export default function StudyPlanPage() {
  const { user } = useAuthStore();
  const prefs = user?.preferences as Record<string, unknown> | undefined;
  const savedExamType = (prefs?.exam_type as string) ?? "";
  const savedExamDate = (prefs?.exam_date as string) ?? "";

  const [examType, setExamType] = useState(savedExamType);
  const [examDate, setExamDate] = useState(savedExamDate);
  const [dailyHours, setDailyHours] = useState(2);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  // Auto-generate if settings already have exam prefs
  useEffect(() => {
    if (savedExamType && savedExamDate && !plan) {
      handleGenerate(savedExamType, savedExamDate, dailyHours);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleGenerate(type = examType, date = examDate, hours = dailyHours) {
    if (!type || !date) return;
    setStatus("loading");
    setErrorMsg("");
    try {
      const data = await adaptivePlanApi.generateExamPlan({ exam_type: type, exam_date: date, daily_hours: hours });
      setPlan(data);
      setStatus("idle");
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.detail ?? "Failed to generate plan. Please try again.");
      setStatus("error");
    }
  }

  // ── No exam set ───────────────────────────────────────────────────────────
  if (!savedExamType && !examType) {
    return (
      <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-2xl mx-auto w-full">
        <h1 className="font-syne font-black text-2xl text-ink mb-2">Study Plan</h1>
        <p className="font-serif text-ink-3 text-sm mb-6">Generate a week-by-week study schedule tailored to your exam and timeline.</p>
        <div className="card p-6 space-y-4">
          <p className="font-syne font-semibold text-sm text-ink">Set your exam to get started</p>
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Target Exam</label>
            <select value={examType} onChange={e => setExamType(e.target.value)}
              className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink">
              <option value="">— Select exam —</option>
              {Object.entries(EXAM_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Exam Date</label>
            <input type="date" value={examDate} onChange={e => setExamDate(e.target.value)}
              min={new Date(Date.now() + 86400000).toISOString().split("T")[0]}
              className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink" />
          </div>
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Daily study hours: <strong>{dailyHours}h</strong></label>
            <input type="range" min={0.5} max={8} step={0.5} value={dailyHours} onChange={e => setDailyHours(Number(e.target.value))} className="w-full accent-ink" />
          </div>
          <button onClick={() => handleGenerate()} disabled={!examType || !examDate || status === "loading"}
            className="w-full btn-primary disabled:opacity-40">
            {status === "loading" ? "Generating…" : "Generate Study Plan"}
          </button>
          {status === "error" && <p className="text-red font-serif text-xs">{errorMsg}</p>}
          <p className="text-ink-3 text-xs font-serif">You can also set your exam in <Link href="/settings" className="underline">Settings</Link> to save it permanently.</p>
        </div>
      </div>
    );
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (status === "loading") {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center space-y-3">
          <svg className="animate-spin w-8 h-8 text-ink-3 mx-auto" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <p className="font-syne text-sm text-ink-2">Claude is building your {EXAM_LABELS[examType] ?? "exam"} study plan…</p>
          <p className="font-serif text-xs text-ink-3">This may take up to 15 seconds.</p>
        </div>
      </div>
    );
  }

  // ── Plan display ──────────────────────────────────────────────────────────
  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-3xl mx-auto w-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{plan?.exam_label ?? EXAM_LABELS[examType] ?? "Exam"} Study Plan</h1>
          {plan && <p className="font-serif text-ink-3 text-sm mt-0.5">{plan.total_weeks} weeks · {plan.daily_hours}h/day · {plan.days_remaining} days left</p>}
        </div>
        <button onClick={() => handleGenerate()}
          className="font-syne font-semibold text-xs border border-border text-ink-2 px-3 py-1.5 rounded hover:border-border-2 hover:text-ink transition-colors">
          Regenerate
        </button>
      </div>

      {/* Countdown */}
      {plan && <div className="card p-4 mb-4"><Countdown days={plan.days_remaining} /></div>}

      {/* Tip */}
      {plan?.tip && (
        <div className="bg-amber-light border border-amber/20 rounded-xl p-4 mb-5">
          <p className="font-syne font-bold text-xs text-amber mb-1">Study Tip</p>
          <p className="font-serif text-sm text-ink leading-relaxed">{plan.tip}</p>
        </div>
      )}

      {status === "error" && (
        <div className="bg-red-light border border-red/20 rounded-xl p-4 mb-5">
          <p className="text-red text-sm font-serif">{errorMsg}</p>
        </div>
      )}

      {/* Weeks */}
      {plan && (
        <div className="space-y-4">
          {plan.weeks.map(week => (
            <div key={week.week} className="card p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <span className="font-syne font-black text-xs text-ink-3 uppercase tracking-wider">Week {week.week}</span>
                  <h3 className="font-syne font-bold text-base text-ink">{week.theme}</h3>
                </div>
                <span className="font-syne text-xs text-ink-3 bg-surface-2 px-2 py-0.5 rounded">{week.daily_hours}h/day</span>
              </div>

              {week.modules.length > 0 && (
                <div className="space-y-2 mb-3">
                  {week.modules.map((m, mi) => (
                    <div key={mi} className="flex items-center justify-between bg-surface rounded-lg border border-border px-3 py-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-1.5 h-1.5 rounded-full bg-ink flex-shrink-0" />
                        {m.module_id ? (
                          <Link href={`/modules/${m.module_id}`}
                            className="font-syne font-semibold text-xs text-ink hover:text-red transition-colors truncate">
                            {m.title}
                          </Link>
                        ) : (
                          <span className="font-syne font-semibold text-xs text-ink truncate">{m.title}</span>
                        )}
                      </div>
                      <span className="font-serif text-[10px] text-ink-3 flex-shrink-0 ml-2">{m.sessions} session{m.sessions !== 1 ? "s" : ""}</span>
                    </div>
                  ))}
                </div>
              )}

              {week.milestone && (
                <div className="bg-green-light border border-green/20 rounded px-3 py-2">
                  <p className="text-xs text-green font-syne font-semibold leading-snug">
                    Milestone: {week.milestone}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* No plan yet (initial state with prefs set) */}
      {!plan && status === "idle" && (
        <div className="card p-6 space-y-4">
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Daily study hours: <strong>{dailyHours}h</strong></label>
            <input type="range" min={0.5} max={8} step={0.5} value={dailyHours} onChange={e => setDailyHours(Number(e.target.value))} className="w-full accent-ink" />
          </div>
          <button onClick={() => handleGenerate()} className="w-full btn-primary">
            Generate {EXAM_LABELS[examType] ?? "Exam"} Study Plan
          </button>
          <p className="font-serif text-xs text-ink-3">
            Exam: <strong>{EXAM_LABELS[examType] ?? examType}</strong> · Date: <strong>{examDate}</strong> ·{" "}
            <Link href="/settings" className="underline">Change</Link>
          </p>
        </div>
      )}
    </div>
  );
}
