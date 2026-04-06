"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuthStore } from "@/lib/store";
import { contentApi, progressApi } from "@/lib/api";

const LEVEL_THRESHOLDS = [0, 500, 2000, 5000, 12000, 25000];

function xpToNextLevel(xp: number, level: number): { current: number; needed: number; pct: number } {
  const start = LEVEL_THRESHOLDS[level - 1] ?? 0;
  const end = LEVEL_THRESHOLDS[level] ?? LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1];
  const current = xp - start;
  const needed = end - start;
  return { current, needed, pct: Math.min((current / needed) * 100, 100) };
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [modules, setModules] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      contentApi.getSpecialties().catch(() => ({ data: [] })),
      progressApi.getStats().catch(() => ({ data: null })),
    ]).then(([modRes, statsRes]) => {
      setModules(modRes.data?.slice(0, 3) ?? []);
      setStats(statsRes.data);
      setLoading(false);
    });
  }, []);

  const level = user?.level ?? 1;
  const xp = user?.xp ?? 0;
  const xpInfo = xpToNextLevel(xp, level);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="font-syne font-black text-2xl text-ink">
          Good day, {user?.first_name} 👋
        </h1>
        <p className="font-serif text-ink-3 text-sm mt-0.5">
          {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
        </p>
      </div>

      {/* XP Progress */}
      <div className="card px-5 py-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <div>
            <span className="font-syne font-bold text-sm text-ink">Level {level}</span>
            <span className="text-ink-3 font-serif text-xs ml-2">
              {xpInfo.current} / {xpInfo.needed} XP to next level
            </span>
          </div>
          <span className="font-syne font-black text-lg text-ink">{xp} XP</span>
        </div>
        <div className="h-2 bg-bg-2 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-red to-amber-2 rounded-full transition-all duration-700"
            style={{ width: `${xpInfo.pct}%` }}
          />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { href: "/ai-tutor", icon: "🤖", label: "AI Tutor", color: "bg-blue-light border-blue/20 text-blue" },
          { href: "/flashcards", icon: "🃏", label: "Flashcards", color: "bg-green-light border-green/20 text-green" },
          { href: "/cases", icon: "🩺", label: "Cases", color: "bg-amber-light border-amber/20 text-amber" },
          { href: "/modules", icon: "📚", label: "Modules", color: "bg-red-light border-red/20 text-red" },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-col items-center gap-2 p-4 rounded-lg border ${item.color} hover:shadow-sm transition-shadow`}
          >
            <span className="text-2xl">{item.icon}</span>
            <span className="font-syne font-bold text-sm">{item.label}</span>
          </Link>
        ))}
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: "Lessons done", value: stats.lessons_completed ?? 0 },
            { label: "Cards reviewed", value: stats.cards_reviewed ?? 0 },
            { label: "Day streak", value: `${stats.streak_days ?? 0}🔥` },
          ].map((s) => (
            <div key={s.label} className="card text-center py-4">
              <div className="font-syne font-black text-2xl text-ink">{s.value}</div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Recent Specialties */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-syne font-bold text-base text-ink">Specialties</h2>
          <Link href="/modules" className="text-ink-3 font-syne text-xs hover:text-ink transition-colors">
            View all →
          </Link>
        </div>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card h-16 animate-pulse bg-bg-2" />
            ))}
          </div>
        ) : modules.length === 0 ? (
          <div className="card text-center py-8">
            <p className="font-serif text-ink-3 text-sm">Loading modules…</p>
          </div>
        ) : (
          <div className="space-y-2">
            {modules.map((spec: any) => (
              <Link
                key={spec.id}
                href={`/modules?specialty=${spec.id}`}
                className="card flex items-center gap-3 hover:border-ink-3 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-ink/10 flex items-center justify-center text-lg font-bold text-ink-2">
                  {spec.name?.[0] ?? "M"}
                </div>
                <div>
                  <div className="font-syne font-bold text-sm text-ink">{spec.name}</div>
                  <div className="font-serif text-ink-3 text-xs">{spec.module_count ?? 0} modules</div>
                </div>
                <div className="ml-auto text-ink-3 text-xs font-syne">→</div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
