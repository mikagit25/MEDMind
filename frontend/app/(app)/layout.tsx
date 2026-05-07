"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useUIStore } from "@/lib/store";
import { Sidebar } from "@/components/layout/Sidebar";
import { AchievementToast, AchievementToastData } from "@/components/ui/AchievementToast";
import { achievementsApi, authApi } from "@/lib/api";

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
  const [toast, setToast] = useState<AchievementToastData | null>(null);
  const [tokenChecked, setTokenChecked] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  // After Zustand hydrates, validate/refresh the token silently
  useEffect(() => {
    if (!_hasHydrated) return;

    async function validateSession() {
      const storedAccess = typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;

      if (!isAuthenticated || !storedAccess) {
        // No session at all — go to login
        setTokenChecked(true);
        router.push("/login");
        return;
      }

      // Try to call /auth/me with the current token
      try {
        const me = await authApi.me();
        // Token is valid — update user data in store (might have changed)
        setAuth(me, storedAccess, localStorage.getItem("refresh_token") ?? "");
        setTokenChecked(true);
      } catch (err: any) {
        if (err?.response?.status === 401) {
          // Token expired — try to refresh
          const refreshToken = localStorage.getItem("refresh_token");
          if (refreshToken) {
            try {
              const res = await authApi.refresh(refreshToken);
              setAuth(res.user ?? user!, res.access_token, res.refresh_token);
              setTokenChecked(true);
              return;
            } catch {
              // Refresh also failed — really log out
            }
          }
          logout();
          router.push("/login");
        } else {
          // Network error — keep the session, don't force logout
          setTokenChecked(true);
        }
      }
    }

    validateSession();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [_hasHydrated]);

  // Redirect to onboarding if not completed
  useEffect(() => {
    if (tokenChecked && isAuthenticated && user && !user.onboarding_completed) {
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
    <div className="flex h-screen overflow-hidden bg-bg dark:bg-[#1a1814]">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
      <AchievementToast achievement={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
