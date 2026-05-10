"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

/** Reads auth state from localStorage (no Zustand needed — works on public pages). */
function useIsLoggedIn(): boolean | null {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  useEffect(() => {
    try {
      const stored = localStorage.getItem("medmind-auth");
      if (stored) {
        const parsed = JSON.parse(stored);
        setLoggedIn(!!parsed?.state?.isAuthenticated && !!parsed?.state?.user);
      } else {
        setLoggedIn(false);
      }
    } catch {
      setLoggedIn(false);
    }
  }, []);
  return loggedIn;
}

export function ArticleNav() {
  const loggedIn = useIsLoggedIn();

  return (
    <nav className="bg-surface border-b border-border sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-6">
        <Link href="/" className="font-syne font-extrabold text-xl text-ink tracking-tight">
          MedMind AI
        </Link>
        <div className="flex gap-4 text-sm font-serif text-ink-2">
          <Link href="/articles" className="hover:text-ink transition-colors">Articles</Link>
          <Link href="/pricing" className="hover:text-ink transition-colors">Pricing</Link>
          {loggedIn === null ? null : loggedIn ? null : (
            <Link href="/login" className="hover:text-ink transition-colors">Sign in</Link>
          )}
        </div>
        <div className="ml-auto flex gap-2">
          {loggedIn === null ? (
            // Skeleton while loading
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
