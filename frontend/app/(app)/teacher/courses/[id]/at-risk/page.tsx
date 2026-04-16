"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

interface AtRiskStudent {
  student_id: string;
  name: string;
  email: string;
  risk_score: number;
  risk_factors: string[];
  last_active: string | null;
  completion_percent: number;
}

interface AtRiskData {
  at_risk: AtRiskStudent[];
  healthy: AtRiskStudent[];
  total_enrolled: number;
}

const RISK_FACTOR_LABELS: Record<string, string> = {
  inactivity: "Inactive >7 days",
  low_completion: "Low completion (<20%)",
  flashcard_struggle: "Flashcard retention <50%",
  no_streak: "No active streak",
};

function riskBadge(score: number) {
  if (score >= 80) return "bg-red-light border-red/30 text-red";
  if (score >= 60) return "bg-amber-light border-amber/30 text-amber";
  return "bg-yellow-50 border-yellow-200 text-yellow-700";
}

function riskLabel(score: number) {
  if (score >= 80) return "High risk";
  if (score >= 60) return "Medium risk";
  return "Watch";
}

function daysSince(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return `${diff} days ago`;
}

export default function AtRiskPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<AtRiskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    teacherApi.getAtRiskStudents(id)
      .then(setData)
      .catch(() => setError("Failed to load at-risk data"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8 text-ink-3 font-serif text-sm">Loading…</div>;
  if (error) return <div className="p-8 text-red font-serif text-sm">{error}</div>;
  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <Link href={`/teacher/courses/${id}`}
        className="text-xs text-ink-3 hover:text-ink font-syne mb-4 inline-block">
        ← Back to course
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">At-Risk Students</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">
            {data.at_risk.length} at-risk · {data.healthy.length} healthy · {data.total_enrolled} total enrolled
          </p>
        </div>
        <Link href={`/teacher/courses/${id}/insights`}
          className="text-xs font-syne text-ink-3 border border-border rounded px-3 py-1.5 hover:border-ink-3 transition-colors">
          📊 Content Insights
        </Link>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { value: data.at_risk.length, label: "At-risk students", color: "text-red" },
          { value: data.healthy.length, label: "Healthy students", color: "text-green" },
          { value: data.total_enrolled, label: "Total enrolled", color: "text-ink" },
        ].map(({ value, label, color }) => (
          <div key={label} className="card text-center py-4">
            <div className={`font-syne font-black text-3xl ${color}`}>{value}</div>
            <div className="font-serif text-ink-3 text-xs mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* At-risk students */}
      {data.at_risk.length === 0 ? (
        <div className="card p-8 text-center mb-6">
          <div className="text-3xl mb-2">✅</div>
          <div className="font-syne font-semibold text-ink">No at-risk students</div>
          <div className="font-serif text-ink-3 text-sm mt-1">All enrolled students are on track.</div>
        </div>
      ) : (
        <div className="mb-8">
          <h2 className="font-syne font-bold text-sm text-ink mb-3 flex items-center gap-2">
            <span className="text-red">⚠</span> Students needing attention
          </h2>
          <div className="card overflow-hidden">
            <div className="divide-y divide-border">
              {data.at_risk
                .sort((a, b) => b.risk_score - a.risk_score)
                .map((s) => (
                  <div key={s.student_id} className="px-4 py-4">
                    <div className="flex items-start gap-3">
                      {/* Risk badge */}
                      <div className={`border rounded-lg px-2 py-1 text-center shrink-0 min-w-[64px] ${riskBadge(s.risk_score)}`}>
                        <div className="font-syne font-black text-lg leading-none">{s.risk_score}</div>
                        <div className="font-syne text-[10px] font-semibold">{riskLabel(s.risk_score)}</div>
                      </div>

                      {/* Student info */}
                      <div className="flex-1 min-w-0">
                        <div className="font-syne font-semibold text-sm text-ink">{s.name || s.email}</div>
                        {s.name && s.name !== s.email && (
                          <div className="font-serif text-xs text-ink-3">{s.email}</div>
                        )}
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {s.risk_factors.map((f) => (
                            <span key={f}
                              className="font-syne text-[10px] bg-red-light border border-red/20 text-red rounded px-1.5 py-0.5">
                              {RISK_FACTOR_LABELS[f] ?? f}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Metrics */}
                      <div className="shrink-0 text-right">
                        <div className="font-syne font-bold text-sm text-ink">{Math.round(s.completion_percent)}%</div>
                        <div className="font-serif text-[10px] text-ink-3">completion</div>
                        <div className="font-serif text-[10px] text-ink-3 mt-0.5">{daysSince(s.last_active)}</div>
                      </div>
                    </div>

                    {/* Completion bar */}
                    <div className="mt-2.5 h-1.5 bg-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-red/50 rounded-full transition-all"
                        style={{ width: `${Math.min(s.completion_percent, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Healthy students */}
      {data.healthy.length > 0 && (
        <div>
          <h2 className="font-syne font-bold text-sm text-ink mb-3 flex items-center gap-2">
            <span className="text-green">✓</span> On-track students
          </h2>
          <div className="card overflow-hidden">
            <div className="divide-y divide-border">
              {data.healthy.map((s) => (
                <div key={s.student_id} className="px-4 py-3 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-green-light border border-green/20 flex items-center justify-center font-syne font-bold text-green text-xs shrink-0">
                    {(s.name || s.email)?.[0]?.toUpperCase() ?? "?"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-syne text-sm text-ink truncate">{s.name || s.email}</div>
                    {s.name && s.name !== s.email && (
                      <div className="font-serif text-xs text-ink-3 truncate">{s.email}</div>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="font-syne font-bold text-sm text-green">{Math.round(s.completion_percent)}%</div>
                    <div className="font-serif text-[10px] text-ink-3">{daysSince(s.last_active)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
