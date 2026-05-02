"use client";

import { useState, useRef, useEffect } from "react";
import { simulationApi } from "@/lib/api";

type Phase = "setup" | "chat" | "evaluate" | "result";

interface ChatMessage {
  role: "student" | "patient";
  content: string;
}

const SPECIALTIES = [
  { value: "internal_medicine", label: "Internal Medicine" },
  { value: "cardiology", label: "Cardiology" },
  { value: "pulmonology", label: "Pulmonology" },
  { value: "gastroenterology", label: "Gastroenterology" },
  { value: "neurology", label: "Neurology" },
  { value: "endocrinology", label: "Endocrinology" },
  { value: "pediatrics", label: "Pediatrics" },
  { value: "emergency_medicine", label: "Emergency Medicine" },
];

const DIFFICULTIES = [
  { value: "beginner", label: "Beginner", desc: "Clear, direct answers" },
  { value: "intermediate", label: "Intermediate", desc: "Some misleading symptoms" },
  { value: "advanced", label: "Advanced", desc: "Vague and incomplete history" },
];

const SPECIES = [
  { value: "human", label: "Human" },
  { value: "canine", label: "Dog 🐕" },
  { value: "feline", label: "Cat 🐈" },
  { value: "equine", label: "Horse 🐎" },
];

