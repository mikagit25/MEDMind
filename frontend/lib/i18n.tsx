"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import type { Translations } from "@/locales/en";
import en from "@/locales/en";

// ─────────────────────────────────────────────────────────────────────────────
// Supported locales
// ─────────────────────────────────────────────────────────────────────────────
export type Locale = "en" | "ru" | "ar" | "tr" | "de" | "fr" | "es";

export const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  ru: "Русский",
  ar: "العربية",
  tr: "Türkçe",
  de: "Deutsch",
  fr: "Français",
  es: "Español",
};

export const RTL_LOCALES: Locale[] = ["ar"];

const STORAGE_KEY = "medmind_locale";

// Lazy load locale bundles
async function loadLocale(locale: Locale): Promise<Translations> {
  switch (locale) {
    case "ru": return (await import("@/locales/ru")).default;
    case "ar": return (await import("@/locales/ar")).default;
    case "tr": return (await import("@/locales/tr")).default;
    case "de": return (await import("@/locales/de")).default;
    case "fr": return (await import("@/locales/fr")).default;
    case "es": return (await import("@/locales/es")).default;
    default: return en;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Deep key lookup with dot notation: t("common.save") → "Сохранить"
// ─────────────────────────────────────────────────────────────────────────────
type DeepValue<T, K extends string> =
  K extends `${infer A}.${infer B}`
    ? A extends keyof T
      ? DeepValue<T[A], B>
      : never
    : K extends keyof T
      ? T[K]
      : never;

function deepGet(obj: Record<string, unknown>, path: string): string {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const part of parts) {
    if (cur == null || typeof cur !== "object") return path;
    cur = (cur as Record<string, unknown>)[part];
  }
  if (typeof cur === "string") return cur;
  return path; // key not found — return key itself as fallback
}

// ─────────────────────────────────────────────────────────────────────────────
// Context
// ─────────────────────────────────────────────────────────────────────────────
interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  isRTL: boolean;
  loading: boolean;
}

const I18nContext = createContext<I18nContextValue | null>(null);

// ─────────────────────────────────────────────────────────────────────────────
// Provider
// ─────────────────────────────────────────────────────────────────────────────
export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [messages, setMessages] = useState<Translations>(en);
  const [loading, setLoading] = useState(false);

  // Initialise from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
    if (stored && stored in LOCALE_LABELS) {
      switchLocale(stored);
      return;
    }
    // Detect browser language
    const browserLang = navigator.language?.split("-")[0]?.toLowerCase();
    const detected = (["en","ru","ar","tr","de","fr","es"] as Locale[]).find(l => l === browserLang);
    if (detected && detected !== "en") {
      switchLocale(detected);
    }
  }, []);

  // Apply dir attribute to <html> for RTL support
  useEffect(() => {
    document.documentElement.dir = RTL_LOCALES.includes(locale) ? "rtl" : "ltr";
    document.documentElement.lang = locale;
  }, [locale]);

  const switchLocale = useCallback(async (next: Locale) => {
    setLoading(true);
    try {
      const bundle = await loadLocale(next);
      setMessages(bundle);
      setLocaleState(next);
      localStorage.setItem(STORAGE_KEY, next);
      // Also set cookie for SSR access
      document.cookie = `medmind_locale=${next};path=/;max-age=31536000;SameSite=Lax`;
    } finally {
      setLoading(false);
    }
  }, []);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>): string => {
      let str = deepGet(messages as unknown as Record<string, unknown>, key);
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          str = str.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
        });
      }
      return str;
    },
    [messages]
  );

  return (
    <I18nContext.Provider
      value={{
        locale,
        setLocale: switchLocale,
        t,
        isRTL: RTL_LOCALES.includes(locale),
        loading,
      }}
    >
      {children}
    </I18nContext.Provider>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────────────────────
export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}

/** Shorthand: const t = useT() */
export function useT(): I18nContextValue["t"] {
  return useI18n().t;
}
