"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { aiApi, contentApi, API_URL, myFlashcardsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import PubMedPanel from "@/components/ui/PubMedPanel";
import { useT, useI18n } from "@/lib/i18n";
import { ga } from "@/lib/gtag";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { VoiceMicButton, VoiceSpeakButton, VoiceModeToggle } from "@/components/ui/VoiceTutor";
import { DifferentialPanel } from "@/components/ui/DifferentialPanel";
import { PatientHandout } from "@/components/ui/PatientHandout";
import { DocumentAnalyzer } from "@/components/ui/DocumentAnalyzer";
import { Download } from "lucide-react";

// MODES is defined inside component so t() is available


type Message = {
  role: "user" | "assistant";
  content: string;
  pubmed?: any[];  messageId?: string;  // DB id for feedback
  feedback?: 1 | -1 | null;};

// ── Save-as-flashcard inline component ───────────────────────────────────────
function SaveFlashcardButton({ question, answer }: { question: string; answer: string }) {
  const t = useT();
  const [phase, setPhase] = useState<"idle" | "form" | "saving" | "saved">("idle");
  const [q, setQ] = useState(question.slice(0, 400));
  const [a, setA] = useState(answer.slice(0, 1000));
  const [difficulty, setDifficulty] = useState("medium");

  const save = useCallback(async () => {
    if (!q.trim() || !a.trim()) return;
    setPhase("saving");
    try {
      await myFlashcardsApi.create({ question: q.trim(), answer: a.trim(), difficulty });
      setPhase("saved");
      setTimeout(() => setPhase("idle"), 3000);
    } catch {
      setPhase("form");
    }
  }, [q, a, difficulty]);

  if (phase === "saved") {
    return <span className="text-xs font-syne text-green font-semibold ml-1">{t("ai_tutor.card_saved")}</span>;
  }

  if (phase === "idle") {
    return (
      <button
        onClick={() => setPhase("form")}
        title={t("ai_tutor.save_card")}
        className="text-xs px-1.5 py-0.5 rounded text-ink-3 hover:text-blue transition-colors font-syne"
      >
        💾
      </button>
    );
  }

  return (
    <div className="mt-2 p-3 rounded-lg border border-stroke bg-bg-2 flex flex-col gap-2 text-xs">
      <div className="flex flex-col gap-1">
        <label className="font-syne font-semibold text-ink-3">{t("ai_tutor.save_question_label")}</label>
        <textarea
          value={q}
          onChange={e => setQ(e.target.value)}
          rows={2}
          maxLength={400}
          className="bg-bg border border-stroke rounded px-2 py-1 font-serif text-ink text-xs resize-none focus:outline-none focus:ring-1 focus:ring-red/30"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="font-syne font-semibold text-ink-3">{t("ai_tutor.save_answer_label")}</label>
        <textarea
          value={a}
          onChange={e => setA(e.target.value)}
          rows={3}
          maxLength={1000}
          className="bg-bg border border-stroke rounded px-2 py-1 font-serif text-ink text-xs resize-none focus:outline-none focus:ring-1 focus:ring-red/30"
        />
      </div>
      <div className="flex items-center gap-2">
        <label className="font-syne font-semibold text-ink-3">{t("ai_tutor.save_difficulty_label")}:</label>
        <select
          value={difficulty}
          onChange={e => setDifficulty(e.target.value)}
          className="bg-bg border border-stroke rounded px-2 py-0.5 font-syne text-ink text-xs focus:outline-none"
        >
          <option value="easy">{t("common.easy")}</option>
          <option value="medium">{t("common.medium")}</option>
          <option value="hard">{t("common.hard")}</option>
        </select>
        <button
          onClick={save}
          disabled={phase === "saving"}
          className="ml-auto btn-primary px-3 py-1 rounded font-syne font-semibold text-xs disabled:opacity-60"
        >
          {phase === "saving" ? t("ai_tutor.saving_card") : t("flashcards.save_card")}
        </button>
        <button onClick={() => setPhase("idle")} className="text-ink-3 hover:text-ink font-syne text-xs px-1">
          {t("common.cancel")}
        </button>
      </div>
    </div>
  );
}

