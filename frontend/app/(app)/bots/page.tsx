"use client";

import { useState, useEffect } from "react";
import { telegramApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import {
  MessageSquare, Zap, Heart, Brain, Bot, CheckCircle2,
  ExternalLink, Unlink, Copy, Check,
} from "lucide-react";

interface LinkResult {
  already_linked: boolean;
  telegram_chat_id?: string;
  code?: string;
  deep_link?: string;
  expires_in?: number;
}

const BOT_FEATURES = [
  {
    icon: Brain,
    title: "AI Medical Tutor",
    desc: "Ask any medical question and get instant, evidence-based answers — anytime, anywhere.",
  },
  {
    icon: Heart,
    title: "Health Tracking",
    desc: "Log symptoms, mood, and vitals via chat. Data syncs to your MedMind Health Hub.",
  },
  {
    icon: Zap,
    title: "Flashcard Reminders",
    desc: "Get daily reminders for spaced repetition reviews so you never forget what you've learned.",
  },
  {
    icon: MessageSquare,
    title: "Quick Consultations",
    desc: "Patient mode for non-specialists — safe, accessible health info with medical disclaimers.",
  },
];

export default function BotsPage() {
  const { user } = useAuthStore();
  const [linked, setLinked] = useState<boolean | null>(null);
  const [telegramId, setTelegramId] = useState<string | null>(null);
  const [linkData, setLinkData] = useState<LinkResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [unlinking, setUnlinking] = useState(false);
  const [copied, setCopied] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user?.telegram_chat_id) {
      setLinked(true);
      setTelegramId(user.telegram_chat_id);
    } else {
      setLinked(false);
    }
  }, [user]);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  async function handleConnect() {
    setLoading(true);
    setError("");
    try {
      const data: LinkResult = await telegramApi.generateWebLink();
      setLinkData(data);
      if (data.already_linked) {
        setLinked(true);
        setTelegramId(data.telegram_chat_id ?? null);
      } else if (data.expires_in) {
        setCountdown(data.expires_in);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to generate link. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleUnlink() {
    setUnlinking(true);
    try {
      await telegramApi.unlink();
      setLinked(false);
      setTelegramId(null);
      setLinkData(null);
    } catch {
      setError("Failed to unlink. Please try again.");
    } finally {
      setUnlinking(false);
    }
  }

  async function copyLink() {
    if (!linkData?.deep_link) return;
    await navigator.clipboard.writeText(linkData.deep_link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-10 space-y-10">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-50 mb-2">
          <Bot className="w-8 h-8 text-blue-600" />
        </div>
        <h1 className="font-syne font-black text-3xl text-ink">MedMind Telegram Bot</h1>
        <p className="font-serif text-base text-ink-2 max-w-md mx-auto">
          Your AI medical assistant — available 24/7 in Telegram. Link your account once and
          start chatting.
        </p>
      </div>

      {/* Connection status */}
      <div className="card p-6">
        {linked === null && (
          <div className="text-center text-ink-3 font-serif text-sm py-4">Loading…</div>
        )}

        {linked === true && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-6 h-6 text-green flex-shrink-0" />
              <div>
                <div className="font-syne font-bold text-ink">Telegram linked</div>
                {telegramId && (
                  <div className="text-xs text-ink-3 font-mono mt-0.5">ID: {telegramId}</div>
                )}
              </div>
            </div>
            <div className="flex gap-3">
              <a
                href="https://t.me/Medmindpro_bot"
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 btn-primary text-center py-2.5 rounded-xl font-syne font-semibold text-sm flex items-center justify-center gap-2"
              >
                Open Bot <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <button
                onClick={handleUnlink}
                disabled={unlinking}
                className="flex items-center gap-1.5 text-sm font-syne text-red border border-red/30 rounded-xl px-4 py-2.5 hover:bg-red/5 transition-colors disabled:opacity-50"
              >
                <Unlink className="w-4 h-4" />
                {unlinking ? "Unlinking…" : "Unlink"}
              </button>
            </div>
          </div>
        )}

        {linked === false && !linkData && (
          <div className="space-y-4">
            <p className="font-serif text-sm text-ink-2">
              Connect your Telegram account to start using the bot. The link expires in 10 minutes.
            </p>
            {error && (
              <p className="text-sm text-red font-serif">{error}</p>
            )}
            <button
              onClick={handleConnect}
              disabled={loading}
              className="w-full btn-primary py-3 rounded-xl font-syne font-semibold flex items-center justify-center gap-2"
            >
              <MessageSquare className="w-4 h-4" />
              {loading ? "Generating link…" : "Connect Telegram"}
            </button>
          </div>
        )}

        {linked === false && linkData && !linkData.already_linked && (
          <div className="space-y-5">
            <div className="text-center">
              <div className="font-syne font-bold text-ink mb-1">Your one-time code</div>
              <div className="inline-block font-mono font-black text-4xl text-ink tracking-widest bg-surface-2 rounded-2xl px-8 py-4 border border-border">
                {linkData.code}
              </div>
              {countdown > 0 && (
                <p className="text-xs text-ink-3 mt-2 font-serif">
                  Expires in {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, "0")}
                </p>
              )}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-serif text-ink-2 text-center">
                Open the bot and it will link automatically, or copy the link below:
              </p>
              <a
                href={linkData.deep_link}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full btn-primary py-3 rounded-xl font-syne font-semibold flex items-center justify-center gap-2 text-center"
              >
                Open in Telegram <ExternalLink className="w-4 h-4" />
              </a>
              <button
                onClick={copyLink}
                className="w-full border border-border rounded-xl py-2.5 font-syne text-sm text-ink-2 hover:bg-surface-2 transition-colors flex items-center justify-center gap-2"
              >
                {copied ? <Check className="w-4 h-4 text-green" /> : <Copy className="w-4 h-4" />}
                {copied ? "Copied!" : "Copy link"}
              </button>
            </div>

            <button
              onClick={() => { setLinkData(null); setError(""); }}
              className="w-full text-xs text-ink-3 hover:text-ink transition-colors font-serif py-1"
            >
              Generate new link
            </button>
          </div>
        )}
      </div>

      {/* Features */}
      <div>
        <h2 className="font-syne font-bold text-lg text-ink mb-5">What the bot can do</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {BOT_FEATURES.map((f) => (
            <div key={f.title} className="card p-5 flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-surface-2 flex items-center justify-center">
                <f.icon className="w-5 h-5 text-ink-2" />
              </div>
              <div>
                <div className="font-syne font-bold text-sm text-ink mb-1">{f.title}</div>
                <p className="font-serif text-xs text-ink-3 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bot commands reference */}
      <div className="card p-6">
        <h2 className="font-syne font-bold text-sm text-ink mb-4 uppercase tracking-wider">Bot commands</h2>
        <div className="space-y-2">
          {[
            { cmd: "/start", desc: "Link account or see welcome message" },
            { cmd: "/ask [question]", desc: "Ask the AI medical tutor" },
            { cmd: "/patient", desc: "Switch to patient-friendly mode" },
            { cmd: "/doctor", desc: "Switch to professional mode" },
            { cmd: "/remind", desc: "Enable daily flashcard reminders" },
            { cmd: "/log [symptom]", desc: "Log a health symptom to your profile" },
            { cmd: "/help", desc: "Show all available commands" },
          ].map(({ cmd, desc }) => (
            <div key={cmd} className="flex items-start gap-3 py-1.5 border-b border-border last:border-0">
              <code className="font-mono text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded flex-shrink-0">
                {cmd}
              </code>
              <span className="font-serif text-xs text-ink-2">{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
