"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore, useUIStore } from "@/lib/store";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileNavWrapper } from "@/components/layout/MobileNav";
import { AchievementToast, AchievementToastData } from "@/components/ui/AchievementToast";
import { GlobalSearch } from "@/components/ui/GlobalSearch";
import { achievementsApi, authApi, refreshApi } from "@/lib/api";
import { isTokenFresh, isTokenExpired, markMeChecked, wasMeCheckedRecently, clearMeCache } from "@/lib/auth";

const ACHIEVEMENT_META: Record<string, { name: string; icon: string; xp: number }> = {
  first_lesson:    { name: "First Steps",        icon: "🎓", xp: 50 },
  module_complete: { name: "Module Master",       icon: "📚", xp: 200 },
  streak_3:        { name: "On Fire",             icon: "🔥", xp: 75 },
  streak_7:        { name: "Dedicated",           icon: "🌟", xp: 200 },
  streak_30:       { name: "Iron Will",           icon: "💪", xp: 1000 },
  flashcard_10:    { name: "Card Shark",          icon: "🃏", xp: 50 },
  flashcard_50:    { name: "Flashcard Pro",       icon: "🃏", xp: 150 },
  mcq_10:          { name: "Quiz Taker",          icon: "❓", xp: 50 },
  mcq_100:         { name: "Quiz Champion",       icon: "💯", xp: 300 },
  ai_learner:      { name: "AI Learner",          icon: "🤖", xp: 75 },
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user, _hasHydrated, setAuth, logout } = useAuthStore();
  const { darkMode } = useUIStore();
  const router = useRouter();
  const pathname = usePathname();
  const [toast, setToast] = useState<AchievementToastData | null>(null);
  const [tokenChecked, setTokenChecked] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  // After Zustand hydrates, validate session smartly (no API call if token is fresh)
  useEffect(() => {
    if (!_hasHydrated) return;

    async function validateSession() {
      const storedAccess  = localStorage.getItem("access_token");
      const storedRefresh = localStorage.getItem("refresh_token");

      // Case 1: No stored credentials and no Zustand state
      // Public pages (drugs, imaging) are accessible without login
      if (!storedAccess && !storedRefresh && !isAuthenticated) {
        const PUBLIC_PATHS = ["/drugs", "/imaging"];
        const isPublic = PUBLIC_PATHS.some(p => pathname.startsWith(p));
        if (isPublic) {
          setTokenChecked(true); // show page without auth
          return;
        }
        setTokenChecked(true);
        router.push("/login");
        return;
      }

      // Case 2: Access token is fresh AND we have a user in store → no network call needed
      // Use localStorage as the me-cache key (persists across tabs) instead of sessionStorage
      if (isTokenFresh(storedAccess) && isAuthenticated && user) {
        setTokenChecked(true);
        return;
      }

      // Case 3: Access token is fresh but no user in store yet → call /auth/me once
      if (isTokenFresh(storedAccess)) {
        try {
          const me = await authApi.me();
          setAuth(me, storedAccess!, storedRefresh ?? "");
          markMeChecked();
        } catch (err: any) {
          if (!err?.response) {
            // Pure network error — stay logged in if we have a user
            if (isAuthenticated && user) { setTokenChecked(true); return; }
          }
          // 401 is auto-handled by interceptor (refreshes token); if it propagates, fall through
        }
        setTokenChecked(true);
        return;
      }

      // Case 4: Access token expired — try refresh using refreshApi (no interceptor loop)
      if (storedRefresh) {
        try {
          const res = await refreshApi.post("/auth/refresh", { refresh_token: storedRefresh });
          const newAccess: string = res.data.access_token;
          const newRefresh: string = res.data.refresh_token;
          localStorage.setItem("access_token", newAccess);
          localStorage.setItem("refresh_token", newRefresh);

          const me = await authApi.me();
          setAuth(me, newAccess, newRefresh);
          markMeChecked();
          setTokenChecked(true);
          return;
        } catch (refreshErr: any) {
          // If refresh returns 401/403, our token is genuinely invalid → logout
          // If it's a network error, stay logged in
          const status = refreshErr?.response?.status;
          if (!status) {
            // Network failure — keep session if we have one
            if (isAuthenticated && user) { setTokenChecked(true); return; }
          }
          // Definitive auth failure → logout
        }
      }

      // Case 5: Nothing worked → login (unless it's a public page)
      const PUBLIC_PATHS = ["/drugs", "/imaging"];
      const isPublicPath = PUBLIC_PATHS.some(p => pathname.startsWith(p));
      logout();
      clearMeCache();
      setTokenChecked(true);
      if (!isPublicPath) router.push("/login");
    }

    validateSession();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [_hasHydrated]);

  // Redirect to onboarding if not completed (skip for admin/teacher — they don't need it)
  useEffect(() => {
    if (
      tokenChecked && isAuthenticated && user &&
      !user.onboarding_completed &&
      user.role !== "admin" && user.role !== "teacher"
    ) {
      router.push("/onboarding");
    }
  }, [tokenChecked, isAuthenticated, user, router]);

  // Poll for new achievements
  const checkAchievements = useCallback(async () => {
    try {
      const newCodes: string[] = await achievementsApi.check();
      if (newCodes?.length > 0) {
        const code = newCodes[0];
        const meta = ACHIEVEMENT_META[code];
        if (meta) {
          setToast({ code, name: meta.name, icon: meta.icon, xp: meta.xp });
        }
      }
    } catch {}
  }, []);

  useEffect(() => {
    if (isAuthenticated && tokenChecked) {
      checkAchievements();
      (window as any).__checkAchievements = checkAchievements;
    }
  }, [isAuthenticated, tokenChecked, checkAchievements]);

  // Show loading spinner while hydrating / validating token
  if (!_hasHydrated || !tokenChecked) {
    return (
      <div className="flex h-screen items-center justify-center bg-bg">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-ink/20 border-t-ink animate-spin" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-dvh overflow-hidden bg-bg dark:bg-[#1a1814]">
      {/* Desktop sidebar — hidden on mobile */}
      <div className="hidden md:flex">
        <Sidebar />
      </div>

      {/* Mobile: header + drawer + bottom nav wrap the children */}
      <div className="flex md:hidden flex-col flex-1 overflow-hidden min-h-0">
        <MobileNavWrapper>
          {children}
        </MobileNavWrapper>
      </div>

      {/* Desktop: children directly in main */}
      <main className="hidden md:flex flex-1 flex-col overflow-hidden">{children}</main>

      <AchievementToast achievement={toast} onDismiss={() => setToast(null)} />
      <GlobalSearch />
    </div>
  );
}
