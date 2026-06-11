"use client";

import { useState } from "react";
import Link from "next/link";

type Question = { question: string; options: Record<string, string> };
type QuizResult = {
  score: number;
  total: number;
  score_pct: number;
  percentile: number;
  total_plays: number;
  results: {
    question: string;
    options: Record<string, string>;
    user_answer: string;
    correct_answer: string;
    is_correct: boolean;
    explanation: string;
  }[];
};

type Props = {
  quiz: {
    slug: string;
    title: string;
    description: string | null;
    category: string;
    question_count: number;
    questions: Question[];
    play_count: number;
  };
  siteUrl: string;
  apiUrl: string;
};

type Phase = "intro" | "playing" | "results";

export default function QuizPlayer({ quiz, siteUrl, apiUrl }: Props) {
  const [phase, setPhase] = useState<Phase>("intro");
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [copied, setCopied] = useState(false);

  const q = quiz.questions[current];
  const totalQ = quiz.questions.length;

  function selectOption(opt: string) {
    if (confirmed) return;
    setSelected(opt);
  }

  function confirmAnswer() {
    if (!selected || confirmed) return;
    setAnswers((prev) => ({ ...prev, [current]: selected }));
    setConfirmed(true);
  }

  function nextQuestion() {
    if (current + 1 < totalQ) {
      setCurrent(current + 1);
      setSelected(null);
      setConfirmed(false);
    } else {
      submitQuiz();
    }
  }

  async function submitQuiz() {
    setPhase("results");
    setSubmitting(true);
    const finalAnswers = { ...answers };
    if (selected) finalAnswers[current] = selected;

    try {
      const res = await fetch(`${apiUrl}/public/quiz/${quiz.slug}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers: Object.fromEntries(
            Object.entries(finalAnswers).map(([k, v]) => [k, v])
          ),
        }),
      });
      if (res.ok) {
        setResult(await res.json());
      }
    } catch {}
    setSubmitting(false);
  }

  function copyShareUrl() {
    const url = `${siteUrl}/quiz/public/${quiz.slug}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function shareResult() {
    if (!result) return;
    const url = `${siteUrl}/quiz/public/${quiz.slug}`;
    const text = `I scored ${result.score}/${result.total} (better than ${result.percentile}% of players) on "${quiz.title}" — try it! ${url}`;
    if (navigator.share) {
      navigator.share({ title: quiz.title, text, url });
    } else {
      navigator.clipboard.writeText(text).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }

  function restart() {
    setCurrent(0);
    setAnswers({});
    setSelected(null);
    setConfirmed(false);
    setResult(null);
    setPhase("intro");
  }

  // ── INTRO ──────────────────────────────────────────────────────────────────
  if (phase === "intro") {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center px-4">
        <div className="max-w-lg w-full text-center">
          <Link href="/quiz/public" className="inline-block mb-6 font-serif text-xs text-ink-3 hover:text-ink">
            ← All Quizzes
          </Link>
          <div className="text-6xl mb-5">
            {quiz.category === "first-aid" ? "🚑" :
             quiz.category === "pharmacology" ? "💊" :
             quiz.category === "symptoms" ? "🩺" :
             quiz.category === "veterinary" ? "🐾" :
             quiz.category === "anatomy" ? "🫀" : "📋"}
          </div>
          <h1 className="font-syne font-black text-2xl sm:text-3xl text-ink mb-3">
            {quiz.title}
          </h1>
          {quiz.description && (
            <p className="font-serif text-sm text-ink-3 mb-6 leading-relaxed">
              {quiz.description}
            </p>
          )}
          <div className="flex items-center justify-center gap-4 mb-8 font-serif text-xs text-ink-3">
            <span>{totalQ} questions</span>
            <span>·</span>
            <span>No signup required</span>
            {quiz.play_count > 0 && (
              <>
                <span>·</span>
                <span>{quiz.play_count.toLocaleString()} plays</span>
              </>
            )}
          </div>
          <button
            onClick={() => setPhase("playing")}
            className="w-full px-8 py-4 rounded-xl bg-ink text-white font-syne font-black text-base hover:bg-ink-2 transition-colors"
          >
            Start Quiz →
          </button>
          <p className="mt-4 font-serif text-xs text-ink-3">
            ⚕️ Educational purposes only — not medical advice.
          </p>
        </div>
      </div>
    );
  }

  // ── PLAYING ────────────────────────────────────────────────────────────────
  if (phase === "playing") {
    const progress = ((current + (confirmed ? 1 : 0)) / totalQ) * 100;

    return (
      <div className="min-h-screen bg-bg px-4 py-8">
        <div className="max-w-2xl mx-auto">
          {/* Progress */}
          <div className="flex items-center gap-3 mb-6">
            <div className="flex-1 h-2 bg-bg-2 rounded-full overflow-hidden">
              <div
                className="h-2 bg-ink rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="font-syne font-bold text-xs text-ink-3 shrink-0">
              {current + 1} / {totalQ}
            </span>
          </div>

          {/* Question */}
          <div className="bg-surface border border-border rounded-2xl p-6 sm:p-8 mb-5">
            <p className="font-syne font-bold text-base sm:text-lg text-ink leading-relaxed">
              {q.question}
            </p>
          </div>

          {/* Options */}
          <div className="space-y-3 mb-6">
            {Object.entries(q.options).map(([key, text]) => {
              let cls =
                "w-full text-left px-5 py-4 rounded-xl border font-serif text-sm transition-all ";
              if (!confirmed) {
                cls +=
                  selected === key
                    ? "border-ink bg-ink text-white"
                    : "border-border bg-surface text-ink hover:border-ink-2";
              } else {
                const r = result?.results[current];
                if (key === (r?.correct_answer ?? "")) {
                  cls += "border-green-500 bg-green-50 text-green-800";
                } else if (key === selected && !r?.is_correct) {
                  cls += "border-red-400 bg-red-50 text-red-700";
                } else {
                  cls += "border-border bg-surface text-ink-3";
                }
              }
              return (
                <button key={key} className={cls} onClick={() => selectOption(key)}>
                  <span className="font-syne font-bold mr-3">{key}.</span>
                  {text}
                </button>
              );
            })}
          </div>

          {/* Explanation after confirmation */}
          {confirmed && result?.results[current] && (
            <div
              className={`rounded-xl p-4 mb-5 text-sm font-serif leading-relaxed ${
                result.results[current].is_correct
                  ? "bg-green-50 border border-green-200 text-green-800"
                  : "bg-red-50 border border-red-200 text-red-700"
              }`}
            >
              <span className="font-syne font-bold mr-2">
                {result.results[current].is_correct ? "✓ Correct!" : "✗ Incorrect."}
              </span>
              {result.results[current].explanation}
            </div>
          )}

          {/* Buttons */}
          {!confirmed ? (
            <button
              disabled={!selected}
              onClick={confirmAnswer}
              className="w-full py-3.5 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Confirm Answer
            </button>
          ) : (
            <button
              onClick={nextQuestion}
              className="w-full py-3.5 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
            >
              {current + 1 < totalQ ? "Next Question →" : "See Results →"}
            </button>
          )}
        </div>
      </div>
    );
  }

  // ── RESULTS ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-bg px-4 py-8">
      <div className="max-w-2xl mx-auto">
        {submitting || !result ? (
          <div className="text-center py-20">
            <div className="font-syne font-bold text-ink text-lg animate-pulse">Calculating results…</div>
          </div>
        ) : (
          <>
            {/* Score card */}
            <div className="bg-surface border border-border rounded-2xl p-8 text-center mb-8">
              <div className="text-6xl mb-4">
                {result.score_pct >= 80 ? "🎉" : result.score_pct >= 50 ? "👍" : "📚"}
              </div>
              <h1 className="font-syne font-black text-3xl text-ink mb-1">
                {result.score} / {result.total}
              </h1>
              <p className="font-serif text-ink-3 text-sm mb-2">
                {result.score_pct}% correct
              </p>
              {result.total_plays > 5 && (
                <p className="font-syne font-semibold text-sm text-accent">
                  Better than {result.percentile}% of {result.total_plays.toLocaleString()} players
                </p>
              )}

              {/* Share buttons */}
              <div className="mt-6 flex items-center justify-center gap-3 flex-wrap">
                <button
                  onClick={shareResult}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
                >
                  {copied ? "✓ Copied!" : "Share Result"}
                </button>
                <button
                  onClick={restart}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border text-ink font-syne font-bold text-sm hover:border-ink transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>

            {/* Answer review */}
            <h2 className="font-syne font-black text-xl text-ink mb-4">Review Your Answers</h2>
            <div className="space-y-4 mb-10">
              {result.results.map((r, i) => (
                <div
                  key={i}
                  className={`rounded-xl border p-5 ${
                    r.is_correct ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"
                  }`}
                >
                  <div className="flex items-start gap-2 mb-3">
                    <span className={`shrink-0 font-syne font-black text-sm ${r.is_correct ? "text-green-600" : "text-red-500"}`}>
                      {r.is_correct ? "✓" : "✗"}
                    </span>
                    <p className="font-syne font-bold text-sm text-ink">{r.question}</p>
                  </div>
                  <div className="ml-5 space-y-1 mb-3">
                    {Object.entries(r.options).map(([key, text]) => (
                      <div key={key} className={`font-serif text-xs ${key === r.correct_answer ? "text-green-700 font-bold" : key === r.user_answer && !r.is_correct ? "text-red-600 line-through" : "text-ink-3"}`}>
                        {key}. {text}
                        {key === r.correct_answer && " ✓"}
                        {key === r.user_answer && !r.is_correct && " (your answer)"}
                      </div>
                    ))}
                  </div>
                  {r.explanation && (
                    <p className="ml-5 font-serif text-xs text-ink-2 leading-relaxed border-t border-current/10 pt-2 mt-2">
                      {r.explanation}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="text-center bg-surface border border-border rounded-2xl p-8">
              <h2 className="font-syne font-black text-xl text-ink mb-2">
                Want to go deeper?
              </h2>
              <p className="font-serif text-sm text-ink-3 mb-5">
                MedMind has 800+ clinical lessons, AI tutor, and flashcards — free to start.
              </p>
              <div className="flex items-center justify-center gap-3 flex-wrap">
                <Link
                  href="/register"
                  className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
                >
                  Create Free Account →
                </Link>
                <Link
                  href="/quiz/public"
                  className="inline-block px-6 py-3 rounded-xl border border-border text-ink font-syne font-bold text-sm hover:border-ink transition-colors"
                >
                  More Quizzes
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
