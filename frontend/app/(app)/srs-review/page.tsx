"use client";

import { useState, useEffect } from "react";
import { srsApi } from "@/lib/api";
import Link from "next/link";

type MCQ = {
  question: string;
  options: Record<string, string>;
  correct: string;
  explanation: string;
};

type SrsItem = {
  item_id: string;
  entity_type: string;
  entity_id: string;
  title: string;
  interval_days: number;
  review_count: number;
  questions: MCQ[];
};

// ── Quality rating labels ──────────────────────────────────────────────────────
const QUALITY_OPTIONS = [
  { quality: 5, label: "Easy", desc: "Perfect recall", color: "bg-green text-white" },
  { quality: 4, label: "Good", desc: "Minor hesitation", color: "bg-blue text-white" },
  { quality: 3, label: "Hard", desc: "Recalled with effort", color: "bg-amber text-ink-1" },
  { quality: 1, label: "Again", desc: "Forgot — repeat soon", color: "bg-red text-white" },
];

// ── Single MCQ review ──────────────────────────────────────────────────────────
function MCQReview({
  mcq,
  onAnswer,
}: {
  mcq: MCQ;
  onAnswer: (correct: boolean) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const answered = selected !== null;

  const handleSelect = (key: string) => {
    if (answered) return;
    setSelected(key);
    onAnswer(key === mcq.correct);
  };

  return (
    <div className="space-y-4">
      <p className="font-serif text-ink-1 leading-relaxed">{mcq.question}</p>
      <div className="space-y-2">
        {Object.entries(mcq.options).map(([key, text]) => {
          let cls = "border border-ink-4 text-ink-2 hover:border-ink-3";
          if (answered) {
            if (key === mcq.correct) cls = "border-green bg-green-light text-green font-bold";
            else if (key === selected) cls = "border-red bg-red/10 text-red";
            else cls = "border-ink-4 text-ink-4 opacity-50";
          }
          return (
            <button
              key={key}
              onClick={() => handleSelect(key)}
              className={`w-full text-left px-4 py-2.5 rounded-lg text-sm font-serif transition-colors ${cls}`}
            >
              <span className="font-syne font-bold mr-2">{key}.</span>
              {text}
            </button>
          );
        })}
      </div>
      {answered && (
        <div className={`p-3 rounded-lg text-sm font-serif ${selected === mcq.correct ? "bg-green-light text-green" : "bg-red/10 text-red"}`}>
          <span className="font-syne font-bold">{selected === mcq.correct ? "Correct. " : "Incorrect. "}</span>
          {mcq.explanation}
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function SrsReviewPage() {
  const [items, setItems] = useState<SrsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [current, setCurrent] = useState(0);
  const [mcqIdx, setMcqIdx] = useState(0);
  const [mcqCorrect, setMcqCorrect] = useState<boolean | null>(null);
  const [showQuality, setShowQuality] = useState(false);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [totalReviewed, setTotalReviewed] = useState(0);

  useEffect(() => {
    srsApi.getQueue()
      .then((data: any) => setItems(data.items ?? []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  const item = items[current];
  const questions = item?.questions ?? [];
  const mcq = questions[mcqIdx] ?? null;
  const allQuestionsAnswered = mcqIdx >= questions.length - 1 && mcqCorrect !== null;

  const handleMcqAnswer = (correct: boolean) => {
    setMcqCorrect(correct);
    if (questions.length === 0 || mcqIdx >= questions.length - 1) {
      setShowQuality(true);
    }
  };

  const handleNextMcq = () => {
    setMcqCorrect(null);
    setMcqIdx((i) => i + 1);
    if (mcqIdx >= questions.length - 1) setShowQuality(true);
  };

  const handleQualitySubmit = async (quality: number) => {
    if (!item || submitting) return;
    setSubmitting(true);
    try {
      await srsApi.review(item.item_id, quality);
      setTotalReviewed((n) => n + 1);
      if (current + 1 >= items.length) {
        setDone(true);
      } else {
        setCurrent((i) => i + 1);
        setMcqIdx(0);
        setMcqCorrect(null);
        setShowQuality(false);
      }
    } catch {/* ignore */}
    finally { setSubmitting(false); }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <p className="font-serif text-ink-3">Loading review queue…</p>
      </div>
    );
  }

  if (done || items.length === 0) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center space-y-6">
        <div className="text-5xl">🎉</div>
        <h1 className="font-syne font-black text-2xl text-ink-1">
          {totalReviewed > 0 ? `${totalReviewed} item${totalReviewed > 1 ? "s" : ""} reviewed!` : "Queue is empty"}
        </h1>
        <p className="font-serif text-ink-3">
          {totalReviewed > 0
            ? "Great work. Your next review session will be scheduled by SM-2."
            : "Complete lessons and click \"Reinforce\" to add items to your review queue."}
        </p>
        <div className="flex gap-3 justify-center">
          <Link href="/dashboard" className="btn-primary font-syne font-bold text-sm px-5 py-2 rounded">
            Back to Dashboard
          </Link>
          <Link href="/modules" className="font-syne font-bold text-sm px-5 py-2 rounded border border-ink-4 text-ink-2 hover:border-ink-3 transition-colors">
            Browse Modules
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="font-serif text-xs text-ink-3 uppercase tracking-wide">Spaced Repetition Review</p>
          <h1 className="font-syne font-black text-xl text-ink-1 mt-0.5">{item.title}</h1>
        </div>
        <div className="text-right">
          <p className="font-syne font-bold text-sm text-ink-2">{current + 1} / {items.length}</p>
          <p className="text-xs font-serif text-ink-4">items today</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-ink-5 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue transition-all duration-300"
          style={{ width: `${((current) / items.length) * 100}%` }}
        />
      </div>

      {/* Card */}
      <div className="border border-ink-4 rounded-xl p-6 bg-surface space-y-5">
        {!showQuality ? (
          <>
            {mcq ? (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-syne font-bold text-ink-4 uppercase tracking-wide">
                    Question {mcqIdx + 1} of {questions.length}
                  </span>
                </div>
                <MCQReview mcq={mcq} onAnswer={handleMcqAnswer} />
                {mcqCorrect !== null && mcqIdx < questions.length - 1 && (
                  <button
                    onClick={handleNextMcq}
                    className="btn-primary font-syne font-bold text-sm px-5 py-2 rounded"
                  >
                    Next question →
                  </button>
                )}
                {(mcqCorrect !== null && mcqIdx >= questions.length - 1) && (
                  <button
                    onClick={() => setShowQuality(true)}
                    className="btn-primary font-syne font-bold text-sm px-5 py-2 rounded"
                  >
                    Rate your recall →
                  </button>
                )}
              </>
            ) : (
              <div className="space-y-3">
                <p className="font-serif text-ink-2">No questions cached for this item yet.</p>
                <button onClick={() => setShowQuality(true)} className="btn-primary font-syne font-bold text-sm px-5 py-2 rounded">
                  Rate recall →
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="space-y-4">
            <p className="font-syne font-bold text-ink-1">How well did you remember this?</p>
            <div className="grid grid-cols-2 gap-2">
              {QUALITY_OPTIONS.map(({ quality, label, desc, color }) => (
                <button
                  key={quality}
                  onClick={() => handleQualitySubmit(quality)}
                  disabled={submitting}
                  className={`p-3 rounded-lg text-left transition-opacity ${color} ${submitting ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  <p className="font-syne font-black text-sm">{label}</p>
                  <p className="text-xs opacity-80 mt-0.5">{desc}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
