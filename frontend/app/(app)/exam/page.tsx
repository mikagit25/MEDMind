"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import ReactMarkdown from "react-markdown";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, examApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import {
  Clock, CheckCircle2, XCircle, BarChart3, MessageSquare,
  ChevronLeft, ChevronRight, AlertTriangle, Layers, Gift,
  Sparkles, X, Loader2, Flag, ChevronDown, ChevronUp, Lightbulb,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

type OptionRationale = { text: string; why: "correct" | "incorrect" };
type Rationales = Record<string, OptionRationale>;

type Question = {
  index: number;
  id: string;
  question: string;
  options: Record<string, string>;
  question_type: string;
  numeric_unit?: string;
  ngn_type?: string;
  bowtie_data?: {
    condition_options: string[];
    action_options: string[];
    parameter_options: string[];
  };
  nclex_client_needs?: string;
  cjmm_skill?: string;
};

type Session = {
  session_id: string;
  mode: string;
  mode_id: string;
  total_questions: number;
  duration_min: number;
  ends_at: string;
  cat_enabled: boolean;
  questions: Question[];
};

type PerQuestion = {
  index: number;
  correct: boolean;
  selected: unknown;
  correct_answer: string | null;
  nclex_client_needs?: string;
  cjmm_skill?: string;
  question_type: string;
  ngn_type?: string;
};

type WrongQuestion = {
  index: number;
  id?: string;
  question: string;
  options?: Record<string, string>;
  your_answer: unknown;
  correct_answer: string;
  explanation?: string;
  rationales?: Rationales;
  key_takeaway?: string;
  test_taking_tip?: string;
  nclex_client_needs?: string;
  cjmm_skill?: string;
};

type Results = {
  session_id: string;
  mode: string;
  mode_id: string;
  total_questions: number;
  correct: number;
  wrong: number;
  score_pct: number;
  passed: boolean;
  pass_threshold: number;
  time_taken_min: number;
  cat_enabled: boolean;
  per_question: PerQuestion[];
  wrong_questions: WrongQuestion[];
  nclex_category_breakdown: Record<string, { total: number; correct: number; pct: number; label: string }>;
  nclex_cjmm_breakdown: Record<string, { total: number; correct: number; pct: number; label: string }>;
  weak_categories: Array<{ key: string; label: string; pct: number }>;
  message: string;
};

// ── Timer ──────────────────────────────────────────────────────────────────────

