"use client";

import Link from "next/link";
import { useState, useRef, useEffect, useCallback } from "react";
import { useAuthStore, useUIStore } from "@/lib/store";
import { telegramApi, API_URL } from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNavWrapper } from "@/components/layout/MobileNav";
import { useT, useI18n } from "@/lib/i18n";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  CheckCircle2, Link2, Link2Off, ExternalLink, RefreshCw, Copy, Check,
  Send, Bot, ChevronDown, ChevronUp, Trash2,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

type Message = { role: "user" | "assistant"; content: string };

// ── Consultation modes ─────────────────────────────────────────────────────────

const MODE_DEFS = [
  { id: "tutor",          emoji: "🎓", color: "blue"   },
  { id: "case",           emoji: "🩺", color: "purple" },
  { id: "differential",  emoji: "🔬", color: "green"  },
  { id: "patient",        emoji: "🏥", color: "orange" },
  { id: "second_opinion", emoji: "⚖️", color: "yellow" },
] as const;

type ModeId = (typeof MODE_DEFS)[number]["id"];

const MODE_COLOR: Record<string, string> = {
  blue:   "border-blue-500/50 text-blue-600 dark:text-blue-400",
  purple: "border-purple-500/50 text-purple-600 dark:text-purple-400",
  green:  "border-green-500/50 text-green-600 dark:text-green-400",
  orange: "border-orange-500/50 text-orange-600 dark:text-orange-400",
  yellow: "border-yellow-500/50 text-yellow-600 dark:text-yellow-400",
};

const STARTERS: Record<ModeId, string[]> = {
  tutor:          ["Explain the RAAS system", "Pathophysiology of heart failure", "How do beta-blockers work?"],
  case:           ["Start a cardiology case", "Give me a pneumonia case", "Present a neurology emergency"],
  differential:   ["35F, RLQ pain, fever, 6 weeks amenorrhea", "Chest pain + dyspnea in 60M", "Confusion in elderly patient"],
  patient:        ["My doctor said I have type 2 diabetes", "What is atrial fibrillation?", "Explain my kidney disease in simple terms"],
  second_opinion: ["Bisoprolol 10mg for HFrEF EF 30% — is this correct?", "Is metformin safe with my stage 3 CKD?"],
};

// ── Telegram icon ──────────────────────────────────────────────────────────────

function TgIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 13.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z" />
    </svg>
  );
}

// ── Telegram connect panel (collapsible) ──────────────────────────────────────

