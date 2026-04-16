"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

interface ModuleInsight {
  module_id: string;
  title: string;
  avg_completion_percent: number;
  difficulty_label: "easy" | "moderate" | "hard" | "very_hard";
  avg_lessons_done: number;
}

interface InsightsData {
  modules: ModuleInsight[];
}

const DIFFICULTY_CONFIG: Record<string, { color: string; bg: string; border: string; label: string; tip?: string }> = {
  very_hard: {
    color: "text-red",
    bg: "bg-red-light",
    border: "border-red/30",
    label: "Very Hard",
    tip: "Consider simplifying this module or adding more scaffolding.",
  },
  hard: {
    color: "text-amber",
    bg: "bg-amber-light",
    border: "border-amber/30",
    label: "Hard",
    tip: "Students are struggling. Review lesson pacing or add examples.",
  },
  moderate: {
    color: "text-blue",
    bg: "bg-blue-light",
    border: "border-blue/30",
    label: "Moderate",
  },
  easy: {
    color: "text-green",
    bg: "bg-green-light",
    border: "border-green/30",
    label: "Easy",
  },
};

export default function ContentInsightsPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<InsightsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    teacherApi.getContentInsights(id)
      .then(setData)
      .catch(() => setError("Failed to load content insights"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8 text-ink-3 font-serif text-sm">Loading…</div>;
  if (error) return <div className="p-8 text-red font-serif text-sm">{error}</div>;
  if (!data) return null;

  const modules = [...data.modules].sort((a, b) => {
    const order = ["very_hard", "hard", "moderate", "easy"];
    return order.indexOf(a.difficulty_label) - order.indexOf(b.difficulty_label);
  });

  const hardCount = modules.filter(m => m.difficulty_label === "very_hard" || m.difficulty_label === "hard").length;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <Link href={`/teacher/courses/${id}`}
        className="text-xs text-ink-3 hover:text-ink font-syne mb-4 inline-block">
        ← Back to course
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">Content Insights</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">
            Module difficulty analysis based on student completion data
          </p>
        </div>
        <Link href={`/teacher/courses/${id}/at-risk`}
          className="text-xs font-syne text-amber border border-amber/30 rounded px-3 py-1.5 hover:bg-amber-light transition-colors">
          ⚠️ At-Risk Students
        </Link>
      </div>

      {/* Alert if hard modules */}
      {hardCount > 0 && (
        <div className="mb-6 p-4 rounded-xl bg-amber-light border border-amber/30">
          <div className="font-syne font-bold text-sm text-amber mb-1">
            ⚠ {hardCount} module{hardCount > 1 ? "s" : ""} need attention
          </div>
          <p className="font-serif text-xs text-ink-3">
            Students are consistently struggling with these modules. Consider revising the content, adding more examples, or breaking them into smaller lessons.
          </p>
        </div>
      )}

      {/* Summary */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {(["very_hard", "hard", "moderate", "easy"] as const).map((d) => {
          const cfg = DIFFICULTY_CONFIG[d];
          const count = modules.filter(m => m.difficulty_label === d).length;
          return (
            <div key={d} className={`card text-center py-3 border ${cfg.border} ${cfg.bg}`}>
              <div className={`font-syne font-black text-2xl ${cfg.color}`}>{count}</div>
              <div className={`font-syne text-xs font-semibold ${cfg.color}`}>{cfg.label}</div>
            </div>
          );
        })}
      </div>

      {/* Module list */}
      {modules.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="text-3xl mb-2">📊</div>
          <div className="font-syne font-semibold text-ink">No data yet</div>
          <div className="font-serif text-ink-3 text-sm mt-1">Students need to start completing modules before insights appear.</div>
        </div>
      ) : (
        <div className="space-y-3">
          {modules.map((m) => {
            const cfg = DIFFICULTY_CONFIG[m.difficulty_label] ?? DIFFICULTY_CONFIG.moderate;
            return (
              <div key={m.module_id} className={`card p-4 border ${cfg.border}`}>
                <div className="flex items-start gap-4">
                  {/* Difficulty badge */}
                  <div className={`rounded-lg px-2.5 py-1.5 shrink-0 border ${cfg.border} ${cfg.bg}`}>
                    <div className={`font-syne font-bold text-xs ${cfg.color}`}>{cfg.label}</div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <Link
                        href={`/teacher/modules/${m.module_id}`}
                        className="font-syne font-bold text-sm text-ink hover:underline truncate"
                      >
                        {m.title}
                      </Link>
                      <span className="font-syne font-bold text-sm text-ink shrink-0">
                        {Math.round(m.avg_completion_percent)}%
                      </span>
                    </div>

                    {/* Completion bar */}
                    <div className="mt-2 h-2 bg-border rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          m.difficulty_label === "very_hard" ? "bg-red/60" :
                          m.difficulty_label === "hard" ? "bg-amber/60" :
                          m.difficulty_label === "moderate" ? "bg-blue/60" : "bg-green/60"
                        }`}
                        style={{ width: `${Math.min(m.avg_completion_percent, 100)}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between mt-1">
                      <span className="font-serif text-xs text-ink-3">
                        Avg {m.avg_lessons_done} lesson{m.avg_lessons_done !== 1 ? "s" : ""} completed
                      </span>
                      <span className="font-serif text-xs text-ink-3">avg completion</span>
                    </div>

                    {/* Recommendation */}
                    {cfg.tip && (
                      <div className={`mt-2 text-xs font-serif ${cfg.color} italic`}>
                        💡 {cfg.tip}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
