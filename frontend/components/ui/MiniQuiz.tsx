"use client";

import { useState } from "react";
import Link from "next/link";
import { useT } from "@/lib/i18n";

export type MiniQuizQuestion = {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
};

interface Props {
  questions: MiniQuizQuestion[];
  quizSlug?: string;
}

export function MiniQuiz({ questions, quizSlug }: Props) {
  const t = useT();
  const [step, setStep] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [answers, setAnswers] = useState<boolean[]>([]);
  const [done, setDone] = useState(false);

  if (!questions.length) return null;

  const current = questions[step];
  const isAnswered = selected !== null;
  const isCorrect = selected === current.correct_index;
  const total = questions.length;

  function handleSelect(idx: number) {
    if (isAnswered) return;
    setSelected(idx);
  }

  function handleNext() {
    const next = [...answers, selected === current.correct_index];
    setAnswers(next);
    if (step + 1 >= total) {
      setDone(true);
    } else {
      setStep(step + 1);
      setSelected(null);
    }
  }

  function handleRetry() {
    setStep(0);
    setSelected(null);
    setAnswers([]);
    setDone(false);
  }

  const score = answers.filter(Boolean).length;

  if (done) {
    const pct = Math.round((score / total) * 100);
    const color = pct >= 70 ? "text-emerald-600" : pct >= 40 ? "text-amber-600" : "text-red-600";
    return (
      <div className="text-center py-8 px-4">
        <div className="text-5xl font-syne font-extrabold mb-2">
          <span className={color}>{score}</span>
          <span className="text-ink-3">/{total}</span>
        </div>
        <p className="font-syne font-semibold text-ink mb-6">
          {t("landing.quiz_result_title")} — {pct}%
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href={quizSlug ? `/quiz/public/${quizSlug}` : "/register"}
            className="bg-ink text-white font-syne font-semibold text-sm px-6 py-3 rounded-xl hover:bg-ink/80 transition-colors"
          >
            {t("landing.quiz_result_cta") as string}
          </Link>
          <button
            onClick={handleRetry}
            className="border border-border font-syne font-semibold text-sm px-6 py-3 rounded-xl hover:border-ink text-ink-2 hover:text-ink transition-colors"
          >
            {t("landing.quiz_result_retry") as string}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Progress */}
      <div className="flex items-center gap-3 mb-6">
        <span className="text-xs font-syne text-ink-3">
          {t("landing.quiz_q_label") as string} {step + 1} {t("landing.quiz_of") as string} {total}
        </span>
        <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${((step + 1) / total) * 100}%` }}
          />
        </div>
        <div className="flex gap-1">
          {questions.map((_, i) => (
            <span
              key={i}
              className={`w-2 h-2 rounded-full transition-colors ${
                i < step
                  ? answers[i]
                    ? "bg-emerald-500"
                    : "bg-red-400"
                  : i === step
                  ? "bg-blue-500"
                  : "bg-border"
              }`}
            />
          ))}
        </div>
      </div>

      {/* Question */}
      <p className="font-syne font-semibold text-base text-ink mb-5 leading-relaxed">
        {current.question}
      </p>

      {/* Options */}
      <div className="space-y-3 mb-6">
        {current.options.map((opt, idx) => {
          let cls =
            "w-full text-start px-4 py-3 rounded-xl border text-sm font-syne transition-colors ";
          if (!isAnswered) {
            cls += "border-border hover:border-blue-400 hover:bg-blue-50 text-ink cursor-pointer";
          } else if (idx === current.correct_index) {
            cls += "border-emerald-400 bg-emerald-50 text-emerald-800 cursor-default";
          } else if (idx === selected) {
            cls += "border-red-400 bg-red-50 text-red-800 cursor-default";
          } else {
            cls += "border-border text-ink-3 cursor-default opacity-60";
          }
          return (
            <button key={idx} className={cls} onClick={() => handleSelect(idx)} disabled={isAnswered}>
              <span className="inline-block w-5 h-5 rounded-full border border-current text-xs font-bold text-center leading-5 mr-3 flex-shrink-0">
                {String.fromCharCode(65 + idx)}
              </span>
              {opt}
            </button>
          );
        })}
      </div>

      {/* Explanation */}
      {isAnswered && (
        <div
          className={`rounded-xl p-4 mb-5 text-sm ${
            isCorrect
              ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
              : "bg-amber-50 border border-amber-200 text-amber-800"
          }`}
        >
          <span className="font-semibold">
            {isCorrect ? (t("landing.quiz_correct") as string) : (t("landing.quiz_wrong") as string)}{" "}
          </span>
          {current.explanation}
        </div>
      )}

      {/* Next button */}
      {isAnswered && (
        <button
          onClick={handleNext}
          className="w-full bg-ink text-white font-syne font-semibold text-sm py-3 rounded-xl hover:bg-ink/80 transition-colors"
        >
          {step + 1 < total
            ? (t("landing.quiz_next") as string)
            : (t("landing.quiz_finish") as string)}
        </button>
      )}
    </div>
  );
}
