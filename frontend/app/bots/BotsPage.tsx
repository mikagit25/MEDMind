"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useAuthStore, useUIStore } from "@/lib/store";
import { telegramApi } from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNavWrapper } from "@/components/layout/MobileNav";
import { useT } from "@/lib/i18n";
import {
  CheckCircle2, Link2, Link2Off, ExternalLink, RefreshCw, Copy, Check,
} from "lucide-react";

// ── Static chat examples ───────────────────────────────────────────────────────
const MODES = [
  {
    id: "tutor",
    icon: "🎓",
    labelKey: "tutor",
    color: "bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400",
    dot: "bg-blue-500",
    descKey: "tutor_desc",
    messages: [
      { role: "user", text: "Explain the renin-angiotensin-aldosterone system" },
      { role: "bot",  text: "**RAAS** is a hormonal cascade that regulates blood pressure and fluid balance:\n\n↓ BP or ↓ Na⁺ → Kidney releases **renin** → converts angiotensinogen to Ang I → ACE converts to **Ang II** → vasoconstriction + aldosterone release → ↑ Na⁺/H₂O retention → ↑ BP\n\n💡 Clinical Tip: ACE inhibitors block this at the ACE step — they're first-line in diabetic nephropathy because they reduce intraglomerular pressure." },
    ],
  },
  {
    id: "case",
    icon: "🩺",
    labelKey: "case",
    color: "bg-purple-500/10 border-purple-500/30 text-purple-600 dark:text-purple-400",
    dot: "bg-purple-500",
    descKey: "case_desc",
    messages: [
      { role: "bot",  text: "**Case:** A 68-year-old male presents with 2 hours of crushing substernal chest pain radiating to the left arm. BP 90/60, HR 110, diaphoretic. ECG shows ST elevation in leads II, III, aVF.\n\nWhat is your working diagnosis and immediate management?" },
      { role: "user", text: "Inferior STEMI — activate cath lab, aspirin, heparin, oxygen if <90% sat" },
      { role: "bot",  text: "✅ Correct! Inferior STEMI (RCA territory). Good call on the cath lab activation.\n\n⚠️ Important caveat: Check a right-sided ECG (V4R) — 40% of inferior STEMIs have RV involvement. If so, **avoid nitrates and diuretics** (RV is preload-dependent). What IV fluid would you give instead?" },
    ],
  },
  {
    id: "differential",
    icon: "🔬",
    labelKey: "differential",
    color: "bg-green-500/10 border-green-500/30 text-green-600 dark:text-green-400",
    dot: "bg-green-500",
    descKey: "differential_desc",
    messages: [
      { role: "user", text: "35F with acute right lower quadrant pain, fever 38.4°C, nausea. Last period 6 weeks ago." },
      { role: "bot",  text: "**Most likely:**\n• Appendicitis (classic location + fever)\n• Ectopic pregnancy ⚠️ — critical given 6-week amenorrhea\n\n**Expanded:**\n• Ovarian torsion (sudden onset, can have fever)\n• Tubo-ovarian abscess (PID complication)\n\n**Can't miss:**\n• Ectopic pregnancy with rupture — check β-hCG **now**\n\n**First 3 investigations:** β-hCG → pelvic USS → CBC + CRP" },
    ],
  },
  {
    id: "patient",
    icon: "🏥",
    labelKey: "patient",
    color: "bg-orange-500/10 border-orange-500/30 text-orange-600 dark:text-orange-400",
    dot: "bg-orange-500",
    descKey: "patient_desc",
    messages: [
      { role: "user", text: "My doctor said I have type 2 diabetes. What does that mean?" },
      { role: "bot",  text: "Type 2 diabetes means your body has trouble using sugar (glucose) properly.\n\nNormally, a hormone called **insulin** acts like a key that lets sugar into your cells for energy. With type 2 diabetes, that key doesn't work as well — so sugar builds up in your blood instead.\n\nThe good news: **it's very manageable** with:\n• Healthy eating (less sugary and processed foods)\n• Regular walking or exercise\n• Sometimes medication\n\n⚕️ Always follow your doctor's specific advice — this is general information only." },
    ],
  },
];

const MODE_LABELS: Record<string, string> = {
  tutor: "Tutor",
  tutor_desc: "Explains any medical topic clearly with key mechanisms and clinical pearls.",
  case: "Clinical Case",
  case_desc: "Interactive clinical case discussion — you play the resident, I play the attendant.",
  differential: "Differential Dx",
  differential_desc: "Structured differential diagnosis for any clinical presentation.",
  patient: "Patient Mode",
  patient_desc: "Plain language explanations — for patients and their families. No medical jargon.",
};

