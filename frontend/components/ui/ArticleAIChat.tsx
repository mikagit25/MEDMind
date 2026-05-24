"use client";

import { useState, useRef, useEffect } from "react";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";
import { Brain, Send, Lock, Zap, ChevronDown, ChevronUp } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";
const FREE_LIMIT = 3;

type Message = { role: "user" | "ai"; text: string };

interface Props {
  slug: string;
  articleTitle: string;
}

export function ArticleAIChat({ slug, articleTitle }: Props) {
  const { isAuthenticated, user } = useAuthStore();
  const isPaid = ["student", "pro", "lifetime"].includes(user?.subscription_tier ?? "");

  const [open,      setOpen]      = useState(false);
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [input,     setInput]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [error,     setError]     = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  async function handleSend() {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setError("");
    setMessages(m => [...m, { role: "user", text: q }]);
    setLoading(true);

    try {
      const token = typeof window !== "undefined"
        ? localStorage.getItem("access_token") ?? sessionStorage.getItem("access_token") ?? ""
        : "";

      const res = await fetch(`${API}/articles/${slug}/ask`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body:    JSON.stringify({ question: q }),
      });

      if (res.status === 429) {
        setError(`Daily limit reached. Upgrade to Pro for unlimited AI consultations.`);
        setMessages(m => m.slice(0, -1));
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? "Request failed");
      }

      const data = await res.json();
      setMessages(m => [...m, { role: "ai", text: data.answer }]);
      if (data.remaining !== null && data.remaining !== undefined) {
        setRemaining(data.remaining);
      }
    } catch (e: any) {
      setError(e.message ?? "Something went wrong");
      setMessages(m => m.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }

  // ── Guest state ───────────────────────────────────────────────────────────
  if (!isAuthenticated) {
    return (
      <div className="mt-16 border-t border-border pt-10">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-xl bg-surface border border-border flex items-center justify-center text-ink-3">
            <Brain size={18} strokeWidth={1.75} />
          </div>
          <h2 className="font-syne font-bold text-xl text-ink">AI Consultation</h2>
        </div>

        <div className="bg-surface border border-border rounded-xl p-6 flex flex-col sm:flex-row items-start sm:items-center gap-5">
          <div className="w-12 h-12 rounded-full bg-bg flex items-center justify-center flex-shrink-0 text-ink-3">
            <Lock size={22} strokeWidth={1.75} />
          </div>
          <div className="flex-1">
            <p className="font-syne font-semibold text-ink mb-1">
              Have questions about this article?
            </p>
            <p className="text-ink-2 text-sm leading-relaxed">
              Sign in to get AI-powered answers based on the article content.
              Free account includes {FREE_LIMIT} questions per day.
            </p>
          </div>
          <div className="flex gap-3 flex-shrink-0">
            <Link
              href={`/login?redirect=/articles/${slug}`}
              className="font-syne font-semibold text-sm border border-border text-ink-2 px-4 py-2 rounded-lg hover:border-ink hover:text-ink transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded-lg hover:bg-red transition-colors"
            >
              Join free
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Authenticated state ───────────────────────────────────────────────────
  return (
    <div className="mt-16 border-t border-border pt-10">
      {/* Header — always visible, click to expand */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between gap-3 mb-0 group"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-surface border border-border flex items-center justify-center text-ink-3 group-hover:border-ink group-hover:text-ink transition-colors">
            <Brain size={18} strokeWidth={1.75} />
          </div>
          <div className="text-left">
            <h2 className="font-syne font-bold text-xl text-ink">AI Consultation</h2>
            <p className="text-ink-3 text-xs font-syne">
              {isPaid
                ? "Unlimited questions · Claude AI"
                : `${remaining !== null ? remaining : FREE_LIMIT} of ${FREE_LIMIT} questions left today · Free`}
            </p>
          </div>
        </div>
        <div className="text-ink-3 group-hover:text-ink transition-colors">
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </button>

      {open && (
        <div className="mt-4 bg-surface border border-border rounded-xl overflow-hidden">
          {/* Upgrade banner for free users near limit */}
          {!isPaid && remaining !== null && remaining <= 1 && (
            <div className="flex items-center justify-between gap-3 px-4 py-2.5 bg-amber/10 border-b border-amber/20">
              <span className="text-xs font-syne text-amber-700">
                {remaining === 0 ? "Daily limit reached." : "Last question for today."}
                {" "}Upgrade for unlimited access.
              </span>
              <Link href="/upgrade" className="text-xs font-syne font-bold text-amber-700 hover:underline flex-shrink-0">
                Upgrade →
              </Link>
            </div>
          )}

          {/* Paid badge */}
          {isPaid && (
            <div className="flex items-center gap-1.5 px-4 py-2 border-b border-border bg-bg">
              <Zap size={12} strokeWidth={2} className="text-gold" />
              <span className="text-[11px] font-syne font-semibold text-gold">
                Claude AI · Unlimited
              </span>
            </div>
          )}

          {/* Messages */}
          <div className="px-4 py-4 space-y-4 max-h-80 overflow-y-auto">
            {messages.length === 0 && (
              <p className="text-ink-3 text-sm font-serif text-center py-4">
                Ask anything about &ldquo;{articleTitle}&rdquo;
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                {m.role === "ai" && (
                  <div className="w-7 h-7 rounded-lg bg-bg border border-border flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Brain size={13} strokeWidth={1.75} className="text-ink-3" />
                  </div>
                )}
                <div className={`max-w-[80%] px-4 py-2.5 rounded-xl text-sm leading-relaxed font-serif ${
                  m.role === "user"
                    ? "bg-ink text-white"
                    : "bg-bg border border-border text-ink-2"
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-lg bg-bg border border-border flex items-center justify-center flex-shrink-0">
                  <Brain size={13} strokeWidth={1.75} className="text-ink-3 animate-pulse" />
                </div>
                <div className="bg-bg border border-border rounded-xl px-4 py-2.5 text-sm text-ink-3 font-serif">
                  Thinking…
                </div>
              </div>
            )}
            {error && (
              <div className="text-xs text-red font-serif bg-red/5 border border-red/20 rounded-lg px-3 py-2">
                {error}{" "}
                {error.includes("limit") && (
                  <Link href="/upgrade" className="font-semibold underline">Upgrade →</Link>
                )}
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-4 py-3 border-t border-border flex gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
              placeholder={
                !isPaid && remaining === 0
                  ? "Daily limit reached — upgrade for more"
                  : "Ask a question about this article…"
              }
              disabled={loading || (!isPaid && remaining === 0)}
              className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:border-ink-2 transition-colors disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading || (!isPaid && remaining === 0)}
              className="w-9 h-9 rounded-lg bg-ink text-white flex items-center justify-center hover:bg-red transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
            >
              <Send size={15} strokeWidth={2} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
