"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type StarterModule = {
  id: string;
  code: string;
  title: string;
  description: string;
  level: number;
  duration_hours: number;
};

type StarterPlan = {
  level: "beginner" | "intermediate" | "advanced";
  modules: StarterModule[];
};

const LEVEL_LABELS: Record<string, { label: string; color: string; desc: string }> = {
  beginner:     { label: "Beginner",     color: "bg-blue-100 text-blue-800",  desc: "We'll build a strong foundation first." },
  intermediate: { label: "Intermediate", color: "bg-amber-100 text-amber-800", desc: "You're on solid ground — let's go deeper." },
  advanced:     { label: "Advanced",     color: "bg-green/15 text-green",      desc: "Impressive! We'll challenge you from the start." },
};

export default function StarterPlanPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [plan, setPlan] = useState<StarterPlan | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    fetch(`${API_URL}/onboarding/starter-plan`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setPlan(d))
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  const levelInfo = LEVEL_LABELS[plan?.level ?? "beginner"];

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-ink-3 font-syne text-sm animate-pulse">Preparing your plan…</div>
      </div>
    );
  }

  if (!plan || plan.modules.length === 0) {
    // Fallback: go to dashboard
    router.replace("/dashboard");
    return null;
  }

  const firstName = user?.first_name || "there";
  const firstModule = plan.modules[0];

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10 space-y-8">

        {/* Header */}
        <div className="text-center space-y-2">
          <div className="text-4xl mb-2">🎯</div>
          <h1 className="font-syne font-black text-2xl text-ink">
            Your Starter Plan, {firstName}!
          </h1>
          <p className="font-serif text-ink-3 text-sm">
            Based on your onboarding, here's where to begin.
          </p>
          {levelInfo && (
            <span className={`inline-block text-xs font-syne font-bold px-3 py-1 rounded-full ${levelInfo.color}`}>
              Level: {levelInfo.label} — {levelInfo.desc}
            </span>
          )}
        </div>

        {/* Module cards */}
        <div className="space-y-4">
          {plan.modules.map((m, i) => (
            <div
              key={m.id}
              className={`card p-5 border transition-all ${i === 0 ? "border-ink shadow-md" : "border-border"}`}
            >
              <div className="flex items-start gap-4">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-syne font-black text-sm shrink-0 ${
                  i === 0 ? "bg-ink text-white" : "bg-surface-2 text-ink-3"
                }`}>
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-syne font-bold text-base text-ink mb-0.5">{m.title}</div>
                  {m.description && (
                    <p className="font-serif text-ink-3 text-sm line-clamp-2 mb-2">{m.description}</p>
                  )}
                  <div className="flex items-center gap-3 text-xs text-ink-3 font-syne">
                    {m.duration_hours > 0 && (
                      <span>⏱ {m.duration_hours}h</span>
                    )}
                    <span>Level {m.level}</span>
                    <span className="text-ink-3/50">·</span>
                    <span className="font-mono text-ink-3/70">{m.code}</span>
                  </div>
                </div>
                {i === 0 ? (
                  <Link
                    href={`/modules/${m.id}`}
                    className="btn-primary px-4 py-1.5 text-sm shrink-0"
                  >
                    Start →
                  </Link>
                ) : (
                  <Link
                    href={`/modules/${m.id}`}
                    className="btn-secondary px-4 py-1.5 text-sm shrink-0"
                  >
                    View
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Primary CTA */}
        <div className="text-center space-y-3">
          <Link
            href={`/modules/${firstModule.id}`}
            className="btn-primary inline-block px-8 py-3 text-base font-syne font-bold"
          >
            Start First Module →
          </Link>
          <div>
            <Link href="/dashboard" className="text-xs text-ink-3 hover:text-ink font-syne underline">
              Go to dashboard instead
            </Link>
          </div>
        </div>

        {/* Reassurance */}
        <div className="bg-surface-2 border border-border rounded-lg p-4 text-center">
          <p className="font-serif text-ink-3 text-xs leading-relaxed">
            You can always browse all modules, change specialties, or adjust your daily goal in Settings.
            Your plan updates as you learn.
          </p>
        </div>

      </div>
    </div>
  );
}
