"use client";

/**
 * USMLE-style quiz at the bottom of article pages.
 * 5 questions, one at a time, with explanations and a final score.
 * No login required — results are local to this session.
 */

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

type Question = {
  question: string;
  options: Record<string, string>;
  correct: string;
  explanation: string;
  difficulty: "easy" | "medium" | "hard";
};

type QuizState = "idle" | "loading" | "ready" | "done" | "error";

const DIFFICULTY_STYLE: Record<string, string> = {
  easy:   "text-green  bg-green/10  border-green/25",
  medium: "text-amber  bg-amber/10  border-amber/25",
  hard:   "text-red    bg-red/10    border-red/25",
};

interface Props {
  slug: string;
}

export function ArticleQuiz({ slug }: Props) {
  const [state,     setState]     = useState<QuizState>("idle");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [current,   setCurrent]   = useState(0);
  const [selected,  setSelected]  = useState<string | null>(null);
  const [answered,  setAnswered]  = useState(false);
  const [score,     setScore]     = useState(0);
  const [results,   setResults]   = useState<boolean[]>([]);

  async function startQuiz() {
    setState("loading");
    try {
      const r = await fetch(`${API}/articles/${slug}/quiz`);
      if (!r.ok) throw new Error("fetch failed");
      const d = await r.json();
      const qs: Question[] = d.questions ?? [];
      if (!qs.length) { setState("error"); return; }
      setQuestions(qs);
      setCurrent(0);
      setSelected(null);
      setAnswered(false);
      setScore(0);
      setResults([]);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  function handleSelect(letter: string) {
    if (answered) return;
    setSelected(letter);
  }

  function handleSubmit() {
    if (!selected || answered) return;
    const q   = questions[current];
    const ok  = selected === q.correct;
    setAnswered(true);
    if (ok) setScore((s) => s + 1);
    setResults((r) => [...r, ok]);
  }

  function handleNext() {
    if (current + 1 >= questions.length) {
      setState("done");
    } else {
      setCurrent((c) => c + 1);
      setSelected(null);
      setAnswered(false);
    }
  }

  if (state === "idle" || state === "error") {
    return (
      <div className="mt-16 border-t border-border pt-10">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-2xl">🧠</span>
          <h2 className="font-syne font-bold text-xl text-ink">Test Your Knowledge</h2>
        </div>
        <p className="font-serif text-ink-2 text-sm mb-5">
          5 USMLE-style clinical questions based on this article.
        </p>
        {state === "error" && (
          <p className="text-red text-xs font-serif mb-3">Quiz temporarily unavailable — try again.</p>
        )}
        <button
          onClick={startQuiz}
          className="inline-flex items-center gap-2 bg-accent text-white font-syne font-semibold text-sm px-5 py-2.5 rounded-xl hover:bg-accent/90 transition-colors"
        >
          Start Quiz
          <svg viewBox="0 0 20 20" className="w-4 h-4 fill-current" aria-hidden>
            <path fillRule="evenodd" d="M10.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L12.586 11H5a1 1 0 110-2h7.586l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
    );
  }

  if (state === "loading") {
    return (
      <div className="mt-16 border-t border-border pt-10">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="font-serif text-ink-2 text-sm">Generating quiz…</span>
        </div>
      </div>
    );
  }

  if (state === "done") {
    const pct     = Math.round((score / questions.length) * 100);
    const grade   = pct >= 80 ? "Excellent" : pct >= 60 ? "Good" : "Keep Studying";
    const gradeC  = pct >= 80 ? "text-green" : pct >= 60 ? "text-amber" : "text-red";

    return (
      <div className="mt-16 border-t border-border pt-10">
        <div className="flex items-center gap-3 mb-6">
          <span className="text-2xl">🏁</span>
          <h2 className="font-syne font-bold text-xl text-ink">Quiz Complete</h2>
        </div>

        {/* Score circle */}
        <div className="flex items-center gap-8 mb-8">
          <div className="flex flex-col items-center justify-center w-24 h-24 rounded-full border-4 border-accent bg-surface">
            <span className={`font-syne font-black text-2xl ${gradeC}`}>{pct}%</span>
            <span className="font-serif text-xs text-ink-3">{score}/{questions.length}</span>
          </div>
          <div>
            <div className={`font-syne font-bold text-lg ${gradeC}`}>{grade}</div>
            <div className="font-serif text-sm text-ink-2 mt-1">
              {pct >= 80
                ? "You've mastered this topic!"
                : pct >= 60
                ? "Solid understanding — review the harder concepts."
                : "Read the article again and focus on key mechanisms."}
            </div>
          </div>
        </div>

        {/* Per-question results */}
        <div className="flex gap-2 mb-8">
          {results.map((ok, i) => (
            <div
              key={i}
              title={`Q${i + 1}: ${ok ? "Correct" : "Wrong"}`}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-syne font-bold ${
                ok ? "bg-green/15 text-green border border-green/30" : "bg-red/10 text-red border border-red/25"
              }`}
            >
              {i + 1}
            </div>
          ))}
        </div>

        <button
          onClick={startQuiz}
          className="inline-flex items-center gap-2 border border-border text-ink font-syne font-semibold text-sm px-5 py-2.5 rounded-xl hover:border-accent hover:text-accent transition-colors"
        >
          Retake Quiz
        </button>
      </div>
    );
  }

  // ── Active question ────────────────────────────────────────────────────────
  const q = questions[current];
  if (!q) return null;

  return (
    <div className="mt-16 border-t border-border pt-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🧠</span>
          <h2 className="font-syne font-bold text-xl text-ink">Quiz</h2>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-[11px] font-syne font-semibold border rounded-full px-2 py-0.5 ${DIFFICULTY_STYLE[q.difficulty]}`}>
            {q.difficulty}
          </span>
          <span className="font-syne text-sm text-ink-3">{current + 1} / {questions.length}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-surface rounded-full mb-6 overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-500"
          style={{ width: `${(current / questions.length) * 100}%` }}
        />
      </div>

      {/* Question */}
      <p className="font-syne font-semibold text-base text-ink leading-snug mb-5">{q.question}</p>

      {/* Options */}
      <div className="space-y-3 mb-6">
        {Object.entries(q.options).map(([letter, text]) => {
          const isSelected = selected === letter;
          const isCorrect  = q.correct === letter;
          let style = "border-border text-ink hover:border-accent/50 hover:bg-surface";
          if (answered) {
            if (isCorrect)        style = "border-green  bg-green/10  text-green  font-semibold";
            else if (isSelected)  style = "border-red    bg-red/10    text-red";
            else                  style = "border-border text-ink-3 opacity-60";
          } else if (isSelected) {
            style = "border-accent bg-accent/10 text-accent font-semibold";
          }

          return (
            <button
              key={letter}
              onClick={() => handleSelect(letter)}
              disabled={answered}
              className={`w-full text-left flex items-start gap-3 p-4 rounded-xl border transition-all font-serif text-sm ${style}`}
            >
              <span className="font-syne font-bold text-xs w-5 shrink-0 mt-0.5">{letter}</span>
              <span className="leading-snug">{text}</span>
            </button>
          );
        })}
      </div>

      {/* Explanation (shown after answer) */}
      {answered && (
        <div className={`rounded-xl p-4 mb-5 border text-sm font-serif ${
          selected === q.correct
            ? "bg-green/10 border-green/30 text-green-800"
            : "bg-red/10   border-red/25   text-red-800"
        }`}>
          <div className="font-syne font-semibold text-xs mb-1">
            {selected === q.correct ? "✓ Correct" : `✗ Incorrect — correct answer: ${q.correct}`}
          </div>
          {q.explanation}
        </div>
      )}

      {/* Buttons */}
      <div className="flex gap-3">
        {!answered ? (
          <button
            onClick={handleSubmit}
            disabled={!selected}
            className="bg-accent text-white font-syne font-semibold text-sm px-6 py-2.5 rounded-xl hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            Submit Answer
          </button>
        ) : (
          <button
            onClick={handleNext}
            className="bg-accent text-white font-syne font-semibold text-sm px-6 py-2.5 rounded-xl hover:bg-accent/90 transition-colors"
          >
            {current + 1 >= questions.length ? "See Results" : "Next Question →"}
          </button>
        )}
      </div>
    </div>
  );
}
