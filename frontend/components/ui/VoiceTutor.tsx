"use client";

/**
 * VoiceTutor — voice I/O for the AI Tutor (V5 Phase 7).
 *
 * STT: Web Speech API (SpeechRecognition) — browser-native, no cost.
 * TTS: Edge TTS via /api/tts/speak — Microsoft Neural Voice.
 *
 * Key Phase 7 additions:
 *   - VoiceMicButton: recognized text exposed via onTranscript for CONFIRMATION
 *     before sending — the page shows a confirmation banner, not auto-send.
 *   - VoiceMicButton: autoStart prop for conversation mode (re-enables after TTS).
 *   - VoiceSpeakButton: onEnded callback so the page can restart the mic.
 *   - VoiceMicButton: patientMode prop — blocks STT with explanatory tooltip.
 *   - notSupportedFallback: visible message when Web Speech API is unavailable.
 */

import { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react";
import { ttsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

// ── SpeechRecognition browser types ──────────────────────────────────────────
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

const LANG_MAP: Record<string, string> = {
  ar: "ar-SA", ru: "ru-RU", de: "de-DE",
  fr: "fr-FR", es: "es-ES", tr: "tr-TR",
};

// ── Voice Mic Button (STT) ────────────────────────────────────────────────────

export interface VoiceMicHandle {
  /** Programmatically start listening (used by conversation mode). */
  startListening: () => void;
}

interface MicProps {
  /** Fired when recognition ends with a final transcript. Show for confirmation — do NOT auto-send. */
  onTranscript: (text: string) => void;
  disabled?: boolean;
  locale?: string;
  /** Block voice in patient mode — show tooltip, don't start recognition. */
  patientMode?: boolean;
  /** Auto-start when mounted or re-triggered (conversation loop). */
  autoStart?: boolean;
}

export const VoiceMicButton = forwardRef<VoiceMicHandle, MicProps>(function VoiceMicButton(
  { onTranscript, disabled, locale = "en", patientMode = false, autoStart = false },
  ref,
) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const [interimText, setInterimText] = useState("");
  const recRef = useRef<any>(null);

  const startListening = useCallback(() => {
    if (!recRef.current || patientMode) return;
    try { recRef.current.start(); setListening(true); } catch { /* already running */ }
  }, [patientMode]);

  useImperativeHandle(ref, () => ({ startListening }), [startListening]);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setSupported(false); return; }

    const rec = new SR() as any;
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = LANG_MAP[locale] ?? "en-US";

    rec.onresult = (e: any) => {
      const results = Array.from(e.results as any[]);
      const interim = results.map((r: any) => r[0].transcript).join(" ").trim();
      setInterimText(interim);

      const finalResults = results.filter((r: any) => r.isFinal);
      if (finalResults.length > 0) {
        const finalText = finalResults.map((r: any) => r[0].transcript).join(" ").trim();
        if (finalText) onTranscript(finalText);
        setInterimText("");
      }
    };
    rec.onend = () => { setListening(false); setInterimText(""); };
    rec.onerror = () => { setListening(false); setInterimText(""); };
    recRef.current = rec;
  }, [locale, onTranscript]);

  // Auto-start for conversation mode
  useEffect(() => {
    if (autoStart && supported && !patientMode) startListening();
  }, [autoStart]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = useCallback(() => {
    if (!recRef.current || patientMode) return;
    if (listening) {
      recRef.current.stop();
      setListening(false);
    } else {
      startListening();
    }
  }, [listening, patientMode, startListening]);

  if (!supported) {
    return (
      <div
        className="h-10 w-10 flex items-center justify-center rounded-xl border border-border text-ink-4 cursor-not-allowed flex-shrink-0"
        title="Voice input not supported in this browser. Try Chrome or Edge."
      >
        <svg className="w-4 h-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 4a3 3 0 013 3v4a3 3 0 01-6 0V7a3 3 0 013-3z" />
        </svg>
      </div>
    );
  }

  if (patientMode) {
    return (
      <div
        className="h-10 w-10 flex items-center justify-center rounded-xl border border-border text-ink-4 cursor-not-allowed flex-shrink-0 opacity-40"
        title="Voice input is disabled in Patient mode. Please type your question."
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 4a3 3 0 013 3v4a3 3 0 01-6 0V7a3 3 0 013-3z" />
        </svg>
      </div>
    );
  }

  return (
    <div className="relative flex-shrink-0">
      <button
        type="button"
        onClick={toggle}
        disabled={disabled}
        title={listening ? "Stop recording" : "Voice input (click to speak)"}
        className={`h-10 w-10 flex items-center justify-center rounded-xl border transition-all ${
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
      {/* Interim transcript tooltip while recognizing */}
      {listening && interimText && (
        <div className="absolute bottom-12 left-0 w-56 bg-ink text-white text-xs font-serif p-2 rounded-lg shadow-lg z-10 pointer-events-none">
          {interimText}
          <div className="absolute bottom-[-4px] left-4 w-2 h-2 bg-ink rotate-45" />
        </div>
      )}
    </div>
  );
});

// ── Voice Speak Button (TTS) ──────────────────────────────────────────────────

interface SpeakProps {
  text: string;
  locale?: string;
  autoPlay?: boolean;
  compact?: boolean;
  /** Called when audio finishes playing (for conversation mode to re-enable mic). */
  onEnded?: () => void;
}

export function VoiceSpeakButton({
  text,
  locale = "en",
  autoPlay = false,
  compact = false,
  onEnded,
}: SpeakProps) {
  const [state, setState] = useState<"idle" | "loading" | "playing" | "error">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const onEndedRef = useRef(onEnded);
  onEndedRef.current = onEnded;

  const cleanup = useCallback(() => {
    audioRef.current?.pause();
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
    setState("idle");
  }, []);

  useEffect(() => () => {
    audioRef.current?.pause();
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
  }, []);

  const play = useCallback(async () => {
    if (state === "playing") { cleanup(); return; }
    cleanup();
    setState("loading");
    try {
      const snippet = text.slice(0, 2000);
      const blob = await ttsApi.speakBlob(snippet, locale, "female");
      const url = URL.createObjectURL(blob);
      blobUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { cleanup(); onEndedRef.current?.(); };
      audio.onerror = () => setState("error");

      await audio.play();
      setState("playing");
    } catch {
      setState("error");
    }
  }, [state, text, locale, cleanup]);

  // Auto-play when text is set (voice mode response)
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

// ── Voice Mode Toggle ─────────────────────────────────────────────────────────

interface VoiceModeProps {
  active: boolean;
  onToggle: () => void;
}

export function VoiceModeToggle({ active, onToggle }: VoiceModeProps) {
  const t = useT();
  return (
    <button
      onClick={onToggle}
      title={active ? "Disable voice mode" : "Enable voice mode (auto-reads AI responses)"}
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
      {active ? (t("ai_tutor.voice_on") as string) || "Voice ON" : (t("ai_tutor.voice") as string) || "Voice"}
    </button>
  );
}

// ── Conversation Mode Toggle ──────────────────────────────────────────────────

interface ConversationModeProps {
  active: boolean;
  onToggle: () => void;
}

export function ConversationModeToggle({ active, onToggle }: ConversationModeProps) {
  return (
    <button
      onClick={onToggle}
      title={
        active
          ? "Conversation mode ON — mic re-enables after each AI response"
          : "Enable conversation mode — hands-free back-and-forth"
      }
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-syne font-semibold text-xs border transition-all ${
        active
          ? "bg-blue/20 text-blue border-blue/40 shadow-sm"
          : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
      }`}
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
      {active ? "Loop ON" : "Loop"}
    </button>
  );
}