function TelegramPanel({ user, onUnlink }: {
  user: { telegram_chat_id?: string | null; subscription_tier: string };
  onUnlink: () => void;
}) {
  const t = useT();
  const isLinked = Boolean(user.telegram_chat_id);
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<"idle" | "loading" | "link_ready" | "unlinking">("idle");
  const [linkData, setLinkData] = useState<{ code: string; deep_link: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    setState("loading");
    try {
      const res = await telegramApi.generateWebLink();
      if (res.already_linked) { setState("idle"); return; }
      setLinkData({ code: res.code!, deep_link: res.deep_link! });
      setState("link_ready");
    } catch { setState("idle"); }
  };

  const handleUnlink = async () => {
    if (!confirm(t("bots_page.tg_confirm_unlink"))) return;
    setState("unlinking");
    try { await telegramApi.unlink(); onUnlink(); } catch {}
    setState("idle");
  };

  const handleCopy = () => {
    if (linkData) { navigator.clipboard.writeText(linkData.deep_link); setCopied(true); setTimeout(() => setCopied(false), 2000); }
  };

  return (
    <div className="border-b border-border bg-surface">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-syne text-ink-3 hover:text-ink transition-colors"
      >
        <TgIcon className="w-3.5 h-3.5 text-[#229ED9]" />
        <span className="flex-1 text-left">
          Telegram{" "}
          {isLinked
            ? <span className="text-green font-semibold">· {t("bots_page.tg_connected")}</span>
            : <span className="text-ink-3">· {t("bots_page.tg_optional")}</span>}
        </span>
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {open && (
        <div className="px-4 pb-4">
          {isLinked ? (
            <div className="flex items-center gap-3 p-3 bg-green/5 border border-green/20 rounded-xl">
              <CheckCircle2 size={16} className="text-green flex-shrink-0" />
              <div className="flex-1 text-xs font-serif text-ink-2">
                {t("bots_page.tg_linked_desc")}{" "}
                <Link href="/ai-history" className="text-[#229ED9] underline underline-offset-2">{t("bots_page.tg_ai_history")}</Link>.
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <a href="https://t.me/Medmindpro_bot" target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 bg-[#229ED9] text-white text-xs font-syne font-bold px-2.5 py-1.5 rounded-lg">
                  <TgIcon className="w-3 h-3" /> {t("bots_page.tg_btn_open")}
                </a>
                <button onClick={handleUnlink} disabled={state === "unlinking"}
                  className="inline-flex items-center gap-1 border border-border text-ink-3 hover:text-red hover:border-red text-xs font-syne px-2.5 py-1.5 rounded-lg transition-colors">
                  <Link2Off size={11} /> {t("bots_page.tg_btn_unlink")}
                </button>
              </div>
            </div>
          ) : (
            <div className="p-3 bg-bg border border-border rounded-xl">
              <p className="text-xs font-serif text-ink-3 mb-3">
                {t("bots_page.tg_link_info")}
              </p>
              {state === "link_ready" && linkData ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-1.5">
                    <span className="font-mono text-xs text-ink-2 flex-1 truncate">{linkData.deep_link}</span>
                    <button onClick={handleCopy} className="text-ink-3 hover:text-ink flex-shrink-0">
                      {copied ? <Check size={13} className="text-green" /> : <Copy size={13} />}
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <a href={linkData.deep_link} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 bg-[#229ED9] text-white text-xs font-syne font-bold px-3 py-1.5 rounded-lg">
                      <ExternalLink size={11} /> {t("bots_page.tg_open_in_tg")}
                    </a>
                    <button onClick={handleGenerate} className="inline-flex items-center gap-1.5 border border-border text-ink-3 text-xs font-syne px-3 py-1.5 rounded-lg">
                      <RefreshCw size={11} /> {t("bots_page.tg_new_link")}
                    </button>
                  </div>
                  <p className="text-[10px] text-ink-3 font-serif">{t("bots_page.tg_link_expires")}</p>
                </div>
              ) : (
                <button onClick={handleGenerate} disabled={state === "loading"}
                  className="inline-flex items-center gap-2 bg-[#229ED9] hover:bg-[#1a8cbf] disabled:opacity-60 text-white text-xs font-syne font-bold px-4 py-2 rounded-lg transition-colors">
                  {state === "loading"
                    ? <><span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" /> {t("bots_page.tg_generating")}</>
                    : <><TgIcon className="w-3.5 h-3.5" /> {t("bots_page.tg_connect")}</>}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Working chat ───────────────────────────────────────────────────────────────

function ConsultationChat({ mode, modeInfo }: { mode: ModeId; modeInfo: { emoji: string; label: string; desc: string } }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const { locale } = useI18n();
  const t = useT();
  const bottomRef = useRef<HTMLDivElement>(null);
  const STARTERS_I18N: Record<ModeId, string[]> = {
    tutor:          (t("bots_page.starters_tutor") as unknown as string[]) || STARTERS.tutor,
    case:           (t("bots_page.starters_case") as unknown as string[]) || STARTERS.case,
    differential:   (t("bots_page.starters_differential") as unknown as string[]) || STARTERS.differential,
    patient:        (t("bots_page.starters_patient") as unknown as string[]) || STARTERS.patient,
    second_opinion: (t("bots_page.starters_second_opinion") as unknown as string[]) || STARTERS.second_opinion,
  };
  const inputRef = useRef<HTMLTextAreaElement>(null);;

  useEffect(() => { setMessages([]); setInput(""); }, [mode]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    setInput("");

    setMessages(p => [
      ...p,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);
    setLoading(true);

    try {
      let token = localStorage.getItem("access_token");

      const makeReq = () => fetch(`${API_URL}/ai/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: text, mode, language: locale || "en" }),
      });

      let res = await makeReq();

      if (res.status === 401) {
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          const rr = await fetch(`${API_URL}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refresh }),
          });
          if (rr.ok) {
            const d = await rr.json();
            localStorage.setItem("access_token", d.access_token);
            localStorage.setItem("refresh_token", d.refresh_token);
            token = d.access_token;
            res = await makeReq();
          } else { window.location.href = "/login"; return; }
        } else { window.location.href = "/login"; return; }
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
            const ev = JSON.parse(line.slice(6));
            if (ev.type === "text") {
              setMessages(p => {
                const arr = [...p];
                arr[arr.length - 1] = { ...arr[arr.length - 1], content: arr[arr.length - 1].content + ev.text };
                return arr;
              });
            }
          } catch {}
        }
      }
    } catch (e: any) {
      setMessages(p => {
        const arr = [...p];
        arr[arr.length - 1] = { ...arr[arr.length - 1], content: `⚠️ ${e.message || "Something went wrong. Please try again."}` };
        return arr;
      });
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [mode, loading, locale]);

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); send(input); };
  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); }
  };
  const autoResize = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 128) + "px";
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          /* Empty state with starters */
          <div className="flex flex-col items-center justify-center min-h-full text-center py-8">
            <div className="text-5xl mb-3">{modeInfo.emoji}</div>
            <h2 className="font-syne font-bold text-base text-ink mb-1">{modeInfo.label}</h2>
            <p className="text-ink-3 text-sm max-w-xs leading-relaxed mb-8">{modeInfo.desc}</p>
            <div className="flex flex-wrap gap-2 justify-center max-w-md">
              {STARTERS_I18N[mode].map(s => (
                <button key={s} onClick={() => send(s)}
                  className="text-xs bg-surface border border-border hover:border-ink-3 text-ink-2 hover:text-ink font-syne px-3 py-1.5 rounded-lg transition-colors text-left">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                {msg.role === "assistant" && (
                  <div className="w-7 h-7 rounded-full bg-ink dark:bg-white/10 flex-shrink-0 flex items-center justify-center mt-0.5">
                    <Bot size={14} className="text-white" />
                  </div>
                )}
                <div className={`max-w-[80%] text-sm rounded-2xl px-4 py-2.5 leading-relaxed ${
                  msg.role === "user"
                    ? "bg-ink text-white rounded-tr-sm font-serif"
                    : "bg-surface border border-border text-ink rounded-tl-sm"
                }`}>
                  {msg.role === "assistant" ? (
                    msg.content ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <span className="inline-block w-4 h-4 border-2 border-ink-3/30 border-t-ink-3 rounded-full animate-spin" />
                    )
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-border px-4 py-3 flex-shrink-0">
        <form onSubmit={handleSubmit} className="flex gap-2 items-end max-w-3xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            onInput={autoResize}
            rows={1}
            disabled={loading}
            placeholder={t("bots_page.chat_placeholder") || "Ask anything…"}
            className="flex-1 resize-none bg-surface border border-border rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:border-ink-3 transition-colors overflow-hidden"
            style={{ minHeight: "42px", maxHeight: "128px" }}
          />
          <button type="submit" disabled={loading || !input.trim()}
            className="w-10 h-10 flex-shrink-0 flex items-center justify-center rounded-xl bg-ink text-white disabled:opacity-40 hover:bg-ink/80 transition-all">
            <Send size={15} />
          </button>
        </form>
        {messages.length > 0 && !loading && (
          <div className="flex justify-center mt-2">
            <button onClick={() => setMessages([])}
              className="inline-flex items-center gap-1 text-[10px] text-ink-3 hover:text-ink font-syne transition-colors">
              <Trash2 size={10} /> {t("bots_page.clear_chat") || "Clear conversation"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Authenticated app view ─────────────────────────────────────────────────────

function ConsultationApp({ user, onUnlink }: { user: any; onUnlink: () => void }) {
  const [mode, setMode] = useState<ModeId>("tutor");
  const t = useT();

  const MODES = MODE_DEFS.map(m => ({
    ...m,
    label: t(`ai_tutor.mode_${m.id}`) || m.id,
    desc: t(`ai_tutor.mode_${m.id}_desc`) || "",
  }));

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
      {/* Telegram panel — optional, collapsed by default */}
      <TelegramPanel user={user} onUnlink={onUnlink} />

      {/* Mode tabs */}
      <div className="border-b border-border bg-surface flex-shrink-0">
        <div className="flex overflow-x-auto scrollbar-hide px-3 py-2 gap-1.5">
          {MODES.map(m => (
            <button
              key={m.id}
              onClick={() => setMode(m.id as ModeId)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-syne font-semibold whitespace-nowrap flex-shrink-0 border transition-colors ${
                mode === m.id
                  ? `bg-ink text-white border-ink`
                  : `bg-transparent border-border text-ink-3 hover:text-ink hover:border-ink-3`
              }`}
            >
              <span>{m.emoji}</span>
              <span>{m.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chat */}
      <ConsultationChat key={mode} mode={mode} modeInfo={MODES.find(m => m.id === mode)!} />
    </div>
  );
}

// ── Public landing page (for unauthenticated users) ────────────────────────────

function StaticChatBubble({ role, text }: { role: string; text: string }) {
  const lines = text.split("\n");
  return (
    <div className={`flex gap-2 ${role === "user" ? "justify-end" : "justify-start"}`}>
      {role === "assistant" && (
        <div className="w-7 h-7 rounded-full bg-[#229ED9] flex-shrink-0 flex items-center justify-center text-white text-[10px] font-bold mt-0.5">AI</div>
      )}
      <div className={`max-w-[82%] text-xs rounded-xl px-3 py-2 leading-relaxed whitespace-pre-wrap ${
        role === "user"
          ? "bg-[#2B5278] text-white rounded-tr-sm"
          : "bg-[#182533] text-white/90 rounded-tl-sm"
      }`}>
        {lines.map((line, i) => {
          const parts = line.split(/(\*\*[^*]+\*\*)/g);
          return (
            <p key={i} className={i > 0 ? "mt-1" : ""}>
              {parts.map((p, j) =>
                p.startsWith("**") && p.endsWith("**")
                  ? <strong key={j}>{p.slice(2, -2)}</strong>
                  : p
              )}
            </p>
          );
        })}
      </div>
    </div>
  );
}

function PublicLanding() {
  const t = useT();
  const stats = t("bots_page.stats") as unknown as [string, string][];
  const steps = t("bots_page.steps") as unknown as { step: string; title: string; desc: string; icon: string }[];

  const PUBLIC_MODES = [
    {
      id: "tutor",
      icon: "🎓",
      label: t("bots_page.mode_tutor_label") as string,
      color: "bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400",
      dot: "bg-blue-500",
      desc: t("bots_page.mode_tutor_promo") as string,
      messages: [
        { role: "user",      text: "Explain the renin-angiotensin-aldosterone system" },
        { role: "assistant", text: "**RAAS** is a hormonal cascade that regulates blood pressure and fluid balance:\n\n↓ BP or ↓ Na⁺ → Kidney releases **renin** → converts angiotensinogen to Ang I → ACE converts to **Ang II** → vasoconstriction + aldosterone release → ↑ Na⁺/H₂O retention → ↑ BP\n\n💡 ACE inhibitors block this at the ACE step — first-line in diabetic nephropathy." },
      ],
    },
    {
      id: "case",
      icon: "🩺",
      label: t("bots_page.mode_case_label") as string,
      color: "bg-purple-500/10 border-purple-500/30 text-purple-600 dark:text-purple-400",
      dot: "bg-purple-500",
      desc: t("bots_page.mode_case_promo") as string,
      messages: [
        { role: "assistant", text: "**Case:** A 68-year-old male presents with 2 hours of crushing substernal chest pain radiating to the left arm. BP 90/60, HR 110, diaphoretic. ECG shows ST elevation in leads II, III, aVF.\n\nWhat is your working diagnosis and immediate management?" },
        { role: "user",      text: "Inferior STEMI — activate cath lab, aspirin, heparin" },
        { role: "assistant", text: "✅ Correct! Inferior STEMI (RCA territory).\n\n⚠️ Check a right-sided ECG (V4R) — 40% of inferior STEMIs have RV involvement. If so, **avoid nitrates and diuretics** (RV is preload-dependent)." },
      ],
    },
    {
      id: "differential",
      icon: "🔬",
      label: t("bots_page.mode_diff_label") as string,
      color: "bg-green-500/10 border-green-500/30 text-green-600 dark:text-green-400",
      dot: "bg-green-500",
      desc: t("bots_page.mode_diff_promo") as string,
      messages: [
        { role: "user",      text: "35F with acute RLQ pain, fever 38.4°C, nausea. Last period 6 weeks ago." },
        { role: "assistant", text: "**Most likely:**\n• Appendicitis (classic location + fever)\n• Ectopic pregnancy ⚠️ — critical given 6-week amenorrhea\n\n**Can't miss:** Ectopic with rupture — check β-hCG **now**\n\n**First investigations:** β-hCG → pelvic USS → CBC + CRP" },
      ],
    },
    {
      id: "patient",
      icon: "🏥",
      label: t("bots_page.mode_patient_label") as string,
      color: "bg-orange-500/10 border-orange-500/30 text-orange-600 dark:text-orange-400",
      dot: "bg-orange-500",
      desc: t("bots_page.mode_patient_promo") as string,
      messages: [
        { role: "user",      text: "My doctor said I have type 2 diabetes. What does that mean?" },
        { role: "assistant", text: "Type 2 diabetes means your body has trouble using sugar properly.\n\nNormally, **insulin** acts like a key that lets sugar into your cells. With type 2, that key doesn't work as well — so sugar builds up in your blood.\n\n✅ The good news: it's very manageable with healthy eating, exercise, and sometimes medication.\n\n⚕️ Always follow your doctor's specific advice." },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-bg">
      {/* Nav */}
      <nav className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link href="/" className="font-syne font-extrabold text-xl text-ink">Med<span className="text-red">Mind</span></Link>
          <div className="flex items-center gap-4">
            <Link href="/pricing" className="text-ink-3 hover:text-ink text-sm font-syne transition-colors hidden sm:block">{t("bots_page.nav_pricing")}</Link>
            <Link href="/register"
              className="inline-flex items-center gap-2 bg-ink hover:bg-ink/80 text-white font-syne font-bold text-sm px-4 py-2 rounded-lg transition-colors">
              {t("bots_page.nav_try_free")}
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 pt-14 sm:pt-20 pb-10 text-center">
        <div className="inline-flex items-center gap-2 bg-ink/5 border border-border px-3 py-1 rounded-full font-syne font-semibold text-xs text-ink-3 mb-5">
          <Bot size={13} /> AI Medical Consultation
        </div>
        <h1 className="font-syne font-extrabold text-3xl sm:text-5xl text-ink mb-4 leading-tight">
          {t("bots_page.hero_h1")}
        </h1>
        <p className="text-ink-2 text-base sm:text-lg max-w-2xl mx-auto mb-8 leading-relaxed">
          {t("bots_page.hero_p")}
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/register"
            className="inline-flex items-center justify-center gap-2 bg-ink hover:bg-ink/80 text-white font-syne font-bold px-8 py-4 rounded-xl text-base transition-colors">
            {t("bots_page.hero_cta_primary")}
          </Link>
          <a href="https://t.me/Medmindpro_bot" target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 border border-border text-ink-2 hover:border-ink hover:text-ink font-syne font-semibold px-8 py-4 rounded-xl text-base transition-colors">
            <TgIcon /> {t("bots_page.hero_cta_tg")}
          </a>
        </div>
        <p className="text-ink-3 text-xs mt-4 font-syne">{t("bots_page.hero_free_note")}</p>
      </section>

      {/* Stats */}
      <section className="border-y border-border bg-surface">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
          {stats.map(([val, label]) => (
            <div key={label}>
              <div className="font-syne font-extrabold text-2xl text-ink">{val}</div>
              <div className="font-serif text-xs text-ink-3 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Mode demos */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="text-center mb-12">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-3">{t("bots_page.modes_section_title")}</h2>
          <p className="text-ink-3 text-sm max-w-xl mx-auto">{t("bots_page.modes_section_hint")}</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {PUBLIC_MODES.map(mode => (
            <div key={mode.id} className="border border-border rounded-2xl overflow-hidden bg-surface">
              <div className="px-5 py-4 border-b border-border flex items-center gap-3">
                <span className="text-xl">{mode.icon}</span>
                <div>
                  <div className={`inline-flex items-center gap-1.5 text-xs font-syne font-semibold px-2 py-0.5 rounded-full border ${mode.color} mb-0.5`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${mode.dot}`} />
                    {mode.label}
                  </div>
                  <p className="text-xs text-ink-3 font-serif">{mode.desc}</p>
                </div>
              </div>
              <div className="bg-[#17212B] p-4 space-y-3 min-h-[160px]">
                {mode.messages.map((msg, i) => (
                  <StaticChatBubble key={i} role={msg.role} text={msg.text} />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Second opinion */}
        <div className="mt-6 border border-border rounded-2xl overflow-hidden bg-surface">
          <div className="px-5 py-4 border-b border-border flex items-center gap-3">
            <span className="text-xl">⚖️</span>
            <div>
              <div className="inline-flex items-center gap-1.5 text-xs font-syne font-semibold px-2 py-0.5 rounded-full border bg-yellow-500/10 border-yellow-500/30 text-yellow-600 dark:text-yellow-400 mb-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" /> {t("bots_page.mode_second_label")}
              </div>
              <p className="text-xs text-ink-3 font-serif">{t("bots_page.mode_second_promo")}</p>
            </div>
          </div>
          <div className="bg-[#17212B] p-4 grid sm:grid-cols-2 gap-3">
            <StaticChatBubble role="user" text="My cardiologist prescribed bisoprolol 10mg for my HFrEF diagnosis. EF is 30%. Is this correct?" />
            <StaticChatBubble role="assistant" text="Bisoprolol is one of 3 beta-blockers with proven mortality benefit in HFrEF — your cardiologist is on the right track.\n\n⚠️ Guideline note: Most guidelines recommend *starting low* (1.25mg) and uptitrating. Starting at 10mg upfront is unusual.\n\n💬 Ask: 'Should we start at a lower dose?'" />
          </div>
        </div>
      </section>

      {/* How to start */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-14">
          <h2 className="font-syne font-extrabold text-2xl text-ink text-center mb-10">{t("bots_page.steps_title")}</h2>
          <div className="grid sm:grid-cols-3 gap-8">
            {steps.map(s => (
              <div key={s.step} className="text-center">
                <div className="w-10 h-10 rounded-full bg-ink text-white font-syne font-bold text-lg flex items-center justify-center mx-auto mb-3">{s.step}</div>
                <div className="text-2xl mb-2">{s.icon}</div>
                <h3 className="font-syne font-bold text-sm text-ink mb-1">{s.title}</h3>
                <p className="font-serif text-xs text-ink-3 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-10">
            <Link href="/register"
              className="inline-flex items-center gap-2 bg-ink hover:bg-ink/80 text-white font-syne font-bold px-8 py-4 rounded-xl text-base transition-colors">
              {t("bots_page.modes_cta")}
            </Link>
          </div>
        </div>
      </section>

      {/* Telegram optional */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-[#229ED9]/10 border border-[#229ED9]/30 flex items-center justify-center flex-shrink-0">
              <TgIcon className="w-6 h-6 text-[#229ED9]" />
            </div>
            <div>
              <div className="font-syne font-bold text-sm text-ink">{t("bots_page.tg_also_available")}</div>
              <div className="font-serif text-xs text-ink-3">{t("bots_page.tg_link_account")}</div>
            </div>
          </div>
          <a href="https://t.me/Medmindpro_bot" target="_blank" rel="noopener noreferrer"
            className="flex-shrink-0 inline-flex items-center gap-2 border border-[#229ED9]/50 hover:bg-[#229ED9]/10 text-[#229ED9] font-syne font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors">
            <TgIcon /> {t("bots_page.nav_open")} @Medmindpro_bot
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Link href="/" className="font-syne font-extrabold text-lg text-ink">Med<span className="text-red">Mind</span></Link>
          <div className="flex gap-5 flex-wrap justify-center">
            {([
              { href: "/",            label: t("bots_page.footer_home") as string },
              { href: "/pricing",     label: t("bots_page.nav_pricing") as string },
              { href: "/articles",    label: "Articles" },
              { href: "/drugs",       label: "Drug DB" },
              { href: "/calculators", label: "Calculators" },
            ]).map(({ href, label }) => (
              <Link key={href} href={href} className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">
                {label}
              </Link>
            ))}
          </div>
          <p className="text-ink-3 text-xs font-syne">For educational purposes. Not a substitute for medical advice.</p>
        </div>
      </footer>
    </div>
  );
}

// ── Root export ────────────────────────────────────────────────────────────────

export default function BotsPage() {
  const { isAuthenticated, user, _hasHydrated, updateUser } = useAuthStore();
  const { darkMode } = useUIStore();
  const t = useT();

  useEffect(() => {
    if (isAuthenticated) document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode, isAuthenticated]);

  const handleUnlink = () => updateUser({ telegram_chat_id: null });

  if (!_hasHydrated) return <div className="min-h-screen bg-bg" />;

  // ── Public guest view ──
  if (!isAuthenticated) return <PublicLanding />;

  // ── Authenticated app view ──
  const appContent = (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden bg-bg dark:bg-[#1a1814]">
      {/* Page header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border flex-shrink-0">
        <Bot size={18} className="text-ink" />
        <h1 className="font-syne font-black text-base text-ink">{t("bots_page.consultation_title")}</h1>
        <span className="ml-auto text-[10px] font-syne text-ink-3 hidden sm:block">
          {t("bots_page.saved_to_history")}{" "}
          <Link href="/ai-history" className="underline underline-offset-2 hover:text-ink transition-colors">AI history</Link>
        </span>
      </div>

      <ConsultationApp user={user} onUnlink={handleUnlink} />
    </div>
  );

  return (
    <div className="flex h-dvh overflow-hidden bg-bg dark:bg-[#1a1814]">
      <div className="hidden md:flex">
        <Sidebar />
      </div>
      <div className="flex md:hidden flex-col flex-1 overflow-hidden min-h-0">
        <MobileNavWrapper>{appContent}</MobileNavWrapper>
      </div>
      <main className="hidden md:flex flex-1 flex-col overflow-hidden">
        {appContent}
      </main>
    </div>
  );
}
