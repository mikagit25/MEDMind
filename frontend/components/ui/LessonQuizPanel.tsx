"use client";

import { useState } from "react";
import Link from "next/link";
import { aiApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type MCQOption = Record<string, string>; // {"A":"...", "B":"...", ...}

type Question = {
  question: string;
  options: MCQOption;
  correct: string;
  explanation: string;
};

type QuizState = "idle" | "loading" | "ready" | "error" | "limit";

const OPTION_LABELS = ["A", "B", "C", "D"] as const;

const CORRECT_COLORS = "bg-green-light border-green/40 text-green";
const WRONG_COLORS   = "bg-red-light border-red/30 text-red";
const DEFAULT_COLORS = "bg-surface border-border text-ink hover:border-border-2";

export default function LessonQuizPanel({
  lessonId,
  lessonTitle,
}: {
  lessonId: string;
  lessonTitle: string;
}) {
  const { isAuthenticated } = useAuthStore();
  const [state, setState] = useState<QuizState>("idle");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [score, setScore] = useState(0);
  const [done, setDone] = useState(false);
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard">("medium");

  if (!isAuthenticated) {
    return (
      <div className="mt-6 bg-surface border border-border rounded-xl p-5 flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <div className="flex-1 min-w-0">
          <p className="font-syne font-bold text-sm text-ink mb-1">Practice Questions</p>
          <p className="text-ink-3 text-xs leading-relaxed">
            Sign in to generate 5 AI-crafted USMLE-style questions from this lesson.
          </p>
        </div>
        <Link
          href="/login"
          className="flex-shrink-0 font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap"
        >
          Sign in
        </Link>
      </div>
    );
  }

  async function generate() {
    setState("loading");
    setDone(false);
    setIdx(0);
    setSelected(null);
    setChecked(false);
    setScore(0);
    try {
      const data = await aiApi.generateLessonQuiz(lessonId, difficulty);
      setQuestions(data.questions || []);
      setState("ready");
    } catch (e: any) {
      setState(e?.response?.status === 429 ? "limit" : "error");
    }
  }

  function checkAnswer() {
    if (!selected) return;
    setChecked(true);
    if (selected === questions[idx].correct) setScore(s => s + 1);
  }

  function next() {
    if (idx + 1 >= questions.length) {
      setDone(true);
    } else {
      setIdx(i => i + 1);
      setSelected(null);
      setChecked(false);
    }
  }

  function restart() {
    setDone(false);
    setIdx(0);
    setSelected(null);
    setChecked(false);
    setScore(0);
    setState("idle");
  }

  // ── Idle ─────────────────────────────────────────────────────────────────
  if (state === "idle") {
    return (
      <div className="mt-6 bg-surface border border-border rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-ink flex items-center justify-center flex-shrink-0">
            <svg className="w-3.5 h-3.5 text-white" viewBox="0 0 16 16" fill="none">
              <path d="M8 1l2 5h5l-4 3 1.5 5L8 11l-4.5 3L5 9 1 6h5z" fill="currentColor"/>
            </svg>
          </div>
          <p className="font-syne font-bold text-sm text-ink">Practice Questions</p>
        </div>
        <p className="text-ink-3 text-xs leading-relaxed">
          Generate 5 USMLE-style questions based on this lesson&apos;s content.
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-syne text-ink-3">Difficulty:</span>
          {(["easy", "medium", "hard"] as const).map(d => (
            <button
              key={d}
              onClick={() => setDifficulty(d)}
              className={`text-xs font-syne font-semibold px-3 py-1 rounded border transition-colors capitalize ${
                difficulty === d
                  ? "bg-ink text-white border-ink"
                  : "border-border text-ink-2 hover:border-border-2"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
        <button
          onClick={generate}
          className="w-full font-syne font-bold text-sm bg-ink text-white py-2.5 rounded hover:bg-red transition-colors"
        >
          Generate Practice Questions
        </button>
      </div>
    );
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (state === "loading") {
    return (
      <div className="mt-6 bg-surface border border-border rounded-xl p-5 flex items-center gap-3">
        <svg className="animate-spin w-5 h-5 text-ink-3 flex-shrink-0" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        <p className="font-syne text-sm text-ink-2">Claude is generating questions for &ldquo;{lessonTitle}&rdquo;…</p>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (state === "limit") {
    return (
      <div className="mt-6 bg-amber-50 border border-amber-200 rounded-xl p-5 space-y-2">
        <p className="font-syne font-bold text-sm text-amber-700">Daily AI limit reached</p>
        <p className="text-xs text-ink-3">You&apos;ve used all your AI questions for today. Upgrade for more.</p>
        <a href="/pricing" className="inline-block text-xs font-syne font-semibold text-ink underline">View plans →</a>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="mt-6 bg-red-light border border-red/20 rounded-xl p-5 space-y-2">
        <p className="font-syne font-bold text-sm text-red">Could not generate questions</p>
        <p className="text-xs text-ink-3">The AI service is temporarily unavailable. Please try again.</p>
        <button onClick={() => setState("idle")} className="text-xs font-syne font-semibold text-ink-2 underline">
          Try again
        </button>
      </div>
    );
  }

  const q = questions[idx];

  // ── Done ──────────────────────────────────────────────────────────────────
  if (done) {
    const pct = Math.round((score / questions.length) * 100);
    const color = pct >= 80 ? "text-green" : pct >= 60 ? "text-amber" : "text-red";
    return (
      <div className="mt-6 bg-surface border border-border rounded-xl p-5 space-y-4">
        <p className="font-syne font-bold text-sm text-ink">Quiz Complete</p>
        <div className="text-center py-4">
          <p className={`font-syne font-black text-4xl ${color}`}>{score}/{questions.length}</p>
          <p className="font-serif text-xs text-ink-3 mt-1">{pct}% correct</p>
          {pct >= 80 && <p className="text-xs text-green font-syne font-semibold mt-2">Excellent work!</p>}
          {pct >= 60 && pct < 80 && <p className="text-xs text-amber font-syne font-semibold mt-2">Good effort — review the explanations.</p>}
          {pct < 60 && <p className="text-xs text-red font-syne font-semibold mt-2">Keep studying — read the lesson again.</p>}
        </div>
        <div className="flex gap-3">
          <button
            onClick={restart}
            className="flex-1 font-syne font-semibold text-sm border border-border text-ink-2 py-2 rounded hover:border-border-2 hover:text-ink transition-colors"
          >
            New Questions
          </button>
          <button
            onClick={() => { setDone(false); setIdx(0); setSelected(null); setChecked(false); setScore(0); }}
            className="flex-1 font-syne font-semibold text-sm bg-ink text-white py-2 rounded hover:bg-red transition-colors"
          >
            Review Again
          </button>
        </div>
      </div>
    );
  }

  // ── Question ──────────────────────────────────────────────────────────────
  return (
    <div className="mt-6 bg-surface border border-border rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="font-syne font-bold text-sm text-ink">Practice Questions</p>
        <span className="font-syne text-xs text-ink-3">
          {idx + 1} / {questions.length}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 bg-surface-2 rounded-full overflow-hidden">
        <div
          className="h-full bg-ink rounded-full transition-all"
          style={{ width: `${((idx) / questions.length) * 100}%` }}
        />
      </div>

      {/* Question */}
      <p className="font-syne font-semibold text-sm text-ink leading-snug">{q.question}</p>

      {/* Options */}
      <div className="space-y-2">
        {OPTION_LABELS.filter(l => q.options[l]).map(label => {
          const isCorrect = label === q.correct;
          const isSelected = label === selected;
          let cls = DEFAULT_COLORS;
          if (checked) {
            if (isCorrect) cls = CORRECT_COLORS;
            else if (isSelected) cls = WRONG_COLORS;
            else cls = "bg-surface border-border text-ink-3 opacity-60";
          } else if (isSelected) {
            cls = "bg-surface-2 border-ink text-ink";
          }
          return (
            <button
              key={label}
              disabled={checked}
              onClick={() => setSelected(label)}
              className={`w-full text-left flex items-start gap-3 p-3 rounded-lg border transition-all text-sm ${cls}`}
            >
              <span className="font-syne font-bold flex-shrink-0 w-5">{label}.</span>
              <span className="font-serif leading-snug">{q.options[label]}</span>
            </button>
          );
        })}
      </div>

      {/* Explanation (after check) */}
      {checked && (
        <div className={`rounded-lg p-3 border text-xs leading-relaxed ${selected === q.correct ? "bg-green-light border-green/20 text-green" : "bg-red-light border-red/20 text-red"}`}>
          <span className="font-syne font-bold">{selected === q.correct ? "Correct! " : `Incorrect. Correct: ${q.correct}. `}</span>
          <span className="font-serif text-ink">{q.explanation}</span>
        </div>
      )}

      {/* Action button */}
      {!checked ? (
        <button
          onClick={checkAnswer}
          disabled={!selected}
          className="w-full font-syne font-bold text-sm bg-ink text-white py-2.5 rounded hover:bg-red transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Check Answer
        </button>
      ) : (
        <button
          onClick={next}
          className="w-full font-syne font-bold text-sm bg-ink text-white py-2.5 rounded hover:bg-red transition-colors"
        >
          {idx + 1 >= questions.length ? "See Results" : "Next Question →"}
        </button>
      )}
    </div>
  );
}
