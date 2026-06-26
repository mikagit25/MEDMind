"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { contentApi, progressApi, simulationApi } from "@/lib/api";
import { useT, useI18n } from "@/lib/i18n";
import Link from "next/link";

type Presentation = {
  chief_complaint?: string;
  history?: string;
  vitals?: Record<string, string>;
  [key: string]: unknown;
};

type Case = {
  id: string;
  title: string;
  presentation: string;
  difficulty: string;
  specialty?: string;
  steps?: Step[] | null;
  initial_step_id?: string | null;
  max_score?: number;
};

function parsePres(raw: string): Presentation {
  try { return JSON.parse(raw); } catch { return { chief_complaint: raw }; }
}

type Step = {
  id: string;
  title: string;
  description: string;
  choices: Choice[];
};

type Choice = {
  id: string;
  text: string;
  next_step: string | null;
  outcome: string;
  score_delta: number;
};

type CaseDetail = Case & {
  vitals?: Record<string, string | number>;
  diagnosis?: string;
  differential_diagnosis?: string[];
  management?: string[];
  teaching_points?: string[];
};

type FSMSession = {
  session_id: string;
  current_step: Step;
  score: number;
  status: string;
  case_title: string;
};

type CompletedResult = {
  status: "completed";
  score: number;
  max_score: number;
  outcome: string;
  debrief_pending: boolean;
};

const DIFF_STYLE: Record<string, string> = {
  beginner: "bg-green-light text-green-2",
  easy: "bg-green-light text-green-2",
  medium: "bg-amber-light text-amber-2",
  intermediate: "bg-amber-light text-amber-2",
  advanced: "bg-red-light text-red",
  hard: "bg-red-light text-red",
};

const DIFF_ICON: Record<string, string> = {
  beginner: "●", easy: "●", medium: "●●", intermediate: "●●", advanced: "●●●", hard: "●●●",
};

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = Math.round((score / max) * 100);
  const color = pct >= 80 ? "bg-green-2" : pct >= 50 ? "bg-amber-2" : "bg-red";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-surface-2 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-syne font-bold text-sm text-ink w-16 text-right">{score}/{max}</span>
    </div>
  );
}