function Timer({ endsAt, onExpire }: { endsAt: string; onExpire: () => void }) {
  const [secs, setSecs] = useState(9999);
  const expired = useRef(false);
  const mountedAt = useRef(Date.now());

  useEffect(() => {
    const tick = () => {
      const left = Math.max(0, Math.floor((new Date(endsAt).getTime() - Date.now()) / 1000));
      setSecs(left);
      // Grace period: never fire onExpire within the first 5 seconds of mount
      // (guards against timezone parse issues on initial render)
      const elapsed = Date.now() - mountedAt.current;
      if (left === 0 && !expired.current && elapsed > 5000) {
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
  return (
    <div className={`font-syne font-black text-xl tabular-nums flex items-center gap-1.5 ${secs < 120 ? "text-red" : "text-ink"}`}>
      <Clock className="w-4 h-4" />
      {String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}
    </div>
  );
}

// ── Question renderer ──────────────────────────────────────────────────────────

type AnswerState = {
  selected_option: string;
  selected_options: string[];
  ordered_options: string[];
  numeric_value: string;
};

function QuestionCard({
  question,
  answer,
  locked,
  onChange,
}: {
  question: Question;
  answer: AnswerState;
  locked: boolean;
  onChange: (a: AnswerState) => void;
}) {
  const t = useT();
  const qtype = question.question_type;
  const options = Object.entries(question.options || {});

  function toggleSATA(key: string) {
    const cur = answer.selected_options;
    const next = cur.includes(key) ? cur.filter(k => k !== key) : [...cur, key];
    onChange({ ...answer, selected_options: next });
  }

  function toggleOrdered(key: string) {
    const cur = answer.ordered_options;
    const next = cur.includes(key) ? cur.filter(k => k !== key) : [...cur, key];
    onChange({ ...answer, ordered_options: next });
  }

  if (qtype === "sata") {
    return (
      <div className="space-y-2">
        <p className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-3">
          {t("exam_page.sata_label")}
        </p>
        {options.map(([key, text]) => {
          const checked = answer.selected_options.includes(key);
          return (
            <button
              key={key}
              onClick={() => !locked && toggleSATA(key)}
              disabled={locked}
              className={`w-full text-left flex items-start gap-3 p-4 rounded-lg border-2 transition-colors disabled:cursor-default ${
                checked ? "border-ink bg-ink/5" : "border-border hover:border-ink-3 bg-surface"
              }`}
            >
              <span className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors ${
                checked ? "border-ink bg-ink" : "border-ink-3"
              }`}>
                {checked && <CheckCircle2 className="w-3 h-3 text-white" />}
              </span>
              <span className="font-serif text-sm text-ink leading-relaxed">{text}</span>
            </button>
          );
        })}
      </div>
    );
  }

  if (qtype === "ordered") {
    const ord = answer.ordered_options;
    const remaining = options.filter(([k]) => !ord.includes(k));
    return (
      <div className="space-y-3">
        <p className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider">
          {t("exam_page.ordered_label")}
        </p>
        {ord.length > 0 && (
          <div className="space-y-1.5">
            {ord.map((key, i) => (
              <div key={key} className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-ink text-white text-xs font-syne font-bold flex items-center justify-center flex-shrink-0">
                  {i + 1}
                </span>
                <button
                  onClick={() => !locked && toggleOrdered(key)}
                  disabled={locked}
                  className="flex-1 text-left px-3 py-2 rounded-lg border-2 border-ink bg-ink/5 font-serif text-sm text-ink disabled:cursor-default"
                >
                  {options.find(([k]) => k === key)?.[1]}
                </button>
              </div>
            ))}
          </div>
        )}
        {remaining.length > 0 && !locked && (
          <div className="space-y-1.5 pt-2 border-t border-border">
            <p className="text-xs font-serif text-ink-3">{t("exam_page.ordered_tap")}</p>
            {remaining.map(([key, text]) => (
              <button
                key={key}
                onClick={() => toggleOrdered(key)}
                className="w-full text-left px-3 py-2 rounded-lg border border-border bg-surface hover:border-ink font-serif text-sm text-ink transition-colors"
              >
                <span className="font-syne font-bold text-ink-3 mr-2">{key}.</span>{text}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (qtype === "calculation") {
    return (
      <div>
        <div className="flex gap-3 items-center mt-4">
          <input
            type="number"
            step="any"
            value={answer.numeric_value}
            onChange={e => !locked && onChange({ ...answer, numeric_value: e.target.value })}
            disabled={locked}
            placeholder={t("exam_page.enter_answer")}
            className="flex-1 bg-bg border border-border rounded-xl px-4 py-3 font-mono text-sm text-ink focus:outline-none focus:border-ink transition-colors disabled:opacity-60"
          />
          {question.numeric_unit && (
            <span className="font-syne font-bold text-sm text-ink-2">{question.numeric_unit}</span>
          )}
        </div>
      </div>
    );
  }

  // Default: MCQ (including bow-tie rendered as MCQ fallback)
  return (
    <div className="space-y-3">
      {question.ngn_type === "bowtie" && (
        <div className="text-xs font-syne font-bold text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-3 py-1.5 mb-2 inline-block">
          {t("exam_page.bowtie_label")}
        </div>
      )}
      {options.map(([key, text]) => {
        const isSelected = answer.selected_option === key;
        return (
          <button
            key={key}
            onClick={() => !locked && onChange({ ...answer, selected_option: key })}
            disabled={locked}
            className={`w-full text-left flex items-start gap-3 p-4 rounded-lg border-2 transition-colors disabled:cursor-default ${
              isSelected ? "border-ink bg-ink/5" : "border-border hover:border-ink-3 bg-surface"
            }`}
          >
            <span className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 text-xs font-syne font-bold mt-0.5 ${
              isSelected ? "border-ink bg-ink text-white" : "border-ink-3 text-ink-3"
            }`}>{key}</span>
            <span className="font-serif text-sm text-ink leading-relaxed">{text}</span>
          </button>
        );
      })}
    </div>
  );
}

// ── Rationale panel ───────────────────────────────────────────────────────────

function RationalePanel({
  rationales,
  keyTakeaway,
  testTakingTip,
  selectedOption,
  selectedOptions,
  options,
}: {
  rationales?: Rationales;
  keyTakeaway?: string;
  testTakingTip?: string;
  selectedOption?: string;
  selectedOptions?: string[];
  options: Record<string, string>;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!rationales && !keyTakeaway) return null;

  const selected = selectedOption || (selectedOptions && selectedOptions[0]) || "";
  const selectedRationale = rationales?.[selected];
  const otherEntries = rationales
    ? Object.entries(rationales).filter(([k]) => k !== selected)
    : [];

  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden text-sm">
      {/* Selected option rationale — always visible */}
      {selectedRationale && (
        <div className={`px-4 pt-4 pb-3 ${selectedRationale.why === "correct" ? "bg-green/5 border-b border-green/20" : "bg-red/5 border-b border-red/20"}`}>
          <div className="flex items-center gap-2 mb-1.5">
            {selectedRationale.why === "correct"
              ? <CheckCircle2 className="w-4 h-4 text-green flex-shrink-0" />
              : <XCircle className="w-4 h-4 text-red flex-shrink-0" />}
            <span className="font-syne font-bold text-xs text-ink">
              Option {selected}: {selectedRationale.why === "correct" ? "Correct" : "Incorrect"}
            </span>
          </div>
          <p className="font-serif text-xs text-ink-2 leading-relaxed">{selectedRationale.text}</p>
        </div>
      )}

      {/* Key takeaway */}
      {keyTakeaway && (
        <div className="px-4 py-3 bg-amber-50 border-b border-amber-100 flex items-start gap-2">
          <Lightbulb className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-syne font-bold text-xs text-amber-700 block mb-0.5">Key Takeaway</span>
            <p className="font-serif text-xs text-amber-800 leading-relaxed">{keyTakeaway}</p>
          </div>
        </div>
      )}

      {/* Other options — collapsible */}
      {otherEntries.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded(e => !e)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-syne font-semibold text-ink-3 hover:text-ink hover:bg-surface-2 transition-colors"
          >
            <span>Explain other options ({otherEntries.length})</span>
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {expanded && (
            <div className="px-4 pb-3 space-y-2.5 border-t border-border pt-2.5">
              {otherEntries.map(([key, r]) => (
                <div key={key} className="flex items-start gap-2">
                  <span className={`w-5 h-5 rounded-full text-[10px] font-syne font-bold flex items-center justify-center flex-shrink-0 mt-0.5 ${
                    r.why === "correct" ? "bg-green text-white" : "bg-ink/10 text-ink-3"
                  }`}>{key}</span>
                  <p className="font-serif text-xs text-ink-2 leading-relaxed flex-1">{r.text}</p>
                </div>
              ))}
              {testTakingTip && (
                <div className="pt-2 border-t border-border">
                  <span className="font-syne font-bold text-xs text-ink-3 block mb-0.5">Test-Taking Tip</span>
                  <p className="font-serif text-xs text-ink-3 italic leading-relaxed">{testTakingTip}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Flag button ────────────────────────────────────────────────────────────────

function FlagButton({ questionId }: { questionId?: string }) {
  const [flagged, setFlagged] = useState(false);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);

  if (!questionId || flagged) {
    return flagged ? (
      <span className="inline-flex items-center gap-1 text-xs font-syne text-ink-3">
        <Flag className="w-3 h-3" /> Flagged
      </span>
    ) : null;
  }

  async function submit() {
    setLoading(true);
    try {
      await api.post(`/exam/questions/${questionId}/flag`, { reason });
      setFlagged(true);
      setOpen(false);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 text-xs font-syne text-ink-3 hover:text-red transition-colors"
        title="Flag this question"
      >
        <Flag className="w-3 h-3" /> Flag
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-bg border border-border rounded-2xl p-5 max-w-sm w-full shadow-xl">
            <h3 className="font-syne font-bold text-sm text-ink mb-2">Flag this question</h3>
            <p className="font-serif text-xs text-ink-3 mb-3">Report an error or unclear content for admin review.</p>
            <textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="Describe the issue (optional)"
              rows={3}
              className="w-full bg-surface border border-border rounded-xl px-3 py-2 text-xs font-serif text-ink resize-none focus:outline-none focus:border-ink mb-3"
            />
            <div className="flex gap-2">
              <button
                onClick={submit}
                disabled={loading}
                className="flex-1 font-syne font-bold text-xs bg-ink text-white px-4 py-2 rounded-xl hover:bg-red transition-colors disabled:opacity-50"
              >
                {loading ? "Submitting…" : "Submit Flag"}
              </button>
              <button
                onClick={() => setOpen(false)}
                className="flex-1 font-syne font-semibold text-xs border border-border px-4 py-2 rounded-xl hover:bg-surface transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ── Exam session ───────────────────────────────────────────────────────────────

const BLANK_ANSWER: AnswerState = {
  selected_option: "",
  selected_options: [],
  ordered_options: [],
  numeric_value: "",
};

const DIFF_CLS: Record<string, string> = {
  easy:   "bg-green/10 text-green border-green/30",
  medium: "bg-amber-50 text-amber-600 border-amber-200",
  hard:   "bg-red/10 text-red border-red/30",
};

function DifficultyBadge({ level }: { level: string }) {
  const t = useT();
  const cls = DIFF_CLS[level] ?? DIFF_CLS.medium;
  const label = level === "easy" ? t("exam_page.difficulty_easy")
              : level === "hard" ? t("exam_page.difficulty_hard")
              : t("exam_page.difficulty_medium");
  return (
    <span className={`text-xs font-syne font-bold border rounded-full px-2 py-0.5 ${cls}`}>
      {label}
    </span>
  );
}

// isPracticeMode: show rationale immediately after answering (not for timed full exams)
function isPracticeMode(modeId: string): boolean {
  return modeId === "nclex_demo" || !modeId.includes("nclex_");
}

type QuestionRationale = { rationales?: Rationales; key_takeaway?: string; test_taking_tip?: string };

function ExamSession({
  session,
  onFinish,
}: {
  session: Session;
  onFinish: (results: Results) => void;
}) {
  const t = useT();
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<number, AnswerState>>({});
  const [locked, setLocked] = useState<Record<number, boolean>>({});
  const [questionRationales, setQuestionRationales] = useState<Record<number, QuestionRationale>>({});
  const [submitting, setSubmitting] = useState(false);
  const [currentDifficulty, setCurrentDifficulty] = useState("medium");
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const showRationale = isPracticeMode(session.mode_id);

  const question = session.questions[current];
  const ans = answers[current] ?? BLANK_ANSWER;

  function hasAnswer(a: AnswerState, q: Question): boolean {
    if (q.question_type === "sata") return a.selected_options.length > 0;
    if (q.question_type === "ordered") return a.ordered_options.length === Object.keys(q.options).length;
    if (q.question_type === "calculation") return a.numeric_value.trim() !== "";
    return a.selected_option !== "";
  }

  const recordAnswer = useCallback(async (idx: number, a: AnswerState, q: Question) => {
    if (!hasAnswer(a, q)) return;
    setLocked(l => ({ ...l, [idx]: true }));
    try {
      const qtype = q.question_type;
      const payload =
        qtype === "sata" ? { selected_options: a.selected_options } :
        qtype === "ordered" ? { ordered_options: a.ordered_options } :
        qtype === "calculation" ? { numeric_value: parseFloat(a.numeric_value) } :
        { selected_option: a.selected_option };
      const res = await examApi.submitAnswer(session.session_id, idx, payload);
      if (session.cat_enabled && res?.current_difficulty) {
        setCurrentDifficulty(res.current_difficulty);
      }
      // Capture rationales returned by the server for practice mode display
      if (res?.rationales || res?.key_takeaway) {
        setQuestionRationales(prev => ({
          ...prev,
          [idx]: { rationales: res.rationales, key_takeaway: res.key_takeaway, test_taking_tip: res.test_taking_tip },
        }));
      }
    } catch {}
  }, [session.session_id, session.cat_enabled]);

  function handleChange(a: AnswerState) {
    if (locked[current]) return;
    setAnswers(prev => ({ ...prev, [current]: a }));
  }

  async function handleLock() {
    if (locked[current] || !hasAnswer(ans, question)) return;
    await recordAnswer(current, ans, question);
  }

  async function handleFinalize() {
    setSubmitting(true);
    for (const [idx, a] of Object.entries(answers)) {
      const i = parseInt(idx);
      if (!locked[i]) await recordAnswer(i, a, session.questions[i]);
    }
    try {
      const results = await examApi.finalizeSession(session.session_id);
      onFinish(results);
    } catch {
      setSubmitting(false);
    }
  }

  // Always reference the latest handleFinalize to avoid stale-closure on timer expiry
  const handleFinalizeRef = useRef(handleFinalize);
  handleFinalizeRef.current = handleFinalize;
  const handleExpire = useCallback(() => { handleFinalizeRef.current(); }, []);

  const answeredCount = Object.keys(locked).length;
  const total = session.questions.length;
  const progressPct = total > 0 ? Math.round((answeredCount / total) * 100) : 0;

  if (!question) {
    return (
      <div className="text-center py-20 text-ink-3 font-serif">{t("common.loading")}</div>
    );
  }

  return (
    <div>
      {/* Submit confirmation dialog */}
      {confirmSubmit && !submitting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-bg border border-border rounded-2xl p-6 max-w-sm w-full shadow-xl">
            <h3 className="font-syne font-bold text-base text-ink mb-2">{t("exam_page.submit_confirm_title")}</h3>
            <p className="font-serif text-sm text-ink-3 mb-5">
              {answeredCount}/{total} {t("exam_page.answered")} — {t("exam_page.submit_confirm_body")}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => { setConfirmSubmit(false); handleFinalize(); }}
                className="flex-1 font-syne font-bold text-sm bg-ink text-white px-4 py-2.5 rounded-xl hover:bg-red transition-colors"
              >
                {t("common.submit")}
              </button>
              <button
                onClick={() => setConfirmSubmit(false)}
                className="flex-1 font-syne font-semibold text-sm border border-border px-4 py-2.5 rounded-xl hover:bg-surface transition-colors"
              >
                {t("exam_page.submit_confirm_cancel")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header bar */}
      <div className="mb-4 p-3 bg-surface border border-border rounded-xl">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-syne font-bold text-sm text-ink truncate">{session.mode}</span>
            {session.cat_enabled && (
              <span className="text-xs font-syne font-bold text-blue-600 bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5 flex-shrink-0">
                CAT
              </span>
            )}
          </div>
          <Timer endsAt={session.ends_at} onExpire={handleExpire} />
          <button
            onClick={() => setConfirmSubmit(true)}
            disabled={submitting}
            className="font-syne font-semibold text-xs px-4 py-2 rounded-lg bg-ink text-white hover:bg-red transition-colors disabled:opacity-50 flex-shrink-0"
          >
            {submitting ? t("exam_page.submitting") : t("common.submit")}
          </button>
        </div>
        {/* Progress bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
            <div
              className="h-full bg-green rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <span className="text-xs font-syne text-ink-3 flex-shrink-0">
            {answeredCount}/{total}
          </span>
        </div>
      </div>

      {/* Progress dots */}
      <div className="flex flex-wrap gap-1 mb-4">
        {session.questions.map((_, i) => (
          <button key={i} onClick={() => setCurrent(i)}
            className={`w-6 h-6 rounded text-[10px] font-syne font-bold transition-colors ${
              i === current ? "bg-ink text-white" :
              locked[i] ? "bg-green/80 text-white" :
              answers[i] ? "bg-amber-200 text-amber-800" :
              "bg-surface border border-border text-ink-3"
            }`}
          >{i + 1}</button>
        ))}
      </div>

      {/* Question card */}
      <div className="bg-surface border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className="text-xs font-syne font-bold text-ink-3">
            Q{current + 1} / {total}
          </span>
          {session.cat_enabled && (
            <DifficultyBadge level={currentDifficulty} />
          )}
          {question.nclex_client_needs && (
            <span className="text-xs font-syne text-ink-3 bg-border/40 rounded px-1.5 py-0.5 capitalize">
              {question.nclex_client_needs.replace(/_/g, " ")}
            </span>
          )}
          {question.cjmm_skill && (
            <span className="text-xs font-syne text-ink-3 bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">
              {question.cjmm_skill.replace(/_/g, " ")}
            </span>
          )}
        </div>

        <p className="font-serif text-ink text-base leading-relaxed mb-6">{question.question}</p>

        <QuestionCard
          question={question}
          answer={ans}
          locked={!!locked[current]}
          onChange={handleChange}
        />

        {/* Confirm answer button */}
        {!locked[current] && (
          <button
            onClick={handleLock}
            disabled={!hasAnswer(ans, question)}
            className="mt-5 font-syne font-bold text-sm bg-ink text-white px-6 py-2.5 rounded-xl hover:bg-red transition-colors disabled:opacity-40"
          >
            {t("exam_page.confirm_answer")}
          </button>
        )}
        {locked[current] && (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="text-xs font-serif text-green flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> {t("exam_page.answer_recorded")}
              </div>
              <AIExplainButton questionId={question.id} questionText={question.question} />
              <FlagButton questionId={question.id} />
            </div>
            {showRationale && questionRationales[current] && (
              <RationalePanel
                rationales={questionRationales[current].rationales}
                keyTakeaway={questionRationales[current].key_takeaway}
                testTakingTip={questionRationales[current].test_taking_tip}
                selectedOption={answers[current]?.selected_option}
                selectedOptions={answers[current]?.selected_options}
                options={question.options}
              />
            )}
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-4">
        <button onClick={() => setCurrent(Math.max(0, current - 1))} disabled={current === 0}
          className="flex items-center gap-1 font-syne font-semibold text-sm px-4 py-2 rounded-lg border border-border hover:bg-surface transition-colors disabled:opacity-30">
          <ChevronLeft className="w-4 h-4" /> {t("exam_page.previous")}
        </button>
        <button onClick={() => setCurrent(Math.min(total - 1, current + 1))} disabled={current === total - 1}
          className="flex items-center gap-1 font-syne font-semibold text-sm px-4 py-2 rounded-lg border border-border hover:bg-surface transition-colors disabled:opacity-30">
          {t("exam_page.next")} <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ── Results view ───────────────────────────────────────────────────────────────

function CategoryBar({ label, pct, total }: { label: string; pct: number; total: number }) {
  const color = pct >= 75 ? "bg-green" : pct >= 60 ? "bg-amber-400" : "bg-red";
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-serif text-ink-2 truncate pr-2">{label}</span>
        <span className="text-xs font-syne font-bold text-ink flex-shrink-0">
          {pct}% <span className="text-ink-3 font-normal">({total})</span>
        </span>
      </div>
      <div className="h-1.5 bg-border rounded-full">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function AIExplainButton({ questionId, questionText }: { questionId?: string; questionText: string }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function fetchExplanation() {
    if (!questionId) {
      // Fallback: redirect to AI tutor
      const prompt = encodeURIComponent(`I need help understanding this NCLEX question:\n\n"${questionText}"\n\nExplain why the correct answer is right and what nursing concepts apply.`);
      window.open(`/ai-tutor?mode=tutor&prompt=${prompt}`, "_blank");
      return;
    }
    setOpen(true);
    if (explanation) return; // already fetched
    setLoading(true);
    setError("");
    try {
      const r = await api.post(`/exam/questions/${questionId}/explain`, {});
      setExplanation(r.data.explanation);
    } catch {
      setError(t("common.error"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        onClick={fetchExplanation}
        className="inline-flex items-center gap-2 text-xs font-syne font-bold border border-ink/30 text-ink px-3 py-1.5 rounded-lg hover:bg-ink hover:text-white transition-colors"
      >
        <Sparkles className="w-3.5 h-3.5" />
        {t("exam_page.ask_ai")}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-bg border border-border rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border flex-shrink-0">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-red" />
                <span className="font-syne font-bold text-sm text-ink">{t("exam_page.ai_explain_title")}</span>
              </div>
              <button onClick={() => setOpen(false)} className="text-ink-3 hover:text-ink transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto p-5 flex-1">
              <p className="font-serif text-sm text-ink-2 italic mb-4 border-l-2 border-border pl-3 leading-relaxed">
                {questionText.length > 200 ? questionText.slice(0, 200) + "…" : questionText}
              </p>

              {loading && (
                <div className="flex items-center gap-2 text-ink-3 font-serif text-sm py-4">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t("exam_page.ai_explain_loading")}
                </div>
              )}
              {error && <p className="text-red text-sm font-serif">{error}</p>}
              {explanation && (
                <div className="prose prose-sm max-w-none font-serif text-ink leading-relaxed">
                  <ReactMarkdown
                    components={{
                      h1: ({ children }) => <h2 className="font-syne font-bold text-base text-ink mt-4 mb-1">{children}</h2>,
                      h2: ({ children }) => <h3 className="font-syne font-bold text-sm text-ink mt-3 mb-1">{children}</h3>,
                      h3: ({ children }) => <h4 className="font-syne font-semibold text-sm text-ink mt-2 mb-0.5">{children}</h4>,
                      p: ({ children }) => <p className="text-sm leading-relaxed mb-2">{children}</p>,
                      strong: ({ children }) => <strong className="font-syne font-bold">{children}</strong>,
                      li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
                    }}
                  >
                    {explanation.replace(/\$\\rightarrow\$/g, "→").replace(/\$([^$]+)\$/g, "$1")}
                  </ReactMarkdown>
                </div>
              )}
            </div>

            <div className="px-5 py-4 border-t border-border flex items-center justify-between flex-shrink-0">
              <button
                type="button"
                onClick={() => window.open(`/ai-tutor?mode=tutor&prompt=${encodeURIComponent(`Help me understand this NCLEX question: "${questionText.slice(0, 300)}"`)}`,"_blank","noopener,noreferrer")}
                className="flex items-center gap-1.5 text-xs font-syne text-ink-3 hover:text-ink transition-colors"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                {t("exam_page.open_ai_tutor")}
              </button>
              <button
                onClick={() => setOpen(false)}
                className="font-syne font-bold text-sm px-4 py-2 rounded-xl bg-ink text-white hover:bg-red transition-colors"
              >
                {t("common.close")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const CATEGORY_LABELS: Record<string, string> = {
  safe_effective_care: "Safe & Effective Care Environment",
  safe_effective_care_environment: "Safe & Effective Care Environment",
  safety: "Safe & Effective Care Environment",
  health_promotion: "Health Promotion & Maintenance",
  health_promotion_and_maintenance: "Health Promotion & Maintenance",
  psychosocial: "Psychosocial Integrity",
  psychosocial_integrity: "Psychosocial Integrity",
  psychological: "Psychosocial Integrity",
  communication: "Psychosocial Integrity",
  basic_care: "Basic Care & Comfort",
  basic_care_and_comfort: "Basic Care & Comfort",
  pharmacological: "Pharmacological & Parenteral Therapies",
  pharmacological_therapies: "Pharmacological & Parenteral Therapies",
  reduction_risk: "Reduction of Risk Potential",
  reduction_of_risk: "Reduction of Risk Potential",
  reduction_of_risk_potential: "Reduction of Risk Potential",
  physiological_adaptation: "Physiological Adaptation",
  physiological: "Physiological Adaptation",
  physiological_integrity: "Physiological Adaptation",
};

function nclexLabel(raw: string, serverLabel?: string): string {
  if (serverLabel && !serverLabel.includes("_")) return serverLabel; // already human-readable from server
  return CATEGORY_LABELS[raw] ?? raw.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function ResultsView({ results, onRetry, onRetryWrong }: { results: Results; onRetry: () => void; onRetryWrong: (ids: string[]) => void }) {
  const t = useT();
  const [expandedQ, setExpandedQ] = useState<number | null>(null);
  const isNclex = results.mode_id?.includes("nclex");
  const hasCategories = Object.keys(results.nclex_category_breakdown || {}).length > 0;

  return (
    <div className="space-y-5">
      {/* Score card */}
      <div className={`rounded-xl p-6 text-center border ${results.passed ? "border-green/30 bg-green/5" : "border-red/20 bg-red/5"}`}>
        <div className={`font-syne font-black text-6xl mb-2 ${results.passed ? "text-green" : "text-red"}`}>
          {results.score_pct}%
        </div>
        <div className="font-syne font-bold text-lg text-ink mb-1">
          {results.passed ? t("exam_page.passed") : t("exam_page.not_passed")} — {results.mode}
        </div>
        <div className="font-serif text-sm text-ink-3 mb-4">{results.message}</div>
        <div className="flex flex-wrap items-center justify-center gap-4 text-sm font-syne">
          <span><strong className="text-green">{results.correct}</strong> {t("exam_page.stat_correct")}</span>
          <span><strong className="text-red">{results.wrong}</strong> {t("exam_page.stat_wrong")}</span>
          <span><strong className="text-ink">{results.time_taken_min}m</strong></span>
          <span className="text-ink-3">{t("exam_page.pass_threshold")} {results.pass_threshold}%</span>
          {results.cat_enabled && <span className="text-blue-600 font-bold">{t("exam_page.cat_adaptive")}</span>}
        </div>
      </div>

      {/* Demo upsell */}
      {results.mode_id === "nclex_demo" && (
        <div className="bg-ink text-white rounded-xl p-6">
          <div className="flex items-center gap-3 mb-3">
            <Gift className="w-5 h-5 text-amber-400 flex-shrink-0" />
            <span className="font-syne font-black text-base">{t("exam_page.demo_upsell_title")}</span>
          </div>
          <p className="font-serif text-sm text-white/70 mb-4">{t("exam_page.demo_upsell_body")}</p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href="/pricing"
              className="font-syne font-bold text-sm bg-white text-ink px-6 py-2.5 rounded-xl hover:bg-white/90 transition-colors text-center"
            >
              {t("exam_page.demo_upsell_cta")}
            </Link>
            <Link
              href="/nurses/nclex"
              className="font-syne text-sm text-white/60 hover:text-white transition-colors px-2 py-2.5 text-center"
            >
              {t("exam_page.demo_back_to_hub")}
            </Link>
          </div>
        </div>
      )}

      {/* NCLEX category breakdown */}
      {isNclex && hasCategories && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
            <Layers className="w-4 h-4" /> {t("exam_page.nclex_breakdown")}
          </h3>
          <div className="space-y-3">
            {Object.entries(results.nclex_category_breakdown)
              .sort((a, b) => a[1].pct - b[1].pct)
              .map(([key, c]) => (
                <CategoryBar key={key} label={nclexLabel(key, c.label)} pct={c.pct} total={c.total} />
              ))}
          </div>
          {results.weak_categories.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border">
              <div className="text-xs font-syne font-bold text-red mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> {t("exam_page.focus_areas")}
              </div>
              <div className="flex flex-wrap gap-2">
                {results.weak_categories.map(c => (
                  <Link
                    key={c.key}
                    href={`/nurses/nclex`}
                    className="text-xs font-syne px-2 py-1 rounded-lg bg-red/10 text-red border border-red/20 hover:bg-red/20 transition-colors"
                  >
                    {c.label} ({c.pct}%) — {t("nclex_hub.practice_cat")} →
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Wrong questions with AI tutor integration */}
      {results.wrong_questions.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="font-syne font-bold text-sm text-ink mb-4">
            {t("exam_page.to_review")} ({results.wrong_questions.length})
          </h3>
          <div className="space-y-3">
            {results.wrong_questions.map((q) => (
              <div key={q.index} className="border border-red/20 rounded-xl p-4 bg-red/5">
                <button
                  onClick={() => setExpandedQ(expandedQ === q.index ? null : q.index)}
                  className="w-full text-left"
                >
                  <p className="font-serif text-sm text-ink leading-relaxed mb-2">{q.question}</p>
                  <div className="flex flex-wrap items-center gap-3 text-xs font-syne">
                    {q.your_answer ? (
                      <span className="flex items-center gap-1 text-red">
                        <XCircle className="w-3 h-3" /> {t("exam_page.your_answer")} <strong>{String(q.your_answer)}</strong>
                      </span>
                    ) : (
                      <span className="text-ink-3 italic">{t("exam_page.not_answered")}</span>
                    )}
                    <span className="flex items-center gap-1 text-green">
                      <CheckCircle2 className="w-3 h-3" /> {t("exam_page.correct_answer")} <strong>{q.correct_answer}</strong>
                    </span>
                    {q.nclex_client_needs && (
                      <span className="text-ink-3 bg-border/40 rounded px-1.5 py-0.5">
                        {q.nclex_client_needs.replace(/_/g, " ")}
                      </span>
                    )}
                    <span className="text-ink-3 ml-auto">
                      {expandedQ === q.index ? t("exam_page.hide_details") : t("exam_page.show_details")}
                    </span>
                  </div>
                </button>

                {expandedQ === q.index && (
                  <div className="mt-3 pt-3 border-t border-red/20 space-y-3">
                    {/* Per-option rationales (review mode) */}
                    {q.rationales ? (
                      <RationalePanel
                        rationales={q.rationales}
                        keyTakeaway={q.key_takeaway}
                        testTakingTip={q.test_taking_tip}
                        selectedOption={typeof q.your_answer === "string" ? q.your_answer : undefined}
                        selectedOptions={Array.isArray(q.your_answer) ? q.your_answer : undefined}
                        options={q.options || {}}
                      />
                    ) : (
                      <>
                        {q.key_takeaway && (
                          <div className="flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2.5">
                            <Lightbulb className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                            <div>
                              <span className="font-syne font-bold text-xs text-amber-700 block mb-0.5">Key Takeaway</span>
                              <p className="font-serif text-xs text-amber-800 leading-relaxed">{q.key_takeaway}</p>
                            </div>
                          </div>
                        )}
                        {q.explanation && (
                          <div className="text-xs font-serif text-ink-2 leading-relaxed bg-ink/5 rounded-lg p-3 whitespace-pre-line">
                            {q.explanation}
                          </div>
                        )}
                      </>
                    )}
                    <div className="flex items-center gap-3 flex-wrap">
                      <AIExplainButton questionId={q.id} questionText={q.question} />
                      <FlagButton questionId={q.id} />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={onRetry}
          className="font-syne font-semibold text-sm px-6 py-2.5 rounded-xl bg-ink text-white hover:bg-red transition-colors"
        >
          {t("exam_page.try_again")}
        </button>
        {results.wrong_questions.length > 0 && (
          <button
            onClick={() => onRetryWrong(results.wrong_questions.map(q => q.id!).filter(Boolean))}
            className="font-syne font-semibold text-sm px-6 py-2.5 rounded-xl border border-red/40 text-red hover:bg-red/10 transition-colors flex items-center gap-2"
          >
            <XCircle className="w-4 h-4" />
            {t("exam_page.retry_wrong")} ({results.wrong_questions.length})
          </button>
        )}
        {isNclex && (
          <Link
            href="/nurses/nclex"
            className="font-syne font-semibold text-sm px-6 py-2.5 rounded-xl border border-border hover:bg-surface transition-colors flex items-center gap-2"
          >
            <BarChart3 className="w-4 h-4" /> {t("exam_page.nclex_hub")}
          </Link>
        )}
        <button
          onClick={() => window.print()}
          className="font-syne font-semibold text-sm px-4 py-2.5 rounded-xl border border-border hover:bg-surface transition-colors text-ink-3"
          title="Print results"
        >
          ⎙ {t("exam_page.print_results")}
        </button>
        <Link
          href="/dashboard"
          className="font-syne font-semibold text-sm px-6 py-2.5 rounded-xl border border-border hover:bg-surface transition-colors"
        >
          {t("common.back")}
        </Link>
      </div>
    </div>
  );
}

// ── Mode selector ──────────────────────────────────────────────────────────────

function ModeSelector({ onStart }: { onStart: (modeId: string) => Promise<void> }) {
  const t = useT();
  const [modes, setModes] = useState<{ id: string; name: string; description: string; questions: number; duration_min: number; locked: boolean; lock_reason: string | null }[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [history, setHistory] = useState<{ session_id: string; mode: string; started_at: string; score_pct: number; passed: boolean; total_questions: number; time_taken_min: number }[]>([]);

  useEffect(() => {
    Promise.all([examApi.getModes(), examApi.getHistory()])
      .then(([m, h]) => { setModes(m); setHistory(h); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-ink-3 font-serif">{t("common.loading")}</div>;

  return (
    <div className="space-y-6">
      <div className="bg-ink/5 border border-ink/10 rounded-xl p-4 flex items-center gap-3">
        <div className="text-2xl">🎓</div>
        <div>
          <div className="font-syne font-bold text-sm text-ink">{t("exam_page.nclex_promo_title")}</div>
          <div className="text-xs font-serif text-ink-3">{t("exam_page.nclex_promo_sub")}</div>
        </div>
        <Link href="/nurses/nclex" className="ml-auto font-syne font-bold text-xs bg-ink text-white px-4 py-2 rounded-lg hover:bg-red transition-colors whitespace-nowrap">
          {t("exam_page.nclex_hub_link")}
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {modes.map((mode) => (
          <div key={mode.id} className={`bg-surface border border-border rounded-xl p-4 flex flex-col gap-3 ${mode.locked ? "opacity-60" : ""}`}>
            <div>
              <div className="font-syne font-bold text-sm text-ink mb-1">{mode.name}</div>
              <div className="font-serif text-xs text-ink-3 leading-relaxed">{mode.description}</div>
            </div>
            <div className="text-xs font-syne text-ink-3 flex gap-3">
              <span>{mode.questions} {t("common.questions")}</span>
              <span>{mode.duration_min} {t("common.minutes")}</span>
            </div>
            {mode.locked ? (
              <div className="text-xs font-serif text-ink-3 italic">{mode.lock_reason}</div>
            ) : (
              <button
                onClick={() => { setStarting(mode.id); onStart(mode.id).finally(() => setStarting(null)); }}
                disabled={starting === mode.id}
                className="w-full py-2 font-syne font-bold text-sm rounded-lg bg-ink text-white hover:bg-red transition-colors disabled:opacity-50"
              >
                {starting === mode.id ? t("exam_page.starting") : t("exam_page.start_exam")}
              </button>
            )}
          </div>
        ))}
      </div>

      {history.length > 0 && (
        <div>
          <h2 className="font-syne font-bold text-sm text-ink mb-3">{t("exam_page.recent_sessions")}</h2>
          <div className="space-y-2">
            {history.slice(0, 5).map(s => (
              <div key={s.session_id} className="flex items-center gap-3 bg-surface border border-border rounded-xl px-4 py-3">
                <div className="flex-1 min-w-0">
                  <div className="font-syne font-semibold text-xs text-ink truncate">{s.mode}</div>
                  <div className="text-ink-3 font-serif text-xs">{new Date(s.started_at).toLocaleDateString()}</div>
                </div>
                <div className="text-right">
                  <div className={`font-syne font-bold text-sm ${s.passed ? "text-green" : "text-red"}`}>{s.score_pct}%</div>
                  <div className="text-ink-3 text-xs">{s.total_questions}Q</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main ───────────────────────────────────────────────────────────────────────

function ExamPageInner() {
  const t = useT();
  const searchParams = useSearchParams();
  const sessionParam = searchParams.get("session");
  const resultsParam = searchParams.get("results");

  const [view, setView] = useState<"modes" | "session" | "results">("modes");
  const [session, setSession] = useState<Session | null>(null);
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (sessionParam && resultsParam) {
      examApi.getResults(sessionParam)
        .then(r => { setResults(r); setView("results"); })
        .catch(() => setError(t("exam_page.err_results")));
    } else if (sessionParam) {
      examApi.getSession(sessionParam)
        .then(s => {
          if (s.status === "completed" || s.status === "expired") {
            // Session already finalized — go straight to results
            examApi.getResults(sessionParam)
              .then(r => { setResults(r); setView("results"); })
              .catch(() => setError(t("exam_page.err_results")));
          } else {
            setSession(s);
            setView("session");
          }
        })
        .catch(() => setError(t("exam_page.err_session")));
    }
  }, [sessionParam, resultsParam]);

  const handleStart = async (modeId: string) => {
    setError("");
    try {
      const sess = await examApi.createSession(modeId);
      setSession(sess);
      setView("session");
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? t("exam_page.err_start"));
    }
  };

  const handleRetryWrong = async (questionIds: string[]) => {
    if (!questionIds.length || !results) return;
    setError("");
    try {
      const sess = await examApi.createSession(results.mode_id, questionIds);
      setSession(sess);
      setResults(null);
      setView("session");
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? t("exam_page.err_start"));
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto">
      <div className="mb-5 flex items-center gap-3">
        {view !== "modes" ? (
          <button onClick={() => { setView("modes"); setSession(null); setResults(null); }} className="text-ink-3 hover:text-ink font-syne text-sm">
            {t("exam_page.back")}
          </button>
        ) : (
          <Link href="/dashboard" className="text-ink-3 hover:text-ink font-syne text-sm">{t("exam_page.back_dashboard")}</Link>
        )}
        <h1 className="font-syne font-black text-xl text-ink">{t("exam_page.title")}</h1>
      </div>

      {error && (
        <div className="mb-4 p-4 rounded-xl bg-red/5 border border-red/20 text-sm font-serif text-red">{error}</div>
      )}

      {view === "modes" && <ModeSelector onStart={handleStart} />}
      {view === "session" && session && (
        <ExamSession session={session} onFinish={res => { setResults(res); setView("results"); }} />
      )}
      {view === "results" && results && (
        <ResultsView
          results={results}
          onRetry={() => { setSession(null); setResults(null); setView("modes"); }}
          onRetryWrong={handleRetryWrong}
        />
      )}
    </div>
  );
}

export default function ExamPage() {
  return (
    <Suspense fallback={<div className="p-6 text-ink-3 font-serif">Loading…</div>}>
      <ExamPageInner />
    </Suspense>
  );
}
