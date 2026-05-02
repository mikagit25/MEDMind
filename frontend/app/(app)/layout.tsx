"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useUIStore } from "@/lib/store";
import { Sidebar } from "@/components/layout/Sidebar";
import { AchievementToast, AchievementToastData } from "@/components/ui/AchievementToast";
import { achievementsApi } from "@/lib/api";

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
  const { isAuthenticated, user } = useAuthStore();
  const { darkMode } = useUIStore();
  const router = useRouter();
  const [toast, setToast] = useState<AchievementToastData | null>(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
    } else if (user && !user.onboarding_completed) {
      router.push("/onboarding");
    }
  }, [isAuthenticated, user, router]);

  // Poll for new achievements after key actions
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

  // Check once on mount and expose globally
  useEffect(() => {
    if (isAuthenticated) {
      checkAchievements();
      (window as any).__checkAchievements = checkAchievements;
    }
  }, [isAuthenticated, checkAchievements]);

  if (!isAuthenticated || (user && !user.onboarding_completed)) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-bg dark:bg-[#1a1814]">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
      <AchievementToast achievement={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