function CasesInner() {
  const t = useT();
  const { locale } = useI18n();
  const searchParams = useSearchParams();

  const [cases, setCases] = useState<Case[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [search, setSearch] = useState("");
  const [diffFilter, setDiffFilter] = useState("");
  const [specialtyFilter, setSpecialtyFilter] = useState("");
  const [specialties, setSpecialties] = useState<string[]>([]);

  const [selected, setSelected] = useState<CaseDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // FSM state
  const [fsmSession, setFsmSession] = useState<FSMSession | null>(null);
  const [fsmCompleted, setFsmCompleted] = useState<CompletedResult | null>(null);
  const [fsmDebriefing, setFsmDebriefing] = useState<string | null>(null);
  const [chosenId, setChosenId] = useState<string | null>(null);
  const [choiceResult, setChoiceResult] = useState<{ outcome: string; score_delta: number } | null>(null);
  const [fsmLoading, setFsmLoading] = useState(false);

  // Legacy mode (no FSM steps)
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<any>(null);
  const [submitLoading, setSubmitLoading] = useState(false);

  const loadAll = useCallback(async () => {
    setLoadingList(true);
    try {
      const res = await contentApi.getAllCases({ locale, limit: 300 });
      setCases(res ?? []);
      // Collect unique specialties
      const specs = Array.from(new Set((res ?? []).map((c: Case) => c.specialty).filter(Boolean))) as string[];
      setSpecialties(specs.sort());
    } finally {
      setLoadingList(false);
    }
  }, [locale]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // Direct link from module page
  useEffect(() => {
    const cid = searchParams.get("case");
    if (cid) openCase(cid);
  }, [searchParams]);

  const openCase = async (caseId: string) => {
    setLoadingDetail(true);
    setSelected(null);
    setFsmSession(null);
    setFsmCompleted(null);
    setFsmDebriefing(null);
    setChosenId(null);
    setChoiceResult(null);
    setAnswer("");
    setFeedback(null);
    try {
      const res = await contentApi.getCase(caseId, locale);
      setSelected(res);
    } finally {
      setLoadingDetail(false);
    }
  };

  const startFSM = async () => {
    if (!selected?.steps?.length) return;
    setFsmLoading(true);
    try {
      const res = await simulationApi.startCase(selected.id);
      setFsmSession(res);
      setFsmCompleted(null);
      setChosenId(null);
      setChoiceResult(null);
    } finally {
      setFsmLoading(false);
    }
  };

  const makeChoice = async (choiceId: string) => {
    if (!fsmSession || chosenId) return;
    setChosenId(choiceId);
    const currentChoice = fsmSession.current_step?.choices?.find(c => c.id === choiceId);
    if (currentChoice) {
      setChoiceResult({ outcome: currentChoice.outcome, score_delta: currentChoice.score_delta });
    }
  };

  const nextStep = async () => {
    if (!fsmSession || !chosenId) return;
    setFsmLoading(true);
    try {
      const res = await simulationApi.makeChoice(fsmSession.session_id, chosenId);
      if (res.status === "completed") {
        setFsmCompleted(res as CompletedResult);
        setFsmSession(null);
        // Poll for debrief
        pollDebrief(fsmSession.session_id);
      } else {
        setFsmSession(prev => prev ? { ...prev, current_step: res.next_step, score: res.score } : null);
        setChosenId(null);
        setChoiceResult(null);
      }
    } finally {
      setFsmLoading(false);
    }
  };

  const pollDebrief = async (sessionId: string) => {
    for (let i = 0; i < 12; i++) {
      await new Promise(r => setTimeout(r, 3000));
      try {
        const sess = await simulationApi.getSession(sessionId);
        if (sess?.debriefing?.text) {
          setFsmDebriefing(sess.debriefing.text);
          return;
        }
      } catch {}
    }
  };

  const submitLegacy = async () => {
    if (!answer.trim() || !selected) return;
    setSubmitLoading(true);
    try {
      const res = await progressApi.completeCase(selected.id, answer);
      setFeedback(res);
    } catch {
      setFeedback({ correct: false, explanation: "Could not evaluate answer." });
    } finally {
      setSubmitLoading(false);
    }
  };

  const backToList = () => {
    setSelected(null);
    setFsmSession(null);
    setFsmCompleted(null);
    setFsmDebriefing(null);
    setChosenId(null);
    setChoiceResult(null);
    setAnswer("");
    setFeedback(null);
  };

  // Filtered list
  const filtered = cases.filter(c => {
    if (diffFilter && c.difficulty !== diffFilter) return false;
    if (specialtyFilter && c.specialty !== specialtyFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      const pres = parsePres(c.presentation ?? "");
      const presText = (pres.chief_complaint ?? "") + " " + (pres.history ?? "");
      if (!c.title.toLowerCase().includes(q) && !presText.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  // ── Case detail / FSM view ────────────────────────────────────────────────
  if (loadingDetail) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="font-syne text-ink-3 text-sm animate-pulse">{t("cases.loading") as string || "Loading…"}</div>
      </div>
    );
  }

  if (selected) {
    const hasFSM = Array.isArray(selected.steps) && selected.steps.length > 0;

    return (
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 max-w-3xl mx-auto w-full">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button onClick={backToList} className="text-ink-3 hover:text-ink transition-colors font-syne text-sm">
            ← {t("cases.back") as string || "Back"}
          </button>
          <span className={`text-xs font-syne font-bold px-2 py-0.5 rounded-full ${DIFF_STYLE[selected.difficulty] ?? "bg-surface-2 text-ink-3"}`}>
            {DIFF_ICON[selected.difficulty]} {selected.difficulty}
          </span>
          {selected.specialty && (
            <span className="text-xs text-ink-3 font-syne">{selected.specialty}</span>
          )}
        </div>

        <h1 className="font-syne font-black text-xl sm:text-2xl text-ink mb-4">{selected.title}</h1>

        {/* Presentation */}
        <div className="bg-surface border border-border rounded-lg p-4 mb-4">
          <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-2">
            {t("cases.presentation") as string || "Presentation"}
          </div>
          {(() => {
            const p = parsePres(selected.presentation);
            return (
              <div className="space-y-2 text-sm text-ink leading-relaxed">
                {p.chief_complaint && <p>{p.chief_complaint}</p>}
                {p.history && <p className="text-ink-2">{p.history}</p>}
              </div>
            );
          })()}
        </div>

        {/* Vitals */}
        {selected.vitals && Object.keys(selected.vitals).length > 0 && (
          <div className="bg-bg border border-border rounded-lg p-3 mb-4 flex flex-wrap gap-3">
            {Object.entries(selected.vitals).map(([k, v]) => (
              <div key={k} className="text-xs">
                <span className="font-syne font-bold text-ink-2">{k}: </span>
                <span className="text-ink">{v}</span>
              </div>
            ))}
          </div>
        )}

        {/* ── FSM mode ──────────────────────────────────────────────────────── */}
        {hasFSM && !fsmSession && !fsmCompleted && (
          <div className="space-y-4">
            {selected.differential_diagnosis?.length ? (
              <div className="bg-surface border border-border rounded-lg p-4">
                <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-2">
                  {t("cases.differentials") as string || "Differential Diagnosis"}
                </div>
                <ul className="space-y-1">
                  {selected.differential_diagnosis.map((d, i) => (
                    <li key={i} className="text-sm text-ink-2 flex items-start gap-2">
                      <span className="text-ink-3 mt-0.5">·</span>{d}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <button
              onClick={startFSM}
              disabled={fsmLoading}
              className="w-full bg-ink text-white font-syne font-bold py-3 rounded-lg hover:bg-red transition-colors disabled:opacity-50"
            >
              {fsmLoading ? "…" : (t("cases.start_case") as string || "▶ Start Interactive Case")}
            </button>
          </div>
        )}

        {/* FSM active */}
        {fsmSession && (
          <div className="space-y-4">
            <ScoreBar score={fsmSession.score} max={selected.max_score ?? 100} />

            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-1">
                {fsmSession.current_step.title}
              </div>
              <p className="text-ink text-sm leading-relaxed mb-5">
                {fsmSession.current_step.description}
              </p>

              <div className="space-y-2">
                {fsmSession.current_step.choices.map(choice => {
                  const isChosen = chosenId === choice.id;
                  const isCorrect = isChosen && choice.score_delta > 10;
                  const isWrong = isChosen && choice.score_delta <= 0;
                  const isNeutral = isChosen && choice.score_delta > 0 && choice.score_delta <= 10;
                  return (
                    <button
                      key={choice.id}
                      onClick={() => makeChoice(choice.id)}
                      disabled={!!chosenId}
                      className={`w-full text-left px-4 py-3 rounded-lg border text-sm font-syne transition-all
                        ${!chosenId ? "border-border bg-bg hover:border-ink hover:bg-surface-2 cursor-pointer" : "cursor-default"}
                        ${isCorrect ? "border-green-2 bg-green-light text-ink" : ""}
                        ${isWrong ? "border-red bg-red-light text-ink" : ""}
                        ${isNeutral ? "border-amber-2 bg-amber-light text-ink" : ""}
                        ${!isChosen && chosenId ? "opacity-40" : ""}
                      `}
                    >
                      <div className="flex items-start gap-3">
                        <span className={`w-5 h-5 rounded-full border flex-shrink-0 flex items-center justify-center text-xs font-bold mt-0.5
                          ${isCorrect ? "border-green-2 bg-green-2 text-white" : ""}
                          ${isWrong ? "border-red bg-red text-white" : ""}
                          ${isNeutral ? "border-amber-2 bg-amber-2 text-white" : ""}
                          ${!isChosen ? "border-border-2" : ""}
                        `}>
                          {isCorrect ? "✓" : isWrong ? "✗" : isNeutral ? "~" : ""}
                        </span>
                        <span>{choice.text}</span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {choiceResult && (
                <div className={`mt-4 p-3 rounded-lg text-sm ${
                  choiceResult.score_delta > 10 ? "bg-green-light text-ink border border-green-2/30" :
                  choiceResult.score_delta <= 0 ? "bg-red-light text-ink border border-red/30" :
                  "bg-amber-light text-ink border border-amber-2/30"
                }`}>
                  <span className="font-syne font-bold mr-1">
                    {choiceResult.score_delta > 0 ? `+${choiceResult.score_delta}` : choiceResult.score_delta} pts —
                  </span>
                  {choiceResult.outcome}
                </div>
              )}

              {chosenId && (
                <button
                  onClick={nextStep}
                  disabled={fsmLoading}
                  className="mt-4 w-full bg-ink text-white font-syne font-bold py-2.5 rounded-lg hover:bg-red transition-colors disabled:opacity-50"
                >
                  {fsmLoading ? "…" : (t("cases.next_step") as string || "Next Step →")}
                </button>
              )}
            </div>
          </div>
        )}

        {/* FSM completed */}
        {fsmCompleted && (
          <div className="space-y-4">
            <div className={`rounded-xl border p-6 text-center ${
              fsmCompleted.score >= fsmCompleted.max_score * 0.8 ? "border-green-2 bg-green-light" :
              fsmCompleted.score >= fsmCompleted.max_score * 0.5 ? "border-amber-2 bg-amber-light" :
              "border-red bg-red-light"
            }`}>
              <div className="text-4xl mb-3">
                {fsmCompleted.score >= fsmCompleted.max_score * 0.8 ? "🏆" :
                 fsmCompleted.score >= fsmCompleted.max_score * 0.5 ? "📊" : "📚"}
              </div>
              <div className="font-syne font-black text-3xl text-ink mb-1">
                {fsmCompleted.score}/{fsmCompleted.max_score}
              </div>
              <div className="font-syne text-sm text-ink-2 mb-2">
                {Math.round((fsmCompleted.score / fsmCompleted.max_score) * 100)}%
              </div>
              <p className="text-sm text-ink-2">{fsmCompleted.outcome}</p>
            </div>

            {/* Teaching points */}
            {selected.teaching_points?.length ? (
              <div className="bg-surface border border-border rounded-lg p-4">
                <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">
                  {t("cases.teaching_points") as string || "Teaching Points"}
                </div>
                <ul className="space-y-2">
                  {selected.teaching_points.map((pt, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-ink">
                      <span className="text-green-2 mt-0.5 flex-shrink-0">✓</span>{pt}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* AI Debrief */}
            <div className="bg-surface border border-border rounded-lg p-4">
              <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">
                AI Debrief
              </div>
              {fsmDebriefing ? (
                <div className="text-sm text-ink leading-relaxed whitespace-pre-line">{fsmDebriefing}</div>
              ) : (
                <div className="text-sm text-ink-3 animate-pulse">Generating debrief…</div>
              )}
            </div>

            <div className="flex gap-3">
              <button onClick={startFSM} className="flex-1 border border-border-2 text-ink-2 font-syne font-semibold py-2.5 rounded-lg hover:border-ink hover:text-ink transition-colors text-sm">
                {t("cases.retry") as string || "Try Again"}
              </button>
              <button onClick={backToList} className="flex-1 bg-ink text-white font-syne font-bold py-2.5 rounded-lg hover:bg-red transition-colors text-sm">
                {t("cases.next_case") as string || "Next Case"}
              </button>
            </div>
          </div>
        )}

        {/* ── Legacy mode (no FSM steps) ─────────────────────────────────── */}
        {!hasFSM && !feedback && (
          <div className="space-y-4">
            {selected.differential_diagnosis?.length ? (
              <div className="bg-surface border border-border rounded-lg p-4">
                <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-2">
                  {t("cases.differentials") as string || "Differential Diagnosis"}
                </div>
                <ul className="space-y-1">
                  {selected.differential_diagnosis.map((d, i) => (
                    <li key={i} className="text-sm text-ink-2 flex items-start gap-2">
                      <span className="text-ink-3 mt-0.5">·</span>{d}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div>
              <div className="font-syne font-bold text-sm text-ink mb-2">
                {t("cases.your_assessment") as string || "Your diagnosis & management plan:"}
              </div>
              <textarea
                value={answer}
                onChange={e => setAnswer(e.target.value)}
                rows={5}
                className="w-full px-3 py-2 rounded-lg border border-border bg-bg text-ink text-sm focus:outline-none focus:border-ink resize-none"
                placeholder={t("cases.answer_placeholder") as string || "Write your clinical assessment…"}
              />
              <button
                onClick={submitLegacy}
                disabled={submitLoading || !answer.trim()}
                className="mt-3 w-full bg-ink text-white font-syne font-bold py-3 rounded-lg hover:bg-red transition-colors disabled:opacity-40"
              >
                {submitLoading ? "…" : (t("cases.submit") as string || "Submit")}
              </button>
            </div>
          </div>
        )}

        {!hasFSM && feedback && (
          <div className={`rounded-xl border p-5 ${feedback.correct ? "border-green-2 bg-green-light" : "border-border bg-surface"}`}>
            <div className={`font-syne font-bold text-base mb-2 ${feedback.correct ? "text-green-2" : "text-ink"}`}>
              {feedback.correct ? "✓ " : ""}{feedback.correct ? (t("cases.correct") as string || "Correct!") : (t("cases.review") as string || "Review:")}
            </div>
            <p className="text-sm text-ink leading-relaxed">{feedback.explanation}</p>
            {feedback.xp_gained > 0 && (
              <div className="font-syne font-semibold text-xs text-amber-2 mt-2">+{feedback.xp_gained} XP</div>
            )}
            <button onClick={backToList} className="mt-4 w-full bg-ink text-white font-syne font-bold py-2.5 rounded-lg hover:bg-red transition-colors text-sm">
              {t("cases.next_case") as string || "Next Case"}
            </button>
          </div>
        )}

        {/* Management & teaching points for legacy */}
        {!hasFSM && selected.management?.length && !feedback && (
          <details className="mt-4">
            <summary className="font-syne text-sm text-ink-3 cursor-pointer hover:text-ink">Show answer</summary>
            <div className="mt-3 bg-surface border border-border rounded-lg p-4 space-y-3">
              <div>
                <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-1">Management</div>
                <ul className="space-y-1">
                  {selected.management.map((m, i) => (
                    <li key={i} className="text-sm text-ink flex items-start gap-2">
                      <span className="text-green-2 mt-0.5 flex-shrink-0">→</span>{m}
                    </li>
                  ))}
                </ul>
              </div>
              {selected.teaching_points?.length ? (
                <div>
                  <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-1">Teaching Points</div>
                  <ul className="space-y-1">
                    {selected.teaching_points.map((pt, i) => (
                      <li key={i} className="text-sm text-ink flex items-start gap-2">
                        <span className="text-amber-2 mt-0.5 flex-shrink-0">✦</span>{pt}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </details>
        )}

        {/* Virtual patient link */}
        <div className="mt-6 p-4 bg-surface border border-border rounded-lg flex items-center justify-between">
          <div>
            <div className="font-syne font-bold text-sm text-ink">Virtual Patient Mode</div>
            <div className="text-xs text-ink-3 mt-0.5">Practice history-taking with an AI patient</div>
          </div>
          <Link href="/simulation" className="font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors">
            Start
          </Link>
        </div>
      </div>
    );
  }

  // ── Case list ─────────────────────────────────────────────────────────────
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 max-w-5xl mx-auto w-full">
      <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("cases.title") as string || "Clinical Cases"}</h1>
          <p className="text-ink-3 text-sm mt-1">{filtered.length} {t("cases.subtitle") as string || "cases"}</p>
        </div>
        <Link href="/simulation"
          className="font-syne font-semibold text-sm border border-border-2 text-ink-2 px-4 py-2 rounded-lg hover:border-ink hover:text-ink transition-colors">
          🤖 Virtual Patient
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={t("cases.search") as string || "Search cases…"}
          className="flex-1 min-w-48 px-3 py-2 rounded-lg border border-border bg-surface text-ink text-sm focus:outline-none focus:border-ink"
        />
        <select
          value={diffFilter}
          onChange={e => setDiffFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-border bg-surface text-ink text-sm focus:outline-none focus:border-ink"
        >
          <option value="">{t("cases.all_difficulties") as string || "All levels"}</option>
          {["beginner","intermediate","advanced"].map(d => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <select
          value={specialtyFilter}
          onChange={e => setSpecialtyFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-border bg-surface text-ink text-sm focus:outline-none focus:border-ink max-w-xs"
        >
          <option value="">{t("cases.all_specialties") as string || "All specialties"}</option>
          {specialties.map(s => (
            <option key={s} value={s}>{s.length > 40 ? s.slice(0, 38) + "…" : s}</option>
          ))}
        </select>
      </div>

      {loadingList ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="bg-surface border border-border rounded-xl p-5 animate-pulse h-32" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-4xl mb-3">🩺</div>
          <div className="font-syne font-bold text-ink mb-1">{t("cases.empty_title") as string || "No cases yet"}</div>
          <p className="text-sm text-ink-3">{t("cases.empty_desc") as string || "Cases are being generated for all modules."}</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map(c => (
            <button
              key={c.id}
              onClick={() => openCase(c.id)}
              className="text-left bg-surface border border-border rounded-xl p-5 hover:border-ink hover:shadow-sm transition-all group"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs font-syne font-bold px-2 py-0.5 rounded-full ${DIFF_STYLE[c.difficulty] ?? "bg-surface-2 text-ink-3"}`}>
                  {DIFF_ICON[c.difficulty]} {c.difficulty}
                </span>
                {Array.isArray(c.steps) && c.steps.length > 0 && (
                  <span className="text-xs font-syne text-ink-3 bg-surface-2 px-2 py-0.5 rounded-full">FSM</span>
                )}
              </div>
              <h3 className="font-syne font-bold text-sm text-ink leading-snug mb-2 group-hover:text-red transition-colors">
                {c.title}
              </h3>
              <p className="text-xs text-ink-3 leading-relaxed line-clamp-3">
                {parsePres(c.presentation).chief_complaint ?? c.presentation}
              </p>
              {c.specialty && (
                <div className="mt-3 text-xs text-ink-3 font-syne truncate">{c.specialty}</div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CasesPage() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex items-center justify-center">
        <span className="font-syne text-ink-3 text-sm animate-pulse">Loading…</span>
      </div>
    }>
      <CasesInner />
    </Suspense>
  );
}
