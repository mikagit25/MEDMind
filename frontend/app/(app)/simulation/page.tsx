"use client";

import { useState, useRef, useEffect } from "react";
import { simulationApi } from "@/lib/api";
import { useT, useI18n } from "@/lib/i18n";

type Phase = "setup" | "chat" | "evaluate" | "result";

interface ChatMessage {
  role: "student" | "patient";
  content: string;
}

const SPECIALTY_KEYS = [
  { value: "internal_medicine", key: "spec_internal_medicine" },
  { value: "cardiology", key: "spec_cardiology" },
  { value: "pulmonology", key: "spec_pulmonology" },
  { value: "gastroenterology", key: "spec_gastroenterology" },
  { value: "neurology", key: "spec_neurology" },
  { value: "endocrinology", key: "spec_endocrinology" },
  { value: "pediatrics", key: "spec_pediatrics" },
  { value: "emergency_medicine", key: "spec_emergency" },
];

const DIFFICULTY_KEYS = [
  { value: "beginner", key: "diff_beginner", descKey: "diff_beginner_desc" },
  { value: "intermediate", key: "diff_intermediate", descKey: "diff_intermediate_desc" },
  { value: "advanced", key: "diff_advanced", descKey: "diff_advanced_desc" },
];

const SPECIES_KEYS = [
  { value: "human", key: "species_human", emoji: "" },
  { value: "canine", key: "species_dog", emoji: "🐕" },
  { value: "feline", key: "species_cat", emoji: "🐈" },
  { value: "equine", key: "species_horse", emoji: "🐎" },
];

const SPECIES_AVATAR: Record<string, string> = {
  human: "👤",
  canine: "🐕",
  feline: "🐈",
  equine: "🐎",
};

