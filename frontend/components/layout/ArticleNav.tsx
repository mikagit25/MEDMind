"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useAuthStore } from "@/lib/store";
import { isTokenExpired, isTokenFresh } from "@/lib/auth";
import { refreshApi } from "@/lib/api";

/**
 * Validates and silently refreshes the session on public pages (news, articles).
 * These pages don't have the (app)/layout.tsx session guard, so we do a lightweight
 * check here: if the access token is expired but we have a refresh token, swap them.
 * On failure we just clear auth state — no redirect (public page, user can still read).
 */
function usePublicPageAuth() {
  const { isAuthenticated, user, _hasHydrated, setAuth, logout } = useAuthStore();

  useEffect(() => {
    if (!_hasHydrated) return;

    async function syncSession() {
      const access  = localStorage.getItem("access_token");
      const refresh = localStorage.getItem("refresh_token");

      // Fresh token — nothing to do
      if (isTokenFresh(access)) return;

      // Expired access token + we have a refresh token → try to swap
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
          // Definitive auth failure → clear state (but stay on page — it's public)
          if (status === 401 || status === 403) logout();
        }
        return;
      }

      // No tokens at all and Zustand still says authenticated → stale state, clear it
      if (!access && !refresh && isAuthenticated) logout();
    }

    syncSession();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [_hasHydrated]);

  return { isAuthenticated, user, _hasHydrated };
}

export function ArticleNav() {
  const { isAuthenticated, user, _hasHydrated } = usePublicPageAuth();

  // null while Zustand is hydrating from localStorage (prevents flash of wrong state)
  const loggedIn: boolean | null = _hasHydrated
    ? (isAuthenticated && !!user)
    : null;

  return (
    <nav className="bg-surface border-b border-border sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-6">
        <Link href="/" className="font-syne font-extrabold text-xl text-ink tracking-tight">
          MedMind AI
        </Link>
        <div className="flex gap-4 text-sm font-serif text-ink-2">
          <Link href="/articles" className="hover:text-ink transition-colors">Articles</Link>
          <Link href="/news" className="hover:text-ink transition-colors">News</Link>
          <Link href="/calculators" className="hover:text-ink transition-colors">Calculators</Link>
          <Link href="/pricing" className="hover:text-ink transition-colors">Pricing</Link>
          {loggedIn ? null : loggedIn === false ? (
            <Link href="/login" className="hover:text-ink transition-colors">Sign in</Link>
          ) : null}
        </div>
        <div className="ml-auto flex gap-2">
          {loggedIn === null ? (
            <div className="w-24 h-7 rounded-lg bg-surface animate-pulse" />
          ) : loggedIn ? (
            <Link
              href="/dashboard"
              className="bg-ink text-white font-syne font-semibold text-sm px-4 py-1.5 rounded-lg hover:bg-ink-2 transition-colors"
            >
              Dashboard →
            </Link>
          ) : (
            <>
              <Link href="/login" className="text-ink-2 font-syne font-semibold text-sm px-3 py-1.5 hover:text-ink">
                Sign in
              </Link>
              <Link href="/register" className="bg-ink text-white font-syne font-semibold text-sm px-4 py-1.5 rounded-lg hover:bg-ink-2 transition-colors">
                Get started free
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