export default function AiTutorPage() {
  const t = useT();
  const { locale } = useI18n();
  const { user } = useAuthStore();

  const MODES = [
    { value: "tutor",    label: `🎓 ${t("ai_tutor.mode_tutor")}`,    desc: t("ai_tutor.mode_tutor_desc") },
    { value: "socratic", label: `❓ ${t("ai_tutor.mode_socratic")}`, desc: t("ai_tutor.mode_socratic_desc") },
    { value: "case",     label: `🩺 ${t("ai_tutor.mode_case")}`,     desc: t("ai_tutor.mode_case_desc") },
    { value: "exam",     label: `📝 ${t("ai_tutor.mode_exam")}`,     desc: t("ai_tutor.mode_exam_desc") },
    {
      value: "patient",
      label: `🏥 ${t("ai_tutor.mode_patient")}`,
      desc: t("ai_tutor.mode_patient_desc"),
    },
    {
      value: "differential",
      label: `🔬 ${t("ai_tutor.mode_differential")}`,
      desc: t("ai_tutor.mode_differential_desc"),
    },
    {
      value: "handout",
      label: `📄 ${t("ai_tutor.mode_handout")}`,
      desc: t("ai_tutor.mode_handout_desc"),
    },
    {
      value: "analyze",
      label: `🔬 ${t("ai_tutor.mode_analyze")}`,
      desc: t("ai_tutor.mode_analyze_desc"),
    },
    {
      value: "second_opinion",
      label: `⚖️ ${t("ai_tutor.mode_second_opinion")}`,
      desc: t("ai_tutor.mode_second_opinion_desc"),
    },
  ];
  const [mode, setMode] = useState("tutor");
  const [specialty, setSpecialty] = useState("");
  const [specialties, setSpecialties] = useState<any[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [pubmedPanel, setPubmedPanel] = useState<any[]>([]);
  const [voiceMode, setVoiceMode] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    contentApi.getSpecialties().then((r) => {
      // Deduplicate by name (handles cases where both DERM and dermatology exist)
      const seen = new Set<string>();
      const deduped = (r ?? []).filter((s: any) => {
        const key = (s.name ?? "").toLowerCase();
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      setSpecialties(deduped);
      if (deduped.length > 0) setSpecialty(deduped[0].code ?? "");
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((p) => [...p, { role: "user", content: text }]);
    ga.aiTutorMessage(specialty);
    setLoading(true);

    // Add empty assistant message that will be filled by stream
    setMessages((p) => [...p, { role: "assistant", content: "" }]);

    try {
      let token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

      const makeRequest = () => fetch(`${API_URL}/ai/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          mode,
          specialty: specialty || undefined,
          conversation_id: conversationId ?? undefined,
          language: locale || "en",
        }),
      });

      let res = await makeRequest();

      if (res.status === 401) {
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          try {
            const refreshRes = await fetch(`${API_URL}/auth/refresh`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ refresh_token: refresh }),
            });
            if (refreshRes.ok) {
              const data = await refreshRes.json();
              localStorage.setItem("access_token", data.access_token);
              localStorage.setItem("refresh_token", data.refresh_token);
              token = data.access_token;
              res = await makeRequest();
            } else {
              localStorage.removeItem("access_token");
              localStorage.removeItem("refresh_token");
              window.location.href = "/login";
              return;
            }
          } catch {
            window.location.href = "/login";
            return;
          }
        } else {
          window.location.href = "/login";
          return;
        }
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail || "Request failed");
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No response body");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "meta") {
              setConversationId(event.conversation_id);
            } else if (event.type === "text") {
              setMessages((p) => {
                const updated = [...p];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  updated[updated.length - 1] = { ...last, content: last.content + event.text };
                }
                return updated;
              });
            } else if (event.type === "done") {
              // Attach the saved message ID for feedback
              if (event.message_id) {
                setMessages((p) => {
                  const updated = [...p];
                  const last = updated[updated.length - 1];
                  if (last.role === "assistant") {
                    updated[updated.length - 1] = { ...last, messageId: event.message_id, feedback: null };
                  }
                  return updated;
                });
              }
            } else if (event.type === "error") {
              setMessages((p) => {
                const updated = [...p];
                updated[updated.length - 1] = { role: "assistant", content: `⚠️ ${event.detail}` };
                return updated;
              });
            }
          } catch {
            // ignore malformed SSE lines
          }
        }
      }
    } catch (err: unknown) {
      const detail = (err as { message?: string })?.message ?? "An error occurred. Please try again.";
      setMessages((p) => {
        const updated = [...p];
        if (updated[updated.length - 1]?.role === "assistant" && updated[updated.length - 1].content === "") {
          updated[updated.length - 1] = { role: "assistant", content: `⚠️ ${detail}` };
        } else {
          updated.push({ role: "assistant", content: `⚠️ ${detail}` });
        }
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setConversationId(null);
    setPubmedPanel([]);
  };

  const isFree = user?.subscription_tier === "free";

  const downloadPDF = async () => {
    if (!conversationId) return;
    const token = localStorage.getItem("access_token") ?? "";
    const res = await fetch(`${API_URL}/ai/conversations/${conversationId}/export-pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `medmind_session.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const submitFeedback = async (msgIndex: number, rating: 1 | -1) => {
    const msg = messages[msgIndex];
    if (!msg?.messageId || msg.feedback !== null) return;
    // Optimistically update UI
    setMessages((p) => {
      const updated = [...p];
      updated[msgIndex] = { ...updated[msgIndex], feedback: rating };
      return updated;
    });
    try {
      await aiApi.feedback(msg.messageId, rating);
    } catch {
      // Revert on failure
      setMessages((p) => {
        const updated = [...p];
        updated[msgIndex] = { ...updated[msgIndex], feedback: null };
        return updated;
      });
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center gap-2 px-3 sm:px-4 py-2.5 border-b border-border bg-surface flex-shrink-0">
          <h1 className="font-syne font-black text-base sm:text-lg text-ink mr-auto">{t("nav.items.ai_tutor")}</h1>

          {/* Specialty */}
          <select
            value={specialty}
            onChange={(e) => setSpecialty(e.target.value)}
            className="px-2.5 py-1.5 rounded border border-border bg-bg font-syne text-xs text-ink focus:outline-none focus:border-ink-3"
          >
            {specialties.map((s) => (
              <option key={s.id} value={s.code ?? s.id}>
                {s.name}
              </option>
            ))}
          </select>

          {/* Mode */}
          <div className="hidden sm:flex gap-1 flex-wrap">
            {MODES.map((m) => (
              <button
                key={m.value}
                onClick={() => setMode(m.value)}
                title={m.desc}
                className={`px-2.5 py-1.5 rounded font-syne font-semibold text-xs transition-colors ${
                  m.value === "patient"
                    ? mode === "patient"
                      ? "bg-green text-white border border-green"
                      : "bg-green/10 text-green border border-green/30 hover:bg-green hover:text-white"
                    : m.value === "differential"
                    ? mode === "differential"
                      ? "bg-blue-2 text-white border border-blue-2"
                      : "bg-blue/10 text-blue-2 border border-blue/30 hover:bg-blue-2 hover:text-white"
                    : m.value === "handout"
                    ? mode === "handout"
                      ? "bg-ink text-white border border-ink"
                      : "bg-bg text-ink-2 border border-border hover:bg-ink hover:text-white"
                    : m.value === "analyze"
                    ? mode === "analyze"
                      ? "bg-red text-white border border-red"
                      : "bg-red/10 text-red border border-red/30 hover:bg-red hover:text-white"
                    : mode === m.value
                    ? "bg-ink text-white"
                    : "bg-bg text-ink-2 hover:bg-bg-2"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Voice mode toggle */}
          <VoiceModeToggle active={voiceMode} onToggle={() => setVoiceMode(v => !v)} />

          {conversationId && messages.length > 0 && (
            <button
              onClick={downloadPDF}
              title="Download session as PDF"
              className="flex items-center gap-1 text-ink-3 hover:text-ink font-syne text-xs transition-colors"
            >
              <Download size={13} /> PDF
            </button>
          )}
          <button
            onClick={clearChat}
            className="text-ink-3 hover:text-ink font-syne text-xs transition-colors"
          >
            {t("ai_tutor.clear")}
          </button>
        </div>

        {/* Differential Diagnosis — dedicated panel, no chat */}
        {mode === "differential" && (
          <div className="flex-1 overflow-y-auto">
            <DifferentialPanel />
          </div>
        )}

        {/* Patient Handout — dedicated panel, no chat */}
        {mode === "handout" && (
          <div className="flex-1 overflow-y-auto">
            <PatientHandout />
          </div>
        )}

        {/* Document Analyzer — dedicated panel, no chat */}
        {mode === "analyze" && (
          <div className="flex-1 overflow-y-auto">
            <DocumentAnalyzer />
          </div>
        )}

        {/* Messages — standard chat for all other modes */}
        {mode !== "differential" && mode !== "handout" && mode !== "analyze" && (
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-5xl mb-4">🤖</div>
              <h2 className="font-syne font-bold text-xl text-ink mb-2">{t("ai_tutor.welcome_title")}</h2>
              <p className="font-serif text-ink-3 text-sm max-w-sm">
                {t("ai_tutor.welcome_sub")}
              </p>
              {isFree && (
                <div className="mt-4 px-4 py-2 bg-amber-light border border-amber/30 rounded text-xs font-syne text-amber">
                  {t("ai_tutor.free_limit")}
                </div>
              )}
              <div className="mt-6 flex flex-wrap gap-2 justify-center max-w-md">
                {[
                  t("ai_tutor.suggestions.heart_failure"),
                  t("ai_tutor.suggestions.meningitis"),
                  t("ai_tutor.suggestions.mi_case"),
                  t("ai_tutor.suggestions.pharmacology"),
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="px-3 py-1.5 bg-surface border border-border rounded-full text-xs font-syne text-ink-2 hover:border-ink-3 hover:text-ink transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 animate-fade-up ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${
                  msg.role === "user" ? "bg-ink text-white" : "bg-red text-white"
                }`}
              >
                {msg.role === "user" ? "You" : "AI"}
              </div>
              <div className="flex flex-col gap-1 max-w-[75%]">
                <div
                  className={`rounded-lg px-4 py-2.5 font-serif text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-ink text-white rounded-tr-none whitespace-pre-wrap"
                      : "bg-surface border border-border text-ink rounded-tl-none"
                  }`}
                >
                  {msg.role === "user" ? msg.content : (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ children }) => <p className="font-syne font-bold text-base mt-2 mb-1">{children}</p>,
                        h2: ({ children }) => <p className="font-syne font-bold text-base mt-2 mb-1">{children}</p>,
                        h3: ({ children }) => <p className="font-syne font-semibold text-sm mt-2 mb-0.5">{children}</p>,
                        h4: ({ children }) => <p className="font-syne font-semibold text-sm mt-1 mb-0.5">{children}</p>,
                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                        strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
                        em: ({ children }) => <em className="italic">{children}</em>,
                        ul: ({ children }) => <ul className="my-1.5 space-y-0.5 pl-4 list-disc">{children}</ul>,
                        ol: ({ children }) => <ol className="my-1.5 space-y-0.5 pl-4 list-decimal">{children}</ol>,
                        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                        hr: () => <hr className="my-2 border-border" />,
                        code: ({ children }) => <code className="bg-bg-2 rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
                        blockquote: ({ children }) => <blockquote className="border-l-2 border-ink-3 pl-3 italic text-ink-2 my-1">{children}</blockquote>,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}
                  {msg.pubmed && msg.pubmed.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-border-2 text-xs text-ink-3 space-y-0.5">
                      <strong className="font-syne">References:</strong>
                      {msg.pubmed.slice(0, 3).map((ref: any) => (
                        <div key={ref.pmid}>
                          <a
                            href={ref.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-2 hover:underline"
                          >
                            {ref.title}
                          </a>{" "}
                          ({ref.year})
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {/* Listen button for assistant messages */}
                {msg.role === "assistant" && msg.content && !loading && (
                  <div className="ml-1">
                    <VoiceSpeakButton text={msg.content} locale={locale} compact />
                  </div>
                )}
                {/* Feedback buttons — only for assistant messages with a DB ID */}
                {msg.role === "assistant" && msg.messageId && (
                  <div className="flex gap-1 ml-1">
                    <button
                      onClick={() => submitFeedback(i, 1)}
                      disabled={msg.feedback !== null && msg.feedback !== undefined}
                      title="Helpful"
                      className={`text-sm px-1.5 py-0.5 rounded transition-colors ${
                        msg.feedback === 1
                          ? "text-green"
                          : "text-ink-3 hover:text-green"
                      }`}
                    >
                      👍
                    </button>
                    <button
                      onClick={() => submitFeedback(i, -1)}
                      disabled={msg.feedback !== null && msg.feedback !== undefined}
                      title="Not helpful"
                      className={`text-sm px-1.5 py-0.5 rounded transition-colors ${
                        msg.feedback === -1
                          ? "text-red"
                          : "text-ink-3 hover:text-red"
                      }`}
                    >
                      👎
                    </button>
                  </div>
                )}
                {/* Save as flashcard — authenticated users, assistant messages only */}
                {msg.role === "assistant" && msg.content && !loading && user && (
                  <div className="ml-1 mt-1">
                    <SaveFlashcardButton
                      question={messages[i - 1]?.content ?? msg.content.slice(0, 200)}
                      answer={msg.content}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 animate-fade-up">
              <div className="w-7 h-7 rounded-full bg-red flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
                AI
              </div>
              <div className="bg-surface border border-border rounded-lg rounded-tl-none px-4 py-3">
                <div className="flex gap-1.5">
                  {[0, 0.2, 0.4].map((delay) => (
                    <span
                      key={delay}
                      className="w-2 h-2 rounded-full bg-ink-3 animate-blink"
                      style={{ animationDelay: `${delay}s` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        )} {/* end mode !== differential/handout */}

        {/* Input — hidden for dedicated tool modes */}
        {mode !== "differential" && mode !== "handout" && mode !== "analyze" && (
        <div className="px-3 sm:px-4 py-2.5 sm:py-3 border-t border-border bg-surface flex-shrink-0">
          <div className="flex gap-2 items-end">
            {/* Voice mic button — STT via Web Speech API */}
            <VoiceMicButton
              onTranscript={(text) => setInput(prev => prev ? prev + " " + text : text)}
              disabled={loading}
              locale={locale}
            />
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={voiceMode ? "🎙️ Speak or type…" : t("ai_tutor.input_placeholder")}
              rows={1}
              className="flex-1 resize-none px-3 py-2.5 rounded-xl border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink-3 transition-colors leading-relaxed"
              style={{ maxHeight: "100px", overflowY: "auto" }}
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              className="btn-primary px-4 py-2.5 h-10 flex-shrink-0 disabled:opacity-40 rounded-xl"
            >
              →
            </button>
          </div>
          {mode === "patient" ? (
            <p className="font-serif text-xs mt-1.5 text-green">
              🏥 <strong>{t("ai_tutor.mode_patient")}</strong> — plain language, no diagnoses, always recommends seeing a doctor. For emergencies call 112 / 911.
            </p>
          ) : (
            <p className="text-ink-3 font-serif text-xs mt-1.5">
              {t("ai_tutor.mode_label")} <strong>{MODES.find((m) => m.value === mode)?.label}</strong> · {t("ai_tutor.disclaimer")}
            </p>
          )}
        </div>
        )} {/* end input block */}
      </div>

      {/* PubMed panel */}
      <PubMedPanel initialRefs={pubmedPanel} onClose={() => setPubmedPanel([])} />
    </div>
  );
}
