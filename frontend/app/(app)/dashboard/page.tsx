"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { contentApi, progressApi, adaptivePlanApi } from "@/lib/api";

const LEVEL_THRESHOLDS = [0, 500, 2000, 5000, 12000, 25000];

function xpToNextLevel(xp: number, level: number) {
  const start = LEVEL_THRESHOLDS[level - 1] ?? 0;
  const end = LEVEL_THRESHOLDS[level] ?? LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1];
  const current = xp - start;
  const needed = end - start;
  return { current, needed, pct: Math.min((current / needed) * 100, 100) };
}

// ── PDF download button ──
function DownloadPDFButton() {
  const [loading, setLoading] = useState(false);

  async function handleDownload() {
    setLoading(true);
    try {
      const blob = await progressApi.exportPDF();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `medmind_cpd_${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Could not generate report. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      className="mt-3 w-full py-2 px-3 rounded bg-green text-white font-syne font-semibold text-xs hover:bg-green/90 transition-colors disabled:opacity-60"
    >
      {loading ? "Generating…" : "⬇ Download CPD/CME Report (PDF)"}
    </button>
  );
}

// ── Shared stat card ──
function StatCard({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="card text-center py-4">
      <div className="font-syne font-black text-2xl text-ink">{value}</div>
      <div className="font-serif text-ink-3 text-xs mt-0.5">{label}</div>
    </div>
  );
}

// ── Role-specific panel: Doctor ──
function DoctorPanel({ stats }: { stats: any }) {
  const cmeCredits = stats?.cme_credits ?? 0;
  const casesCompleted = stats?.cases_completed ?? 0;
  const mcqAccuracy = stats?.mcq_accuracy ?? 0;
  return (
    <div className="mb-6">
      <h2 className="font-syne font-bold text-base text-ink mb-3">Clinical Dashboard</h2>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatCard value={`${cmeCredits}`} label="CME Credits" />
        <StatCard value={casesCompleted} label="Cases solved" />
        <StatCard value={`${Math.round(mcqAccuracy * 100)}%`} label="MCQ accuracy" />
      </div>
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-syne font-semibold text-sm text-ink">Continue Practice</h3>
          <Link href="/cases" className="text-xs text-ink-3 hover:text-ink font-syne">View all →</Link>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Link href="/cases" className="flex items-center gap-2 p-3 rounded bg-amber-light border border-amber/20 hover:border-amber/40 transition-colors">
            <span className="text-xl">🩺</span>
            <div>
              <div className="font-syne font-semibold text-xs text-amber">Clinical Cases</div>
              <div className="font-serif text-xs text-ink-3">Evidence-based</div>
            </div>
          </Link>
          <Link href="/drugs" className="flex items-center gap-2 p-3 rounded bg-blue-light border border-blue/20 hover:border-blue/40 transition-colors">
            <span className="text-xl">💊</span>
            <div>
              <div className="font-syne font-semibold text-xs text-blue">Drug Reference</div>
              <div className="font-serif text-xs text-ink-3">Interactions & dosing</div>
            </div>
          </Link>
        </div>
        {cmeCredits >= 0 && (
          <div className="mt-3 p-3 rounded bg-green-light border border-green/20">
            <div className="flex items-center justify-between">
              <span className="font-syne font-semibold text-xs text-green">CME Progress</span>
              <span className="font-syne font-bold text-xs text-green">{cmeCredits} / 50 credits</span>
            </div>
            <div className="mt-1.5 h-1.5 bg-green/20 rounded-full">
              <div className="h-full bg-green rounded-full" style={{ width: `${Math.min((cmeCredits / 50) * 100, 100)}%` }} />
            </div>
            <p className="font-serif text-xs text-ink-3 mt-1.5">Complete modules to earn CME/CPD credits</p>
            <DownloadPDFButton />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Role-specific panel: Professor ──
function ProfessorPanel({ stats }: { stats: any }) {
  const modulesCompleted = stats?.modules_completed ?? 0;
  const lessonsCompleted = stats?.lessons_completed ?? 0;
  return (
    <div className="mb-6">
      <h2 className="font-syne font-bold text-base text-ink mb-3">Teaching Dashboard</h2>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatCard value={modulesCompleted} label="Modules done" />
        <StatCard value={lessonsCompleted} label="Lessons taught" />
        <StatCard value={stats?.streak_days ?? 0} label="Day streak 🔥" />
      </div>
      {/* Teacher authoring shortcut */}
      <Link href="/teacher/modules" className="flex items-center justify-between p-4 rounded-xl bg-ink text-white mb-3 hover:bg-ink/90 transition-colors">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✏️</span>
          <div>
            <div className="font-syne font-bold text-sm">My Lessons</div>
            <div className="font-serif text-xs text-white/70">Create and manage your modules</div>
          </div>
        </div>
        <span className="text-white/60 text-lg">→</span>
      </Link>
      <div className="card p-4 mb-3">
        <h3 className="font-syne font-semibold text-sm text-ink mb-3">Curriculum Tools</h3>
        <div className="grid grid-cols-2 gap-2">
          <Link href="/modules" className="flex items-center gap-2 p-3 rounded bg-red-light border border-red/20 hover:border-red/40 transition-colors">
            <span className="text-xl">📚</span>
            <div>
              <div className="font-syne font-semibold text-xs text-red">All Modules</div>
              <div className="font-serif text-xs text-ink-3">Browse curriculum</div>
            </div>
          </Link>
          <Link href="/quiz" className="flex items-center gap-2 p-3 rounded bg-blue-light border border-blue/20 hover:border-blue/40 transition-colors">
            <span className="text-xl">📝</span>
            <div>
              <div className="font-syne font-semibold text-xs text-blue">Quiz Bank</div>
              <div className="font-serif text-xs text-ink-3">MCQ practice</div>
            </div>
          </Link>
          <Link href="/ai-tutor" className="flex items-center gap-2 p-3 rounded bg-green-light border border-green/20 hover:border-green/40 transition-colors">
            <span className="text-xl">🤖</span>
            <div>
              <div className="font-syne font-semibold text-xs text-green">AI Assistant</div>
              <div className="font-serif text-xs text-ink-3">Research & explain</div>
            </div>
          </Link>
          <Link href="/search" className="flex items-center gap-2 p-3 rounded border border-border bg-surface hover:border-ink-3 transition-colors">
            <span className="text-xl">🔍</span>
            <div>
              <div className="font-syne font-semibold text-xs text-ink">Search</div>
              <div className="font-serif text-xs text-ink-3">Find any content</div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ── Role-specific panel: Veterinarian ──
function VeterinarianPanel({ stats }: { stats: any }) {
  return (
    <div className="mb-6">
      <h2 className="font-syne font-bold text-base text-ink mb-3">Veterinary Dashboard</h2>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatCard value={stats?.lessons_completed ?? 0} label="Lessons done" />
        <StatCard value={stats?.cards_reviewed ?? 0} label="Cards reviewed" />
        <StatCard value={`${stats?.streak_days ?? 0}🔥`} label="Day streak" />
      </div>
      <div className="card p-4 mb-3">
        <h3 className="font-syne font-semibold text-sm text-ink mb-3">Vet Tools</h3>
        <div className="grid grid-cols-2 gap-2">
          <Link href="/drugs?vet=true" className="flex items-center gap-2 p-3 rounded bg-amber-light border border-amber/20 hover:border-amber/40 transition-colors">
            <span className="text-xl">🐾</span>
            <div>
              <div className="font-syne font-semibold text-xs text-amber">Vet Drug Reference</div>
              <div className="font-serif text-xs text-ink-3">Species-specific dosing</div>
            </div>
          </Link>
          <Link href="/cases?vet=true" className="flex items-center gap-2 p-3 rounded bg-green-light border border-green/20 hover:border-green/40 transition-colors">
            <span className="text-xl">🩺</span>
            <div>
              <div className="font-syne font-semibold text-xs text-green">Vet Cases</div>
              <div className="font-serif text-xs text-ink-3">Clinical scenarios</div>
            </div>
          </Link>
        </div>
      </div>
      <div className="card p-3 bg-amber-light/40 border-amber/20">
        <p className="font-syne font-semibold text-xs text-amber-dark mb-1">⚠️ Toxicity Quick Check</p>
        <p className="font-serif text-xs text-ink-2">
          Common dangers: paracetamol (cats), xylitol (dogs), permethrin (cats).{" "}
          <Link href="/drugs" className="text-amber underline">Check drug safety →</Link>
        </p>
      </div>
    </div>
  );
}

// ── Streak Calendar (last 7 days) ──────────────────────────────────────────
function StreakCalendar({ streakDays }: { streakDays: number }) {
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return {
      label: d.toLocaleDateString("en-US", { weekday: "short" }).slice(0, 1),
      date: d.toISOString().slice(0, 10),
      // Assume consecutive days going back from today
      active: i >= 7 - Math.min(streakDays, 7),
      isToday: i === 6,
    };
  });

  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-syne font-bold text-sm text-ink">Study Streak</span>
        <span className="font-syne font-black text-sm text-amber">{streakDays} 🔥</span>
      </div>
      <div className="flex gap-1.5">
        {days.map((d, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={`w-full aspect-square rounded-md transition-all ${
                d.active
                  ? d.isToday
                    ? "bg-amber shadow-sm shadow-amber/30"
                    : "bg-amber/40"
                  : "bg-bg-2"
              }`}
            />
            <span className={`font-syne text-xs ${d.isToday ? "font-bold text-ink" : "text-ink-3"}`}>
              {d.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Today's Plan ────────────────────────────────────────────────────────────
function TodaysPlan() {
  const router = useRouter();
  const [plan, setPlan] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adaptivePlanApi.getCurrent().catch(() => null).then((data: any) => {
      setPlan(data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return null;

  const upNext: any[] = plan?.up_next?.slice(0, 3) ?? [];
  const dueReviews: any[] = plan?.due_reviews?.slice(0, 2) ?? [];
  const weakAreas: any[] = plan?.weak_areas?.slice(0, 2) ?? [];

  const tasks = [
    ...upNext.map((t: any) => ({
      label: t.title ?? t.topic ?? "Continue studying",
      icon: "📚",
      href: t.lesson_id ? `/modules/${t.module_id}` : "/modules",
      color: "text-blue",
      bg: "bg-blue-light",
    })),
    ...dueReviews.map((t: any) => ({
      label: `Review: ${t.topic ?? t.title ?? "Flashcards"}`,
      icon: "🃏",
      href: "/flashcards",
      color: "text-green",
      bg: "bg-green-light",
    })),
    ...weakAreas.map((t: any) => ({
      label: `Strengthen: ${t.topic ?? t.title ?? "Weak area"}`,
      icon: "💪",
      href: "/quiz",
      color: "text-amber",
      bg: "bg-amber-light",
    })),
  ].slice(0, 4);

  if (tasks.length === 0) {
    return (
      <div className="card p-4 mb-4 flex items-center gap-3">
        <span className="text-xl">✅</span>
        <div>
          <div className="font-syne font-bold text-sm text-ink">All caught up!</div>
          <div className="font-serif text-xs text-ink-3">Generate your adaptive plan to get personalized tasks.</div>
        </div>
        <button
          onClick={() => router.push("/recommendations")}
          className="ml-auto font-syne font-semibold text-xs text-ink border border-border rounded px-2 py-1 hover:border-ink transition-colors"
        >
          Plan →
        </button>
      </div>
    );
  }

  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-syne font-bold text-sm text-ink">Today's Plan</span>
        <button
          onClick={() => router.push("/recommendations")}
          className="font-syne text-xs text-ink-3 hover:text-ink"
        >
          See all →
        </button>
      </div>
      <div className="space-y-2">
        {tasks.map((task, i) => (
          <button
            key={i}
            onClick={() => router.push(task.href)}
            className="w-full flex items-center gap-3 p-2.5 rounded-lg hover:bg-bg-2 transition-colors text-left"
          >
            <span className={`w-7 h-7 rounded-md ${task.bg} flex items-center justify-center text-sm flex-shrink-0`}>
              {task.icon}
            </span>
            <span className={`font-serif text-sm ${task.color} truncate`}>{task.label}</span>
            <span className="ml-auto text-ink-3 text-xs">→</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main dashboard ──
export default function DashboardPage() {
  const { user } = useAuthStore();
  const [specialties, setSpecialties] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      contentApi.getSpecialties().catch(() => ({ data: [] })),
      progressApi.getStats().catch(() => ({ data: null })),
    ]).then(([modRes, statsRes]) => {
      setSpecialties(modRes.data?.slice(0, 3) ?? []);
      setStats(statsRes.data);
      setLoading(false);
    });
  }, []);

  const level = user?.level ?? 1;
  const xp = user?.xp ?? 0;
  const xpInfo = xpToNextLevel(xp, level);
  const role = user?.role ?? "student";

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="font-syne font-black text-2xl text-ink">
          Good day, {user?.first_name} 👋
        </h1>
        <p className="font-serif text-ink-3 text-sm mt-0.5">
          {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
        </p>
      </div>

      {/* XP Progress */}
      <div className="card px-5 py-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <div>
            <span className="font-syne font-bold text-sm text-ink">Level {level}</span>
            <span className="text-ink-3 font-serif text-xs ml-2">
              {xpInfo.current} / {xpInfo.needed} XP to next level
            </span>
          </div>
          <span className="font-syne font-black text-lg text-ink">{xp} XP</span>
        </div>
        <div className="h-2 bg-bg-2 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-red to-amber-2 rounded-full transition-all duration-700"
            style={{ width: `${xpInfo.pct}%` }}
          />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { href: "/ai-tutor", icon: "🤖", label: "AI Tutor", color: "bg-blue-light border-blue/20 text-blue" },
          { href: "/flashcards", icon: "🃏", label: "Flashcards", color: "bg-green-light border-green/20 text-green" },
          { href: "/quiz", icon: "📝", label: "Quiz", color: "bg-amber-light border-amber/20 text-amber" },
          { href: "/modules", icon: "📚", label: "Modules", color: "bg-red-light border-red/20 text-red" },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-col items-center gap-2 p-4 rounded-lg border ${item.color} hover:shadow-sm transition-shadow`}
          >
            <span className="text-2xl">{item.icon}</span>
            <span className="font-syne font-bold text-sm">{item.label}</span>
          </Link>
        ))}
      </div>

      {/* Role-specific panel */}
      {role === "doctor" && <DoctorPanel stats={stats} />}
      {(role === "professor" || role === "teacher" || role === "admin") && <ProfessorPanel stats={stats} />}
      {role === "veterinarian" && <VeterinarianPanel stats={stats} />}

      {/* Default stats for students (or fallback) */}
      {(role === "student" || !["doctor", "professor", "teacher", "admin", "veterinarian"].includes(role)) && (
        <>
          {stats && (
            <div className="grid grid-cols-3 gap-3 mb-4">
              <StatCard value={stats.lessons_completed ?? 0} label="Lessons done" />
              <StatCard value={stats.cards_reviewed ?? 0} label="Cards reviewed" />
              <StatCard value={stats.mcqs_answered ?? 0} label="MCQs answered" />
            </div>
          )}
          <StreakCalendar streakDays={stats?.streak_days ?? 0} />
          <TodaysPlan />
        </>
      )}

      {/* Specialties */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-syne font-bold text-base text-ink">Specialties</h2>
          <Link href="/modules" className="text-ink-3 font-syne text-xs hover:text-ink transition-colors">
            View all →
          </Link>
        </div>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card h-16 animate-pulse bg-bg-2" />
            ))}
          </div>
        ) : specialties.length === 0 ? (
          <div className="card text-center py-8">
            <p className="font-serif text-ink-3 text-sm">No specialties yet — import modules to get started.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {specialties.map((spec: any) => (
              <Link
                key={spec.id}
                href={`/modules?specialty=${spec.id}`}
                className="card flex items-center gap-3 hover:border-ink-3 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-ink/10 flex items-center justify-center text-lg font-bold text-ink-2">
                  {spec.icon ?? spec.name?.[0] ?? "M"}
                </div>
                <div>
                  <div className="font-syne font-bold text-sm text-ink">{spec.name}</div>
                  <div className="font-serif text-ink-3 text-xs">{spec.module_count ?? 0} modules</div>
                </div>
                <div className="ml-auto text-ink-3 text-xs font-syne">→</div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
