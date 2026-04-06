"use client";

import { useState, useRef, useEffect } from "react";
import { aiApi, contentApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

const MODES = [
  { value: "tutor", label: "🎓 Tutor", desc: "Explain & teach" },
  { value: "socratic", label: "❓ Socratic", desc: "Guided questions" },
  { value: "case", label: "🩺 Case", desc: "Clinical reasoning" },
  { value: "exam", label: "📝 Exam", desc: "Test knowledge" },
];

type Message = {
  role: "user" | "assistant";
  content: string;
  pubmed?: any[];  messageId?: string;  // DB id for feedback
  feedback?: 1 | -1 | null;};

export default function AiTutorPage() {
  const { user } = useAuthStore();
  const [mode, setMode] = useState("tutor");
  const [specialty, setSpecialty] = useState("");
  const [specialties, setSpecialties] = useState<any[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [pubmedPanel, setPubmedPanel] = useState<any[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    contentApi.getSpecialties().then((r) => {
      setSpecialties(r.data);
      if (r.data.length > 0) setSpecialty(r.data[0].code ?? "");
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
    setLoading(true);

    // Add empty assistant message that will be filled by stream
    setMessages((p) => [...p, { role: "assistant", content: "" }]);

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

      const res = await fetch(`${apiUrl}/ai/ask/stream`, {
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
        }),
      });

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

  const submitFeedback = async (msgIndex: number, rating: 1 | -1) => {
    const msg = messages[msgIndex];
    if (!msg.messageId || msg.feedback !== null) return;
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
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-surface flex-shrink-0">
          <h1 className="font-syne font-black text-lg text-ink mr-auto">AI Tutor</h1>

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
          <div className="hidden sm:flex gap-1">
            {MODES.map((m) => (
              <button
                key={m.value}
                onClick={() => setMode(m.value)}
                title={m.desc}
                className={`px-2.5 py-1.5 rounded font-syne font-semibold text-xs transition-colors ${
                  mode === m.value
                    ? "bg-ink text-white"
                    : "bg-bg text-ink-2 hover:bg-bg-2"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          <button
            onClick={clearChat}
            className="text-ink-3 hover:text-ink font-syne text-xs transition-colors"
          >
            Clear
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-5xl mb-4">🤖</div>
              <h2 className="font-syne font-bold text-xl text-ink mb-2">How can I help you today?</h2>
              <p className="font-serif text-ink-3 text-sm max-w-sm">
                Ask me anything about medicine. I can explain concepts, guide you through clinical cases, or test your knowledge.
              </p>
              {isFree && (
                <div className="mt-4 px-4 py-2 bg-amber-light border border-amber/30 rounded text-xs font-syne text-amber">
                  Free plan: 5 questions/day. Upgrade for unlimited access.
                </div>
              )}
              <div className="mt-6 flex flex-wrap gap-2 justify-center max-w-md">
                {[
                  "Explain the pathophysiology of heart failure",
                  "What are the signs of meningitis?",
                  "Walk me through an MI case",
                  "MCQ on pharmacology",
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
                  className={`rounded-lg px-4 py-2.5 font-serif text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-ink text-white rounded-tr-none"
                      : "bg-surface border border-border text-ink rounded-tl-none"
                  }`}
                >
                  {msg.content}
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

        {/* Input */}
        <div className="px-4 py-3 border-t border-border bg-surface flex-shrink-0">
          <div className="flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a medical question… (Enter to send, Shift+Enter for new line)"
              rows={1}
              className="flex-1 resize-none px-3.5 py-2.5 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink-3 transition-colors leading-relaxed"
              style={{ maxHeight: "120px", overflowY: "auto" }}
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              className="btn-primary px-4 py-2.5 h-10 flex-shrink-0 disabled:opacity-40"
            >
              →
            </button>
          </div>
          <p className="text-ink-3 font-serif text-xs mt-1.5">
            Mode: <strong>{MODES.find((m) => m.value === mode)?.label}</strong> · AI may make mistakes — verify clinical decisions
          </p>
        </div>
      </div>

      {/* PubMed panel */}
      {pubmedPanel.length > 0 && (
        <div className="w-64 border-l border-border bg-surface flex-shrink-0 overflow-y-auto p-3">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider">
              PubMed References
            </h3>
            <button
              onClick={() => setPubmedPanel([])}
              className="text-ink-3 hover:text-ink text-xs"
            >
              ×
            </button>
          </div>
          <div className="space-y-3">
            {pubmedPanel.map((ref: any) => (
              <div key={ref.pmid} className="text-xs">
                <a
                  href={ref.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-syne font-semibold text-blue hover:text-blue-2 transition-colors leading-tight block"
                >
                  {ref.title}
                </a>
                <p className="text-ink-3 font-serif mt-0.5">
                  {ref.authors?.[0]} et al. · {ref.journal}, {ref.year}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
