"use client";

import Link from "next/link";
import { useAuthStore } from "@/lib/store";

interface Props {
  startFreeLabel: string;
  viewPricingLabel: string;
}

export function ArticlesFooterCTA({ startFreeLabel, viewPricingLabel }: Props) {
  const { isAuthenticated, _hasHydrated } = useAuthStore();
  const loggedIn = _hasHydrated ? isAuthenticated : null;

  return (
    <div className="flex gap-3">
      {loggedIn === null ? (
        <div className="w-32 h-9 rounded-lg bg-surface animate-pulse" />
      ) : loggedIn ? (
        <Link
          href="/dashboard"
          className="bg-ink text-white font-syne font-semibold text-sm px-5 py-2 rounded-lg hover:bg-ink-2 transition-colors"
        >
          Dashboard →
        </Link>
      ) : (
        <Link
          href="/register"
          className="bg-ink text-white font-syne font-semibold text-sm px-5 py-2 rounded-lg hover:bg-ink-2 transition-colors"
        >
          {startFreeLabel}
        </Link>
      )}
      <Link
        href="/pricing"
        className="border border-border text-ink font-syne font-semibold text-sm px-5 py-2 rounded-lg hover:border-ink transition-colors"
      >
        {viewPricingLabel}
      </Link>
    </div>
  );
}
