"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import ReactMarkdown from "react-markdown";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, examApi } from "@/lib/api";
import { useT, useI18n } from "@/lib/i18n";
import {
  Clock, CheckCircle2, XCircle, BarChart3, MessageSquare,
  ChevronLeft, ChevronRight, AlertTriangle, Layers, Gift,
  Sparkles, X, Loader2, Flag, ChevronDown, ChevronUp, Lightbulb,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

type OptionRationale = { text: string; why: "correct" | "incorrect" };
type Rationales = Record<string, OptionRationale>;

type SourceRef = {
  name: string;
  url: string;
  type: "pubmed" | "textbook" | "regulatory" | "guideline";
  pmid?: string;
  journal?: string;
};

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

type ReviewQuestion = {
  index: number;
  id?: string;
  question: string;
  options?: Record<string, string>;
  your_answer: unknown;
  correct_answer: string;
  correct?: boolean | null;
  explanation?: string;
  rationales?: Rationales;
  key_takeaway?: string;
  test_taking_tip?: string;
  rationales_es?: Rationales;
  key_takeaway_es?: string;
  test_taking_tip_es?: string;
  explanation_es?: string;
  explanation_ar?: string;
  rationales_ar?: Rationales;
  key_takeaway_ar?: string;
  test_taking_tip_ar?: string;
  nclex_client_needs?: string;
  cjmm_skill?: string;
  source_refs?: SourceRef[];
};
type WrongQuestion = ReviewQuestion;

type Results = {
  session_id: string;
  mode: string;
  mode_id: string;
  total_questions: number;
  answered?: number;
  unanswered?: number;
  correct: number;
  wrong: number;
  score_pct: number;
  passed: boolean;
  pass_threshold: number;
  time_taken_min: number;
  cat_enabled: boolean;
  per_question: PerQuestion[];
  wrong_questions: WrongQuestion[];
  all_questions: ReviewQuestion[];
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
  correctAnswer,
}: {
  question: Question;
  answer: AnswerState;
  locked: boolean;
  onChange: (a: AnswerState) => void;
  correctAnswer?: string;
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
        const isCorrectKey = correctAnswer && key === correctAnswer;
        const isWrongSelected = locked && correctAnswer && isSelected && !isCorrectKey;
        const optClass = locked && correctAnswer
          ? isCorrectKey
            ? "border-green bg-green/10 cursor-default"
            : isWrongSelected
              ? "border-red bg-red/10 cursor-default opacity-90"
              : "border-border bg-surface cursor-default opacity-50"
          : isSelected
            ? "border-ink bg-ink/5"
            : "border-border hover:border-ink-3 bg-surface";
        const dotClass = locked && correctAnswer
          ? isCorrectKey
            ? "border-green bg-green text-white"
            : isWrongSelected
              ? "border-red bg-red text-white"
              : "border-ink-3 text-ink-3"
          : isSelected
            ? "border-ink bg-ink text-white"
            : "border-ink-3 text-ink-3";
        return (
          <button
            key={key}
            onClick={() => !locked && onChange({ ...answer, selected_option: key })}
            disabled={locked}
            className={`w-full text-left flex items-start gap-3 p-4 rounded-lg border-2 transition-colors disabled:cursor-default ${optClass}`}
          >
            <span className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 text-xs font-syne font-bold mt-0.5 ${dotClass}`}>{key}</span>
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
  explanation,
  rationalesEs,
  keyTakeawayEs,
  testTakingTipEs,
  explanationEs,
  explanationAr,
  rationalesAr,
  keyTakeawayAr,
  testTakingTipAr,
  lang,
  hasSpanish,
  hasArabic,
  onSetLang,
  selectedOption,
  selectedOptions,
  options,
  sourceRefs,
}: {
  rationales?: Rationales;
  keyTakeaway?: string;
  testTakingTip?: string;
  explanation?: string;
  rationalesEs?: Rationales;
  keyTakeawayEs?: string;
  testTakingTipEs?: string;
  explanationEs?: string;
  explanationAr?: string;
  rationalesAr?: Rationales;
  keyTakeawayAr?: string;
  testTakingTipAr?: string;
  lang: ReviewLang;
  hasSpanish: boolean;
  hasArabic: boolean;
  onSetLang: (l: ReviewLang) => void;
  selectedOption?: string;
  selectedOptions?: string[];
  options: Record<string, string>;
  sourceRefs?: SourceRef[];
}) {
  const [expanded, setExpanded] = useState(false);

  const activeRationales =
    lang === "es" && rationalesEs ? rationalesEs :
    lang === "ar" && rationalesAr ? rationalesAr :
    rationales;
  const activeKeyTakeaway =
    lang === "es" && keyTakeawayEs ? keyTakeawayEs :
    lang === "ar" && keyTakeawayAr ? keyTakeawayAr :
    keyTakeaway;
  const activeExplanation =
    lang === "es" && explanationEs ? explanationEs :
    lang === "ar" && explanationAr ? explanationAr :
    explanation;
  const activeTestTakingTip =
    lang === "es" && testTakingTipEs ? testTakingTipEs :
    lang === "ar" && testTakingTipAr ? testTakingTipAr :
    testTakingTip;

  if (!activeRationales && !activeKeyTakeaway && !activeExplanation) return null;

  const selected = selectedOption || (selectedOptions && selectedOptions[0]) || "";
  const selectedRationale = activeRationales?.[selected];
  const otherEntries = activeRationales
    ? Object.entries(activeRationales).filter(([k]) => k !== selected)
    : [];

  const isRTL = lang === "ar";

  // Build available language tabs based on what translations exist for this question
  const availableLangs: { value: ReviewLang; label: string }[] = [
    { value: "en", label: "🇺🇸 EN" },
    ...(hasSpanish ? [{ value: "es" as ReviewLang, label: "🇪🇸 ES" }] : []),
    ...(hasArabic  ? [{ value: "ar" as ReviewLang, label: "🇸🇦 AR" }] : []),
  ];
  const showLangTabs = availableLangs.length > 1;

  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden text-sm">
      {/* Language tabs — visible whenever translations exist */}
      {showLangTabs && (
        <div className="flex items-center gap-1 px-3 py-1.5 border-b border-border bg-surface-2">
          {availableLangs.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => onSetLang(value)}
              className={`text-[11px] font-syne font-semibold px-2 py-0.5 rounded transition-colors ${
                lang === value
                  ? "bg-gold/20 text-ink ring-1 ring-gold/40"
                  : "text-ink-3 hover:text-ink hover:bg-surface-3"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* Selected option rationale — always visible */}
      {selectedRationale && (
        <div className={`px-4 pt-4 pb-3 ${selectedRationale.why === "correct" ? "bg-green/5 border-b border-green/20" : "bg-red/5 border-b border-red/20"}`}
          dir={isRTL ? "rtl" : undefined}>
          <div className="flex items-center gap-2 mb-1.5">
            {selectedRationale.why === "correct"
              ? <CheckCircle2 className="w-4 h-4 text-green flex-shrink-0" />
              : <XCircle className="w-4 h-4 text-red flex-shrink-0" />}
            <span className="font-syne font-bold text-xs text-ink">
              {lang === "ar"
                ? `الخيار ${selected}: ${selectedRationale.why === "correct" ? "صحيح" : "خطأ"}`
                : lang === "es"
                ? `Opción ${selected}: ${selectedRationale.why === "correct" ? "Correcta" : "Incorrecta"}`
                : `Option ${selected}: ${selectedRationale.why === "correct" ? "Correct" : "Incorrect"}`}
            </span>
          </div>
          <p className="font-serif text-xs text-ink-2 leading-relaxed">{selectedRationale.text}</p>
        </div>
      )}

      {/* Key takeaway */}
      {activeKeyTakeaway && (
        <div className="px-4 py-3 bg-amber-50 border-b border-amber-100 flex items-start gap-2"
          dir={isRTL ? "rtl" : undefined}>
          <Lightbulb className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-syne font-bold text-xs text-amber-700 block mb-0.5">
              {lang === "ar" ? "النقطة الرئيسية" : lang === "es" ? "Punto Clave" : "Key Takeaway"}
            </span>
            <p className="font-serif text-xs text-amber-800 leading-relaxed">{activeKeyTakeaway}</p>
          </div>
        </div>
      )}

      {/* Explanation fallback — shown when per-option rationales are unavailable */}
      {!activeRationales && activeExplanation && (
        <div className="px-4 py-3 text-xs font-serif text-ink-2 leading-relaxed"
          dir={isRTL ? "rtl" : undefined}>
          {activeExplanation.replace(/\$\\rightarrow\$/g, "→").replace(/\$([^$]+)\$/g, "$1")}
        </div>
      )}

      {/* Other options — collapsible */}
      {otherEntries.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded(e => !e)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-syne font-semibold text-ink-3 hover:text-ink hover:bg-surface-2 transition-colors"
          >
            <span>
              {lang === "ar" ? `شرح الخيارات الأخرى (${otherEntries.length})` : lang === "es" ? `Explicar otras opciones (${otherEntries.length})` : `Explain other options (${otherEntries.length})`}
            </span>
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
              {activeTestTakingTip && (
                <div className="pt-2 border-t border-border">
                  <span className="font-syne font-bold text-xs text-ink-3 block mb-0.5">
                    {lang === "ar" ? "نصيحة للاختبار" : lang === "es" ? "Consejo para el Examen" : "Test-Taking Tip"}
                  </span>
                  <p className="font-serif text-xs text-ink-3 italic leading-relaxed">{activeTestTakingTip}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Sources */}
      {sourceRefs && sourceRefs.length > 0 && (
        <div className="px-4 py-3 border-t border-border bg-surface-2">
          <p className="font-syne font-bold text-[10px] uppercase tracking-wider text-ink-4 mb-2">
            {lang === "ar" ? "المصادر" : lang === "es" ? "Fuentes" : "Sources"}
          </p>
          <ul className="space-y-1">
            {sourceRefs.map((ref, i) => {
              const icon =
                ref.type === "pubmed" ? "🔬" :
                ref.type === "textbook" ? "📚" :
                "📋";
              return (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-[11px] mt-0.5 flex-shrink-0">{icon}</span>
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] font-serif text-blue-600 hover:text-blue-800 hover:underline leading-snug break-words"
                  >
                    {ref.name}
                    {ref.journal && (
                      <span className="text-ink-4 not-italic"> — {ref.journal}</span>
                    )}
                  </a>
                </li>
              );
            })}
          </ul>
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

// isPracticeMode: show rationale immediately after answering.
// Excluded: NCLEX timed simulations and Gulf Full Simulations (real exam conditions).
function isPracticeMode(modeId: string): boolean {
  if (["nclex_rn_75", "nclex_rn_85", "nclex_rn_145"].includes(modeId)) return false;
  if (modeId.endsWith("_full")) return false;  // Gulf Full Simulations
  return true;
}

type QuestionRationale = {
  rationales?: Rationales; key_takeaway?: string; test_taking_tip?: string;
  rationales_es?: Rationales; key_takeaway_es?: string; test_taking_tip_es?: string;
  explanation?: string; explanation_es?: string;
  explanation_ar?: string; rationales_ar?: Rationales; key_takeaway_ar?: string; test_taking_tip_ar?: string;
  source_refs?: SourceRef[];
  correct_answer?: string;
};

type ReviewLang = "en" | "es" | "ar";

function ExamSession({
  session,
  onFinish,
}: {
  session: Session;
  onFinish: (results: Results, bookmarks: Set<number>) => void;
}) {
  const t = useT();
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<number, AnswerState>>({});
  const [locked, setLocked] = useState<Record<number, boolean>>({});
  const [questionRationales, setQuestionRationales] = useState<Record<number, QuestionRationale>>({});
  const [submitting, setSubmitting] = useState(false);
  const [currentDifficulty, setCurrentDifficulty] = useState("medium");
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const [reviewLang, setReviewLang] = useState<ReviewLang>("en");
  const [bookmarked, setBookmarked] = useState<Set<number>>(new Set());
  const [timerWarning, setTimerWarning] = useState<string | null>(null);
  const timerWarned = useRef<Set<string>>(new Set());
  const showRationale = isPracticeMode(session.mode_id);
  const isGulfSession = session.mode_id.includes("snle") || session.mode_id.includes("dha") ||
    session.mode_id.includes("qchp") || session.mode_id.includes("omsb") ||
    session.mode_id.includes("nhra") || session.mode_id.includes("mohuae") ||
    session.mode_id.includes("haad");

  function setLang(l: ReviewLang) {
    setReviewLang(l);
  }

  function toggleBookmark(idx: number) {
    setBookmarked(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  }

  // Timer warning toasts (not shown in demo mode)
  useEffect(() => {
    if (session.mode_id === "nclex_demo") return;
    const endsMs = new Date(session.ends_at).getTime();
    const checkWarnings = () => {
      const secsLeft = Math.floor((endsMs - Date.now()) / 1000);
      if (secsLeft <= 1800 && secsLeft > 1790 && !timerWarned.current.has("30")) {
        timerWarned.current.add("30");
        setTimerWarning("30 minutes remaining");
        setTimeout(() => setTimerWarning(null), 5000);
      }
      if (secsLeft <= 600 && secsLeft > 590 && !timerWarned.current.has("10")) {
        timerWarned.current.add("10");
        setTimerWarning("10 minutes remaining — wrap up!");
        setTimeout(() => setTimerWarning(null), 6000);
      }
    };
    const id = setInterval(checkWarnings, 5000);
    return () => clearInterval(id);
  }, [session.ends_at]);

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
      if (res?.rationales || res?.key_takeaway || res?.explanation || res?.correct_answer) {
        setQuestionRationales(prev => ({
          ...prev,
          [idx]: {
            rationales: res.rationales, key_takeaway: res.key_takeaway, test_taking_tip: res.test_taking_tip,
            rationales_es: res.rationales_es, key_takeaway_es: res.key_takeaway_es,
            test_taking_tip_es: res.test_taking_tip_es, explanation: res.explanation, explanation_es: res.explanation_es,
            explanation_ar: res.explanation_ar, rationales_ar: res.rationales_ar, key_takeaway_ar: res.key_takeaway_ar, test_taking_tip_ar: res.test_taking_tip_ar,
            source_refs: res.source_refs || [],
            correct_answer: res.correct_answer,
          },
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
      onFinish(results, bookmarked);
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
      {/* Timer warning toast */}
      {timerWarning && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-amber-500 text-white font-syne font-bold text-sm px-5 py-3 rounded-xl shadow-lg flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <Clock className="w-4 h-4" />
          {timerWarning}
        </div>
      )}

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
          {session.mode_id !== "nclex_demo" && <Timer endsAt={session.ends_at} onExpire={handleExpire} />}
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

      {/* Progress dots — show for ≤75 questions; for longer exams the bar above is sufficient */}
      {total <= 75 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {session.questions.map((_, i) => (
            <button key={i} onClick={() => setCurrent(i)}
              className={`w-6 h-6 rounded text-[10px] font-syne font-bold transition-colors ${
                i === current ? "bg-ink text-white" :
                bookmarked.has(i) ? "bg-purple-500 text-white" :
                locked[i] ? "bg-green/80 text-white" :
                answers[i] ? "bg-amber-200 text-amber-800" :
                "bg-surface border border-border text-ink-3"
              }`}
            >{i + 1}</button>
          ))}
        </div>
      )}

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
          {/* Bookmark button */}
          <button
            onClick={() => toggleBookmark(current)}
            className={`ml-auto p-1 rounded transition-colors ${bookmarked.has(current) ? "text-purple-500" : "text-ink-3 hover:text-ink"}`}
            title={bookmarked.has(current) ? "Remove bookmark" : "Bookmark for review"}
          >
            <svg className="w-4 h-4" fill={bookmarked.has(current) ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
            </svg>
          </button>
        </div>

        <p className="font-serif text-ink text-base leading-relaxed mb-6">{question.question}</p>

        <QuestionCard
          question={question}
          answer={ans}
          locked={!!locked[current]}
          onChange={handleChange}
          correctAnswer={locked[current] ? questionRationales[current]?.correct_answer : undefined}
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
              <CommunityPassRate questionId={question.id} />
              <AIExplainButton questionId={question.id} questionText={question.question} selectedAnswer={ans.selected_option || (ans.selected_options?.[0])} />
              <FlagButton questionId={question.id} />
            </div>
            {showRationale && questionRationales[current] && (
              <RationalePanel
                rationales={questionRationales[current].rationales}
                keyTakeaway={questionRationales[current].key_takeaway}
                testTakingTip={questionRationales[current].test_taking_tip}
                explanation={questionRationales[current].explanation}
                rationalesEs={questionRationales[current].rationales_es}
                keyTakeawayEs={questionRationales[current].key_takeaway_es}
                testTakingTipEs={questionRationales[current].test_taking_tip_es}
                explanationEs={questionRationales[current].explanation_es}
                explanationAr={questionRationales[current].explanation_ar}
                rationalesAr={questionRationales[current].rationales_ar}
                keyTakeawayAr={questionRationales[current].key_takeaway_ar}
                testTakingTipAr={questionRationales[current].test_taking_tip_ar}
                lang={reviewLang}
                hasSpanish={!!(questionRationales[current].rationales_es || questionRationales[current].explanation_es)}
                hasArabic={!!(questionRationales[current].rationales_ar || questionRationales[current].explanation_ar)}
                onSetLang={setLang}
                selectedOption={answers[current]?.selected_option}
                selectedOptions={answers[current]?.selected_options}
                options={question.options}
                sourceRefs={questionRationales[current].source_refs}
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

function CommunityPassRate({ questionId }: { questionId?: string }) {
  const [data, setData] = useState<{ available: boolean; pass_rate_pct?: number; attempts?: number } | null>(null);

  useEffect(() => {
    if (!questionId) return;
    api.get(`/exam/questions/${questionId}/community`)
      .then(r => setData(r.data))
      .catch(() => {});
  }, [questionId]);

  if (!data?.available || data.pass_rate_pct == null) return null;

  const pct = data.pass_rate_pct;
  const isHard = pct < 50;
  return (
    <span className={`text-xs font-serif ${isHard ? "text-amber-600" : "text-ink-3"}`}>
      {pct}% get this right
      {isHard && " ← challenging"}
    </span>
  );
}

const FOLLOWUP_CHIPS = [
  { chip: "explain_differently", label: "Explain differently" },
  { chip: "why_not_distractor", label: "Why my answer?" },
  { chip: "mnemonic", label: "Give mnemonic" },
  { chip: "beginner", label: "For beginners" },
  { chip: "clinical_story", label: "Clinical story" },
] as const;

function AIExplainButton({
  questionId,
  questionText,
  selectedAnswer,
}: {
  questionId?: string;
  questionText: string;
  selectedAnswer?: string;
}) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [followupLoading, setFollowupLoading] = useState(false);
  const [followupText, setFollowupText] = useState<string | null>(null);
  const [activeChip, setActiveChip] = useState<string | null>(null);

  async function fetchFollowup(chip: string) {
    if (!questionId) return;
    setFollowupLoading(true);
    setActiveChip(chip);
    setFollowupText(null);
    try {
      const r = await api.post(`/exam/questions/${questionId}/followup`, {
        chip,
        selected_answer: selectedAnswer,
      });
      setFollowupText(r.data.explanation);
    } catch {
      setFollowupText("Could not load follow-up explanation. Please try again.");
    } finally {
      setFollowupLoading(false);
    }
  }

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
                <>
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

                  {/* Follow-up chips */}
                  <div className="mt-4 pt-3 border-t border-border">
                    <p className="font-syne font-semibold text-xs text-ink-3 mb-2">Still unclear? Ask another way:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {FOLLOWUP_CHIPS.map(c => (
                        <button
                          key={c.chip}
                          onClick={() => fetchFollowup(c.chip)}
                          disabled={followupLoading}
                          className={`text-xs font-syne font-semibold px-3 py-1.5 rounded-lg border transition-all ${
                            activeChip === c.chip
                              ? "border-red bg-red text-white"
                              : "border-border text-ink-3 hover:border-red hover:text-red"
                          }`}
                        >
                          {c.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Follow-up response */}
                  {followupLoading && (
                    <div className="flex items-center gap-2 text-ink-3 font-serif text-sm py-3 mt-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Thinking…
                    </div>
                  )}
                  {followupText && !followupLoading && (
                    <div className="mt-3 p-3 bg-surface-2 rounded-xl border border-border">
                      <div className="prose prose-sm max-w-none font-serif text-ink leading-relaxed">
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => <p className="text-sm leading-relaxed mb-2">{children}</p>,
                            strong: ({ children }) => <strong className="font-syne font-bold">{children}</strong>,
                            li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
                          }}
                        >
                          {followupText}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </>
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

function ResultsView({
  results, onRetry, onRetryWrong, bookmarkedIndices,
}: {
  results: Results;
  onRetry: () => void;
  onRetryWrong: (ids: string[]) => void;
  bookmarkedIndices?: Set<number>;
}) {
  const t = useT();
  const [expandedQ, setExpandedQ] = useState<number | null>(null);
  const [reviewTab, setReviewTab] = useState<"wrong" | "all" | "bookmarked">("wrong");
  const [reviewLang, setReviewLang] = useState<ReviewLang>("en");
  const isNclex = results.mode_id?.includes("nclex");
  const isGulf = results.mode_id?.includes("snle") || results.mode_id?.includes("dha") ||
    results.mode_id?.includes("qchp") || results.mode_id?.includes("omsb") ||
    results.mode_id?.includes("nhra") || results.mode_id?.includes("mohuae") ||
    results.mode_id?.includes("haad");
  const hasCategories = Object.keys(results.nclex_category_breakdown || {}).length > 0;

  function setLang(l: ReviewLang) {
    setReviewLang(l);
  }

  const allQs = results.all_questions || [];
  const wrongQs = results.wrong_questions || [];
  const bookmarkedQs = bookmarkedIndices
    ? allQs.filter(q => bookmarkedIndices.has(q.index))
    : [];

  const reviewList =
    reviewTab === "all" ? allQs :
    reviewTab === "bookmarked" ? bookmarkedQs :
    wrongQs;

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
          {(results.unanswered ?? 0) > 0 && (
            <span><strong className="text-ink-3">{results.unanswered}</strong> skipped</span>
          )}
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

      {/* Category breakdown — shows for NCLEX and Gulf exams (both use nclex_client_needs) */}
      {(isNclex || isGulf) && hasCategories && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="font-syne font-bold text-sm text-ink mb-4 flex items-center gap-2">
            <Layers className="w-4 h-4" /> {isGulf ? "Topic Breakdown" : t("exam_page.nclex_breakdown")}
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
                    href={isGulf ? `/nurses/gulf` : `/nurses/nclex`}
                    className="text-xs font-syne px-2 py-1 rounded-lg bg-red/10 text-red border border-red/20 hover:bg-red/20 transition-colors"
                  >
                    {c.label} ({c.pct}%) — Practice →
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Question Review Section with tabs */}
      {(wrongQs.length > 0 || allQs.length > 0) && (
        <div className="bg-surface border border-border rounded-xl p-5">
          {/* Tab bar */}
          <div className="flex gap-1 mb-4 bg-bg rounded-lg p-1">
            <button
              onClick={() => setReviewTab("wrong")}
              className={`flex-1 font-syne font-semibold text-xs px-3 py-1.5 rounded-md transition-colors ${reviewTab === "wrong" ? "bg-red text-white" : "text-ink-3 hover:text-ink"}`}
            >
              Wrong ({wrongQs.length})
            </button>
            <button
              onClick={() => setReviewTab("all")}
              className={`flex-1 font-syne font-semibold text-xs px-3 py-1.5 rounded-md transition-colors ${reviewTab === "all" ? "bg-ink text-white" : "text-ink-3 hover:text-ink"}`}
            >
              All ({allQs.length})
            </button>
            {bookmarkedQs.length > 0 && (
              <button
                onClick={() => setReviewTab("bookmarked")}
                className={`flex-1 font-syne font-semibold text-xs px-3 py-1.5 rounded-md transition-colors ${reviewTab === "bookmarked" ? "bg-purple-500 text-white" : "text-ink-3 hover:text-ink"}`}
              >
                Bookmarked ({bookmarkedQs.length})
              </button>
            )}
          </div>

          {reviewList.length === 0 ? (
            <p className="text-center text-sm font-serif text-ink-3 py-4">
              {reviewTab === "wrong" ? "All answers correct!" : "No questions to show."}
            </p>
          ) : (
            <div className="space-y-3">
              {reviewList.map((q) => {
                const isSkipped = q.correct === null || q.correct === undefined;
                const isCorrect = !isSkipped && q.correct === true;
                const borderColor = isSkipped ? "border-border" : isCorrect ? "border-green/20" : "border-red/20";
                const bgColor = isSkipped ? "bg-surface opacity-75" : isCorrect ? "bg-green/3" : "bg-red/5";
                return (
                  <div key={q.index} className={`border ${borderColor} rounded-xl p-4 ${bgColor}`}>
                    <button
                      onClick={() => setExpandedQ(expandedQ === q.index ? null : q.index)}
                      className="w-full text-left"
                    >
                      <div className="flex items-start gap-2 mb-2">
                        {isCorrect
                          ? <CheckCircle2 className="w-4 h-4 text-green flex-shrink-0 mt-0.5" />
                          : <XCircle className="w-4 h-4 text-red flex-shrink-0 mt-0.5" />}
                        <p className="font-serif text-sm text-ink leading-relaxed">{q.question}</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-xs font-syne pl-6">
                        {q.your_answer ? (
                          <span className={`flex items-center gap-1 ${isCorrect ? "text-green" : "text-red"}`}>
                            {t("exam_page.your_answer")} <strong>{String(q.your_answer)}</strong>
                          </span>
                        ) : (
                          <span className="text-ink-3 italic">{t("exam_page.not_answered")}</span>
                        )}
                        {!isCorrect && (
                          <span className="flex items-center gap-1 text-green">
                            <CheckCircle2 className="w-3 h-3" /> {t("exam_page.correct_answer")} <strong>{q.correct_answer}</strong>
                          </span>
                        )}
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
                      <div className="mt-3 pt-3 border-t border-border/40 space-y-3">
                        <RationalePanel
                          rationales={q.rationales}
                          keyTakeaway={q.key_takeaway}
                          testTakingTip={q.test_taking_tip}
                          explanation={q.explanation}
                          rationalesEs={q.rationales_es}
                          keyTakeawayEs={q.key_takeaway_es}
                          testTakingTipEs={q.test_taking_tip_es}
                          explanationEs={q.explanation_es}
                          explanationAr={q.explanation_ar}
                          rationalesAr={q.rationales_ar}
                          keyTakeawayAr={q.key_takeaway_ar}
                          testTakingTipAr={q.test_taking_tip_ar}
                          lang={reviewLang}
                          hasSpanish={!!(q.rationales_es || q.explanation_es)}
                          hasArabic={!!(q.rationales_ar || q.explanation_ar)}
                          onSetLang={setLang}
                          selectedOption={typeof q.your_answer === "string" ? q.your_answer : undefined}
                          selectedOptions={Array.isArray(q.your_answer) ? q.your_answer : undefined}
                          options={q.options || {}}
                          sourceRefs={q.source_refs}
                        />
                        <div className="flex items-center gap-3 flex-wrap">
                          <AIExplainButton questionId={q.id} questionText={q.question} />
                          <FlagButton questionId={q.id} />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
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
  const [modes, setModes] = useState<{ id: string; name: string; description: string; questions: number; duration_min: number; locked: boolean; lock_reason: string | null; gulf?: boolean }[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [history, setHistory] = useState<{ session_id: string; mode: string; started_at: string; score_pct: number; passed: boolean; total_questions: number; time_taken_min: number }[]>([]);

  useEffect(() => {
    Promise.all([examApi.getModes(), examApi.getHistory()])
      .then(([m, h]) => { setModes(m); setHistory(h); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-ink-3 font-serif">{t("common.loading")}</div>;

  // Separate gulf modes from general modes
  const gulfModes = modes.filter(m => m.gulf);
  const generalModes = modes.filter(m => !m.gulf);

  return (
    <div className="space-y-6">
      {/* Nursing Hub promos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-ink/5 border border-ink/10 rounded-xl p-4 flex items-center gap-3">
          <div className="text-2xl">🎓</div>
          <div className="flex-1 min-w-0">
            <div className="font-syne font-bold text-sm text-ink">{t("exam_page.nclex_promo_title")}</div>
            <div className="text-xs font-serif text-ink-3">{t("exam_page.nclex_promo_sub")}</div>
          </div>
          <Link href="/nurses/nclex" className="ml-auto font-syne font-bold text-xs bg-ink text-white px-3 py-2 rounded-lg hover:bg-red transition-colors whitespace-nowrap flex-shrink-0">
            {t("exam_page.nclex_hub_link")}
          </Link>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
          <div className="text-2xl">🌍</div>
          <div className="flex-1 min-w-0">
            <div className="font-syne font-bold text-sm text-ink">Gulf Prometric? Use the Gulf Hub</div>
            <div className="text-xs font-serif text-ink-3">SNLE · DHA · QCHP · OMSB · NHRA · HAAD</div>
          </div>
          <Link href="/nurses/gulf" className="ml-auto font-syne font-bold text-xs bg-amber-700 text-white px-3 py-2 rounded-lg hover:bg-amber-800 transition-colors whitespace-nowrap flex-shrink-0">
            Gulf Hub →
          </Link>
        </div>
      </div>

      {/* General exam modes */}
      <div>
        <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-3">General Practice</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {generalModes.map((mode) => (
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
      </div>

      {/* Gulf modes — quick access */}
      {gulfModes.length > 0 && (() => {
        const unlockedGulf = gulfModes.filter(m => !m.locked);
        const allLocked = unlockedGulf.length === 0;
        if (allLocked) {
          return (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-start gap-4">
              <div className="text-3xl flex-shrink-0">🌍</div>
              <div className="flex-1">
                <h3 className="font-syne font-black text-sm text-ink mb-1">Gulf Prometric Exams</h3>
                <p className="font-serif text-xs text-ink-3 mb-3">
                  SNLE, DHA, QCHP, OMSB, NHRA, MOH UAE, HAAD — practice and full simulations (40–200Q).
                </p>
                <p className="font-serif text-xs text-amber-700 mb-3">
                  Gulf Bundle or Pro subscription required.
                </p>
                <Link href="/pricing" className="inline-block font-syne font-bold text-xs bg-amber-700 text-white px-4 py-2 rounded-lg hover:bg-amber-800 transition-colors">
                  Upgrade to unlock →
                </Link>
              </div>
            </div>
          );
        }
        return (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider">Gulf Prometric</h2>
              <Link href="/nurses/gulf" className="text-xs font-syne text-ink-3 hover:text-ink transition-colors">Full Gulf Hub →</Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {unlockedGulf.map((mode) => (
                <div key={mode.id} className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-3">
                  <div>
                    <div className="font-syne font-bold text-sm text-ink mb-1">{mode.name}</div>
                    <div className="font-serif text-xs text-ink-3 leading-relaxed">{mode.description}</div>
                  </div>
                  <div className="text-xs font-syne text-ink-3 flex gap-3">
                    <span>{mode.questions} {t("common.questions")}</span>
                    <span>{mode.duration_min} {t("common.minutes")}</span>
                  </div>
                  <button
                    onClick={() => { setStarting(mode.id); onStart(mode.id).finally(() => setStarting(null)); }}
                    disabled={starting === mode.id}
                    className="w-full py-2 font-syne font-bold text-sm rounded-lg bg-ink text-white hover:bg-red transition-colors disabled:opacity-50"
                  >
                    {starting === mode.id ? t("exam_page.starting") : t("exam_page.start_exam")}
                  </button>
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {history.length > 0 && (
        <div>
          <h2 className="font-syne font-bold text-sm text-ink mb-3">{t("exam_page.recent_sessions")}</h2>
          <div className="space-y-2">
            {history.slice(0, 5).map(s => (
              <Link
                key={s.session_id}
                href={`/exam?session=${s.session_id}&results=1`}
                className="flex items-center gap-3 bg-surface border border-border rounded-xl px-4 py-3 hover:border-ink-3 hover:bg-surface-2 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-syne font-semibold text-xs text-ink truncate">{s.mode}</div>
                  <div className="text-ink-3 font-serif text-xs">{new Date(s.started_at).toLocaleDateString()}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className={`font-syne font-bold text-sm ${s.passed ? "text-green" : "text-red"}`}>{s.score_pct}%</div>
                  <div className="text-ink-3 text-xs">{s.total_questions}Q · View →</div>
                </div>
              </Link>
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
  const [sessionBookmarks, setSessionBookmarks] = useState<Set<number>>(new Set());
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
        <ExamSession
          session={session}
          onFinish={(res, bookmarks) => { setResults(res); setSessionBookmarks(bookmarks); setView("results"); }}
        />
      )}
      {view === "results" && results && (
        <ResultsView
          results={results}
          onRetry={() => { setSession(null); setResults(null); setSessionBookmarks(new Set()); setView("modes"); }}
          onRetryWrong={handleRetryWrong}
          bookmarkedIndices={sessionBookmarks}
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
