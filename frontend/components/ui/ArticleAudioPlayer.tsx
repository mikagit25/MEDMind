"use client";

import { useEffect, useRef, useState } from "react";

type Gender = "female" | "male";
type Rate   = "-20%" | "-10%" | "+0%" | "+10%" | "+20%";

interface Props {
  articleId: string;
  locale?: string;
  title?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export function ArticleAudioPlayer({ articleId, locale = "en", title }: Props) {
  const [state, setState] = useState<"idle" | "loading" | "playing" | "paused" | "error">("idle");
  const [gender, setGender] = useState<Gender>("female");
  const [rate,   setRate]   = useState<Rate>("+0%");
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const buildSrc = (g: Gender, r: Rate) => {
    const params = new URLSearchParams({ locale, gender: g, rate: r });
    return `${API_URL}/tts/article/${articleId}?${params}`;
  };

  const cleanup = () => {
    const a = audioRef.current;
    if (a) {
      a.pause();
      a.removeAttribute("src");
      a.load();
    }
    setProgress(0);
    setDuration(0);
  };

  useEffect(() => () => { cleanup(); }, []);

  const load = (g: Gender = gender, r: Rate = rate) => {
    cleanup();
    setState("loading");

    const audio = new Audio();
    audioRef.current = audio;

    audio.preload = "none";
    audio.src = buildSrc(g, r);

    audio.addEventListener("loadedmetadata", () => setDuration(audio.duration));
    audio.addEventListener("timeupdate", () => setProgress(audio.currentTime));
    audio.addEventListener("ended", () => { setState("paused"); setProgress(0); });
    audio.addEventListener("error", () => setState("error"));
    audio.addEventListener("canplay", () => {
      // First data arrived — update state from loading to playing
      if (state === "loading" || audioRef.current === audio) {
        setState("playing");
      }
    });

    // Start playing immediately — browser streams while downloading
    audio.play()
      .then(() => setState("playing"))
      .catch(() => setState("error"));
  };

  const togglePlay = () => {
    if (!audioRef.current || audioRef.current.src === "" || audioRef.current.readyState === 0) {
      load();
      return;
    }
    if (state === "playing") {
      audioRef.current.pause();
      setState("paused");
    } else {
      audioRef.current.play().then(() => setState("playing")).catch(() => setState("error"));
    }
  };

  const seek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const t = parseFloat(e.target.value);
    if (audioRef.current) audioRef.current.currentTime = t;
    setProgress(t);
  };

  const changeGender = (g: Gender) => {
    setGender(g);
    cleanup();
    setState("idle");
  };

  const changeRate = (r: Rate) => {
    setRate(r);
    if (state !== "idle") {
      load(gender, r);
    }
  };

  const fmt = (s: number) => {
    if (!isFinite(s)) return "--:--";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="card p-4 my-4 border border-border">
      <div className="flex items-center gap-3">
        {/* Play/Pause */}
        <button
          onClick={togglePlay}
          disabled={state === "loading"}
          className="w-10 h-10 rounded-full bg-ink text-white flex items-center justify-center flex-shrink-0 hover:bg-ink-2 transition-colors disabled:opacity-50"
          aria-label={state === "playing" ? "Pause" : "Play"}
        >
          {state === "loading" ? (
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : state === "playing" ? (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          ) : (
            <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Info + progress */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-syne font-bold text-xs text-ink">
              {state === "idle"    ? "🔊 Listen to article" :
               state === "loading" ? "⏳ Starting audio…" :
               state === "error"   ? "❌ Audio unavailable" :
               title ? `🔊 ${title.slice(0, 40)}` : "🔊 Playing"}
            </span>
            {(state === "playing" || state === "paused") && (
              <span className="text-[10px] font-syne text-ink-3">
                {fmt(progress)}{duration > 0 ? ` / ${fmt(duration)}` : ""}
              </span>
            )}
          </div>

          {(state === "playing" || state === "paused") && (
            <input
              type="range"
              min={0}
              max={duration || 100}
              value={progress}
              onChange={seek}
              className="w-full h-1.5 rounded-full accent-ink cursor-pointer"
            />
          )}

          {state === "idle" && (
            <p className="font-serif text-[10px] text-ink-3">
              AI-narrated · Microsoft Neural Voice · {locale.toUpperCase()} · Streams instantly
            </p>
          )}
          {state === "loading" && (
            <div className="w-full h-1.5 rounded-full bg-surface-2 overflow-hidden">
              <div className="h-full bg-ink/30 animate-pulse rounded-full" style={{ width: "60%" }} />
            </div>
          )}
        </div>

        {/* Settings */}
        <button
          onClick={() => setExpanded(e => !e)}
          className="text-ink-3 hover:text-ink p-1 rounded transition-colors"
          title="Voice settings"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>

      {/* Expanded settings */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-border flex flex-wrap gap-4">
          <div>
            <div className="font-syne font-bold text-[10px] text-ink-3 uppercase mb-1.5">Voice</div>
            <div className="flex gap-1.5">
              {(["female", "male"] as Gender[]).map(g => (
                <button key={g} onClick={() => changeGender(g)}
                  className={`px-2.5 py-1 rounded font-syne text-xs border transition-colors ${
                    gender === g ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"
                  }`}>
                  {g === "female" ? "👩 Female" : "👨 Male"}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="font-syne font-bold text-[10px] text-ink-3 uppercase mb-1.5">Speed</div>
            <div className="flex gap-1.5">
              {(["-20%", "-10%", "+0%", "+10%", "+20%"] as Rate[]).map(r => (
                <button key={r} onClick={() => changeRate(r)}
                  className={`px-2 py-1 rounded font-syne text-xs border transition-colors ${
                    rate === r ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"
                  }`}>
                  {r === "+0%" ? "1×" : r === "+20%" ? "1.2×" : r === "+10%" ? "1.1×" : r === "-10%" ? "0.9×" : "0.8×"}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
