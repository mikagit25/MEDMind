"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useAuthStore } from "@/lib/store";
import { useI18n } from "@/lib/i18n";
import { isTokenExpired, isTokenFresh } from "@/lib/auth";
import { refreshApi } from "@/lib/api";

type Locale = "en" | "ru" | "ar" | "de" | "fr" | "es" | "tr";

const LANGS: { value: Locale; flag: string }[] = [
  { value: "en", flag: "🇬🇧" },
  { value: "ru", flag: "🇷🇺" },
  { value: "de", flag: "🇩🇪" },
  { value: "fr", flag: "🇫🇷" },
  { value: "ar", flag: "🇸🇦" },
  { value: "tr", flag: "🇹🇷" },
  { value: "es", flag: "🇪🇸" },
];

/**
 * Silently validates / refreshes the session on public pages.
 * These pages don't have the (app)/layout.tsx session guard.
 */
function usePublicPageAuth() {
  const { isAuthenticated, user, _hasHydrated, setAuth, logout } = useAuthStore();

  useEffect(() => {
    if (!_hasHydrated) return;

    async function syncSession() {
      const access  = localStorage.getItem("access_token");
      const refresh = localStorage.getItem("refresh_token");

      if (isTokenFresh(access)) return;

      if (isTokenExpired(access) && refresh) {
        try {
          const res = await refreshApi.post("/auth/refresh", { refresh_token: refresh });
          const newAccess: string  = res.data.access_token;
          const newRefresh: string = res.data.refresh_token;
          localStorage.setItem("access_token", newAccess);
          localStorage.setItem("refresh_token", newRefresh);
          if (user) setAuth(user, newAccess, newRefresh);
        } catch (err: any) {
          const status = err?.response?.status;
          if (status === 401 || status === 403) logout();
        }
        return;
      }

      if (!access && !refresh && isAuthenticated) logout();
    }

    syncSession();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [_hasHydrated]);

  return { isAuthenticated, user, _hasHydrated };
}

export function ArticleNav() {
  const { isAuthenticated, user, _hasHydrated } = usePublicPageAuth();
  const { locale, setLocale, t, isRTL } = useI18n();

  const loggedIn: boolean | null = _hasHydrated ? (isAuthenticated && !!user) : null;

  const navLinks = [
    { href: "/articles",    label: t("landing.nav_articles") },
    { href: "/news",        label: t("landing.nav_news") },
    { href: "/calculators", label: t("landing.nav_calculators") },
    { href: "/drugs",       label: t("landing.nav_drugs") },
    { href: "/pricing",     label: t("landing.nav_pricing") },
  ];

  return (
    <nav className="bg-surface border-b border-border sticky top-0 z-50" dir={isRTL ? "rtl" : "ltr"}>
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-4">
        {/* Logo */}
        <Link href="/" className="font-syne font-extrabold text-xl text-ink tracking-tight flex-shrink-0">
          MedMind AI
        </Link>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-1 flex-1">
          {navLinks.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-1.5"
            >
              {item.label}
            </Link>
          ))}
        </div>

        {/* Right side: language switcher + auth */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Language switcher */}
          <select
            value={locale}
            onChange={e => setLocale(e.target.value as Locale)}
            className="text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none cursor-pointer"
            aria-label="Language"
          >
            {LANGS.map(l => (
              <option key={l.value} value={l.value}>{l.flag}</option>
            ))}
          </select>

          {/* Auth button */}
          {loggedIn === null ? (
            <div className="w-24 h-7 rounded-lg bg-surface animate-pulse" />
          ) : loggedIn ? (
            <Link
              href="/dashboard"
              className="bg-ink text-white font-syne font-semibold text-sm px-4 py-1.5 rounded-lg hover:bg-ink/80 transition-colors whitespace-nowrap"
            >
              Dashboard →
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden sm:block text-ink-2 font-syne font-semibold text-sm px-3 py-1.5 hover:text-ink transition-colors"
              >
                {t("landing.nav_sign_in")}
              </Link>
              <Link
                href="/register"
                className="bg-ink text-white font-syne font-semibold text-sm px-4 py-1.5 rounded-lg hover:bg-ink/80 transition-colors whitespace-nowrap"
              >
                {t("landing.hero_cta") || "Get started free"}
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