export default function SimulationPage() {
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
      });
      setSessionToken(data.session_token);
      setMessages([{ role: "patient", content: data.patient_opening }]);
      setTurns(0);
      setPhase("chat");
    } catch {
      alert("Failed to start session. Please try again.");
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
      const data = await simulationApi.chatVirtualPatient(sessionToken, text);
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
      const data = await simulationApi.evaluateVirtualPatient(sessionToken, diagnosis);
      setEvaluation(data);
      setPhase("result");
    } catch {
      alert("Failed to evaluate. Please try again.");
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

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="font-syne font-black text-2xl text-ink">Clinical Simulation</h1>
        <p className="font-serif text-ink-3 text-sm mt-0.5">
          Practice history-taking with an AI virtual patient
        </p>
      </div>

      {/* SETUP */}
      {phase === "setup" && (
        <div className="space-y-6">
          <div className="card p-6 space-y-5">
            <h2 className="font-syne font-bold text-base text-ink">Configure Your Patient</h2>

            {/* Specialty */}
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">Specialty</label>
              <div className="grid grid-cols-2 gap-2">
                {SPECIALTIES.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setSpecialty(s.value)}
                    className={`px-3 py-2 rounded-lg border font-syne font-semibold text-xs text-left transition-all ${
                      specialty === s.value
                        ? "border-ink bg-ink text-white"
                        : "border-border text-ink-2 hover:border-ink-3"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">Difficulty</label>
              <div className="grid grid-cols-3 gap-2">
                {DIFFICULTIES.map((d) => (
                  <button
                    key={d.value}
                    onClick={() => setDifficulty(d.value)}
                    className={`px-3 py-3 rounded-lg border transition-all text-left ${
                      difficulty === d.value
                        ? "border-ink bg-ink text-white"
                        : "border-border hover:border-ink-3"
                    }`}
                  >
                    <div className="font-syne font-bold text-xs">{d.label}</div>
                    <div className={`font-serif text-xs mt-0.5 ${difficulty === d.value ? "text-white/70" : "text-ink-3"}`}>
                      {d.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Species */}
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">Patient Type</label>
              <div className="flex gap-2">
                {SPECIES.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setSpecies(s.value)}
                    className={`px-4 py-2 rounded-lg border font-syne font-semibold text-xs transition-all ${
                      species === s.value
                        ? "border-ink bg-ink text-white"
                        : "border-border text-ink-2 hover:border-ink-3"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Seed (optional) */}
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
                Patient seed <span className="text-ink-3 font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={patientSeed}
                onChange={(e) => setPatientSeed(e.target.value)}
                placeholder="e.g. 65yo diabetic with chest pain"
                className="w-full px-3 py-2 rounded border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink"
              />
              <p className="font-serif text-ink-3 text-xs mt-1">Leave blank for a random patient</p>
            </div>

            <button
              onClick={startSession}
              disabled={loading}
              className="btn-primary w-full disabled:opacity-40"
            >
              {loading ? "Preparing patient…" : "Start Simulation →"}
            </button>
          </div>

          {/* Tips */}
          <div className="card p-5">
            <h3 className="font-syne font-bold text-sm text-ink mb-3">How it works</h3>
            <ol className="space-y-2">
              {[
                "The AI plays a patient with a hidden diagnosis",
                "Ask open-ended questions to gather history",
                "Use clinical reasoning to form a differential",
                "Submit your working diagnosis for AI evaluation",
              ].map((tip, i) => (
                <li key={i} className="flex gap-3">
                  <span className="w-5 h-5 rounded-full bg-ink text-white font-syne font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <span className="font-serif text-ink-2 text-sm">{tip}</span>
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
                {species === "human" ? "👤" : species === "canine" ? "🐕" : species === "feline" ? "🐈" : "🐎"}
              </div>
              <div>
                <div className="font-syne font-bold text-sm text-ink capitalize">
                  {species === "human" ? "Virtual Patient" : `Virtual ${species.charAt(0).toUpperCase() + species.slice(1)} Patient`}
                </div>
                <div className="font-serif text-ink-3 text-xs capitalize">{specialty.replace("_", " ")} · {difficulty}</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-serif text-ink-3 text-xs">{turns} question{turns !== 1 ? "s" : ""} asked</span>
              <button
                onClick={() => setPhase("evaluate")}
                className="btn-primary text-sm"
              >
                Submit Diagnosis →
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
                  {m.role === "patient" ? "P" : "Dr"}
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
                <div className="w-7 h-7 rounded-full bg-amber-light flex items-center justify-center text-xs text-amber flex-shrink-0">P</div>
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
              placeholder="Ask the patient a question…"
              disabled={loading}
              className="flex-1 px-4 py-3 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="btn-primary px-5 disabled:opacity-40"
            >
              Send
            </button>
          </div>

          <p className="font-serif text-ink-3 text-xs text-center">
            When you have enough information, click "Submit Diagnosis" to get AI feedback
          </p>
        </div>
      )}

      {/* EVALUATE */}
      {phase === "evaluate" && (
        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="font-syne font-bold text-base text-ink mb-3">Submit Your Diagnosis</h2>
            <p className="font-serif text-ink-2 text-sm mb-4">
              Based on your history-taking ({turns} questions asked), what is your working diagnosis and reasoning?
            </p>
            <textarea
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
              rows={5}
              placeholder="e.g. My working diagnosis is community-acquired pneumonia. The patient presented with productive cough, fever, and right-sided chest pain. Key findings included…"
              className="w-full px-4 py-3 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setPhase("chat")}
                className="flex-1 px-4 py-2.5 rounded-lg border border-border font-syne font-semibold text-sm text-ink hover:bg-bg-2 transition-colors"
              >
                ← Back to Patient
              </button>
              <button
                onClick={submitEvaluation}
                disabled={loading || !diagnosis.trim()}
                className="flex-2 btn-primary disabled:opacity-40"
              >
                {loading ? "Evaluating…" : "Get AI Feedback →"}
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
              <div className="font-serif text-ink-3 text-xs mt-0.5">Questions asked</div>
            </div>
            <div className="card p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink capitalize">{evaluation.difficulty ?? difficulty}</div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">Difficulty</div>
            </div>
            <div className="card p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink capitalize">
                {(evaluation.specialty ?? specialty).replace("_", " ")}
              </div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">Specialty</div>
            </div>
          </div>

          {/* Evaluation */}
          <div className="card p-6">
            <h2 className="font-syne font-bold text-base text-ink mb-4">AI Evaluation</h2>
            <div className="font-serif text-sm text-ink-2 leading-relaxed whitespace-pre-wrap prose prose-sm max-w-none">
              {evaluation.evaluation}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button onClick={reset} className="flex-1 btn-primary">
              New Simulation
            </button>
            <button
              onClick={() => { setPhase("chat"); }}
              className="flex-1 px-4 py-2.5 rounded-lg border border-border font-syne font-semibold text-sm text-ink hover:bg-bg-2 transition-colors"
            >
              Review Conversation
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
