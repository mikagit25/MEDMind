"use client";

import { useEffect, useState } from "react";
import { progressApi } from "@/lib/api";

const ACHIEVEMENT_META: Record<string, { name: string; description: string; icon: string; xp: number }> = {
  streak_7:           { name: "Week Warrior",       description: "7 days in a row",               icon: "🔥", xp: 100 },
  streak_30:          { name: "Monthly Master",      description: "30 days of activity",            icon: "🏆", xp: 500 },
  module_master:      { name: "Module Master",       description: "100% on any module",             icon: "🎓", xp: 200 },
  flashcard_champion: { name: "Flashcard Champion",  description: "500 cards rated 4-5",            icon: "⚡", xp: 300 },
  polyglot:           { name: "Polyglot",            description: "3+ specialties studied",         icon: "🌐", xp: 150 },
  deep_diver:         { name: "Deep Diver",          description: "Level 5 in one topic",           icon: "🔬", xp: 250 },
  first_lesson:       { name: "First Step",          description: "Completed first lesson",         icon: "👣", xp: 25  },
  case_solver:        { name: "Case Solver",         description: "Solved 10 clinical cases",       icon: "🩺", xp: 200 },
  ai_explorer:        { name: "AI Explorer",         description: "Asked 50 AI questions",          icon: "🤖", xp: 100 },
};

const ALL_CODES = Object.keys(ACHIEVEMENT_META);

export default function AchievementsPage() {
  const [unlocked, setUnlocked] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    progressApi.getAchievements?.()
      .then((data: any[]) => {
        setUnlocked(new Set(data.map((a: any) => a.achievement_code)));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const unlockedList = ALL_CODES.filter(c => unlocked.has(c));
  const lockedList   = ALL_CODES.filter(c => !unlocked.has(c));

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <h1 className="font-syne font-black text-2xl text-ink mb-1">Achievements</h1>
      <p className="text-ink-3 text-sm mb-8">{unlockedList.length} / {ALL_CODES.length} unlocked</p>

      {loading ? (
        <div className="text-ink-3 text-center py-16">Loading…</div>
      ) : (
        <>
          {unlockedList.length > 0 && (
            <section className="mb-10">
              <h2 className="font-syne font-bold text-base text-ink mb-4">Unlocked</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {unlockedList.map(code => <AchievementCard key={code} code={code} unlocked />)}
              </div>
            </section>
          )}

          <section>
            <h2 className="font-syne font-bold text-base text-ink-3 mb-4">Locked</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {lockedList.map(code => <AchievementCard key={code} code={code} unlocked={false} />)}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function AchievementCard({ code, unlocked }: { code: string; unlocked: boolean }) {
  const meta = ACHIEVEMENT_META[code] ?? { name: code, description: "", icon: "🏅", xp: 0 };
  return (
    <div className={`card flex items-center gap-4 p-4 ${unlocked ? "" : "opacity-40 grayscale"}`}>
      <div className="text-3xl w-10 text-center">{meta.icon}</div>
      <div className="flex-1 min-w-0">
        <div className="font-syne font-bold text-sm text-ink">{meta.name}</div>
        <div className="text-xs text-ink-3 mt-0.5">{meta.description}</div>
      </div>
      <div className="text-xs font-mono text-accent font-bold whitespace-nowrap">+{meta.xp} XP</div>
    </div>
  );
}
