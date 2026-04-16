"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

interface LessonStat {
  lesson_id: string;
  title: string;
  lesson_order: number;
  completions: number;
  completion_rate: number;
  estimated_minutes: number;
  status: string;
}

interface AnalyticsData {
  module_id: string;
  module_title: string;
  total_students: number;
  avg_completion_rate: number;
  drop_off_lesson_id: string | null;
  lessons: LessonStat[];
}

export default function ModuleAnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/lessons/modules/${id}/analytics`)
      .then(r => setData(r.data))
      .catch(() => setError("Could not load analytics"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8 text-ink-3 font-serif">Loading analytics…</div>;
  if (error) return <div className="p-8 text-red-500 font-serif">{error}</div>;
  if (!data) return null;

  const maxCompletions = Math.max(...data.lessons.map(l => l.completions), 1);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Back */}
      <Link href={`/teacher/courses/${id}`} className="text-xs text-ink-3 hover:text-ink font-syne mb-4 inline-block">
        ← Back to course
      </Link>

      <div className="flex items-start justify-between mb-1">
        <h1 className="font-syne font-black text-2xl text-ink">{data.module_title}</h1>
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
      <p className="font-serif text-ink-3 text-sm mb-6">Engagement Analytics</p>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { value: data.total_students, label: "Enrolled students" },
          { value: `${data.avg_completion_rate}%`, label: "Avg completion" },
          { value: data.lessons.length, label: "Total lessons" },
        ].map(({ value, label }) => (
          <div key={label} className="card text-center py-4">
            <div className="font-syne font-black text-2xl text-ink">{value}</div>
            <div className="font-serif text-ink-3 text-xs mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Per-lesson bar chart */}
      <div className="card p-6">
        <h2 className="font-syne font-bold text-sm text-ink mb-5">Lesson Completion Funnel</h2>
        <div className="space-y-3">
          {data.lessons.map((lesson, i) => {
            const isDropOff = lesson.lesson_id === data.drop_off_lesson_id;
            const pct = maxCompletions > 0 ? (lesson.completions / maxCompletions) * 100 : 0;
            return (
              <div key={lesson.lesson_id}>
                <div className="flex items-center justify-between mb-1">
                  <span className={`font-syne text-xs ${isDropOff ? "text-red-500 font-bold" : "text-ink"} truncate max-w-xs`}>
                    {i + 1}. {lesson.title}{isDropOff ? " ⚠ Drop-off" : ""}
                  </span>
                  <span className="font-syne font-bold text-xs text-ink-3 ml-2 shrink-0">
                    {lesson.completions} ({lesson.completion_rate}%)
                  </span>
                </div>
                <div className="h-2 bg-ink/5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${isDropOff ? "bg-red-400" : "bg-blue"}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
        {data.drop_off_lesson_id && (
          <p className="mt-4 text-xs font-serif text-amber-600 bg-amber-50 p-3 rounded">
            ⚠ Students are dropping off significantly at the highlighted lesson. Consider revising its difficulty or adding more context.
          </p>
        )}
      </div>
    </div>
  );
}
