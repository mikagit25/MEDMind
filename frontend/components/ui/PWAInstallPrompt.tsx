"use client";

import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

type Mode = "android" | "ios" | null;

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [mode, setMode] = useState<Mode>(null);
  const [show, setShow] = useState(false);

  // Register service worker
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
    }
  }, []);

  useEffect(() => {
    // Already running as standalone PWA
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    const dismissed = localStorage.getItem("pwa_prompt_dismissed");
    if (dismissed && Date.now() - parseInt(dismissed) < 7 * 24 * 60 * 60 * 1000) return;

    const isIOS =
      /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

    if (isIOS) {
      // iOS: show manual instructions banner after 30s
      const t = setTimeout(() => {
        setMode("ios");
        setShow(true);
      }, 30_000);
      return () => clearTimeout(t);
    }

    // Android/Chrome: wait for browser install event, then show after 30s
    let timer: ReturnType<typeof setTimeout> | null = null;
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setMode("android");
      timer = setTimeout(() => setShow(true), 30_000);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      if (timer) clearTimeout(timer);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "dismissed") localStorage.setItem("pwa_prompt_dismissed", Date.now().toString());
    setShow(false);
    setDeferredPrompt(null);
  };

  const handleDismiss = () => {
    setShow(false);
    localStorage.setItem("pwa_prompt_dismissed", Date.now().toString());
  };

  if (!show) return null;

  return (
    <div className="fixed bottom-20 left-3 right-3 md:bottom-6 md:left-auto md:right-6 md:w-80 z-50 animate-fade-up">
      <div className="card p-4 shadow-xl border border-border flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-ink flex items-center justify-center flex-shrink-0 overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/icon-192.png" alt="MedMind" className="w-full h-full object-cover" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-syne font-bold text-sm text-ink">Install MedMind</div>

          {mode === "ios" ? (
            <div className="font-serif text-xs text-ink-3 mt-0.5 leading-snug">
              Tap the{" "}
              <span className="inline-block align-middle">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline">
                  <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                  <polyline points="16 6 12 2 8 6" />
                  <line x1="12" y1="2" x2="12" y2="15" />
                </svg>
              </span>{" "}
              Share button, then <strong>Add to Home Screen</strong>.
            </div>
          ) : (
            <div className="font-serif text-xs text-ink-3 mt-0.5">
              Study offline, faster access, push notifications.
            </div>
          )}

          <div className="flex gap-2 mt-3">
            {mode === "android" && (
              <button
                onClick={handleInstall}
                className="px-3 py-1.5 bg-ink text-white font-syne font-semibold text-xs rounded-lg hover:bg-ink-2 transition-colors"
              >
                Install
              </button>
            )}
            <button
              onClick={handleDismiss}
              className="px-3 py-1.5 text-ink-3 font-syne text-xs hover:text-ink transition-colors"
            >
              {mode === "ios" ? "Got it" : "Not now"}
            </button>
          </div>
        </div>
        <button onClick={handleDismiss} className="text-ink-3 hover:text-ink text-sm flex-shrink-0">✕</button>
      </div>
    </div>
  );
}