// ── Telegram SVG icon ──────────────────────────────────────────────────────────
function TgIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 13.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z" />
    </svg>
  );
}

// ── Chat bubble ────────────────────────────────────────────────────────────────
function ChatBubble({ role, text }: { role: "user" | "bot"; text: string }) {
  const lines = text.split("\n");
  return (
    <div className={`flex gap-2 ${role === "user" ? "justify-end" : "justify-start"}`}>
      {role === "bot" && (
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

// ── Telegram linking panel (for authenticated users) ──────────────────────────
function TelegramLinkPanel({ user, onUnlink }: {
  user: { email: string; first_name?: string; subscription_tier: string; telegram_chat_id?: string | null };
  onUnlink: () => void;
}) {
  const [state, setState] = useState<"idle" | "loading" | "link_ready" | "unlinking">("idle");
  const [linkData, setLinkData] = useState<{ code: string; deep_link: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const isLinked = Boolean(user.telegram_chat_id);

  const handleGenerateLink = async () => {
    setState("loading");
    try {
      const res = await telegramApi.generateWebLink();
      if (res.already_linked) {
        setState("idle");
        return;
      }
      setLinkData({ code: res.code!, deep_link: res.deep_link! });
      setState("link_ready");
    } catch {
      setState("idle");
    }
  };

  const handleUnlink = async () => {
    if (!confirm("Remove Telegram linking? You can re-link at any time.")) return;
    setState("unlinking");
    try {
      await telegramApi.unlink();
      onUnlink();
    } catch {}
    setState("idle");
  };

  const handleCopy = () => {
    if (linkData) {
      navigator.clipboard.writeText(linkData.deep_link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLinked) {
    return (
      <div className="bg-[#229ED9]/10 border border-[#229ED9]/30 rounded-2xl p-5 mb-6 flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-[#229ED9]/20 flex items-center justify-center flex-shrink-0">
          <CheckCircle2 className="w-5 h-5 text-[#229ED9]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-syne font-bold text-sm text-ink mb-0.5">Telegram Connected</div>
          <div className="font-serif text-xs text-ink-3 mb-3">
            Your MedMind account is linked. Bot conversations sync to your{" "}
            <Link href="/ai-history" className="text-[#229ED9] underline underline-offset-2">AI history</Link>.
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              href="https://t.me/Medmindpro_bot"
              target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 bg-[#229ED9] hover:bg-[#1a8cbf] text-white font-syne font-bold text-xs px-3 py-1.5 rounded-lg transition-colors"
            >
              <TgIcon className="w-3.5 h-3.5" /> Open Bot
            </a>
            <button
              onClick={handleUnlink}
              disabled={state === "unlinking"}
              className="inline-flex items-center gap-1.5 border border-border text-ink-3 hover:text-red hover:border-red font-syne text-xs px-3 py-1.5 rounded-lg transition-colors"
            >
              <Link2Off className="w-3 h-3" /> Unlink
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-2xl p-5 mb-6">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-[#229ED9]/10 flex items-center justify-center flex-shrink-0">
          <Link2 className="w-5 h-5 text-[#229ED9]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-syne font-bold text-sm text-ink mb-0.5">Connect Telegram to Your Account</div>
          <div className="font-serif text-xs text-ink-3 mb-4">
            Link your Telegram to unlock your {user.subscription_tier} plan in the bot and sync all conversations to your account history.
          </div>

          {state === "link_ready" && linkData ? (
            <div className="space-y-3">
              <div className="bg-bg border border-border rounded-xl p-3 flex items-center gap-2">
                <TgIcon className="w-4 h-4 text-[#229ED9] flex-shrink-0" />
                <span className="font-mono text-xs text-ink-2 flex-1 truncate">{linkData.deep_link}</span>
                <button onClick={handleCopy} className="text-ink-3 hover:text-ink transition-colors flex-shrink-0">
                  {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <a
                  href={linkData.deep_link}
                  target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 bg-[#229ED9] hover:bg-[#1a8cbf] text-white font-syne font-bold text-xs px-4 py-2 rounded-lg transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> Open in Telegram
                </a>
                <button
                  onClick={handleGenerateLink}
                  className="inline-flex items-center gap-1.5 border border-border text-ink-3 hover:text-ink font-syne text-xs px-3 py-2 rounded-lg transition-colors"
                >
                  <RefreshCw className="w-3 h-3" /> New link
                </button>
              </div>
              <p className="font-serif text-[10px] text-ink-3">⏱ Link expires in 10 minutes. Opens @Medmindpro_bot automatically.</p>
            </div>
          ) : (
            <button
              onClick={handleGenerateLink}
              disabled={state === "loading"}
              className="inline-flex items-center gap-2 bg-[#229ED9] hover:bg-[#1a8cbf] disabled:opacity-60 text-white font-syne font-bold text-sm px-5 py-2.5 rounded-xl transition-colors"
            >
              {state === "loading" ? (
                <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Generating…</>
              ) : (
                <><TgIcon className="w-4 h-4" /> Connect Telegram</>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page content ──────────────────────────────────────────────────────────
function BotsContent({ isAuthenticated, user, onUnlink }: {
  isAuthenticated: boolean;
  user: any;
  onUnlink: () => void;
}) {
  const t = useT();

  const stats = t("bots_page.stats") as unknown as [string, string][];
  const steps = t("bots_page.steps") as unknown as { step: string; title: string; desc: string; icon: string }[];
  const freeFeat = t("bots_page.plan_free_features") as unknown as string[];
  const proFeat  = t("bots_page.plan_pro_features")  as unknown as string[];

  return (
    <div className={isAuthenticated ? "flex-1 overflow-y-auto" : "min-h-screen bg-bg"}>

      {/* ── Nav (public only — app layout provides nav for auth users) ──── */}
      {!isAuthenticated && (
        <nav className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
            <Link href="/" className="font-syne font-extrabold text-xl text-ink">
              Med<span className="text-red">Mind</span>
            </Link>
            <div className="flex items-center gap-4">
              <Link href="/pricing" className="text-ink-3 hover:text-ink text-sm font-syne transition-colors hidden sm:block">
                {t("bots_page.nav_pricing")}
              </Link>
              <a
                href="https://t.me/Medmindpro_bot"
                target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-[#229ED9] hover:bg-[#1a8cbf] text-white font-syne font-bold text-sm px-4 py-2 rounded-lg transition-colors"
              >
                <TgIcon className="w-4 h-4" /> {t("bots_page.nav_open")}
              </a>
            </div>
          </div>
        </nav>
      )}

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-10 sm:pt-16 pb-8 sm:pb-10 text-center">
        <div className="inline-flex items-center gap-2 bg-[#229ED9]/10 border border-[#229ED9]/30 px-3 py-1 rounded-full font-syne font-semibold text-xs text-[#229ED9] mb-5">
          <TgIcon className="w-3.5 h-3.5" /> {t("bots_page.badge")}
        </div>
        <h1 className="font-syne font-extrabold text-3xl sm:text-5xl text-ink mb-4 leading-tight">
          {t("bots_page.title")}
        </h1>
        <p className="text-ink-2 text-base sm:text-lg max-w-2xl mx-auto mb-8 leading-relaxed">
          {t("bots_page.subtitle")}
        </p>

        {/* CTA — different for auth vs guest */}
        {isAuthenticated ? (
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <a
              href="https://t.me/Medmindpro_bot"
              target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 bg-[#229ED9] hover:bg-[#1a8cbf] text-white font-syne font-bold px-8 py-4 rounded-xl text-base transition-colors"
            >
              <TgIcon /> Open @Medmindpro_bot
            </a>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 border border-border text-ink-2 hover:border-ink hover:text-ink font-syne font-semibold px-8 py-4 rounded-xl text-base transition-colors"
            >
              Dashboard →
            </Link>
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <a
              href="https://t.me/Medmindpro_bot"
              target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 bg-[#229ED9] hover:bg-[#1a8cbf] text-white font-syne font-bold px-8 py-4 rounded-xl text-base transition-colors"
            >
              <TgIcon /> {t("bots_page.cta_open")}
            </a>
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 border border-border text-ink-2 hover:border-ink hover:text-ink font-syne font-semibold px-8 py-4 rounded-xl text-base transition-colors"
            >
              {t("bots_page.cta_register")}
            </Link>
          </div>
        )}
        <p className="text-ink-3 text-xs mt-4 font-syne">{t("bots_page.cta_note")}</p>
      </section>

      {/* ── Telegram account panel (auth users only) ─────────────────── */}
      {isAuthenticated && user && (
        <div className="max-w-2xl mx-auto px-4 sm:px-6">
          <TelegramLinkPanel user={user} onUnlink={onUnlink} />
        </div>
      )}

      {/* ── Stats strip ───────────────────────────────────────────────── */}
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

      {/* ── Mode demos ────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="text-center mb-12">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-3">{t("bots_page.modes_title")}</h2>
          <p className="text-ink-3 text-sm max-w-xl mx-auto">{t("bots_page.modes_hint")}</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {MODES.map(mode => (
            <div key={mode.id} className="border border-border rounded-2xl overflow-hidden bg-surface">
              <div className="px-5 py-4 border-b border-border flex items-center gap-3">
                <span className="text-xl">{mode.icon}</span>
                <div>
                  <div className={`inline-flex items-center gap-1.5 text-xs font-syne font-semibold px-2 py-0.5 rounded-full border ${mode.color} mb-0.5`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${mode.dot}`} />
                    {MODE_LABELS[mode.labelKey]}
                  </div>
                  <p className="text-xs text-ink-3 font-serif">{MODE_LABELS[mode.descKey]}</p>
                </div>
              </div>
              <div className="bg-[#17212B] p-4 space-y-3 min-h-[180px]">
                {mode.messages.map((msg, i) => (
                  <ChatBubble key={i} role={msg.role as "user" | "bot"} text={msg.text} />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* 5th mode: Second Opinion */}
        <div className="mt-8 border border-border rounded-2xl overflow-hidden bg-surface">
          <div className="px-5 py-4 border-b border-border flex items-center gap-3">
            <span className="text-xl">⚖️</span>
            <div>
              <div className="inline-flex items-center gap-1.5 text-xs font-syne font-semibold px-2 py-0.5 rounded-full border bg-yellow-500/10 border-yellow-500/30 text-yellow-600 dark:text-yellow-400 mb-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" /> Second Opinion
              </div>
              <p className="text-xs text-ink-3 font-serif">Review any treatment plan against current clinical guidelines.</p>
            </div>
          </div>
          <div className="bg-[#17212B] p-4 grid sm:grid-cols-2 gap-3">
            <ChatBubble role="user" text="My cardiologist prescribed bisoprolol 10mg for my new HFrEF diagnosis. EF is 30%. Is this correct?" />
            <ChatBubble role="bot" text="Bisoprolol is one of 3 beta-blockers with proven mortality benefit in HFrEF — your cardiologist is on the right track.\n\n⚠️ Guideline note: Most guidelines recommend *starting low* (1.25mg) and uptitrating over weeks to reach the target dose of 10mg. Starting at 10mg upfront is unusual.\n\n💬 Questions to ask your doctor:\n• 'Should we start at a lower dose?'\n• 'When should I schedule my next echo?'" />
          </div>
        </div>
      </section>

      {/* ── How to start ──────────────────────────────────────────────── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-14 sm:py-16">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink text-center mb-10">{t("bots_page.steps_title")}</h2>
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
            <a
              href="https://t.me/Medmindpro_bot"
              target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-[#229ED9] hover:bg-[#1a8cbf] text-white font-syne font-bold px-8 py-4 rounded-xl text-base transition-colors"
            >
              <TgIcon /> {t("bots_page.cta_try")}
            </a>
          </div>
        </div>
      </section>

      {/* ── Pricing ───────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="text-center mb-10">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">{t("bots_page.pricing_title")}</h2>
          <p className="text-ink-3 text-sm">{t("bots_page.pricing_sub")}</p>
        </div>
        <div className="grid sm:grid-cols-2 gap-6">
          <div className="rounded-2xl border-2 border-border p-6 relative bg-bg">
            <div className="font-syne font-bold text-lg text-ink mb-1">{t("bots_page.plan_free_name")}</div>
            <div className="flex items-baseline gap-1 mb-5">
              <span className="font-syne font-extrabold text-3xl text-ink">$0</span>
              <span className="text-ink-3 text-sm font-serif">{t("bots_page.plan_forever")}</span>
            </div>
            <ul className="space-y-2.5 mb-6">
              {freeFeat.map(f => (
                <li key={f} className="flex items-start gap-2 text-sm font-serif text-ink-2">
                  <svg className="w-4 h-4 text-green-2 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  {f}
                </li>
              ))}
            </ul>
            <a href="https://t.me/Medmindpro_bot" target="_blank" rel="noopener noreferrer"
              className="block w-full text-center font-syne font-bold py-3 rounded-xl text-sm border border-border hover:border-ink text-ink-2 hover:text-ink transition-colors">
              {t("bots_page.plan_free_cta")}
            </a>
          </div>
          <div className="rounded-2xl border-2 border-accent p-6 relative bg-surface shadow-lg">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-accent text-white text-xs font-syne font-bold px-4 py-1 rounded-full">{t("bots_page.plan_most_popular")}</div>
            <div className="font-syne font-bold text-lg text-ink mb-1">{t("bots_page.plan_pro_name")}</div>
            <div className="flex items-baseline gap-1 mb-5">
              <span className="font-syne font-extrabold text-3xl text-ink">$40</span>
              <span className="text-ink-3 text-sm font-serif">{t("bots_page.plan_month")}</span>
            </div>
            <ul className="space-y-2.5 mb-6">
              {proFeat.map(f => (
                <li key={f} className="flex items-start gap-2 text-sm font-serif text-ink-2">
                  <svg className="w-4 h-4 text-green-2 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  {f}
                </li>
              ))}
            </ul>
            <Link href="/pricing"
              className="block w-full text-center font-syne font-bold py-3 rounded-xl text-sm btn-primary transition-colors">
              {t("bots_page.plan_pro_cta")}
            </Link>
          </div>
        </div>
      </section>

      {/* ── Coming soon: WhatsApp ────────────────────────────────────── */}
      <section className="bg-surface border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-[#25D366]/10 border border-[#25D366]/30 flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 text-[#25D366]" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
              </svg>
            </div>
            <div>
              <div className="font-syne font-bold text-sm text-ink">{t("bots_page.whatsapp_title")}</div>
              <div className="font-serif text-xs text-ink-3">{t("bots_page.whatsapp_sub")}</div>
            </div>
          </div>
          {isAuthenticated ? (
            <Link href="/settings" className="flex-shrink-0 border border-border hover:border-ink font-syne font-semibold text-sm text-ink-2 hover:text-ink px-5 py-2.5 rounded-xl transition-colors">
              Notify me →
            </Link>
          ) : (
            <Link href="/register" className="flex-shrink-0 border border-border hover:border-ink font-syne font-semibold text-sm text-ink-2 hover:text-ink px-5 py-2.5 rounded-xl transition-colors">
              {t("bots_page.whatsapp_cta")}
            </Link>
          )}
        </div>
      </section>

      {/* ── Footer (public only — app layout has its own footer) ──────── */}
      {!isAuthenticated && (
        <footer className="border-t border-border">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link href="/" className="font-syne font-extrabold text-lg text-ink">
              Med<span className="text-red">Mind</span>
            </Link>
            <div className="flex gap-5 flex-wrap justify-center">
              {["/", "/pricing", "/articles", "/drugs", "/calculators"].map(href => (
                <Link key={href} href={href} className="text-ink-3 text-sm hover:text-ink transition-colors font-syne capitalize">
                  {href === "/" ? "Home" : href.replace("/", "")}
                </Link>
              ))}
            </div>
            <p className="text-ink-3 text-xs font-syne">{t("bots_page.footer_note")}</p>
          </div>
        </footer>
      )}
    </div>
  );
}

// ── Root export ────────────────────────────────────────────────────────────────
export default function BotsPage() {
  const { isAuthenticated, user, _hasHydrated, updateUser } = useAuthStore();
  const { darkMode } = useUIStore();

  // Apply dark mode when used as authenticated app page
  useEffect(() => {
    if (isAuthenticated) {
      document.documentElement.classList.toggle("dark", darkMode);
    }
  }, [darkMode, isAuthenticated]);

  const handleUnlink = () => {
    updateUser({ telegram_chat_id: null });
  };

  // Wait for Zustand hydration on client before deciding layout
  if (!_hasHydrated) {
    return <div className="min-h-screen bg-bg" />;
  }

  const content = (
    <BotsContent
      isAuthenticated={isAuthenticated}
      user={user}
      onUnlink={handleUnlink}
    />
  );

  // Authenticated: wrap in full app layout (sidebar + mobile nav)
  if (isAuthenticated) {
    return (
      <div className="flex h-dvh overflow-hidden bg-bg dark:bg-[#1a1814]">
        <div className="hidden md:flex">
          <Sidebar />
        </div>
        <div className="flex md:hidden flex-col flex-1 overflow-hidden min-h-0">
          <MobileNavWrapper>
            {content}
          </MobileNavWrapper>
        </div>
        <main className="hidden md:flex flex-1 flex-col overflow-hidden">
          {content}
        </main>
      </div>
    );
  }

  // Guest: public layout
  return content;
}
