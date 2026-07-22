"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { contentApi, progressApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

type MCQQuestion = {
  id: string;
  question: string;
  options: Record<string, string>;
  difficulty: "easy" | "medium" | "hard";
  question_type?: "mcq" | "sata" | "ordered" | "calculation";
  ngn_type?: string;
  numeric_unit?: string;
};

type AnswerResult = {
  correct: boolean;
  correct_answer: string;
  explanation: string;
  xp_earned: number;
  partial_score?: number;
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: "text-green bg-green-light",
  medium: "text-amber bg-amber-light",
  hard: "text-red bg-red-light",
};

function formatTime(secs: number) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function QuizPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const t = useT();

  const examMode = searchParams.get("exam") === "1";
  const examCountParam = parseInt(searchParams.get("count") ?? "0") || 0;

  const [questions, setQuestions] = useState<MCQQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedMultiple, setSelectedMultiple] = useState<string[]>([]); // sata
  const [orderedSelection, setOrderedSelection] = useState<string[]>([]); // ordered
  const [numericValue, setNumericValue] = useState<string>(""); // calculation
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0, xp: 0 });
  const [finished, setFinished] = useState(false);
  const [modTitle, setModTitle] = useState("");

  // Exam mode state
  const [examAnswers, setExamAnswers] = useState<Record<string, string>>({});
  const [examResults, setExamResults] = useState<Record<string, AnswerResult | null>>({});
  const [timeLeft, setTimeLeft] = useState(0);
  const [startTime, setStartTime] = useState(0);
  const [submittingExam, setSubmittingExam] = useState(false);
  const [timeExpired, setTimeExpired] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (!id) return;
    Promise.all([
      contentApi.getMCQ(id),
      contentApi.getModule(id),
    ]).then(([mcqRes, modRes]) => {
      let qs: MCQQuestion[] = (mcqRes ?? []).sort(() => Math.random() - 0.5);
      if (examMode && examCountParam > 0) qs = qs.slice(0, examCountParam);
      setQuestions(qs);
      setModTitle(modRes?.title ?? "Module");
      if (examMode) {
        const totalSecs = qs.length * 120; // 2 min per question
        setTimeLeft(totalSecs);
        setStartTime(Date.now());
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Exam mode countdown
  const finishExam = useCallback(async () => {
    if (submittingExam || finished) return;
    clearInterval(timerRef.current);
    setSubmittingExam(true);
    const answered = Object.entries(examAnswers);
    const pairs = await Promise.all(
      answered.map(([qId, letter]) =>
        progressApi.answerMCQ(qId, letter)
          .then((r: AnswerResult) => ({ qId, result: r }))
          .catch(() => ({ qId, result: null as AnswerResult | null }))
      )
    );
    const map: Record<string, AnswerResult | null> = {};
    let correct = 0, xp = 0;
    for (const { qId, result: r } of pairs) {
      map[qId] = r;
      if (r?.correct) correct++;
      xp += r?.xp_earned ?? 0;
    }
    setExamResults(map);
    setScore({ correct, total: answered.length, xp });
    setSubmittingExam(false);
    setFinished(true);
  }, [examAnswers, submittingExam, finished]);

  useEffect(() => {
    if (!examMode || !startTime || finished || loading) return;
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const totalSecs = questions.length * 120;
      const left = totalSecs - elapsed;
      if (left <= 0) {
        clearInterval(timerRef.current);
        setTimeLeft(0);
        setTimeExpired(true);
      } else {
        setTimeLeft(left);
      }
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [examMode, startTime, finished, loading, questions.length]);

  useEffect(() => {
    if (timeExpired) { finishExam(); }
  }, [timeExpired, finishExam]);

  const resetQuestionState = () => {
    setSelected(null);
    setSelectedMultiple([]);
    setOrderedSelection([]);
    setNumericValue("");
    setResult(null);
  };

  // Normal quiz handlers
  const handleSelect = (letter: string) => {
    if (result) return;
    const qtype = questions[current]?.question_type ?? "mcq";
    if (qtype === "sata") {
      setSelectedMultiple(prev =>
        prev.includes(letter) ? prev.filter(l => l !== letter) : [...prev, letter]
      );
    } else if (qtype === "ordered") {
      setOrderedSelection(prev => {
        if (prev.includes(letter)) return prev.filter(l => l !== letter);
        return [...prev, letter];
      });
    } else {
      setSelected(letter);
      if (examMode) {
        setExamAnswers(prev => ({ ...prev, [questions[current].id]: letter }));
      }
    }
  };

  const handleSubmit = async () => {
    const q = questions[current];
    if (!q || submitting) return;
    const qtype = q.question_type ?? "mcq";
    if (qtype === "mcq" && !selected) return;
    if (qtype === "sata" && selectedMultiple.length === 0) return;
    if (qtype === "ordered" && orderedSelection.length === 0) return;
    if (qtype === "calculation" && numericValue === "") return;

    setSubmitting(true);
    try {
      let answer: string | string[] | number = selected ?? "";
      if (qtype === "sata") answer = selectedMultiple;
      else if (qtype === "ordered") answer = orderedSelection;
      else if (qtype === "calculation") answer = parseFloat(numericValue);

      const res = await progressApi.answerMCQ(q.id, answer, qtype);
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
    } catch { /* ignore */ }
    finally { setSubmitting(false); }
  };

  const handleNext = () => {
    if (current + 1 >= questions.length) {
      setFinished(true);
    } else {
      setCurrent((c) => c + 1);
      resetQuestionState();
    }
  };

  const handleExamNext = () => {
    if (current + 1 >= questions.length) {
      finishExam();
    } else {
      setCurrent((c) => c + 1);
      setSelected(examAnswers[questions[current + 1]?.id] ?? null);
    }
  };

  const handleExamPrev = () => {
    if (current > 0) {
      setCurrent((c) => c - 1);
      setSelected(examAnswers[questions[current - 1]?.id] ?? null);
    }
  };

  if (loading || submittingExam) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="font-serif text-ink-3 text-sm animate-pulse">
          {submittingExam ? t("quiz.score") + "…" : t("common.loading")}
        </p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
        <div className="text-4xl">📋</div>
        <h2 className="font-syne font-bold text-xl text-ink">{t("quiz.no_quizzes")}</h2>
        <p className="font-serif text-ink-2 text-sm text-center max-w-sm">
          This module doesn&apos;t have MCQ questions available yet.
        </p>
        <button onClick={() => router.back()} className="btn-primary mt-2">
          ← {t("common.back")}
        </button>
      </div>
    );
  }

  // ── Exam final screen ───────────────────────────────────────
  if (finished && examMode) {
    const pct = score.total > 0 ? Math.round((score.correct / score.total) * 100) : 0;
    const grade =
      pct >= 80 ? { label: t("quiz.correct"), color: "text-green", emoji: "🎉" }
      : pct >= 60 ? { label: "Good job!", color: "text-amber", emoji: "👍" }
      : { label: t("quiz.retry"), color: "text-red", emoji: "📚" };
    const totalExamSecs = questions.length * 120;
    const timeTaken = totalExamSecs - timeLeft;
    const wrongQuestions = questions.filter(q => {
      const r = examResults[q.id];
      return r && !r.correct;
    });
    const skipped = questions.filter(q => !examAnswers[q.id]);

    return (
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto">
          {/* Score card */}
          <div className="card p-8 text-center mb-6">
            <div className="text-5xl mb-3">{grade.emoji}</div>
            <h1 className={`font-syne font-black text-3xl mb-1 ${grade.color}`}>{pct}%</h1>
            <p className="font-serif text-ink-2 text-sm mb-1">{modTitle}</p>
            <p className="font-syne text-xs text-ink-3 mb-6">{t("quiz.exam_mode")}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <div className="card bg-surface-2 p-3 rounded-lg text-center">
                <div className="font-syne font-black text-xl text-ink">{score.correct}/{score.total}</div>
                <div className="font-syne text-xs text-ink-3 mt-0.5">{t("quiz.correct")}</div>
              </div>
              <div className="card bg-surface-2 p-3 rounded-lg text-center">
                <div className="font-syne font-black text-xl text-red">{wrongQuestions.length}</div>
                <div className="font-syne text-xs text-ink-3 mt-0.5">{t("quiz.exam_wrong")}</div>
              </div>
              <div className="card bg-surface-2 p-3 rounded-lg text-center">
                <div className="font-syne font-black text-xl text-ink-3">{skipped.length}</div>
                <div className="font-syne text-xs text-ink-3 mt-0.5">{t("quiz.exam_skipped")}</div>
              </div>
              <div className="card bg-surface-2 p-3 rounded-lg text-center">
                <div className="font-syne font-black text-xl text-amber">+{score.xp}</div>
                <div className="font-syne text-xs text-ink-3 mt-0.5">{t("progress.xp_earned")}</div>
              </div>
            </div>

            <div className="text-xs text-ink-3 font-syne mb-6">
              {t("quiz.exam_time_taken")}: {formatTime(timeTaken)}
            </div>

            <div className="flex gap-3 justify-center">
              <button
                onClick={() => router.push(`/quiz/${id}?exam=1&count=${examCountParam}`)}
                className="btn-primary"
              >
                {t("quiz.retry")}
              </button>
              <Link href={`/modules/${id}`} className="btn-secondary">
                ← {t("common.back")}
              </Link>
            </div>
          </div>

          {/* Wrong answers review */}
          {wrongQuestions.length > 0 && (
            <div>
              <h2 className="font-syne font-bold text-base text-ink mb-3">
                {t("quiz.exam_review_title")} ({wrongQuestions.length})
              </h2>
              <div className="space-y-4">
                {wrongQuestions.map((q, i) => {
                  const r = examResults[q.id];
                  const userAnswer = examAnswers[q.id];
                  return (
                    <div key={q.id} className="card p-4 border-l-4 border-red">
                      <div className="font-syne font-semibold text-sm text-ink mb-3">
                        {i + 1}. {q.question}
                      </div>
                      <div className="space-y-1.5 mb-3">
                        {Object.entries(q.options).sort().map(([letter, text]) => {
                          const isCorrect = letter === r?.correct_answer;
                          const isYours = letter === userAnswer;
                          let cls = "flex items-start gap-2 text-xs font-serif rounded px-2 py-1.5 ";
                          if (isCorrect) cls += "bg-green-light text-green font-semibold";
                          else if (isYours && !isCorrect) cls += "bg-red-light text-red";
                          else cls += "text-ink-3";
                          return (
                            <div key={letter} className={cls}>
                              <span className="font-syne font-bold flex-shrink-0">{letter}.</span>
                              <span>{text}</span>
                              {isCorrect && <span className="ml-auto flex-shrink-0">✓</span>}
                              {isYours && !isCorrect && <span className="ml-auto flex-shrink-0">✗</span>}
                            </div>
                          );
                        })}
                      </div>
                      {r?.explanation && (
                        <p className="font-serif text-xs text-ink-2 leading-relaxed border-t border-border pt-2">
                          {r.explanation}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Normal final score screen ───────────────────────────────
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
              <div className="font-syne text-xs text-ink-3 mt-1">{t("quiz.correct")}</div>
            </div>
            <div className="card bg-surface-2 p-4 rounded-lg">
              <div className="font-syne font-black text-2xl text-ink">{pct}%</div>
              <div className="font-syne text-xs text-ink-3 mt-1">{t("quiz.score")}</div>
            </div>
            <div className="card bg-surface-2 p-4 rounded-lg">
              <div className="font-syne font-black text-2xl text-amber">+{score.xp}</div>
              <div className="font-syne text-xs text-ink-3 mt-1">{t("progress.xp_earned")}</div>
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
              {t("quiz.retry")}
            </button>
            <Link href={`/modules/${id}`} className="font-syne font-semibold text-sm text-ink-2 hover:text-ink text-center transition-colors">
              ← {t("common.back")}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Question screen ─────────────────────────────────────────
  const q = questions[current];
  const qtype = q.question_type ?? "mcq";
  const optionLetters = Object.keys(q.options).sort();
  const isLastQuestion = current + 1 >= questions.length;
  const answeredCount = Object.keys(examAnswers).length;

  // Exam mode: timer color
  const timerCritical = examMode && timeLeft <= 60;
  const timerWarning = examMode && timeLeft <= 300 && timeLeft > 60;

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <button onClick={() => router.back()} className="text-ink-3 hover:text-ink text-xs font-syne truncate max-w-[40%]">
            ← {modTitle}
          </button>
          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            {/* Exam timer */}
            {examMode && (
              <div className={`flex items-center gap-1.5 font-mono font-bold text-sm px-2.5 py-1 rounded-lg border transition-colors ${
                timerCritical
                  ? "border-red/50 bg-red-light text-red animate-pulse"
                  : timerWarning
                  ? "border-amber/50 bg-amber-light text-amber"
                  : "border-border bg-surface-2 text-ink"
              }`}>
                ⏱ {formatTime(timeLeft)}
              </div>
            )}
            {!examMode && (
              <span className={`badge ${DIFFICULTY_COLOR[q.difficulty] ?? "text-ink-2 bg-surface-2"}`}>
                {q.difficulty}
              </span>
            )}
            <span className="font-syne text-xs text-ink-3">
              {current + 1} / {questions.length}
            </span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1.5 bg-surface-2 rounded-full mb-6">
          <div
            className={`h-1.5 rounded-full transition-all ${examMode ? "bg-amber" : "bg-ink"}`}
            style={{ width: `${examMode ? (answeredCount / questions.length) * 100 : (current / questions.length) * 100}%` }}
          />
        </div>

        {/* Exam mode badge */}
        {examMode && (
          <div className="flex items-center gap-2 mb-4">
            <span className="badge text-amber bg-amber-light text-[10px] font-syne font-bold uppercase tracking-wider">
              ⏱ {t("quiz.exam_mode")}
            </span>
            <span className="text-xs text-ink-3 font-serif">{t("quiz.exam_mode_desc")}</span>
          </div>
        )}

        {/* Question */}
        <div className="card p-5 sm:p-6 mb-5">
          <p className="font-syne font-semibold text-base text-ink leading-relaxed">
            {q.question}
          </p>
        </div>

        {/* Question type / NGN hint */}
        {(qtype !== "mcq" || q.ngn_type) && (
          <div className="mb-3 flex items-center gap-2 flex-wrap">
            {qtype !== "mcq" && (
              <span className={`text-xs font-syne font-semibold px-2.5 py-1 rounded-full border ${
                qtype === "sata" ? "bg-blue-50 border-blue-200 text-blue-700" :
                qtype === "ordered" ? "bg-purple-50 border-purple-200 text-purple-700" :
                "bg-orange-50 border-orange-200 text-orange-700"
              }`}>
                {qtype === "sata" ? "Select All That Apply" :
                 qtype === "ordered" ? "Put in Correct Order" :
                 "Enter Numeric Answer"}
              </span>
            )}
            {q.ngn_type && (
              <span className="text-xs font-syne font-semibold px-2.5 py-1 rounded-full border bg-violet-50 border-violet-200 text-violet-700">
                NGN: {q.ngn_type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
              </span>
            )}
          </div>
        )}

        {/* Options */}
        <div className="space-y-2.5 mb-5">
          {/* MCQ — standard single-select */}
          {qtype === "mcq" && optionLetters.map((letter) => {
            let cls = "w-full text-left px-4 py-3 rounded-lg border transition-all font-serif text-sm text-ink ";
            if (examMode) {
              cls += selected === letter
                ? "border-amber bg-amber-light text-amber font-semibold"
                : "border-border hover:border-ink/50 bg-surface";
            } else if (!result) {
              cls += selected === letter ? "border-ink bg-ink text-white" : "border-border hover:border-ink/50 bg-surface";
            } else {
              const correctLetters = result.correct_answer.split(",");
              if (correctLetters.includes(letter)) cls += "border-green bg-green-light text-green font-semibold";
              else if (letter === selected && !result.correct) cls += "border-red bg-red-light text-red";
              else cls += "border-border bg-surface text-ink-3 opacity-60";
            }
            return (
              <button key={letter} onClick={() => handleSelect(letter)} disabled={!examMode && !!result} className={cls}>
                <span className="font-syne font-bold mr-3">{letter}.</span>{q.options[letter]}
              </button>
            );
          })}

          {/* SATA — multi-select checkboxes */}
          {qtype === "sata" && optionLetters.map((letter) => {
            const isChecked = selectedMultiple.includes(letter);
            const correctLetters = result ? result.correct_answer.split(",") : [];
            let cls = "w-full text-left px-4 py-3 rounded-lg border transition-all font-serif text-sm flex items-center gap-3 ";
            if (result) {
              if (correctLetters.includes(letter)) cls += "border-green bg-green-light text-green font-semibold";
              else if (isChecked && !correctLetters.includes(letter)) cls += "border-red bg-red-light text-red";
              else cls += "border-border bg-surface text-ink-3 opacity-60";
            } else {
              cls += isChecked ? "border-ink bg-ink text-white" : "border-border hover:border-ink/50 bg-surface text-ink";
            }
            return (
              <button key={letter} onClick={() => handleSelect(letter)} disabled={!!result} className={cls}>
                <span className={`flex-shrink-0 w-4 h-4 rounded border-2 flex items-center justify-center ${isChecked ? "border-current bg-current" : "border-current/50"}`}>
                  {isChecked && <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 10 8" fill="currentColor"><path d="M1 4l3 3 5-6"/></svg>}
                </span>
                <span className="font-syne font-bold flex-shrink-0">{letter}.</span>
                <span>{q.options[letter]}</span>
              </button>
            );
          })}

          {/* Ordered — tap to sequence */}
          {qtype === "ordered" && (
            <div className="space-y-2">
              {result && (
                <p className="text-xs font-syne text-ink-3 mb-2">Correct order: {result.correct_answer.split(",").map(l => `${l}. ${q.options[l] ?? l}`).join(" → ")}</p>
              )}
              {orderedSelection.length > 0 && (
                <div className="mb-3 p-3 bg-surface border border-border rounded-lg">
                  <p className="text-xs font-syne text-ink-3 mb-2">Your order:</p>
                  <div className="flex flex-wrap gap-2">
                    {orderedSelection.map((l, i) => (
                      <span key={l} className="font-syne font-bold text-xs bg-ink text-white px-2 py-1 rounded">
                        {i+1}. {l}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {optionLetters.map((letter) => {
                const pos = orderedSelection.indexOf(letter);
                const placed = pos !== -1;
                const cls = `w-full text-left px-4 py-3 rounded-lg border transition-all font-serif text-sm flex items-center gap-3 ${
                  result
                    ? result.correct_answer.split(",")[pos] === letter && placed
                      ? "border-green bg-green-light text-green"
                      : placed ? "border-red bg-red-light text-red" : "border-border bg-surface text-ink-3 opacity-60"
                    : placed
                      ? "border-ink bg-ink/5 text-ink"
                      : "border-border hover:border-ink/50 bg-surface text-ink"
                }`;
                return (
                  <button key={letter} onClick={() => handleSelect(letter)} disabled={!!result} className={cls}>
                    <span className="font-syne font-bold w-6 flex-shrink-0 text-center">
                      {placed ? `${pos+1}.` : letter + "."}
                    </span>
                    <span>{q.options[letter]}</span>
                    {placed && !result && (
                      <span className="ml-auto text-ink-3 text-xs">(#{pos+1})</span>
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Calculation — numeric input */}
          {qtype === "calculation" && (
            <div className="space-y-3">
              <div className="flex gap-2 items-center">
                <input
                  type="number"
                  step="any"
                  value={numericValue}
                  onChange={e => setNumericValue(e.target.value)}
                  disabled={!!result}
                  placeholder="Enter your answer..."
                  className="flex-1 px-4 py-3 rounded-lg border border-border bg-surface text-ink font-mono text-lg focus:outline-none focus:border-ink transition-colors disabled:opacity-60"
                />
                {q.numeric_unit && (
                  <span className="font-syne font-semibold text-ink-2 text-sm px-3 py-3 bg-surface-2 border border-border rounded-lg flex-shrink-0">
                    {q.numeric_unit}
                  </span>
                )}
              </div>
              {result && (
                <div className={`rounded-lg p-3 border text-sm font-serif ${result.correct ? "border-green/30 bg-green-light text-green" : "border-red/30 bg-red-light text-red"}`}>
                  {result.correct
                    ? `✓ Correct! Answer: ${result.correct_answer}`
                    : `✗ Incorrect. Correct answer: ${result.correct_answer}`}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Exam mode navigation */}
        {examMode ? (
          <div className="flex items-center gap-3">
            <button
              onClick={handleExamPrev}
              disabled={current === 0}
              className="btn-secondary flex-1 disabled:opacity-30"
            >
              ← {t("common.back")}
            </button>
            {isLastQuestion ? (
              <button
                onClick={() => finishExam()}
                className="btn-primary flex-1"
              >
                {t("quiz.finish")} ({answeredCount}/{questions.length})
              </button>
            ) : (
              <button
                onClick={handleExamNext}
                className="btn-primary flex-1"
              >
                {t("quiz.next_question")} →
              </button>
            )}
          </div>
        ) : (
          // Normal quiz submit/next
          !result ? (
            <button
              onClick={handleSubmit}
              disabled={submitting ||
                (qtype === "mcq" && !selected) ||
                (qtype === "sata" && selectedMultiple.length === 0) ||
                (qtype === "ordered" && orderedSelection.length !== optionLetters.length) ||
                (qtype === "calculation" && numericValue === "")
              }
              className="btn-primary w-full"
            >
              {submitting ? t("common.loading") : t("quiz.submit_answer")}
            </button>
          ) : (
            <div>
              <div className={`rounded-lg border p-4 mb-4 ${result.correct ? "border-green/30 bg-green-light" : (result.partial_score && result.partial_score > 0) ? "border-amber/30 bg-amber-light" : "border-red/30 bg-red-light"}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">{result.correct ? "✅" : result.partial_score && result.partial_score > 0 ? "⚠️" : "❌"}</span>
                  <span className={`font-syne font-bold text-sm ${result.correct ? "text-green" : result.partial_score && result.partial_score > 0 ? "text-amber" : "text-red"}`}>
                    {result.correct
                      ? `${t("quiz.correct")} +${result.xp_earned} XP`
                      : result.partial_score != null && result.partial_score > 0
                        ? `Partial credit (${Math.round(result.partial_score * 100)}%) — Correct: ${result.correct_answer}`
                        : qtype === "calculation"
                          ? `Incorrect — Correct answer: ${result.correct_answer}`
                          : `${t("quiz.incorrect")} — Correct: ${result.correct_answer}`}
                  </span>
                </div>
                <p className="font-serif text-sm text-ink leading-relaxed">{result.explanation}</p>
              </div>
              <div className="flex items-center justify-between gap-3 mb-3">
                <button
                  onClick={() => {
                    const prompt = !result.correct
                      ? `I got this question wrong. Please explain:\n\n"${q.question}"\n\nCorrect answer: ${result.correct_answer}${q.options[result.correct_answer] ? ` — ${q.options[result.correct_answer]}` : ""}.\n\nExplanation given: ${result.explanation}`
                      : `Help me understand more about this topic:\n\n"${q.question}"`;
                    window.open(`/ai-tutor?mode=tutor&prompt=${encodeURIComponent(prompt)}`, "_blank", "noopener,noreferrer");
                  }}
                  className="flex items-center gap-1.5 text-xs font-syne text-ink-3 hover:text-ink transition-colors"
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  Ask AI Tutor
                </button>
                <button onClick={handleNext} className="btn-primary flex-1">
                  {isLastQuestion ? t("quiz.finish") : t("quiz.next_question")}
                </button>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
