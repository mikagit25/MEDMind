"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { contentApi, progressApi } from "@/lib/api";

type MCQQuestion = {
  id: string;
  question: string;
  options: Record<string, string>;
  difficulty: "easy" | "medium" | "hard";
};

type AnswerResult = {
  correct: boolean;
  correct_answer: string;
  explanation: string;
  xp_earned: number;
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: "text-green bg-green-light",
  medium: "text-amber bg-amber-light",
  hard: "text-red bg-red-light",
};

export default function QuizPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [questions, setQuestions] = useState<MCQQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0, xp: 0 });
  const [finished, setFinished] = useState(false);
  const [modTitle, setModTitle] = useState("");

  useEffect(() => {
    if (!id) return;
    Promise.all([
      contentApi.getMCQ(id),
      contentApi.getModule(id),
    ]).then(([mcqRes, modRes]) => {
      const qs: MCQQuestion[] = mcqRes ?? [];
      // Shuffle so every attempt is different
      setQuestions(qs.sort(() => Math.random() - 0.5));
      setModTitle(modRes?.title ?? "Module");
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  const handleSelect = (letter: string) => {
    if (result) return; // already answered
    setSelected(letter);
  };

  const handleSubmit = async () => {
    if (!selected || !questions[current] || submitting) return;
    setSubmitting(true);
    try {
      const res = await progressApi.answerMCQ(questions[current].id, selected);
      const ans: AnswerResult = res;
      setResult(ans);
      setScore((s) => ({
        correct: s.correct + (ans.correct ? 1 : 0),
        total: s.total + 1,
        xp: s.xp + (ans.xp_earned ?? 0),
      }));
      if ((res as any)?.newly_unlocked?.length > 0) {
        (window as any).__checkAchievements?.();
      }
    } catch {
      /* ignore */
    } finally {
      setSubmitting(false);
    }
  };

  const handleNext = () => {
    if (current + 1 >= questions.length) {
      setFinished(true);
    } else {
      setCurrent((c) => c + 1);
      setSelected(null);
      setResult(null);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="font-serif text-ink-3 text-sm animate-pulse">Loading quiz…</p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
        <div className="text-4xl">📋</div>
        <h2 className="font-syne font-bold text-xl text-ink">No quiz questions yet</h2>
        <p className="font-serif text-ink-2 text-sm text-center max-w-sm">
          This module doesn't have MCQ questions available yet.
          Try studying the lessons or reviewing flashcards.
        </p>
        <button
          onClick={() => router.back()}
          className="btn-primary mt-2"
        >
          ← Back to module
        </button>
      </div>
    );
  }

  // ── Final score screen ──────────────────────────────────────
  if (finished) {
    const pct = Math.round((score.correct / score.total) * 100);
    const grade =
      pct >= 80 ? { label: "Excellent!", color: "text-green", emoji: "🎉" }
      : pct >= 60 ? { label: "Good job!", color: "text-amber", emoji: "👍" }
      : { label: "Keep practising", color: "text-red", emoji: "📚" };

    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="card p-8 max-w-md w-full text-center">
          <div className="text-5xl mb-4">{grade.emoji}</div>
          <h1 className={`font-syne font-black text-3xl mb-1 ${grade.color}`}>{grade.label}</h1>
          <p className="font-serif text-ink-2 text-sm mb-6">{modTitle}</p>

          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="card bg-surface-2 p-4 rounded-lg">
              <div className="font-syne font-black text-2xl text-ink">{score.correct}/{score.total}</div>
              <div className="font-syne text-xs text-ink-3 mt-1">Correct</div>
            </div>
            <div className="card bg-surface-2 p-4 rounded-lg">
              <div className="font-syne font-black text-2xl text-ink">{pct}%</div>
              <div className="font-syne text-xs text-ink-3 mt-1">Score</div>
            </div>
            <div className="card bg-surface-2 p-4 rounded-lg">
              <div className="font-syne font-black text-2xl text-amber">+{score.xp}</div>
              <div className="font-syne text-xs text-ink-3 mt-1">XP earned</div>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <button
              onClick={() => {
                setCurrent(0);
                setSelected(null);
                setResult(null);
                setScore({ correct: 0, total: 0, xp: 0 });
                setFinished(false);
                setQuestions((q) => [...q].sort(() => Math.random() - 0.5));
              }}
              className="btn-primary"
            >
              Retry quiz
            </button>
            <Link
              href={`/modules/${id}`}
              className="font-syne font-semibold text-sm text-ink-2 hover:text-ink text-center transition-colors"
            >
              ← Back to module
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Question screen ─────────────────────────────────────────
  const q = questions[current];
  const optionLetters = Object.keys(q.options).sort();

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => router.back()} className="text-ink-3 hover:text-ink text-xs font-syne">
            ← {modTitle}
          </button>
          <div className="flex items-center gap-3">
            <span className={`badge ${DIFFICULTY_COLOR[q.difficulty] ?? "text-ink-2 bg-surface-2"}`}>
              {q.difficulty}
            </span>
            <span className="font-syne text-xs text-ink-3">
              {current + 1} / {questions.length}
            </span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1.5 bg-surface-2 rounded-full mb-8">
          <div
            className="h-1.5 bg-ink rounded-full transition-all"
            style={{ width: `${((current) / questions.length) * 100}%` }}
          />
        </div>

        {/* Question */}
        <div className="card p-6 mb-5">
          <p className="font-syne font-semibold text-base text-ink leading-relaxed">
            {q.question}
          </p>
        </div>

        {/* Options */}
        <div className="space-y-3 mb-6">
          {optionLetters.map((letter) => {
            let cls =
              "w-full text-left px-4 py-3 rounded-lg border transition-all font-serif text-sm text-ink ";

            if (!result) {
              cls +=
                selected === letter
                  ? "border-ink bg-ink text-white"
                  : "border-border hover:border-ink/50 bg-surface";
            } else {
              if (letter === result.correct_answer) {
                cls += "border-green bg-green-light text-green font-semibold";
              } else if (letter === selected && !result.correct) {
                cls += "border-red bg-red-light text-red";
              } else {
                cls += "border-border bg-surface text-ink-3 opacity-60";
              }
            }

            return (
              <button
                key={letter}
                onClick={() => handleSelect(letter)}
                disabled={!!result}
                className={cls}
              >
                <span className="font-syne font-bold mr-3">{letter}.</span>
                {q.options[letter]}
              </button>
            );
          })}
        </div>

        {/* Submit / Next */}
        {!result ? (
          <button
            onClick={handleSubmit}
            disabled={!selected || submitting}
            className="btn-primary w-full"
          >
            {submitting ? "Checking…" : "Submit answer"}
          </button>
        ) : (
          <div>
            {/* Explanation */}
            <div
              className={`rounded-lg border p-4 mb-4 ${
                result.correct
                  ? "border-green/30 bg-green-light"
                  : "border-red/30 bg-red-light"
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{result.correct ? "✅" : "❌"}</span>
                <span className={`font-syne font-bold text-sm ${result.correct ? "text-green" : "text-red"}`}>
                  {result.correct ? `Correct! +${result.xp_earned} XP` : `Incorrect — correct answer: ${result.correct_answer}`}
                </span>
              </div>
              <p className="font-serif text-sm text-ink leading-relaxed">{result.explanation}</p>
            </div>

            <button onClick={handleNext} className="btn-primary w-full">
              {current + 1 >= questions.length ? "See results →" : "Next question →"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
