"use client";

/**
 * VoiceTutor — voice I/O for the AI Tutor.
 *
 * STT: Web Speech API (SpeechRecognition) — browser-native, no cost.
 * TTS: Edge TTS via /api/tts/speak — Microsoft Neural Voice.
 *
 * Usage:
 *   <VoiceMicButton onTranscript={(text) => setInput(text)} disabled={loading} />
 *   <VoiceSpeakButton text={aiReply} locale="en" autoPlay />
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ttsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

// ── SpeechRecognition browser types ──────────────────────────────────────────
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

// ── Voice Mic Button (STT) ────────────────────────────────────────────────────

interface MicProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  locale?: string;
}

export function VoiceMicButton({ onTranscript, disabled, locale = "en" }: MicProps) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const recRef = useRef<any>(null);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setSupported(false); return; }

    const rec = new SR() as any;
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = locale === "ar" ? "ar-SA"
              : locale === "ru" ? "ru-RU"
              : locale === "de" ? "de-DE"
              : locale === "fr" ? "fr-FR"
              : locale === "es" ? "es-ES"
              : locale === "tr" ? "tr-TR"
              : "en-US";

    rec.onresult = (e: any) => {
      const text = Array.from(e.results as any[])
        .map((r: any) => r[0].transcript)
        .join(" ")
        .trim();
      if (text) onTranscript(text);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
  }, [locale, onTranscript]);

  const toggle = useCallback(() => {
    if (!recRef.current) return;
    if (listening) {
      recRef.current.stop();
      setListening(false);
    } else {
      recRef.current.start();
      setListening(true);
    }
  }, [listening]);

  if (!supported) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={disabled}
      title={listening ? "Stop recording" : "Voice input"}
      className={`h-10 w-10 flex items-center justify-center rounded-xl border transition-all flex-shrink-0 ${
        listening
          ? "bg-red border-red text-white animate-pulse"
          : "border-border text-ink-3 hover:border-ink-3 hover:text-ink bg-surface"
      } disabled:opacity-40`}
    >
      {listening ? (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <rect x="9" y="9" width="6" height="6" rx="1" />
          <path d="M12 1a3 3 0 0 0-3 3v4a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" opacity="0.4" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 4a3 3 0 013 3v4a3 3 0 01-6 0V7a3 3 0 013-3z" />
        </svg>
      )}
    </button>
  );
}

// ── Voice Speak Button (TTS) ──────────────────────────────────────────────────

interface SpeakProps {
  text: string;
  locale?: string;
  autoPlay?: boolean;
  compact?: boolean;
}

export function VoiceSpeakButton({ text, locale = "en", autoPlay = false, compact = false }: SpeakProps) {
  const [state, setState] = useState<"idle" | "loading" | "playing" | "error">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  const cleanup = useCallback(() => {
    audioRef.current?.pause();
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
    setState("idle");
  }, []);

  useEffect(() => () => { audioRef.current?.pause(); if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current); }, []);

  const play = useCallback(async () => {
    if (state === "playing") { cleanup(); return; }
    cleanup();
    setState("loading");
    try {
      // Truncate to 2000 chars for quick playback
      const snippet = text.slice(0, 2000);
      const blob = await ttsApi.speakBlob(snippet, locale, "female");
      const url = URL.createObjectURL(blob);
      blobUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = cleanup;
      audio.onerror = () => setState("error");

      await audio.play();
      setState("playing");
    } catch {
      setState("error");
    }
  }, [state, text, locale, cleanup]);

  // Auto-play when text changes (for voice mode)
  useEffect(() => {
    if (autoPlay && text) play();
  }, [text]); // eslint-disable-line react-hooks/exhaustive-deps

  if (compact) {
    return (
      <button
        onClick={play}
        disabled={state === "loading"}
        title={state === "playing" ? "Stop" : "Listen"}
        className={`p-1 rounded transition-colors ${
          state === "playing" ? "text-blue" : "text-ink-3/50 hover:text-ink-3"
        } disabled:opacity-40`}
      >
        {state === "loading" ? (
          <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
        ) : state === "playing" ? (
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M15.536 8.464a5 5 0 010 7.072M12 6.343a8 8 0 010 11.314M9 10l.01 4M6 10l.01 4" />
          </svg>
        )}
      </button>
    );
  }

  return (
    <button
      onClick={play}
      disabled={state === "loading"}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-syne text-xs border transition-colors ${
        state === "playing"
          ? "bg-blue-light border-blue/20 text-blue"
          : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
      } disabled:opacity-40`}
    >
      {state === "loading" ? (
        <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
      ) : state === "playing" ? (
        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M15.536 8.464a5 5 0 010 7.072M12 6.343a8 8 0 010 11.314" />
        </svg>
      )}
      {state === "playing" ? "Stop" : "Listen"}
    </button>
  );
}

// ── Voice Mode Toggle (for AI Tutor header) ───────────────────────────────────
interface VoiceModeProps {
  active: boolean;
  onToggle: () => void;
}

export function VoiceModeToggle({ active, onToggle }: VoiceModeProps) {
  const t = useT();
  return (
    <button
      onClick={onToggle}
      title={active ? "Disable voice mode" : "Enable voice mode"}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-syne font-semibold text-xs border transition-all ${
        active
          ? "bg-blue text-white border-blue shadow-sm"
          : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
      }`}
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 4a3 3 0 013 3v4a3 3 0 01-6 0V7a3 3 0 013-3z" />
      </svg>
      {active ? t("ai_tutor.voice_on") as string || "Voice ON" : t("ai_tutor.voice") as string || "Voice"}
    </button>
  );
}
