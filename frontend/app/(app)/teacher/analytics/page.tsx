"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

type ModuleStats = {
  module_id: string;
  title: string;
  is_published: boolean;
  lessons: {
    lesson_id: string;
    title: string;
    status: string;
    lesson_order: number;
    estimated_minutes: number;
    completions: number;
    avg_time_seconds: number | null;
    avg_quiz_score: number | null;
  }[];
};

type MyModule = { id: string; title: string; is_published: boolean };

function formatTime(seconds: number | null) {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)}m`;
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-ink-3 text-xs">—</span>;
  const color = score >= 80 ? "text-green" : score >= 60 ? "text-amber" : "text-red";
  return <span className={`font-syne font-semibold text-xs ${color}`}>{score.toFixed(0)}%</span>;
}

export default function TeacherAnalyticsPage() {
  const [modules, setModules] = useState<MyModule[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [stats, setStats] = useState<ModuleStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingStats, setLoadingStats] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    teacherApi.listMyModules()
      .then((mods: MyModule[]) => {
        setModules(mods);
        if (mods.length > 0) setSelected(mods[0].id);
      })
      .catch(() => setError("Failed to load modules"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoadingStats(true);
    setStats(null);
    teacherApi.moduleAnalytics(selected)
      .then(setStats)
      .catch(() => setError("Failed to load analytics"))
      .finally(() => setLoadingStats(false));
  }, [selected]);

  const totalCompletions = stats?.lessons.reduce((s, l) => s + l.completions, 0) ?? 0;
  const publishedLessons = stats?.lessons.filter(l => l.status === "published").length ?? 0;
  const avgQuiz = (() => {
    const scored = stats?.lessons.filter(l => l.avg_quiz_score !== null) ?? [];
    if (!scored.length) return null;
    return scored.reduce((s, l) => s + (l.avg_quiz_score ?? 0), 0) / scored.length;
  })();

  if (loading) return <div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>;

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="mb-5">
        <Link href="/teacher/modules" className="text-ink-3 text-sm font-syne hover:text-ink">← My Modules</Link>
        <h1 className="font-syne font-black text-2xl text-ink mt-2">Analytics</h1>
        <p className="font-serif text-ink-3 text-sm">Student engagement with your lessons</p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">{error}</div>
      )}

      {modules.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="text-3xl mb-2">📊</div>
          <div className="font-syne font-semibold text-ink">No modules yet</div>
          <div className="font-serif text-ink-3 text-sm mt-1">Create modules and publish lessons to see analytics.</div>
        </div>
      ) : (
        <>
          {/* Module selector */}
          <div className="card p-3 mb-4">
            <label className="font-syne text-xs text-ink-3 block mb-1.5">Select module</label>
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="w-full border border-border rounded-lg px-3 py-2 font-syne text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            >
              {modules.map((m) => (
                <option key={m.id} value={m.id}>{m.title}{!m.is_published ? " (unpublished)" : ""}</option>
              ))}
            </select>
          </div>

          {loadingStats ? (
            <div className="text-ink-3 font-serif text-sm p-4">Loading stats...</div>
          ) : stats ? (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-3 gap-3 mb-5">
                <div className="card p-4 text-center">
                  <div className="font-syne font-black text-2xl text-ink">{totalCompletions}</div>
                  <div className="font-serif text-xs text-ink-3 mt-0.5">Total completions</div>
                </div>
                <div className="card p-4 text-center">
                  <div className="font-syne font-black text-2xl text-ink">{publishedLessons}</div>
                  <div className="font-serif text-xs text-ink-3 mt-0.5">Published lessons</div>
                </div>
                <div className="card p-4 text-center">
                  <div className={`font-syne font-black text-2xl ${avgQuiz !== null ? (avgQuiz >= 80 ? "text-green" : avgQuiz >= 60 ? "text-amber" : "text-red") : "text-ink-3"}`}>
                    {avgQuiz !== null ? `${avgQuiz.toFixed(0)}%` : "—"}
                  </div>
                  <div className="font-serif text-xs text-ink-3 mt-0.5">Avg quiz score</div>
                </div>
              </div>

              {/* Per-lesson table */}
              <div className="card overflow-hidden">
                <div className="px-4 py-3 border-b border-border">
                  <h2 className="font-syne font-bold text-sm text-ink">Lessons</h2>
                </div>
                {stats.lessons.length === 0 ? (
                  <div className="p-6 text-center text-ink-3 font-serif text-sm">No lessons in this module yet.</div>
                ) : (
                  <div className="divide-y divide-border">
                    {/* Header */}
                    <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-surface text-xs font-syne text-ink-3">
                      <div className="col-span-4">Lesson</div>
                      <div className="col-span-2 text-center">Status</div>
                      <div className="col-span-2 text-center">Completions</div>
                      <div className="col-span-2 text-center">Avg time</div>
                      <div className="col-span-2 text-center">Avg quiz</div>
                    </div>
                    {stats.lessons.map((lesson) => (
                      <div key={lesson.lesson_id} className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-surface/50 transition-colors">
                        <div className="col-span-4">
                          <Link
                            href={`/teacher/lessons/${lesson.lesson_id}/edit`}
                            className="font-syne text-sm text-ink hover:underline line-clamp-1"
                          >
                            {lesson.lesson_order + 1}. {lesson.title}
                          </Link>
                          <span className="font-serif text-xs text-ink-3">{lesson.estimated_minutes} min</span>
                        </div>
                        <div className="col-span-2 text-center">
                          <span className={`text-xs font-syne px-1.5 py-0.5 rounded border ${
                            lesson.status === "published" ? "bg-green-light text-green border-green/30" :
                            lesson.status === "draft" ? "bg-surface text-ink-3 border-border" :
                            "bg-amber-light text-amber border-amber/30"
                          }`}>
                            {lesson.status}
                          </span>
                        </div>
                        <div className="col-span-2 text-center">
                          <span className="font-syne font-semibold text-sm text-ink">{lesson.completions}</span>
                        </div>
                        <div className="col-span-2 text-center">
                          <span className="font-serif text-sm text-ink-3">{formatTime(lesson.avg_time_seconds)}</span>
                        </div>
                        <div className="col-span-2 text-center">
                          <ScoreBadge score={lesson.avg_quiz_score} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Empty state hint */}
              {totalCompletions === 0 && publishedLessons > 0 && (
                <div className="mt-4 p-3 rounded-lg bg-blue-light border border-blue/20">
                  <p className="font-syne font-semibold text-sm text-blue mb-0.5">No completions yet</p>
                  <p className="font-serif text-xs text-ink-3">
                    Share your module with students. Once they start completing lessons, data will appear here.
                  </p>
                </div>
              )}
            </>
          ) : null}
        </>
      )}
    </div>
  );
}
