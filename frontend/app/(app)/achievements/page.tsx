"use client";

import { useEffect, useState } from "react";
import { progressApi, achievementsApi } from "@/lib/api";

// XP thresholds per level (level 1-6)
const XP_LEVELS = [0, 100, 300, 600, 1100, 2000, 3500];
const LEVEL_NAMES = ["Newcomer", "Student", "Resident", "Specialist", "Expert", "Master", "Legend"];

const ACHIEVEMENT_META: Record<string, {
  name: string; description: string; icon: string; xp: number; category: string;
}> = {
  first_lesson:       { name: "First Step",          description: "Complete your first lesson",        icon: "👣", xp: 25,  category: "Learning"   },
  module_master:      { name: "Module Master",        description: "Score 100% on any module",          icon: "🎓", xp: 200, category: "Learning"   },
  deep_diver:         { name: "Deep Diver",           description: "Reach level 5 in one topic",        icon: "🔬", xp: 250, category: "Learning"   },
  polyglot:           { name: "Polyglot",             description: "Study 3+ specialties",              icon: "🌐", xp: 150, category: "Learning"   },
  streak_7:           { name: "Week Warrior",         description: "7-day study streak",                icon: "🔥", xp: 100, category: "Dedication" },
  streak_30:          { name: "Monthly Master",       description: "30-day study streak",               icon: "🏆", xp: 500, category: "Dedication" },
  flashcard_champion: { name: "Flashcard Champion",   description: "Rate 500 cards 4-5 stars",          icon: "⚡", xp: 300, category: "Flashcards" },
  case_solver:        { name: "Case Solver",          description: "Solve 10 clinical cases",           icon: "🩺", xp: 200, category: "Cases"      },
  ai_explorer:        { name: "AI Explorer",          description: "Ask 50 AI questions",               icon: "🤖", xp: 100, category: "AI"         },
  mcq_10:             { name: "Quiz Taker",           description: "Answer 10 MCQ questions",           icon: "📝", xp: 50,  category: "Quizzes"    },
  mcq_100:            { name: "Quiz Champion",        description: "Answer 100 MCQ questions",          icon: "🏅", xp: 200, category: "Quizzes"    },
};

const CATEGORIES = ["All", "Learning", "Dedication", "Flashcards", "Cases", "Quizzes", "AI"];

type Stats = { total_xp: number; level: number; streak_days: number };

