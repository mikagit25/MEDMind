"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { examApi } from "@/lib/api";

type ExamMode = {
  id: string;
  name: string;
  description: string;
  questions: number;
  duration_min: number;
  difficulty: string | null;
  icon: string;
  locked: boolean;
  lock_reason: string | null;
};

type Question = {
  index: number;
  id: string;
  question: string;
  options: Record<string, string>;
};

type Session = {
  session_id: string;
  mode: string;
  total_questions: number;
  duration_min: number;
  ends_at: string;
  questions: Question[];
};

type Results = {
  session_id: string;
  mode: string;
  total_questions: number;
  correct: number;
  wrong: number;
  score_pct: number;
  passed: boolean;
  time_taken_min: number;
  per_question: { index: number; correct: boolean; selected: string | null; correct_answer: string | null }[];
  wrong_questions: { index: number; question: string; your_answer: string | null; correct_answer: string }[];
  message: string;
};

// ── Timer ──────────────────────────────────────────────────────────────────────
function Timer({ endsAt, onExpire }: { endsAt: string; onExpire: () => void }) {
  const [secs, setSecs] = useState(0);
  const expired = useRef(false);

  useEffect(() => {
    const tick = () => {
      const left = Math.max(0, Math.floor((new Date(endsAt).getTime() - Date.now()) / 1000));
      setSecs(left);
      if (left === 0 && !expired.current) {
        expired.current = true;
        onExpire();
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [endsAt, onExpire]);

  const m = Math.floor(secs / 60);
  const s = secs % 60;
  const urgent = secs < 60;
  return (
    <div className={`font-syne font-black text-2xl tabular-nums ${urgent ? "text-red animate-pulse" : "text-ink"}`}>
      {String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}
    </div>
  );
}

// ── Mode selector ──────────────────────────────────────────────────────────────
function ModeSelector({ onStart }: { onStart: (modeId: string) => void }) {
  const [modes, setModes] = useState<ExamMode[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([examApi.getModes(), examApi.getHistory()])
      .then(([m, h]) => { setModes(m); setHistory(h); })
      .finally(() => setLoading(false));
  }, []);

  const handleStart = async (modeId: string) => {
    setStarting(modeId);
    try { await onStart(modeId); } finally { setStarting(null); }
  };

  if (loading) return <div className="text-center py-20 text-ink-3 font-serif">Loading exam modes…</div>;

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {modes.map((mode) => (
          <div key={mode.id} className={`card p-5 flex flex-col gap-3 ${mode.locked ? "opacity-60" : ""}`}>
            <div className="flex items-center gap-3">
              <span className="text-3xl">{mode.icon}</span>
              <div>
                <div className="font-syne font-bold text-sm text-ink">{mode.name}</div>
                {mode.difficulty && (
                  <span className={`text-[10px] font-syne font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full ${
                    mode.difficulty === "hard" ? "bg-red/10 text-red" : "bg-amber/10 text-amber-700"
                  }`}>{mode.difficulty}</span>
                )}
              </div>
            </div>
            <div className="font-serif text-xs text-ink-3 flex-1">{mode.description}</div>
            <div className="flex items-center gap-3 text-xs font-syne text-ink-3">
              <span>📝 {mode.questions} questions</span>
              <span>⏱ {mode.duration_min} min</span>
            </div>
            {mode.locked ? (
              <div className="text-xs font-serif text-ink-3 italic">{mode.lock_reason}</div>
            ) : (
              <button
                onClick={() => handleStart(mode.id)}
                disabled={starting === mode.id}
                className="w-full py-2 font-syne font-semibold text-sm rounded-lg bg-ink text-white hover:bg-ink-2 transition-colors disabled:opacity-50"
              >
                {starting === mode.id ? "Starting…" : "Start Exam"}
              </button>
            )}
          </div>
        ))}
      </div>

      {history.length > 0 && (
        <div>
          <h2 className="font-syne font-bold text-base text-ink mb-3">Recent Sessions</h2>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-2">
                  <th className="text-left px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Mode</th>
                  <th className="text-left px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Date</th>
                  <th className="text-right px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Score</th>
                  <th className="text-right px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Time</th>
                  <th className="text-right px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Result</th>
                </tr>
              </thead>
              <tbody>
                {history.map((s) => (
                  <tr key={s.session_id} className="border-t border-border hover:bg-surface-2 transition-colors">
                    <td className="px-4 py-3 font-syne font-semibold text-xs text-ink">{s.mode}</td>
                    <td className="px-4 py-3 font-serif text-xs text-ink-3">
                      {new Date(s.started_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    </td>
                    <td className="px-4 py-3 text-right font-syne font-bold text-ink">{s.score_pct}%</td>
                    <td className="px-4 py-3 text-right font-serif text-xs text-ink-3">{s.time_taken_min}m</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-[11px] font-syne font-bold uppercase ${s.passed ? "text-green" : "text-red"}`}>
                        {s.passed ? "Pass" : "Fail"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}

// ── Exam session UI ────────────────────────────────────────────────────────────
function ExamSession({ session, onFinish }: { session: Session; onFinish: (results: Results) => void }) {
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const question = session.questions[current];
  const options = Object.entries(question?.options ?? {});
  const selected = answers[current];

  const handleSelect = async (option: string) => {
    if (selected) return; // don't allow changing answer
    setAnswers(prev => ({ ...prev, [current]: option }));
    try {
      await examApi.submitAnswer(session.session_id, current, option);
    } catch {}
  };

  const handleFinalize = async () => {
    setSubmitting(true);
    try {
      const results = await examApi.finalizeSession(session.session_id);
      onFinish(results);
    } catch {
      setSubmitting(false);
    }
  };

  const handleExpire = useCallback(() => { handleFinalize(); }, []);

  const answered = Object.keys(answers).length;
  const total = session.questions.length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 p-4 card">
        <div>
          <div className="font-syne font-bold text-sm text-ink">{session.mode}</div>
          <div className="text-xs font-serif text-ink-3">{answered}/{total} answered</div>
        </div>
        <Timer endsAt={session.ends_at} onExpire={handleExpire} />
        <button
          onClick={handleFinalize}
          disabled={submitting}
          className="font-syne font-semibold text-sm px-4 py-2 rounded-lg bg-ink text-white hover:bg-ink-2 transition-colors disabled:opacity-50"
        >
          {submitting ? "Submitting…" : "Submit Exam"}
        </button>
      </div>

      {/* Progress dots */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {session.questions.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={`w-7 h-7 rounded text-[11px] font-syne font-bold transition-colors ${
              i === current ? "bg-ink text-white" :
              answers[i] ? "bg-green text-white" :
              "bg-surface-2 text-ink-3 border border-border"
            }`}
          >
            {i + 1}
          </button>
        ))}
      </div>

      {/* Question */}
      <div className="card p-6 flex-1">
        <div className="text-xs font-syne text-ink-3 mb-2">Question {current + 1} of {total}</div>
        <p className="font-serif text-ink text-base leading-relaxed mb-6">{question?.question}</p>
        <div className="space-y-3">
          {options.map(([key, text]) => {
            const isSelected = selected === key;
            return (
              <button
                key={key}
                onClick={() => handleSelect(key)}
                disabled={!!selected}
                className={`w-full text-left flex items-start gap-3 p-4 rounded-lg border-2 transition-colors ${
                  isSelected
                    ? "border-ink bg-ink/5"
                    : "border-border hover:border-ink-3 bg-surface"
                } disabled:cursor-default`}
              >
                <span className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 text-xs font-syne font-bold mt-0.5 ${
                  isSelected ? "border-ink bg-ink text-white" : "border-ink-3 text-ink-3"
                }`}>{key}</span>
                <span className="font-serif text-sm text-ink leading-relaxed">{text}</span>
              </button>
            );
          })}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-6">
          <button
            onClick={() => setCurrent(Math.max(0, current - 1))}
            disabled={current === 0}
            className="font-syne font-semibold text-sm px-4 py-2 rounded-lg border border-border hover:bg-surface-2 transition-colors disabled:opacity-30"
          >
            ← Previous
          </button>
          <button
            onClick={() => setCurrent(Math.min(total - 1, current + 1))}
            disabled={current === total - 1}
            className="font-syne font-semibold text-sm px-4 py-2 rounded-lg border border-border hover:bg-surface-2 transition-colors disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Results view ───────────────────────────────────────────────────────────────
function ResultsView({ results, onRetry }: { results: Results; onRetry: () => void }) {
  return (
    <div>
      {/* Score card */}
      <div className={`card p-8 mb-6 text-center ${results.passed ? "border-green/30 bg-green-light/20" : "border-red/20 bg-red/5"}`}>
        <div className="text-6xl mb-3">{results.passed ? "🎉" : "💪"}</div>
        <div className={`font-syne font-black text-5xl mb-1 ${results.passed ? "text-green" : "text-red"}`}>
          {results.score_pct}%
        </div>
        <div className="font-syne font-bold text-lg text-ink mb-2">{results.passed ? "Passed!" : "Not passed"}</div>
        <div className="font-serif text-sm text-ink-3 mb-4">{results.message}</div>
        <div className="flex items-center justify-center gap-6 text-sm font-syne">
          <span><strong className="text-green">{results.correct}</strong> correct</span>
          <span><strong className="text-red">{results.wrong}</strong> wrong</span>
          <span><strong className="text-ink">{results.time_taken_min}m</strong> taken</span>
        </div>
      </div>

      {/* Wrong questions review */}
      {results.wrong_questions.length > 0 && (
        <div className="mb-6">
          <h2 className="font-syne font-bold text-base text-ink mb-3">Review — Questions to Study</h2>
          <div className="space-y-3">
            {results.wrong_questions.map((q) => (
              <div key={q.index} className="card p-4 border-l-4 border-red/40">
                <p className="font-serif text-sm text-ink mb-2">{q.question}</p>
                <div className="flex flex-wrap gap-3 text-xs font-syne">
                  {q.your_answer && (
                    <span className="text-red">Your answer: <strong>{q.your_answer}</strong></span>
                  )}
                  {!q.your_answer && <span className="text-ink-3 italic">Not answered</span>}
                  <span className="text-green">Correct: <strong>{q.correct_answer}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={onRetry}
          className="font-syne font-semibold text-sm px-6 py-2.5 rounded-lg bg-ink text-white hover:bg-ink-2 transition-colors"
        >
          Take Another Exam
        </button>
        <Link href="/dashboard" className="font-syne font-semibold text-sm px-6 py-2.5 rounded-lg border border-border hover:bg-surface-2 transition-colors">
          Dashboard
        </Link>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function ExamPage() {
  const [view, setView] = useState<"modes" | "session" | "results">("modes");
  const [session, setSession] = useState<Session | null>(null);
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState("");

  const handleStart = async (modeId: string) => {
    setError("");
    try {
      const sess = await examApi.createSession(modeId);
      setSession(sess);
      setView("session");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to start exam. Make sure you have a Pro subscription.");
    }
  };

  const handleFinish = (res: Results) => {
    setResults(res);
    setView("results");
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto">
      <div className="mb-6 flex items-center gap-3">
        {view !== "modes" ? (
          <button onClick={() => setView("modes")} className="text-ink-3 hover:text-ink font-syne text-sm transition-colors">
            ← Back
          </button>
        ) : (
          <Link href="/dashboard" className="text-ink-3 hover:text-ink font-syne text-sm transition-colors">
            ← Dashboard
          </Link>
        )}
        <span className="text-border">|</span>
        <h1 className="font-syne font-black text-2xl text-ink">Board Exam Prep</h1>
        {view === "session" && session && (
          <span className="text-sm font-serif text-ink-3 ml-auto">{session.mode}</span>
        )}
      </div>

      {error && (
        <div className="mb-4 p-4 rounded-lg bg-red/5 border border-red/20 text-sm font-serif text-red">{error}</div>
      )}

      {view === "modes" && <ModeSelector onStart={handleStart} />}
      {view === "session" && session && (
        <ExamSession session={session} onFinish={handleFinish} />
      )}
      {view === "results" && results && (
        <ResultsView results={results} onRetry={() => { setSession(null); setResults(null); setView("modes"); }} />
      )}
    </div>
  );
}
