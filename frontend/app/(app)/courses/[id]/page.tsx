"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { studentCoursesApi } from "@/lib/api";

type ModuleProgress = {
  module_id: string;
  module_title: string;
  completion_percent: number;
  lessons_completed: number;
  total_lessons: number;
};

type CourseDetail = {
  id: string;
  title: string;
  description?: string;
  teacher_name?: string;
  specialty?: string;
  total_modules: number;
  overall_completion: number;
  enrolled_at?: string;
  modules?: { id: string; title: string; order: number }[];
};

export default function CourseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.id as string;

  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [progress, setProgress] = useState<ModuleProgress[]>([]);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    if (!courseId) return;
    setLoading(true);
    Promise.all([
      studentCoursesApi.getCourse(courseId).catch(() => null),
      studentCoursesApi.getProgress(courseId).catch(() => []),
      studentCoursesApi.getLeaderboard(courseId).catch(() => []),
    ]).then(([c, prog, lb]) => {
      setCourse(c);
      setProgress(Array.isArray(prog) ? prog : prog?.modules ?? []);
      setLeaderboard(Array.isArray(lb) ? lb : lb?.entries ?? []);
    }).finally(() => setLoading(false));
  }, [courseId]);

  const handleLeave = async () => {
    if (!confirm("Leave this course? Your progress will be saved.")) return;
    setLeaving(true);
    try {
      await studentCoursesApi.leave(courseId);
      router.push("/my-courses");
    } catch {
      setLeaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="font-serif text-ink-3 text-sm animate-pulse">Loading course…</div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4">
        <div className="text-4xl">📭</div>
        <p className="font-serif text-ink-3 text-sm">Course not found or you are not enrolled.</p>
        <Link href="/my-courses" className="btn-primary px-5 py-2 text-sm">← Back to courses</Link>
      </div>
    );
  }

  const pct = Math.round(course.overall_completion ?? 0);
  const progressMap = new Map(progress.map(p => [p.module_id, p]));

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-3 sm:px-6 py-4 sm:py-6">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-serif text-ink-3 mb-5">
          <Link href="/my-courses" className="hover:text-ink">My courses</Link>
          <span>/</span>
          <span className="text-ink-2 truncate">{course.title}</span>
        </div>

        {/* Header */}
        <div className="card p-5 mb-5">
          <div className="flex items-start gap-4">
            <div className="flex-1">
              {course.specialty && (
                <span className="font-syne text-[10px] font-semibold text-ink-3 uppercase tracking-wide block mb-1">
                  {course.specialty}
                </span>
              )}
              <h1 className="font-syne font-black text-xl text-ink leading-tight mb-1">{course.title}</h1>
              {course.teacher_name && (
                <p className="font-serif text-sm text-ink-3">by {course.teacher_name}</p>
              )}
              {course.description && (
                <p className="font-serif text-sm text-ink-2 mt-3 leading-relaxed">{course.description}</p>
              )}
            </div>
            <div className="flex-shrink-0 text-right">
              <div className={`font-syne font-black text-3xl leading-none ${pct >= 100 ? "text-green" : "text-ink"}`}>
                {pct}%
              </div>
              <div className="font-serif text-xs text-ink-3 mt-1">
                {course.total_modules} module{course.total_modules !== 1 ? "s" : ""}
              </div>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-4 h-2 bg-border-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-green" : "bg-gradient-to-r from-blue to-blue/60"}`}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
          <div className="mt-2 text-xs font-serif text-ink-3">
            {pct >= 100 ? "🎉 Course completed!" : `${pct}% complete`}
          </div>
        </div>

        {/* Module list */}
        <section className="mb-5">
          <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Course modules</h2>
          {progress.length === 0 ? (
            <div className="card p-6 text-center text-ink-3 font-serif text-sm">
              No modules added yet.
            </div>
          ) : (
            <div className="space-y-2">
              {progress.map((mod, idx) => {
                const mp = Math.round(mod.completion_percent ?? 0);
                return (
                  <Link
                    key={mod.module_id}
                    href={`/modules/${mod.module_id}`}
                    className="card flex items-center gap-4 p-4 hover:border-ink hover:shadow-sm transition-all group"
                  >
                    {/* Index */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 font-syne font-bold text-sm ${
                      mp >= 100
                        ? "bg-green text-white"
                        : mp > 0
                        ? "bg-blue text-white"
                        : "bg-surface-2 text-ink-3"
                    }`}>
                      {mp >= 100 ? "✓" : idx + 1}
                    </div>
                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="font-syne font-semibold text-sm text-ink group-hover:text-accent transition-colors line-clamp-1">
                        {mod.module_title}
                      </div>
                      {mod.total_lessons > 0 && (
                        <div className="text-xs font-serif text-ink-3 mt-0.5">
                          {mod.lessons_completed}/{mod.total_lessons} lessons
                        </div>
                      )}
                      {mp > 0 && (
                        <div className="mt-1.5 h-1 bg-border-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${mp >= 100 ? "bg-green" : "bg-blue/60"}`}
                            style={{ width: `${mp}%` }}
                          />
                        </div>
                      )}
                    </div>
                    {/* Percent */}
                    <div className="flex-shrink-0 text-right">
                      <span className={`font-syne font-bold text-sm ${mp >= 100 ? "text-green" : mp > 0 ? "text-blue" : "text-ink-3"}`}>
                        {mp}%
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </section>

        {/* Leaderboard */}
        {leaderboard.length > 0 && (
          <section className="mb-5">
            <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Class leaderboard</h2>
            <div className="card divide-y divide-border">
              {leaderboard.slice(0, 8).map(entry => (
                <div
                  key={entry.user_id}
                  className={`flex items-center gap-3 px-4 py-3 ${entry.is_me ? "bg-blue-light" : ""}`}
                >
                  <span className="font-syne font-black text-sm w-6 text-center text-ink-3 flex-shrink-0">
                    {entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : `${entry.rank}.`}
                  </span>
                  <span className={`font-syne text-sm flex-1 ${entry.is_me ? "text-blue font-bold" : "text-ink"}`}>
                    {entry.name}
                    {entry.is_me && <span className="ml-1 text-[10px] opacity-70">(you)</span>}
                  </span>
                  <span className="font-syne font-bold text-xs text-ink-3 flex-shrink-0">
                    {entry.xp} XP
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Leave */}
        <div className="flex justify-end">
          <button
            onClick={handleLeave}
            disabled={leaving}
            className="text-xs font-syne text-ink-3 hover:text-red border border-border hover:border-red/30 rounded-lg px-4 py-2 transition-colors disabled:opacity-40"
          >
            {leaving ? "Leaving…" : "Leave course"}
          </button>
        </div>
      </div>
    </div>
  );
}
