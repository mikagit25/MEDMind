"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { teacherApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

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

export default function ContentInsightsPage() {
  const t = useT();
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

  const DIFFICULTY_CONFIG: Record<string, { color: string; bg: string; border: string; labelKey: string; tipKey?: string }> = {
    very_hard: {
      color: "text-red",
      bg: "bg-red-light",
      border: "border-red/30",
      labelKey: "teacher.courses.diff_very_hard",
      tipKey: "teacher.courses.tip_very_hard",
    },
    hard: {
      color: "text-amber",
      bg: "bg-amber-light",
      border: "border-amber/30",
      labelKey: "teacher.courses.diff_hard",
      tipKey: "teacher.courses.tip_hard",
    },
    moderate: {
      color: "text-blue",
      bg: "bg-blue-light",
      border: "border-blue/30",
      labelKey: "teacher.courses.diff_moderate",
    },
    easy: {
      color: "text-green",
      bg: "bg-green-light",
      border: "border-green/30",
      labelKey: "teacher.courses.diff_easy",
    },
  };

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
        {t("teacher.courses.back_course")}
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("teacher.courses.insights_title")}</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">
            {t("teacher.courses.insights_subtitle")}
          </p>
        </div>
        <Link href={`/teacher/courses/${id}/at-risk`}
          className="text-xs font-syne text-amber border border-amber/30 rounded px-3 py-1.5 hover:bg-amber-light transition-colors">
          ⚠️ {t("teacher.courses.at_risk_btn")}
        </Link>
      </div>

      {/* Alert if hard modules */}
      {hardCount > 0 && (
        <div className="mb-6 p-4 rounded-xl bg-amber-light border border-amber/30">
          <div className="font-syne font-bold text-sm text-amber mb-1">
            ⚠ {hardCount} {t("teacher.courses.need_attention")}
          </div>
          <p className="font-serif text-xs text-ink-3">
            {t("teacher.courses.hard_advice")}
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
              <div className={`font-syne text-xs font-semibold ${cfg.color}`}>{t(cfg.labelKey as any)}</div>
            </div>
          );
        })}
      </div>

      {/* Module list */}
      {modules.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="text-3xl mb-2">📊</div>
          <div className="font-syne font-semibold text-ink">{t("teacher.courses.no_data")}</div>
          <div className="font-serif text-ink-3 text-sm mt-1">{t("teacher.courses.no_data_hint")}</div>
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
                    <div className={`font-syne font-bold text-xs ${cfg.color}`}>{t(cfg.labelKey as any)}</div>
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
                        {t("teacher.analytics.avg_completion")} {m.avg_lessons_done} {t("teacher.courses.avg_lessons")}
                      </span>
                      <span className="font-serif text-xs text-ink-3">{t("teacher.courses.avg_completion_label")}</span>
                    </div>

                    {/* Recommendation */}
                    {cfg.tipKey && (
                      <div className={`mt-2 text-xs font-serif ${cfg.color} italic`}>
                        💡 {t(cfg.tipKey as any)}
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
