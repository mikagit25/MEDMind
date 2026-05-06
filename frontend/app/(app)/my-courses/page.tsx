"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { studentCoursesApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface CourseModule {
  module_id: string;
  module_title: string;
  completion_percent: number;
  lessons_completed: number;
  total_lessons: number;
}

interface EnrolledCourse {
  id: string;
  title: string;
  description?: string;
  teacher_name?: string;
  specialty?: string;
  total_modules: number;
  overall_completion: number;
  enrolled_at: string;
}

interface LeaderboardEntry {
  rank: number;
  user_id: string;
  name: string;
  xp: number;
  is_me: boolean;
}

export default function MyCoursesPage() {
  const t = useT();
  const [courses, setCourses] = useState<EnrolledCourse[]>([]);
  const [loading, setLoading] = useState(true);

  // Join form
  const [joinCode, setJoinCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState("");
  const [joinSuccess, setJoinSuccess] = useState("");

  const [leaveError, setLeaveError] = useState("");

  // Expanded course detail
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [moduleProgress, setModuleProgress] = useState<Record<string, CourseModule[]>>({});
  const [leaderboard, setLeaderboard] = useState<Record<string, LeaderboardEntry[]>>({});
  const [detailLoading, setDetailLoading] = useState<string | null>(null);

  useEffect(() => {
    studentCoursesApi
      .getEnrolled()
      .then((data) => setCourses(Array.isArray(data) ? data : data?.courses ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault();
    if (!joinCode.trim()) return;
    setJoining(true);
    setJoinError("");
    setJoinSuccess("");
    try {
      const result = await studentCoursesApi.join(joinCode.trim());
      setJoinSuccess(`Joined "${result.title ?? "course"}" successfully!`);
      setJoinCode("");
      const updated = await studentCoursesApi.getEnrolled();
      setCourses(Array.isArray(updated) ? updated : updated?.courses ?? []);
    } catch (e: any) {
      setJoinError(e?.response?.data?.detail ?? "Invalid invite code or already enrolled.");
    } finally {
      setJoining(false);
    }
  }

  async function toggleCourse(courseId: string) {
    if (expandedId === courseId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(courseId);
    if (!moduleProgress[courseId]) {
      setDetailLoading(courseId);
      try {
        const [prog, lb] = await Promise.all([
          studentCoursesApi.getProgress(courseId).catch(() => []),
          studentCoursesApi.getLeaderboard(courseId).catch(() => []),
        ]);
        setModuleProgress((prev) => ({
          ...prev,
          [courseId]: Array.isArray(prog) ? prog : prog?.modules ?? [],
        }));
        setLeaderboard((prev) => ({
          ...prev,
          [courseId]: Array.isArray(lb) ? lb : lb?.entries ?? [],
        }));
      } finally {
        setDetailLoading(null);
      }
    }
  }

  async function handleLeave(courseId: string, title: string) {
    if (!confirm(`Leave "${title}"? Your progress will be retained but you will lose access.`)) return;
    try {
      await studentCoursesApi.leave(courseId);
      setCourses((cs) => cs.filter((c) => c.id !== courseId));
      if (expandedId === courseId) setExpandedId(null);
    } catch {
      setLeaveError(t("common.error_retry"));
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="font-syne font-black text-2xl text-ink">{t("nav.items.my_courses")}</h1>
        <p className="font-serif text-ink-3 text-sm mt-0.5">
          {loading ? t("common.loading") : `${courses.length} course${courses.length !== 1 ? "s" : ""} enrolled`}
        </p>
      </div>

      {leaveError && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">
          {leaveError}
        </div>
      )}

      {/* Join with invite code */}
      <div className="card p-4 mb-6">
        <h2 className="font-syne font-bold text-sm text-ink mb-3">Join a Course</h2>
        <form onSubmit={handleJoin} className="flex gap-2">
          <input
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            placeholder="Enter invite code from your teacher..."
            className="flex-1 border border-border rounded-lg px-3 py-2 font-mono text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
          />
          <button
            type="submit"
            disabled={joining || !joinCode.trim()}
            className="btn-primary px-5 py-2 rounded-lg font-syne font-semibold text-sm disabled:opacity-50 shrink-0"
          >
            {joining ? "Joining…" : "Join"}
          </button>
        </form>
        {joinError && (
          <p className="text-red font-serif text-xs mt-2">{joinError}</p>
        )}
        {joinSuccess && (
          <p className="text-green font-serif text-xs mt-2">✓ {joinSuccess}</p>
        )}
      </div>

      {/* Courses list */}
      {loading ? (
        <div className="text-center py-12 text-ink-3 font-serif text-sm animate-pulse">{t("common.loading")}</div>
      ) : courses.length === 0 ? (
        <div className="card p-10 text-center">
          <div className="text-4xl mb-3">🎓</div>
          <div className="font-syne font-bold text-ink mb-1">{t("common.no_results")}</div>
          <div className="font-serif text-ink-3 text-sm max-w-xs mx-auto">
            Ask your teacher for an invite code and enter it above to join a course.
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {courses.map((course) => {
            const isOpen = expandedId === course.id;
            const pct = Math.round(course.overall_completion ?? 0);
            const mods = moduleProgress[course.id] ?? [];
            const lb = leaderboard[course.id] ?? [];
            const isLoadingDetail = detailLoading === course.id;

            return (
              <div key={course.id} className="card overflow-hidden">
                {/* Course header — click to expand */}
                <button
                  onClick={() => toggleCourse(course.id)}
                  className="w-full px-4 py-4 text-left hover:bg-surface transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="font-syne font-bold text-sm text-ink">{course.title}</div>
                      <div className="font-serif text-xs text-ink-3 mt-0.5">
                        {course.teacher_name && `by ${course.teacher_name}`}
                        {course.teacher_name && course.specialty && " · "}
                        {course.specialty}
                        {!course.teacher_name && !course.specialty && `${course.total_modules} module${course.total_modules !== 1 ? "s" : ""}`}
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div
                        className={`font-syne font-black text-lg leading-none ${
                          pct >= 100 ? "text-green" : "text-ink"
                        }`}
                      >
                        {pct}%
                      </div>
                      <div className="font-serif text-[10px] text-ink-3 mt-0.5">
                        {course.total_modules} modules
                      </div>
                    </div>
                    <span className="text-ink-3 text-xs shrink-0 mt-1.5">{isOpen ? "▲" : "▼"}</span>
                  </div>

                  {/* Completion bar */}
                  <div className="mt-3 h-1.5 bg-border rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        pct >= 100
                          ? "bg-green"
                          : "bg-gradient-to-r from-blue to-blue/50"
                      }`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </button>

                {/* Expanded detail */}
                {isOpen && (
                  <div className="border-t border-border">
                    {isLoadingDetail ? (
                      <div className="px-4 py-8 text-center text-ink-3 font-serif text-sm animate-pulse">
                        Loading details…
                      </div>
                    ) : (
                      <div className="px-4 py-4 space-y-5">
                        {/* Module progress */}
                        {mods.length > 0 && (
                          <div>
                            <h3 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">
                              Module Progress
                            </h3>
                            <div className="space-y-2">
                              {mods.map((m) => {
                                const mp = Math.round(m.completion_percent ?? 0);
                                return (
                                  <Link
                                    key={m.module_id}
                                    href={`/modules/${m.module_id}`}
                                    className="flex items-center gap-3 hover:bg-surface rounded-lg px-2 py-2 -mx-2 transition-colors group"
                                  >
                                    <div className="flex-1 min-w-0">
                                      <div className="font-syne text-xs text-ink group-hover:underline truncate">
                                        {m.module_title}
                                      </div>
                                      <div className="mt-1.5 h-1 bg-border rounded-full overflow-hidden">
                                        <div
                                          className={`h-full rounded-full transition-all ${
                                            mp >= 100 ? "bg-green" : "bg-blue/60"
                                          }`}
                                          style={{ width: `${Math.min(mp, 100)}%` }}
                                        />
                                      </div>
                                    </div>
                                    <div className="shrink-0 text-right">
                                      <span className="font-syne font-bold text-xs text-ink-3">{mp}%</span>
                                      {m.total_lessons > 0 && (
                                        <div className="font-serif text-[10px] text-ink-3">
                                          {m.lessons_completed}/{m.total_lessons}
                                        </div>
                                      )}
                                    </div>
                                  </Link>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {mods.length === 0 && (
                          <p className="font-serif text-xs text-ink-3 text-center py-2">
                            No modules in this course yet.
                          </p>
                        )}

                        {/* Class leaderboard */}
                        {lb.length > 0 && (
                          <div>
                            <h3 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">
                              Class Leaderboard
                            </h3>
                            <div className="space-y-1">
                              {lb.slice(0, 5).map((entry) => (
                                <div
                                  key={entry.user_id}
                                  className={`flex items-center gap-2 px-2 py-1.5 rounded-lg ${
                                    entry.is_me
                                      ? "bg-blue-light border border-blue/20"
                                      : ""
                                  }`}
                                >
                                  <span className="font-syne font-black text-xs text-ink-3 w-6 text-center shrink-0">
                                    {entry.rank === 1
                                      ? "🥇"
                                      : entry.rank === 2
                                      ? "🥈"
                                      : entry.rank === 3
                                      ? "🥉"
                                      : `${entry.rank}.`}
                                  </span>
                                  <span
                                    className={`font-syne text-xs flex-1 ${
                                      entry.is_me ? "text-blue font-bold" : "text-ink"
                                    }`}
                                  >
                                    {entry.name}
                                    {entry.is_me && (
                                      <span className="ml-1 text-[10px] text-blue/70">(you)</span>
                                    )}
                                  </span>
                                  <span className="font-syne font-bold text-xs text-ink-3 shrink-0">
                                    {entry.xp} XP
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Leave course */}
                        <div className="flex justify-end pt-1 border-t border-border">
                          <button
                            onClick={() => handleLeave(course.id, course.title)}
                            className="text-xs font-syne text-red/70 hover:text-red border border-red/20 hover:border-red/40 rounded px-3 py-1.5 transition-colors mt-3"
                          >
                            Leave course
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