export default function AchievementsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [unlocked, setUnlocked] = useState<Set<string>>(new Set());
  const [unlockedAt, setUnlockedAt] = useState<Record<string, string>>({});
  const [category, setCategory] = useState("All");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      progressApi.getStats?.().catch(() => null),
      achievementsApi.list().catch(() => []),
    ]).then(([statsData, achData]) => {
      if (statsData) setStats(statsData);
      const codes = new Set<string>();
      const dates: Record<string, string> = {};
      for (const a of (achData ?? [])) {
        codes.add(a.achievement_code);
        dates[a.achievement_code] = a.unlocked_at;
      }
      setUnlocked(codes);
      setUnlockedAt(dates);
    }).finally(() => setLoading(false));
  }, []);

  const allCodes = Object.keys(ACHIEVEMENT_META);
  const filtered = allCodes.filter((c) => {
    if (category !== "All" && ACHIEVEMENT_META[c].category !== category) return false;
    return true;
  });
  const unlockedFiltered = filtered.filter((c) => unlocked.has(c));
  const lockedFiltered = filtered.filter((c) => !unlocked.has(c));

  const totalXP = stats?.total_xp ?? 0;
  const level = stats?.level ?? 1;
  const clampedLevel = Math.min(level, XP_LEVELS.length - 1);
  const xpForCurrent = XP_LEVELS[clampedLevel - 1] ?? 0;
  const xpForNext = XP_LEVELS[clampedLevel] ?? XP_LEVELS[XP_LEVELS.length - 1];
  const xpProgress = xpForNext > xpForCurrent
    ? Math.round(((totalXP - xpForCurrent) / (xpForNext - xpForCurrent)) * 100)
    : 100;
  const totalUnlocked = Array.from(unlocked).filter((c) => c in ACHIEVEMENT_META).length;
  const totalXPFromAch = Array.from(unlocked)
    .filter((c) => c in ACHIEVEMENT_META)
    .reduce((s, c) => s + ACHIEVEMENT_META[c].xp, 0);

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
      <h1 className="font-syne font-black text-2xl text-ink mb-6">Achievements</h1>

      {loading ? (
        <div className="text-center py-16 font-serif text-ink-3 text-sm">Loading…</div>
      ) : (
        <>
          {/* XP / Level card */}
          <div className="card p-5 mb-6">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-ink flex items-center justify-center flex-shrink-0">
                  <span className="font-syne font-black text-white text-xl">{level}</span>
                </div>
                <div>
                  <div className="font-syne font-black text-base text-ink">
                    {LEVEL_NAMES[clampedLevel] ?? "Legend"}
                  </div>
                  <div className="font-serif text-ink-3 text-xs">
                    {totalXP.toLocaleString()} XP total
                  </div>
                </div>
              </div>
              <div className="flex gap-4 text-center">
                <div>
                  <div className="font-syne font-black text-lg text-ink">{stats?.streak_days ?? 0}</div>
                  <div className="font-serif text-xs text-ink-3">day streak 🔥</div>
                </div>
                <div>
                  <div className="font-syne font-black text-lg text-ink">{totalUnlocked}</div>
                  <div className="font-serif text-xs text-ink-3">achievements</div>
                </div>
                <div>
                  <div className="font-syne font-black text-lg text-amber">+{totalXPFromAch}</div>
                  <div className="font-serif text-xs text-ink-3">XP earned</div>
                </div>
              </div>
            </div>

            {/* XP progress bar */}
            {clampedLevel < XP_LEVELS.length - 1 && (
              <div>
                <div className="flex justify-between font-syne text-xs text-ink-3 mb-1.5">
                  <span>Level {level}</span>
                  <span>{totalXP - xpForCurrent} / {xpForNext - xpForCurrent} XP to level {level + 1}</span>
                </div>
                <div className="h-2.5 bg-bg-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-ink rounded-full transition-all duration-700"
                    style={{ width: `${Math.min(xpProgress, 100)}%` }}
                  />
                </div>
              </div>
            )}
            {clampedLevel >= XP_LEVELS.length - 1 && (
              <div className="text-center font-syne font-bold text-xs text-amber">
                🏆 Maximum level reached!
              </div>
            )}
          </div>

          {/* Category filter */}
          <div className="flex flex-wrap gap-1.5 mb-5">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`px-3 py-1 rounded-full font-syne font-semibold text-xs transition-all border ${
                  category === cat
                    ? "bg-ink text-white border-ink"
                    : "border-border text-ink-3 hover:border-ink hover:text-ink"
                }`}
              >
                {cat}
                {cat === "All"
                  ? ` (${totalUnlocked}/${allCodes.length})`
                  : ` (${allCodes.filter((c) => ACHIEVEMENT_META[c].category === cat && unlocked.has(c)).length}/${allCodes.filter((c) => ACHIEVEMENT_META[c].category === cat).length})`
                }
              </button>
            ))}
          </div>

          {/* Unlocked */}
          {unlockedFiltered.length > 0 && (
            <section className="mb-6">
              <h2 className="font-syne font-bold text-xs text-ink-2 uppercase mb-3">
                Unlocked — {unlockedFiltered.length}
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {unlockedFiltered.map((code) => (
                  <AchievementCard
                    key={code}
                    code={code}
                    unlocked
                    unlockedAt={unlockedAt[code]}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Locked */}
          {lockedFiltered.length > 0 && (
            <section>
              <h2 className="font-syne font-bold text-xs text-ink-3 uppercase mb-3">
                Locked — {lockedFiltered.length} remaining
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {lockedFiltered.map((code) => (
                  <AchievementCard key={code} code={code} unlocked={false} />
                ))}
              </div>
            </section>
          )}

          {filtered.length === 0 && (
            <p className="text-center font-serif text-ink-3 text-sm py-8">No achievements in this category.</p>
          )}
        </>
      )}
    </div>
  );
}

function AchievementCard({
  code,
  unlocked,
  unlockedAt,
}: {
  code: string;
  unlocked: boolean;
  unlockedAt?: string;
}) {
  const meta = ACHIEVEMENT_META[code] ?? { name: code, description: "", icon: "🏅", xp: 0, category: "" };
  const date = unlockedAt ? new Date(unlockedAt).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : null;

  return (
    <div
      className={`card flex items-center gap-4 p-4 transition-all ${
        unlocked ? "border-border" : "opacity-50 grayscale"
      }`}
    >
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl flex-shrink-0 ${
        unlocked ? "bg-amber-light" : "bg-bg-2"
      }`}>
        {meta.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-syne font-bold text-sm text-ink">{meta.name}</div>
        <div className="font-serif text-xs text-ink-3 mt-0.5">{meta.description}</div>
        {unlocked && date && (
          <div className="font-serif text-xs text-green mt-1">✓ Unlocked {date}</div>
        )}
      </div>
      <div className={`font-syne font-bold text-sm flex-shrink-0 ${unlocked ? "text-amber" : "text-ink-3"}`}>
        +{meta.xp} XP
      </div>
    </div>
  );
}