export default function SimulationPage() {
  const t = useT();
  const { locale } = useI18n();
  const [phase, setPhase] = useState<Phase>("setup");
  const [specialty, setSpecialty] = useState("internal_medicine");
  const [difficulty, setDifficulty] = useState("intermediate");
  const [species, setSpecies] = useState("human");
  const [patientSeed, setPatientSeed] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [loading, setLoading] = useState(false);
  const [evaluation, setEvaluation] = useState<any>(null);
  const [turns, setTurns] = useState(0);
  const [setupError, setSetupError] = useState("");
  const [evalError, setEvalError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startSession = async () => {
    setLoading(true);
    try {
      const data = await simulationApi.startVirtualPatient({
        specialty,
        difficulty,
        species,
        patient_seed: patientSeed || undefined,
        language: locale || "en",
      });
      setSessionToken(data.session_token);
      setMessages([{ role: "patient", content: data.patient_opening }]);
      setTurns(0);
      setPhase("chat");
    } catch {
      setSetupError(t("common.error_retry"));
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "student", content: text }]);
    setLoading(true);
    try {
      const data = await simulationApi.chatVirtualPatient(sessionToken, text, locale || "en");
      setSessionToken(data.session_token);
      setMessages((prev) => [...prev, { role: "patient", content: data.patient_response }]);
      setTurns(data.turns);
    } catch {
      setMessages((prev) => [...prev, { role: "patient", content: "(Error — please try again)" }]);
    } finally {
      setLoading(false);
    }
  };

  const submitEvaluation = async () => {
    if (!diagnosis.trim() || loading) return;
    setLoading(true);
    try {
      const data = await simulationApi.evaluateVirtualPatient(sessionToken, diagnosis, locale || "en");
      setEvaluation(data);
      setPhase("result");
    } catch {
      setEvalError(t("common.error_retry"));
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setPhase("setup");
    setMessages([]);
    setSessionToken("");
    setDiagnosis("");
    setEvaluation(null);
    setTurns(0);
    setInput("");
  };

  const speciesLabel = (value: string) => {
    const s = SPECIES_KEYS.find((k) => k.value === value);
    if (!s) return value;
    const label = t(`simulation.${s.key}` as any);
    return s.emoji ? `${label} ${s.emoji}` : label;
  };

  const specialtyLabel = (value: string) => {
    const s = SPECIALTY_KEYS.find((k) => k.value === value);
    return s ? t(`simulation.${s.key}` as any) : value.replace(/_/g, " ");
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="font-syne font-black text-2xl text-ink">{t("simulation.title")}</h1>
        <p className="font-serif text-ink-3 text-sm mt-0.5">
          {t("simulation.subtitle")}
        </p>
      </div>

      {/* SETUP */}
      {phase === "setup" && (
        <div className="space-y-6">
          <div className="card p-6 space-y-5">
            <h2 className="font-syne font-bold text-base text-ink">{t("simulation.configure")}</h2>

            {/* Specialty */}
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">{t("simulation.specialty_label")}</label>
              <div className="grid grid-cols-2 gap-2">
                {SPECIALTY_KEYS.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setSpecialty(s.value)}
                    className={`px-3 py-2 rounded-lg border font-syne font-semibold text-xs text-left transition-all ${
                      specialty === s.value
                        ? "border-ink bg-ink text-white"
                        : "border-border text-ink-2 hover:border-ink-3"
                    }`}
                  >
                    {t(`simulation.${s.key}` as any)}
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">{t("simulation.difficulty_label")}</label>
              <div className="grid grid-cols-3 gap-2">
                {DIFFICULTY_KEYS.map((d) => (
                  <button
                    key={d.value}
                    onClick={() => setDifficulty(d.value)}
                    className={`px-3 py-3 rounded-lg border transition-all text-left ${
                      difficulty === d.value
                        ? "border-ink bg-ink text-white"
                        : "border-border hover:border-ink-3"
                    }`}
                  >
                    <div className="font-syne font-bold text-xs">{t(`simulation.${d.key}` as any)}</div>
                    <div className={`font-serif text-xs mt-0.5 ${difficulty === d.value ? "text-white/70" : "text-ink-3"}`}>
                      {t(`simulation.${d.descKey}` as any)}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Species */}
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">{t("simulation.species")}</label>
              <div className="flex gap-2">
                {SPECIES_KEYS.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setSpecies(s.value)}
                    className={`px-4 py-2 rounded-lg border font-syne font-semibold text-xs transition-all ${
                      species === s.value
                        ? "border-ink bg-ink text-white"
                        : "border-border text-ink-2 hover:border-ink-3"
                    }`}
                  >
                    {speciesLabel(s.value)}
                  </button>
                ))}
              </div>
            </div>

            {/* Seed (optional) */}
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
                {t("simulation.patient_seed_label")} <span className="text-ink-3 font-normal">({t("simulation.patient_seed_hint")})</span>
              </label>
              <input
                type="text"
                value={patientSeed}
                onChange={(e) => setPatientSeed(e.target.value)}
                placeholder={t("simulation.patient_seed_placeholder")}
                className="w-full px-3 py-2 rounded border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink"
              />
              <p className="font-serif text-ink-3 text-xs mt-1">{t("simulation.seed_empty_hint")}</p>
            </div>

            {setupError && (
              <div className="p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">
                {setupError}
              </div>
            )}
            <button
              onClick={startSession}
              disabled={loading}
              className="btn-primary w-full disabled:opacity-40"
            >
              {loading ? t("common.loading") : t("simulation.start")}
            </button>
          </div>

          {/* Tips */}
          <div className="card p-5">
            <h3 className="font-syne font-bold text-sm text-ink mb-3">{t("simulation.how_it_works")}</h3>
            <ol className="space-y-2">
              {(["tip_1", "tip_2", "tip_3", "tip_4"] as const).map((key, i) => (
                <li key={key} className="flex gap-3">
                  <span className="w-5 h-5 rounded-full bg-ink text-white font-syne font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <span className="font-serif text-ink-2 text-sm">{t(`simulation.${key}` as any)}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {/* CHAT */}
      {phase === "chat" && (
        <div className="flex flex-col gap-4">
          {/* Header bar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-ink flex items-center justify-center text-white text-sm">
                {SPECIES_AVATAR[species] ?? "👤"}
              </div>
              <div>
                <div className="font-syne font-bold text-sm text-ink">
                  {species === "human"
                    ? t("simulation.virtual_patient")
                    : `${t("simulation.virtual_patient")} (${t(`simulation.${SPECIES_KEYS.find((k) => k.value === species)?.key ?? "species_human"}` as any)})`}
                </div>
                <div className="font-serif text-ink-3 text-xs">
                  {specialtyLabel(specialty)} · {t(`simulation.diff_${difficulty}` as any)}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-serif text-ink-3 text-xs">
                {turns} {turns === 1 ? t("simulation.question_asked") : t("simulation.questions_asked")}
              </span>
              <button
                onClick={() => setPhase("evaluate")}
                className="btn-primary text-sm"
              >
                {t("simulation.end_session")}
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="card p-4 space-y-4 min-h-[400px] max-h-[500px] overflow-y-auto">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "student" ? "flex-row-reverse" : ""}`}>
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                    m.role === "patient" ? "bg-amber-light text-amber" : "bg-ink text-white"
                  }`}
                >
                  {m.role === "patient" ? t("simulation.patient_avatar") : t("simulation.doctor_avatar")}
                </div>
                <div
                  className={`max-w-[80%] px-4 py-3 rounded-xl font-serif text-sm leading-relaxed ${
                    m.role === "patient"
                      ? "bg-bg-2 text-ink-2"
                      : "bg-ink text-white"
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-full bg-amber-light flex items-center justify-center text-xs text-amber flex-shrink-0">
                  {t("simulation.patient_avatar")}
                </div>
                <div className="bg-bg-2 px-4 py-3 rounded-xl">
                  <span className="inline-flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-ink-3 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-ink-3 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-ink-3 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder={t("simulation.input_placeholder")}
              disabled={loading}
              className="flex-1 px-4 py-3 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="btn-primary px-5 disabled:opacity-40"
            >
              {t("simulation.send")}
            </button>
          </div>

          <p className="font-serif text-ink-3 text-xs text-center">
            {t("simulation.end_hint")}
          </p>
        </div>
      )}

      {/* EVALUATE */}
      {phase === "evaluate" && (
        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="font-syne font-bold text-base text-ink mb-3">{t("simulation.session_summary")}</h2>
            <p className="font-serif text-ink-2 text-sm mb-4">
              {t("simulation.diagnosis_prompt").replace("{n}", String(turns))}
            </p>
            <textarea
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
              rows={5}
              placeholder={t("simulation.diagnosis_placeholder")}
              className="w-full px-4 py-3 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink resize-none"
            />
            {evalError && (
              <div className="mt-3 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">
                {evalError}
              </div>
            )}
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setPhase("chat")}
                className="flex-1 px-4 py-2.5 rounded-lg border border-border font-syne font-semibold text-sm text-ink hover:bg-bg-2 transition-colors"
              >
                {t("common.back")}
              </button>
              <button
                onClick={submitEvaluation}
                disabled={loading || !diagnosis.trim()}
                className="flex-2 btn-primary disabled:opacity-40"
              >
                {loading ? t("simulation.submitting") : t("simulation.submit_diagnosis")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RESULT */}
      {phase === "result" && evaluation && (
        <div className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="card p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">{evaluation.turns_taken}</div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">{t("simulation.stat_questions")}</div>
            </div>
            <div className="card p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">
                {t(`simulation.diff_${evaluation.difficulty ?? difficulty}` as any)}
              </div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">{t("simulation.stat_difficulty")}</div>
            </div>
            <div className="card p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">
                {specialtyLabel(evaluation.specialty ?? specialty)}
              </div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">{t("simulation.stat_specialty")}</div>
            </div>
          </div>

          {/* Evaluation */}
          <div className="card p-6">
            <h2 className="font-syne font-bold text-base text-ink mb-4">{t("simulation.feedback")}</h2>
            <div className="font-serif text-sm text-ink-2 leading-relaxed whitespace-pre-wrap prose prose-sm max-w-none">
              {evaluation.evaluation}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button onClick={reset} className="flex-1 btn-primary">
              {t("simulation.new_patient")}
            </button>
            <button
              onClick={() => { setPhase("chat"); }}
              className="flex-1 px-4 py-2.5 rounded-lg border border-border font-syne font-semibold text-sm text-ink hover:bg-bg-2 transition-colors"
            >
              {t("simulation.review_conversation")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
