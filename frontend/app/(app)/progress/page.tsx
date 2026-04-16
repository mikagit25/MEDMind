"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { progressApi, achievementsApi, memoryApi, studentCoursesApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

const LEVEL_THRESHOLDS = [0, 500, 2000, 5000, 12000, 25000];

function LevelBar({ xp, level }: { xp: number; level: number }) {
  const start = LEVEL_THRESHOLDS[level - 1] ?? 0;
  const end = LEVEL_THRESHOLDS[level] ?? LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1];
  const pct = Math.min(((xp - start) / (end - start)) * 100, 100);
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="font-syne font-black text-3xl text-ink">Level {level}</span>
          <span className="text-ink-3 font-serif text-sm ml-3">{xp} XP total</span>
        </div>
        <div className="text-right">
          <div className="font-syne font-bold text-sm text-ink-2">Next level</div>
          <div className="font-serif text-xs text-ink-3">{end - xp} XP remaining</div>
        </div>
      </div>
      <div className="h-3 bg-bg-2 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-red to-amber-2 rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function ProgressPage() {
  const { user } = useAuthStore();
  const [stats, setStats] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [weaknesses, setWeaknesses] = useState<any[]>([]);
  const [achievements, setAchievements] = useState<any[]>([]);
  const [modulesProgress, setModulesProgress] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Courses & Memory
  const [enrolledCourses, setEnrolledCourses] = useState<any[]>([]);
  const [memoryStats, setMemoryStats] = useState<any>(null);
  const [memoryItems, setMemoryItems] = useState<any[]>([]);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [memoryLoading, setMemoryLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      progressApi.getStats().catch(() => ({ data: null })),
      progressApi.getHistory().catch(() => ({ data: [] })),
      progressApi.getWeaknesses().catch(() => ({ data: { weaknesses: [] } })),
      achievementsApi.list().catch(() => ({ data: [] })),
      progressApi.getModulesProgress().catch(() => ({ data: [] })),
      studentCoursesApi.getEnrolled().catch(() => []),
      memoryApi.stats().catch(() => null),
    ]).then(([statsRes, histRes, weakRes, achRes, modProgRes, courses, mStats]) => {
      setStats(statsRes.data);
      setHistory(histRes.data ?? []);
      setWeaknesses(weakRes.data?.weaknesses ?? []);
      setAchievements(achRes.data ?? []);
      setModulesProgress(modProgRes.data ?? []);
      setEnrolledCourses(Array.isArray(courses) ? courses : courses?.courses ?? []);
      setMemoryStats(mStats);
      setLoading(false);
    });
  }, []);

  async function loadMemory() {
    if (memoryItems.length > 0) { setMemoryOpen((v) => !v); return; }
    setMemoryOpen(true);
    setMemoryLoading(true);
    try {
      const data = await memoryApi.list({ limit: 20 });
      setMemoryItems(Array.isArray(data) ? data : data?.items ?? []);
    } catch {
      // non-critical
    } finally {
      setMemoryLoading(false);
    }
  }

  async function handleDeleteMemory(id: string) {
    try {
      await memoryApi.remove(id);
      setMemoryItems((prev) => prev.filter((m) => m.id !== id));
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="font-serif text-ink-3 text-sm animate-pulse">Loading…</div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h1 className="font-syne font-black text-2xl text-ink mb-6">My Progress</h1>

      {/* XP Level bar */}
      <div className="mb-6">
        <LevelBar xp={user?.xp ?? 0} level={user?.level ?? 1} />
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { label: "Lessons completed", value: stats?.lessons_completed ?? 0, icon: "📖" },
          { label: "Cards reviewed", value: stats?.cards_reviewed ?? 0, icon: "🃏" },
          { label: "MCQs answered", value: stats?.mcqs_answered ?? 0, icon: "❓" },
          { label: "Day streak", value: `${stats?.streak_days ?? 0} 🔥`, icon: "📅" },
          { label: "Correct rate", value: `${stats?.correct_rate ?? 0}%`, icon: "✅" },
          { label: "Modules started", value: stats?.modules_started ?? 0, icon: "📚" },
          { label: "Modules done", value: stats?.modules_completed ?? 0, icon: "🏆" },
          { label: "Total sessions", value: stats?.total_sessions ?? 0, icon: "⏱" },
        ].map((s) => (
          <div key={s.label} className="card text-center py-4">
            <div className="text-2xl mb-1">{s.icon}</div>
            <div className="font-syne font-black text-xl text-ink">{s.value}</div>
            <div className="font-serif text-ink-3 text-xs mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Modules in progress */}
      {modulesProgress.length > 0 && (
        <div className="mb-8">
          <h2 className="font-syne font-bold text-base text-ink mb-3">📚 My Modules</h2>
          <div className="space-y-2">
            {modulesProgress.slice(0, 8).map((m: any) => {
              const pct = Math.round(m.completion_percent);
              return (
                <div key={m.module_id} className="card flex items-center gap-4 px-4 py-3">
                  <div className="flex-1 min-w-0">
                    <div className="font-syne font-semibold text-sm text-ink truncate">{m.module_title}</div>
                    <div className="text-xs text-ink-3 font-mono mt-0.5">{m.module_code}</div>
                  </div>
                  <div className="w-32 flex-shrink-0">
                    <div className="flex justify-between text-[10px] font-syne text-ink-3 mb-1">
                      <span>{pct}%</span>
                      <span>{m.lessons_completed} lessons</span>
                    </div>
                    <div className="h-1.5 bg-bg-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-green" : "bg-gradient-to-r from-red to-amber-2"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                  <div
                    className="text-[10px] font-syne font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                    style={{
                      background: pct >= 100 ? "#e8f5e9" : pct > 50 ? "#fdf8ec" : "#fdf0ef",
                      color: pct >= 100 ? "#2e7d32" : pct > 50 ? "#8a5a00" : "#c0392b",
                    }}
                  >
                    {pct >= 100 ? "Done" : pct > 50 ? "In progress" : "Started"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Enrolled Courses */}
      {enrolledCourses.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-syne font-bold text-base text-ink">🎓 My Courses</h2>
            <Link href="/my-courses" className="text-xs font-syne text-ink-3 hover:text-ink underline">
              View all →
            </Link>
          </div>
          <div className="space-y-2">
            {enrolledCourses.slice(0, 4).map((c: any) => {
              const pct = Math.round(c.overall_completion ?? 0);
              return (
                <Link key={c.id} href="/my-courses"
                  className="card flex items-center gap-4 px-4 py-3 hover:border-ink-3 transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="font-syne font-semibold text-sm text-ink truncate">{c.title}</div>
                    {c.teacher_name && (
                      <div className="font-serif text-xs text-ink-3 mt-0.5">by {c.teacher_name}</div>
                    )}
                  </div>
                  <div className="w-28 shrink-0">
                    <div className="flex justify-between text-[10px] font-syne text-ink-3 mb-1">
                      <span>{pct}%</span>
                      <span>{c.total_modules} modules</span>
                    </div>
                    <div className="h-1.5 bg-bg-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-green" : "bg-blue/60"}`}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Weaknesses */}
      {weaknesses.length > 0 && (
        <div className="mb-8">
          <h2 className="font-syne font-bold text-base text-ink mb-3">⚠️ Areas to Improve</h2>
          <div className="space-y-2">
            {weaknesses.map((w: any, i: number) => {
              const isFlashcard = w.reason === "low_flashcard_score";
              const score = isFlashcard
                ? Math.round((w.avg_quality / 5) * 100)
                : Math.round(w.completion_percent ?? 0);
              const label = isFlashcard
                ? `Avg quality: ${w.avg_quality?.toFixed(1)} / 5`
                : `Completion: ${score}%`;
              return (
                <div key={i} className="card flex items-center gap-3">
                  <div className="flex-1">
                    <div className="font-syne font-semibold text-sm text-ink">{w.module_title}</div>
                    <div className="text-xs text-ink-3 mt-0.5">{label}</div>
                  </div>
                  <div
                    className="text-xs font-syne font-bold px-2 py-1 rounded-full"
                    style={{
                      background: score < 50 ? "#fdf0ef" : "#fdf8ec",
                      color: score < 50 ? "#c0392b" : "#8a5a00",
                    }}
                  >
                    {score < 50 ? "Needs work" : "Review"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Achievements */}
      {achievements.length > 0 && (
        <div className="mb-8">
          <h2 className="font-syne font-bold text-base text-ink mb-3">🏆 Achievements</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
            {achievements.map((a: any) => (
              <div
                key={a.code}
                className={`card py-4 px-3 text-center transition-all ${
                  a.unlocked ? "" : "opacity-40 grayscale"
                }`}
              >
                <div className="text-2xl mb-1.5">{a.icon}</div>
                <div className="font-syne font-bold text-xs text-ink leading-tight">{a.title}</div>
                <div className="font-serif text-ink-3 text-[10px] mt-1 leading-tight">{a.desc}</div>
                {a.unlocked && a.xp_reward > 0 && (
                  <div className="mt-2 text-[10px] font-syne font-bold text-green bg-green-light rounded-full px-2 py-0.5 inline-block">
                    +{a.xp_reward} XP
                  </div>
                )}
                {!a.unlocked && (
                  <div className="mt-2 text-[10px] font-serif text-ink-3">Locked</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Knowledge Bank / Memory */}
      {memoryStats && (
        <div className="mb-8">
          <button
            onClick={loadMemory}
            className="w-full flex items-center justify-between mb-3 group"
          >
            <h2 className="font-syne font-bold text-base text-ink">🧠 Knowledge Bank</h2>
            <div className="flex items-center gap-2">
              {memoryStats.total > 0 && (
                <span className="font-syne font-bold text-xs text-ink-3 bg-surface border border-border rounded-full px-2 py-0.5">
                  {memoryStats.total} entries
                </span>
              )}
              <span className="text-ink-3 text-xs group-hover:text-ink transition-colors">
                {memoryOpen ? "▲" : "▼"}
              </span>
            </div>
          </button>

          {/* Stats row */}
          {memoryStats.by_type && Object.keys(memoryStats.by_type).length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {Object.entries(memoryStats.by_type as Record<string, number>).map(([type, count]) => (
                <span key={type}
                  className="font-syne text-[10px] font-semibold bg-surface border border-border rounded-full px-2.5 py-1 text-ink-3 capitalize">
                  {type.replace(/_/g, " ")}: {count}
                </span>
              ))}
            </div>
          )}

          {memoryOpen && (
            <div className="space-y-2">
              {memoryLoading ? (
                <div className="text-center py-6 text-ink-3 font-serif text-sm animate-pulse">Loading memory…</div>
              ) : memoryItems.length === 0 ? (
                <div className="card p-6 text-center">
                  <p className="font-serif text-sm text-ink-3">
                    Your knowledge bank is empty. Study modules and review flashcards to build it up.
                  </p>
                </div>
              ) : (
                <>
                  {memoryItems.map((m: any) => (
                    <div key={m.id} className="card px-4 py-3 flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="font-syne font-semibold text-xs text-ink-3 uppercase tracking-wide mb-0.5 capitalize">
                          {(m.memory_type ?? m.type ?? "note").replace(/_/g, " ")}
                          {m.specialty && ` · ${m.specialty}`}
                        </div>
                        <div className="font-serif text-sm text-ink leading-relaxed line-clamp-3">
                          {m.content ?? m.summary ?? m.text ?? "—"}
                        </div>
                        {m.created_at && (
                          <div className="font-serif text-[10px] text-ink-3 mt-1">
                            {new Date(m.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteMemory(m.id)}
                        className="text-ink-3 hover:text-red text-xs shrink-0 mt-0.5 transition-colors"
                        title="Remove from knowledge bank"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <p className="text-center font-serif text-xs text-ink-3 pt-1">
                    Showing latest 20 entries
                  </p>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Recent activity — day-by-day summary */}
      {history.filter((d: any) => (d.lessons > 0 || d.cards > 0)).length > 0 && (
        <div>
          <h2 className="font-syne font-bold text-base text-ink mb-3">Recent Activity</h2>
          <div className="space-y-2">
            {history
              .filter((d: any) => d.lessons > 0 || d.cards > 0)
              .slice(0, 14)
              .map((d: any, i: number) => (
                <div key={i} className="card flex items-center gap-3">
                  <div className="text-xl w-8 text-center">📅</div>
                  <div className="flex-1">
                    <div className="font-syne font-semibold text-sm text-ink">
                      {d.lessons > 0 && `${d.lessons} lesson${d.lessons !== 1 ? "s" : ""}`}
                      {d.lessons > 0 && d.cards > 0 && " · "}
                      {d.cards > 0 && `${d.cards} card${d.cards !== 1 ? "s" : ""} reviewed`}
                    </div>
                    <div className="font-serif text-xs text-ink-3">
                      {d.date ? new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {history.filter((d: any) => d.lessons > 0 || d.cards > 0).length === 0 && (
        <div className="text-center py-12">
          <div className="text-4xl mb-3">📊</div>
          <p className="font-serif text-ink-3 text-sm">
            No activity yet. Complete lessons and review flashcards to see your progress here.
          </p>
        </div>
      )}
    </div>
  );
}
