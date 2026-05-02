"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { contentApi, adaptivePlanApi } from "@/lib/api";

interface Recommendation {
  module_id: string;
  module_title: string;
  reason: string;
  priority: number;
}

interface DailyPlan {
  date: string;
  goal_minutes: number;
  tasks: Array<{ type: string; label: string; href: string; minutes: number }>;
}

interface AdaptivePlanModule {
  module_id: string;
  module_title: string;
  reason: string;
  priority_score?: number;
  suggested_action?: string;
}

interface AdaptivePlan {
  generated_at: string;
  weak_areas: AdaptivePlanModule[];
  next_modules: AdaptivePlanModule[];
  due_reviews: AdaptivePlanModule[];
}

const REASON_LABELS: Record<string, string> = {
  weak_area: "Improve weak area",
  not_started: "New for you",
  due_review: "Due for review",
  next_in_path: "Next in your path",
};

const TASK_ICONS: Record<string, string> = {
  flashcard: "🃏",
  lesson: "📖",
  mcq: "❓",
  case: "🩺",
};

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [daily, setDaily] = useState<DailyPlan | null>(null);
  const [loading, setLoading] = useState(true);

  const [adaptivePlan, setAdaptivePlan] = useState<AdaptivePlan | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState("");
  const [planTab, setPlanTab] = useState<"weak" | "next" | "review">("weak");

  useEffect(() => {
    Promise.all([
      contentApi.getRecommendations().catch(() => []),
      contentApi.getDailyPlan().catch(() => null),
      adaptivePlanApi.getCurrent().catch(() => null),
    ]).then(([r, d, plan]) => {
      setRecs(Array.isArray(r) ? r : r?.recommendations ?? []);
      setDaily(d);
      if (plan) setAdaptivePlan(plan);
    }).finally(() => setLoading(false));
  }, []);

  async function handleGeneratePlan() {
    setPlanLoading(true);
    setPlanError("");
    try {
      const plan = await adaptivePlanApi.generate();
      setAdaptivePlan(plan);
    } catch {
      setPlanError("Could not generate plan. Complete some modules first.");
    } finally {
      setPlanLoading(false);
    }
  }

  const planSections = adaptivePlan
    ? [
        { key: "weak" as const, label: "Weak Areas", icon: "⚠️", items: adaptivePlan.weak_areas ?? [] },
        { key: "next" as const, label: "Up Next", icon: "➡️", items: adaptivePlan.next_modules ?? [] },
        { key: "review" as const, label: "Due Reviews", icon: "🔄", items: adaptivePlan.due_reviews ?? [] },
      ]
    : [];

  const activePlanItems = planSections.find((s) => s.key === planTab)?.items ?? [];

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="font-syne font-black text-2xl text-ink">For You</h1>
        <Link
          href="/my-courses"
          className="text-xs font-syne text-ink-3 border border-border rounded px-3 py-1.5 hover:border-ink-3 transition-colors"
        >
          🎓 My Courses
        </Link>
      </div>

      {loading ? (
        <div className="text-center py-16 text-ink-3 animate-pulse">Loading…</div>
      ) : (
        <>
          {/* Daily Plan */}
          {daily && (
            <section className="card p-6">
              <h2 className="font-syne font-bold text-base text-ink mb-1">Today's Plan</h2>
              <p className="font-serif text-xs text-ink-3 mb-4">
                Goal: {daily.goal_minutes} min ·{" "}
                {new Date(daily.date).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}
              </p>
              {(daily.tasks ?? []).length === 0 ? (
                <p className="font-serif text-sm text-ink-3">No tasks for today. Complete some modules first.</p>
              ) : (
                <div className="space-y-2">
                  {(daily.tasks ?? []).map((task, i) => (
                    <Link
                      key={i}
                      href={task.href}
                      className="flex items-center gap-3 hover:bg-surface rounded-lg p-2 -mx-2 transition-colors"
                    >
                      <span className="text-lg">{TASK_ICONS[task.type] ?? "📌"}</span>
                      <span className="flex-1 text-sm text-ink font-serif">{task.label}</span>
                      <span className="text-xs text-ink-3 font-syne shrink-0">{task.minutes} min</span>
                    </Link>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Adaptive Study Plan */}
          <section className="card p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="font-syne font-bold text-base text-ink">Adaptive Study Plan</h2>
                <p className="font-serif text-xs text-ink-3 mt-0.5">
                  {adaptivePlan
                    ? `Generated ${new Date(adaptivePlan.generated_at).toLocaleDateString()}`
                    : "AI-personalized based on your weak areas and progress"}
                </p>
              </div>
              <button
                onClick={handleGeneratePlan}
                disabled={planLoading}
                className="btn-primary text-xs px-4 py-2 rounded-lg font-syne font-semibold disabled:opacity-50 shrink-0"
              >
                {planLoading ? "Generating…" : adaptivePlan ? "Refresh Plan" : "Generate Plan"}
              </button>
            </div>

            {planError && (
              <p className="font-serif text-xs text-red mb-3">{planError}</p>
            )}

            {!adaptivePlan ? (
              <div className="text-center py-8">
                <div className="text-4xl mb-3">🧠</div>
                <p className="font-serif text-sm text-ink-3">
                  Generate your first adaptive plan to get personalized study recommendations based on your performance.
                </p>
              </div>
            ) : (
              <>
                {/* Plan tabs */}
                <div className="flex gap-1 mb-4 bg-surface rounded-lg p-1">
                  {planSections.map((s) => (
                    <button
                      key={s.key}
                      onClick={() => setPlanTab(s.key)}
                      className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md font-syne text-xs font-semibold transition-colors ${
                        planTab === s.key
                          ? "bg-white shadow-sm text-ink"
                          : "text-ink-3 hover:text-ink"
                      }`}
                    >
                      <span>{s.icon}</span>
                      <span>{s.label}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                        planTab === s.key ? "bg-ink/10 text-ink" : "bg-border text-ink-3"
                      }`}>
                        {s.items.length}
                      </span>
                    </button>
                  ))}
                </div>

                {activePlanItems.length === 0 ? (
                  <p className="font-serif text-sm text-ink-3 text-center py-4">
                    {planTab === "weak" && "No weak areas detected — great work!"}
                    {planTab === "next" && "No upcoming modules suggested."}
                    {planTab === "review" && "No reviews due — you're up to date!"}
                  </p>
                ) : (
                  <div className="space-y-2">
                    {activePlanItems.map((item, i) => (
                      <Link
                        key={item.module_id ?? i}
                        href={`/modules/${item.module_id}`}
                        className="flex items-center gap-3 hover:bg-surface rounded-lg p-2.5 -mx-1 transition-colors group"
                      >
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center font-syne font-bold text-xs shrink-0 ${
                          planTab === "weak"
                            ? "bg-red-light text-red"
                            : planTab === "review"
                            ? "bg-amber-light text-amber"
                            : "bg-blue-light text-blue"
                        }`}>
                          {i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-syne font-semibold text-sm text-ink group-hover:underline truncate">
                            {item.module_title}
                          </div>
                          {item.suggested_action && (
                            <div className="font-serif text-xs text-ink-3 mt-0.5">{item.suggested_action}</div>
                          )}
                          {item.reason && !item.suggested_action && (
                            <div className="font-serif text-xs text-ink-3 mt-0.5">
                              {REASON_LABELS[item.reason] ?? item.reason}
                            </div>
                          )}
                        </div>
                        {item.priority_score !== undefined && (
                          <div className="shrink-0 text-xs font-syne font-bold text-ink-3">
                            {Math.round(item.priority_score)}%
                          </div>
                        )}
                        <span className="text-ink-3 text-sm shrink-0">→</span>
                      </Link>
                    ))}
                  </div>
                )}
              </>
            )}
          </section>

          {/* Module Recommendations */}
          {recs.length > 0 && (
            <section>
              <h2 className="font-syne font-bold text-base text-ink mb-4">Recommended Modules</h2>
              <div className="space-y-2">
                {recs.map((rec, i) => (
                  <Link
                    key={rec.module_id}
                    href={`/modules/${rec.module_id}`}
                    className="card flex items-center gap-4 px-4 py-3 hover:bg-surface transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-blue-light text-blue font-bold text-sm flex items-center justify-center shrink-0 font-syne">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-syne font-semibold text-sm text-ink truncate">{rec.module_title}</div>
                      <div className="font-serif text-xs text-ink-3 mt-0.5">
                        {REASON_LABELS[rec.reason] ?? rec.reason}
                      </div>
                    </div>
                    <span className="text-ink-3 text-lg shrink-0">→</span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {recs.length === 0 && !daily && !adaptivePlan && (
            <div className="text-center py-8 text-ink-3">
              <div className="text-4xl mb-3">🎯</div>
              <p className="font-serif text-sm">
                Complete some modules to get personalized recommendations.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
