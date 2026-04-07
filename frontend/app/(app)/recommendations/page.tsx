"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { contentApi } from "@/lib/api";

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

export default function RecommendationsPage() {
  const [recs, setRecs]         = useState<Recommendation[]>([]);
  const [daily, setDaily]       = useState<DailyPlan | null>(null);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      contentApi.getRecommendations().catch(() => []),
      contentApi.getDailyPlan().catch(() => null),
    ]).then(([r, d]) => {
      setRecs(Array.isArray(r) ? r : r?.recommendations ?? []);
      setDaily(d);
    }).finally(() => setLoading(false));
  }, []);

  const REASON_LABELS: Record<string, string> = {
    weak_area:     "Improve weak area",
    not_started:   "New for you",
    due_review:    "Due for review",
    next_in_path:  "Next in your path",
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-8">
      <h1 className="font-syne font-black text-2xl text-ink">Recommendations</h1>

      {loading ? (
        <div className="text-center py-16 text-ink-3">Loading…</div>
      ) : (
        <>
          {/* Daily Plan */}
          {daily && (
            <section className="card p-6">
              <h2 className="font-syne font-bold text-base text-ink mb-1">Today's Plan</h2>
              <p className="text-xs text-ink-3 mb-4">
                Goal: {daily.goal_minutes} min · {new Date(daily.date).toLocaleDateString()}
              </p>
              <div className="space-y-2">
                {(daily.tasks ?? []).map((task, i) => (
                  <Link key={i} href={task.href} className="flex items-center gap-3 hover:bg-surface-2 rounded-lg p-2 -mx-2 transition-colors">
                    <span className="text-lg">
                      {task.type === "flashcard" ? "🃏" : task.type === "lesson" ? "📖" : task.type === "mcq" ? "❓" : "🩺"}
                    </span>
                    <span className="flex-1 text-sm text-ink">{task.label}</span>
                    <span className="text-xs text-ink-3">{task.minutes} min</span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Module Recommendations */}
          <section>
            <h2 className="font-syne font-bold text-base text-ink mb-4">Recommended Modules</h2>
            {recs.length === 0 ? (
              <div className="text-center py-8 text-ink-3">
                Complete some modules to get personalized recommendations.
              </div>
            ) : (
              <div className="space-y-3">
                {recs.map((rec, i) => (
                  <Link
                    key={rec.module_id}
                    href={`/modules/${rec.module_id}`}
                    className="card flex items-center gap-4 px-4 py-3 hover:bg-surface-2 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-accent/10 text-accent font-bold text-sm flex items-center justify-center shrink-0">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm text-ink truncate">{rec.module_title}</div>
                      <div className="text-xs text-ink-3 mt-0.5">
                        {REASON_LABELS[rec.reason] ?? rec.reason}
                      </div>
                    </div>
                    <span className="text-ink-3 text-lg">→</span>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
