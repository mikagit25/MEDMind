"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, teacherApi } from "@/lib/api";

interface LessonStat {
  lesson_id: string;
  title: string;
  lesson_order: number;
  completions: number;
  completion_rate: number;
  estimated_minutes: number;
  avg_quiz_score: number | null;
  status: string;
}

interface ModuleAnalytics {
  module_id: string;
  module_title: string;
  total_students: number;
  avg_completion_rate: number;
  drop_off_lesson_id: string | null;
  lessons: LessonStat[];
}

interface CourseModule {
  id: string;
  title: string;
  module_order: number;
}

export default function CourseAnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const preselectedModule = searchParams.get("module");

  const [courseModules, setCourseModules] = useState<CourseModule[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState<string>("");
  const [stats, setStats] = useState<ModuleAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingStats, setLoadingStats] = useState(false);
  const [error, setError] = useState("");
  const [courseTitle, setCourseTitle] = useState("");

  // Load course modules
  useEffect(() => {
    teacherApi.getCourse(id)
      .then((course: any) => {
        setCourseTitle(course.title ?? "");
        const mods: CourseModule[] = (course.modules ?? []).sort(
          (a: any, b: any) => a.module_order - b.module_order
        );
        setCourseModules(mods);
        const first = preselectedModule && mods.find((m) => m.id === preselectedModule)
          ? preselectedModule
          : mods[0]?.id ?? "";
        setSelectedModuleId(first);
      })
      .catch(() => setError("Failed to load course"))
      .finally(() => setLoading(false));
  }, [id, preselectedModule]);

  // Load analytics when module selected
  useEffect(() => {
    if (!selectedModuleId) return;
    setLoadingStats(true);
    setStats(null);
    api.get(`/lessons/modules/${selectedModuleId}/analytics`)
      .then((r) => setStats(r.data))
      .catch(() => setError("Failed to load analytics"))
      .finally(() => setLoadingStats(false));
  }, [selectedModuleId]);

  const maxCompletions = Math.max(...(stats?.lessons.map((l) => l.completions) ?? [0]), 1);

  function exportCSV() {
    if (!stats) return;
    const rows = [
      ["#", "Title", "Status", "Completions", "Completion %", "Est. minutes", "Avg Quiz %"],
      ...stats.lessons.map((l, i) => [
        i + 1,
        l.title,
        l.status,
        l.completions,
        l.completion_rate,
        l.estimated_minutes,
        l.avg_quiz_score ?? "",
      ]),
    ];
    const csv = rows.map((r) => r.map((v) => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `analytics_${stats.module_title.replace(/\s+/g, "_")}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  if (loading) return <div className="p-8 text-ink-3 font-serif">Loading…</div>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <Link href={`/teacher/courses/${id}`} className="text-xs text-ink-3 hover:text-ink font-syne mb-4 inline-block">
        ← Back to {courseTitle || "course"}
      </Link>

      <div className="flex items-start justify-between mb-4 gap-3">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">Course Analytics</h1>
          <p className="font-serif text-ink-3 text-sm">Per-module lesson engagement</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Link href={`/teacher/courses/${id}/at-risk`}
            className="text-xs font-syne text-amber border border-amber/30 rounded px-3 py-1.5 hover:bg-amber-light transition-colors">
            ⚠️ At-Risk
          </Link>
          <Link href={`/teacher/courses/${id}/insights`}
            className="text-xs font-syne text-ink-3 border border-border rounded px-3 py-1.5 hover:border-ink-3 transition-colors">
            📊 Insights
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">{error}</div>
      )}

      {courseModules.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="text-3xl mb-2">📊</div>
          <div className="font-syne font-semibold text-ink">No modules in this course</div>
        </div>
      ) : (
        <>
          {/* Module selector */}
          <div className="flex items-center gap-3 mb-5">
            <select
              value={selectedModuleId}
              onChange={(e) => setSelectedModuleId(e.target.value)}
              className="flex-1 border border-border rounded-lg px-3 py-2 font-syne text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            >
              {courseModules.map((m) => (
                <option key={m.id} value={m.id}>{m.title}</option>
              ))}
            </select>
            {stats && (
              <button
                onClick={exportCSV}
                className="text-xs font-syne text-ink-3 border border-border rounded px-3 py-2 hover:border-ink-3 transition-colors shrink-0"
              >
                ⬇ CSV
              </button>
            )}
          </div>

          {loadingStats ? (
            <div className="text-ink-3 font-serif text-sm p-4">Loading…</div>
          ) : stats ? (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="card text-center py-4">
                  <div className="font-syne font-black text-2xl text-ink">{stats.total_students}</div>
                  <div className="font-serif text-xs text-ink-3 mt-0.5">Enrolled students</div>
                </div>
                <div className="card text-center py-4">
                  <div className={`font-syne font-black text-2xl ${
                    stats.avg_completion_rate >= 70 ? "text-green" :
                    stats.avg_completion_rate >= 40 ? "text-amber" : "text-red"
                  }`}>
                    {stats.avg_completion_rate}%
                  </div>
                  <div className="font-serif text-xs text-ink-3 mt-0.5">Avg completion</div>
                </div>
                <div className="card text-center py-4">
                  <div className="font-syne font-black text-2xl text-ink">{stats.lessons.length}</div>
                  <div className="font-serif text-xs text-ink-3 mt-0.5">Total lessons</div>
                </div>
              </div>

              {/* Bar chart funnel */}
              <div className="card p-5 mb-4">
                <h2 className="font-syne font-bold text-sm text-ink mb-4">Completion Funnel</h2>
                <div className="space-y-3">
                  {stats.lessons.map((lesson, i) => {
                    const isDropOff = lesson.lesson_id === stats.drop_off_lesson_id;
                    const barPct = (lesson.completions / maxCompletions) * 100;
                    const ratePct = lesson.completion_rate;
                    const rateColor = ratePct >= 70 ? "bg-green" : ratePct >= 40 ? "bg-amber" : "bg-red";
                    return (
                      <div key={lesson.lesson_id}>
                        <div className="flex items-center justify-between mb-1 gap-2">
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            <span className="font-syne text-xs text-ink-3 shrink-0 w-5">{i + 1}.</span>
                            <span className={`font-syne text-xs truncate ${isDropOff ? "text-red font-semibold" : "text-ink"}`}>
                              {lesson.title}
                            </span>
                            {isDropOff && <span className="text-xs shrink-0">⚠</span>}
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            <span className="font-syne text-xs text-ink-3">{lesson.completions} done</span>
                            <span className={`font-syne font-bold text-xs ${
                              ratePct >= 70 ? "text-green" : ratePct >= 40 ? "text-amber" : "text-red"
                            }`}>{ratePct}%</span>
                          </div>
                        </div>
                        <div className="h-2 bg-bg-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${isDropOff ? "bg-red" : rateColor}`}
                            style={{ width: `${barPct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {stats.drop_off_lesson_id && (
                  <div className="mt-4 p-3 rounded-lg bg-amber-light/60 border border-amber/20">
                    <p className="font-syne font-semibold text-xs text-amber">
                      ⚠ Drop-off detected — students are stopping at this lesson. Consider simplifying it or adding more context.
                    </p>
                  </div>
                )}
              </div>

              {/* Detailed lesson table */}
              <div className="card overflow-hidden">
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                  <h2 className="font-syne font-bold text-sm text-ink">Lesson Detail</h2>
                </div>
                <div className="divide-y divide-border">
                  <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-surface text-xs font-syne text-ink-3">
                    <div className="col-span-4">Lesson</div>
                    <div className="col-span-2 text-center">Status</div>
                    <div className="col-span-2 text-center">Completions</div>
                    <div className="col-span-2 text-center">Rate</div>
                    <div className="col-span-2 text-center">Avg Quiz</div>
                  </div>
                  {stats.lessons.map((lesson, i) => {
                    const quizScore = lesson.avg_quiz_score;
                    const quizColor = quizScore === null ? "text-ink-3" :
                      quizScore >= 80 ? "text-green" : quizScore >= 60 ? "text-amber" : "text-red";
                    return (
                      <div key={lesson.lesson_id}
                        className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-surface/50 transition-colors">
                        <div className="col-span-4 min-w-0">
                          <Link
                            href={`/teacher/lessons/${lesson.lesson_id}/edit`}
                            className="font-syne text-sm text-ink hover:underline line-clamp-1"
                          >
                            {i + 1}. {lesson.title}
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
                          <span className={`font-syne font-semibold text-sm ${
                            lesson.completion_rate >= 70 ? "text-green" :
                            lesson.completion_rate >= 40 ? "text-amber" : "text-red"
                          }`}>
                            {lesson.completion_rate}%
                          </span>
                        </div>
                        <div className="col-span-2 text-center">
                          <span className={`font-syne font-semibold text-sm ${quizColor}`}>
                            {quizScore !== null ? `${quizScore.toFixed(0)}%` : "—"}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          ) : null}
        </>
      )}
    </div>
  );
}
