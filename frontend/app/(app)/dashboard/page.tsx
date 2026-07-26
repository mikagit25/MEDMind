"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { contentApi, progressApi, adaptivePlanApi, examApi, authApi, API_URL } from "@/lib/api";

// ── My Assignments ────────────────────────────────────────────
function MyAssignments() {
  const [assignments, setAssignments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    fetch(`${API_URL}/courses/my-assignments-all`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => setAssignments(d?.assignments ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Only show if there are non-completed assignments
  const pending = assignments.filter((a) => a.status !== "completed");
  if (loading || pending.length === 0) return null;

  const statusColor: Record<string, string> = {
    overdue:     "text-red bg-red/10 border-red/20",
    due_soon:    "text-amber bg-amber/10 border-amber/20",
    upcoming:    "text-ink-3 bg-surface-2 border-border",
    no_deadline: "text-ink-3 bg-surface-2 border-border",
  };
  const statusLabel: Record<string, string> = {
    overdue:     "Overdue",
    due_soon:    "Due soon",
    upcoming:    "Upcoming",
    no_deadline: "No deadline",
  };

  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-syne font-bold text-sm text-ink">My Assignments</span>
        <Link href="/teacher/courses" className="text-xs text-ink-3 font-syne hover:text-ink">All courses →</Link>
      </div>
      <div className="space-y-2">
        {pending.slice(0, 4).map((a: any) => (
          <div key={a.id} className="flex items-center gap-3 p-2.5 rounded-lg border border-border hover:bg-surface-2 transition-colors">
            <div className="flex-1 min-w-0">
              <div className="font-syne font-semibold text-xs text-ink truncate">{a.title}</div>
              <div className="font-serif text-[10px] text-ink-3 truncate">{a.course_title}</div>
            </div>
            <div className="flex flex-col items-end gap-1 shrink-0">
              <span className={`text-[10px] font-syne font-semibold px-2 py-0.5 rounded-full border ${statusColor[a.status] ?? statusColor.upcoming}`}>
                {statusLabel[a.status] ?? a.status}
              </span>
              {a.due_date && (
                <span className="font-serif text-[10px] text-ink-3">
                  {new Date(a.due_date).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Mini Leaderboard ──────────────────────────────────────────
function MiniLeaderboard() {
  const t = useT();
  const [board, setBoard] = useState<any[]>([]);
  const [myRank, setMyRank] = useState<number | null>(null);

  useEffect(() => {
    progressApi.getLeaderboard("week", 5).then((data: any) => {
      setBoard(data?.leaderboard ?? []);
      setMyRank(data?.my_rank ?? null);
    }).catch(() => {});
  }, []);

  if (board.length === 0) return null;

  const medalColor = ["text-amber-2", "text-ink-3", "text-amber"];

  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-syne font-bold text-sm text-ink">{t("dashboard.leaderboard_widget_title")}</h3>
        <Link href="/leaderboard" className="text-xs text-ink-3 font-syne hover:text-ink">
          {t("dashboard.leaderboard_full_link")}
        </Link>
      </div>
      <div className="space-y-2">
        {board.slice(0, 3).map((entry: any) => (
          <div
            key={entry.rank}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg ${entry.is_me ? "bg-amber-light border border-amber/20" : "bg-bg-2"}`}
          >
            <span className={`font-syne font-black text-base w-5 text-center ${medalColor[(entry.rank - 1) % 3] ?? "text-ink-3"}`}>
              {entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : "🥉"}
            </span>
            <div className="flex-1 min-w-0">
              <div className="font-syne font-semibold text-xs text-ink truncate">
                {entry.name}{entry.is_me ? ` ${t("dashboard.leaderboard_you")}` : ""}
              </div>
              <div className="font-serif text-[10px] text-ink-3">{t(`dashboard.level_${Math.min(entry.level ?? 1, 6)}` as any) || t("dashboard.level_2")}</div>
            </div>
            <div className="text-right">
              <div className="font-syne font-bold text-xs text-ink">{entry.xp} XP</div>
              <div className="font-serif text-[10px] text-ink-3">{entry.streak_days}🔥</div>
            </div>
          </div>
        ))}
      </div>
      {myRank && myRank > 3 && (
        <div className="mt-2 text-center font-serif text-xs text-ink-3">
          {t("dashboard.leaderboard_my_rank")} <span className="font-syne font-bold text-ink">#{myRank}</span>
        </div>
      )}
    </div>
  );
}

// ── New User Welcome ──────────────────────────────────────────
function NewUserWelcome({ firstName }: { firstName?: string }) {
  const t = useT();
  const steps = [
    { icon: "📚", label: t("dashboard.welcome_step_modules"), href: "/modules", color: "bg-blue-light text-blue border-blue/20" },
    { icon: "🃏", label: t("dashboard.welcome_step_flashcards"), href: "/flashcards", color: "bg-green-light text-green border-green/20" },
    { icon: "🤖", label: t("dashboard.welcome_step_ai"), href: "/ai-tutor", color: "bg-amber-light text-amber border-amber/20" },
    { icon: "📝", label: t("dashboard.welcome_step_quiz"), href: "/quiz", color: "bg-red-light text-red border-red/20" },
  ];
  return (
    <div className="card p-5 mb-4 border-amber/30 bg-amber-light/20">
      <div className="font-syne font-black text-base text-ink mb-1">
        {t("dashboard.welcome_title")}{firstName ? `, ${firstName}` : ""}! 🎉
      </div>
      <p className="font-serif text-ink-3 text-xs mb-4">
        {t("dashboard.welcome_subtitle")}
      </p>
      <div className="grid grid-cols-2 gap-2">
        {steps.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className={`flex items-center gap-2 p-3 rounded-lg border text-xs font-syne font-semibold hover:shadow-sm transition-shadow ${s.color}`}
          >
            <span className="text-base">{s.icon}</span>
            <span className="leading-tight">{s.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
import { useT, useI18n } from "@/lib/i18n";

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
  const t = useT();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleDownload() {
    setLoading(true);
    setError("");
    try {
      const blob = await progressApi.exportPDF();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `medmind_cpd_${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError(t("common.error_retry"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {error && (
        <div className="mt-2 text-xs text-red font-serif">{error}</div>
      )}
      <button
        onClick={handleDownload}
        disabled={loading}
        className="mt-3 w-full py-2 px-3 rounded bg-green text-white font-syne font-semibold text-xs hover:bg-green/90 transition-colors disabled:opacity-60"
      >
        {loading ? t("dashboard.generating") : t("dashboard.download_cme")}
      </button>
    </>
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
  const t = useT();
  const cmeCredits = stats?.cme_credits ?? 0;
  const casesCompleted = stats?.cases_completed ?? 0;
  const mcqAccuracy = stats?.correct_rate ?? stats?.mcq_accuracy ?? 0;
  return (
    <div className="mb-6">
      <h2 className="font-syne font-bold text-base text-ink mb-3">{t("dashboard.clinical_dashboard")}</h2>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatCard value={`${cmeCredits}`} label={t("dashboard.stat_cme")} />
        <StatCard value={casesCompleted} label={t("dashboard.stat_cases")} />
        <StatCard value={`${Math.round(typeof mcqAccuracy === "number" && mcqAccuracy <= 1 ? mcqAccuracy * 100 : mcqAccuracy)}%`} label={t("dashboard.stat_accuracy")} />
      </div>
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-syne font-semibold text-sm text-ink">{t("dashboard.continue_practice")}</h3>
          <Link href="/cases" className="text-xs text-ink-3 hover:text-ink font-syne">{t("common.view_all")} →</Link>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Link href="/cases" className="flex items-center gap-2 p-3 rounded bg-amber-light border border-amber/20 hover:border-amber/40 transition-colors">
            <span className="text-xl">🩺</span>
            <div>
              <div className="font-syne font-semibold text-xs text-amber">{t("dashboard.clinical_cases")}</div>
              <div className="font-serif text-xs text-ink-3">{t("dashboard.evidence_based")}</div>
            </div>
          </Link>
          <Link href="/drugs" className="flex items-center gap-2 p-3 rounded bg-blue-light border border-blue/20 hover:border-blue/40 transition-colors">
            <span className="text-xl">💊</span>
            <div>
              <div className="font-syne font-semibold text-xs text-blue">{t("nav.items.drugs")}</div>
              <div className="font-serif text-xs text-ink-3">{t("dashboard.interactions_dosing")}</div>
            </div>
          </Link>
        </div>
        {cmeCredits >= 0 && (
          <div className="mt-3 p-3 rounded bg-green-light border border-green/20">
            <div className="flex items-center justify-between">
              <span className="font-syne font-semibold text-xs text-green">{t("dashboard.cme_this_year")}</span>
              <span className="font-syne font-bold text-xs text-green">{stats?.cme_credits_this_year ?? cmeCredits} {t("dashboard.cme_credits_year")}</span>
            </div>
            <div className="mt-1.5 h-1.5 bg-green/20 rounded-full">
              <div className="h-full bg-green rounded-full" style={{ width: `${Math.min(((stats?.cme_credits_this_year ?? cmeCredits) / 50) * 100, 100)}%` }} />
            </div>
            <p className="font-serif text-xs text-ink-3 mt-1.5">
              {cmeCredits} {t("dashboard.cme_total_hint")}
            </p>
            <DownloadPDFButton />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Role-specific panel: Professor ──
function ProfessorPanel({ stats }: { stats: any }) {
  const t = useT();
  const modulesCompleted = stats?.modules_completed ?? 0;
  const lessonsCompleted = stats?.lessons_completed ?? 0;
  return (
    <div className="mb-6">
      <h2 className="font-syne font-bold text-base text-ink mb-3">{t("dashboard.teaching_dashboard")}</h2>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatCard value={modulesCompleted} label={t("dashboard.stat_modules_done")} />
        <StatCard value={lessonsCompleted} label={t("dashboard.stat_lessons_taught")} />
        <StatCard value={stats?.streak_days ?? 0} label={t("dashboard.stat_day_streak")} />
      </div>
      {/* Teacher authoring shortcut */}
      <Link href="/teacher/modules" className="flex items-center justify-between p-4 rounded-xl bg-ink text-white mb-3 hover:bg-ink/90 transition-colors">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✏️</span>
          <div>
            <div className="font-syne font-bold text-sm">{t("dashboard.teaching_my_lessons")}</div>
            <div className="font-serif text-xs text-white/70">{t("dashboard.teaching_my_lessons_hint")}</div>
          </div>
        </div>
        <span className="text-white/60 text-lg">→</span>
      </Link>
      <div className="card p-4 mb-3">
        <h3 className="font-syne font-semibold text-sm text-ink mb-3">{t("dashboard.teaching_curriculum_tools")}</h3>
        <div className="grid grid-cols-2 gap-2">
          <Link href="/modules" className="flex items-center gap-2 p-3 rounded bg-red-light border border-red/20 hover:border-red/40 transition-colors">
            <span className="text-xl">📚</span>
            <div>
              <div className="font-syne font-semibold text-xs text-red">{t("dashboard.teaching_all_modules")}</div>
              <div className="font-serif text-xs text-ink-3">{t("dashboard.teaching_browse_curriculum")}</div>
            </div>
          </Link>
          <Link href="/quiz" className="flex items-center gap-2 p-3 rounded bg-blue-light border border-blue/20 hover:border-blue/40 transition-colors">
            <span className="text-xl">📝</span>
            <div>
              <div className="font-syne font-semibold text-xs text-blue">{t("dashboard.teaching_quiz_bank")}</div>
              <div className="font-serif text-xs text-ink-3">{t("dashboard.teaching_mcq_practice")}</div>
            </div>
          </Link>
          <Link href="/ai-tutor" className="flex items-center gap-2 p-3 rounded bg-green-light border border-green/20 hover:border-green/40 transition-colors">
            <span className="text-xl">🤖</span>
            <div>
              <div className="font-syne font-semibold text-xs text-green">{t("dashboard.teaching_ai_assistant")}</div>
              <div className="font-serif text-xs text-ink-3">{t("dashboard.teaching_research")}</div>
            </div>
          </Link>
          <Link href="/search" className="flex items-center gap-2 p-3 rounded border border-border bg-surface hover:border-ink-3 transition-colors">
            <span className="text-xl">🔍</span>
            <div>
              <div className="font-syne font-semibold text-xs text-ink">{t("dashboard.teaching_search")}</div>
              <div className="font-serif text-xs text-ink-3">{t("dashboard.teaching_find_content")}</div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ── Role-specific panel: Veterinarian ──
function VeterinarianPanel({ stats }: { stats: any }) {
  const t = useT();
  return (
    <div className="mb-6">
      <h2 className="font-syne font-bold text-base text-ink mb-3">{t("dashboard.vet_dashboard")}</h2>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <StatCard value={stats?.lessons_completed ?? 0} label={t("dashboard.stat_lessons_done")} />
        <StatCard value={stats?.cards_reviewed ?? 0} label={t("dashboard.stat_cards_reviewed")} />
        <StatCard value={`${stats?.streak_days ?? 0}🔥`} label={t("dashboard.stat_day_streak")} />
      </div>
      <div className="card p-4 mb-3">
        <h3 className="font-syne font-semibold text-sm text-ink mb-3">{t("dashboard.vet_tools")}</h3>
        <div className="grid grid-cols-2 gap-2">
          <Link href="/drugs?vet=true" className="flex items-center gap-2 p-3 rounded bg-amber-light border border-amber/20 hover:border-amber/40 transition-colors">
            <span className="text-xl">🐾</span>
            <div>
              <div className="font-syne font-semibold text-xs text-amber">{t("dashboard.vet_drug_ref")}</div>
              <div className="font-serif text-xs text-ink-3">{t("dashboard.vet_drug_hint")}</div>
            </div>
          </Link>
          <Link href="/cases?vet=true" className="flex items-center gap-2 p-3 rounded bg-green-light border border-green/20 hover:border-green/40 transition-colors">
            <span className="text-xl">🩺</span>
            <div>
              <div className="font-syne font-semibold text-xs text-green">{t("dashboard.vet_cases")}</div>
              <div className="font-serif text-xs text-ink-3">{t("dashboard.vet_cases_hint")}</div>
            </div>
          </Link>
        </div>
      </div>
      <div className="card p-3 bg-amber-light/40 border-amber/20">
        <p className="font-syne font-semibold text-xs text-amber-dark mb-1">{t("dashboard.vet_toxicity_title")}</p>
        <p className="font-serif text-xs text-ink-2">
          Common dangers: paracetamol (cats), xylitol (dogs), permethrin (cats).{" "}
          <Link href="/drugs" className="text-amber underline">{t("dashboard.vet_check_drug_safety")}</Link>
        </p>
      </div>
    </div>
  );
}

// ── Streak Calendar (last 7 days) ──────────────────────────────────────────
function StreakCalendar({
  streakDays,
  longestStreak,
  studiedToday,
}: {
  streakDays: number;
  longestStreak?: number;
  studiedToday?: boolean;
}) {
  const t = useT();
  const { locale } = useI18n();

  // Browser locale tag for day names (e.g. "ru-RU" for Russian)
  const localeTag = locale === "ru" ? "ru-RU" : locale === "ar" ? "ar-SA" : locale === "tr" ? "tr-TR" : locale === "de" ? "de-DE" : locale === "fr" ? "fr-FR" : locale === "es" ? "es-ES" : "en-US";

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return {
      label: d.toLocaleDateString(localeTag, { weekday: "narrow" }),
      active: i >= 7 - Math.min(streakDays, 7),
      isToday: i === 6,
    };
  });

  const atRisk = streakDays > 0 && !studiedToday;
  const neverStarted = streakDays === 0 && !studiedToday;

  return (
    <div className={`card p-4 mb-4 ${atRisk ? "border-amber/40 bg-amber-light/20" : ""}`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="font-syne font-bold text-sm text-ink">{t("dashboard.streak_title")}</span>
          {longestStreak && longestStreak > streakDays && (
            <span className="font-serif text-[10px] text-ink-3 ml-2">
              {t("dashboard.streak_best")} {longestStreak} {t("dashboard.streak_days_label")}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`font-syne font-black text-xl ${atRisk ? "text-amber animate-pulse" : streakDays > 0 ? "text-amber" : "text-ink-3"}`}>
            {streakDays > 0 ? `${streakDays} 🔥` : "0"}
          </span>
        </div>
      </div>

      <div className="flex gap-1.5 mb-3">
        {days.map((d, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={`w-full aspect-square rounded-md transition-all ${
                d.active
                  ? d.isToday && studiedToday
                    ? "bg-green shadow-sm shadow-green/30"
                    : d.isToday
                    ? "bg-amber shadow-sm shadow-amber/30"
                    : "bg-amber/40"
                  : d.isToday
                  ? "bg-bg-2 border-2 border-dashed border-amber/40"
                  : "bg-bg-2"
              }`}
            />
            <span className={`font-syne text-[10px] ${d.isToday ? "font-bold text-ink" : "text-ink-3"}`}>
              {d.label}
            </span>
          </div>
        ))}
      </div>

      {studiedToday ? (
        <div className="text-xs font-serif text-green">{t("dashboard.streak_today_done")}</div>
      ) : atRisk ? (
        <div className="text-xs font-serif text-amber">{t("dashboard.streak_at_risk")}</div>
      ) : neverStarted ? (
        <div className="text-xs font-serif text-ink-3">{t("dashboard.streak_start")}</div>
      ) : null}
    </div>
  );
}

// ── Today's Plan ────────────────────────────────────────────────────────────
function TodaysPlan() {
  const router = useRouter();
  const t = useT();
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
    ...upNext.map((item: any) => ({
      label: item.title ?? item.topic ?? t("dashboard.plan_continue_studying"),
      icon: "📚",
      href: item.lesson_id ? `/modules/${item.module_id}` : "/modules",
      color: "text-blue",
      bg: "bg-blue-light",
    })),
    ...dueReviews.map((item: any) => ({
      label: `${t("dashboard.plan_review_prefix")} ${item.topic ?? item.title ?? t("dashboard.plan_flashcards")}`,
      icon: "🃏",
      href: "/flashcards",
      color: "text-green",
      bg: "bg-green-light",
    })),
    ...weakAreas.map((item: any) => ({
      label: `${t("dashboard.plan_strengthen_prefix")} ${item.topic ?? item.title ?? t("dashboard.plan_weak_area")}`,
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
          <div className="font-syne font-bold text-sm text-ink">{t("dashboard.plan_caught_up")}</div>
          <div className="font-serif text-xs text-ink-3">{t("dashboard.plan_caught_up_hint")}</div>
        </div>
        <button
          onClick={() => router.push("/recommendations")}
          className="ml-auto font-syne font-semibold text-xs text-ink border border-border rounded px-2 py-1 hover:border-ink transition-colors"
        >
          {t("dashboard.plan_get_plan")}
        </button>
      </div>
    );
  }

  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-syne font-bold text-sm text-ink">{t("dashboard.plan_title")}</span>
        <button
          onClick={() => router.push("/recommendations")}
          className="font-syne text-xs text-ink-3 hover:text-ink"
        >
          {t("dashboard.plan_see_all")}
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

// ── Continue Learning ─────────────────────────────────────────
function ContinueLearning({ modules }: { modules: any[] }) {
  const t = useT();
  const { locale } = useI18n();
  if (!modules || modules.length === 0) return null;
  const inProgress = modules.filter((m: any) => (m.completion_percent ?? 0) < 100).slice(0, 3);
  if (inProgress.length === 0) return null;
  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-syne font-bold text-sm text-ink">{t("dashboard.continue_learning")}</span>
        <Link href="/progress" className="text-xs text-ink-3 font-syne hover:text-ink">{t("dashboard.all_modules")}</Link>
      </div>
      <div className="space-y-2">
        {inProgress.map((m: any) => {
          const pct = Math.round(m.completion_percent ?? 0);
          return (
            <Link
              key={m.id}
              href={`/modules/${m.id}`}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-bg-2 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="font-syne font-semibold text-xs text-ink truncate">{(locale === "en" ? m.title_en : undefined) || m.title}</div>
                <div className="flex items-center gap-2 mt-1">
                  <div className="h-1 flex-1 bg-bg-2 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-red to-amber-2 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="font-syne text-[10px] text-ink-3 shrink-0">{pct}%</span>
                </div>
              </div>
              <span className="text-ink-3 text-xs shrink-0">→</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

// ── Daily Goal ────────────────────────────────────────────────
function DailyGoalWidget({ flashcardsDue, srsDue, dailyGoalMinutes }: { flashcardsDue: number; srsDue: number; dailyGoalMinutes: number }) {
  const t = useT();
  const totalDue = flashcardsDue + srsDue;
  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <span className="font-syne font-bold text-sm text-ink">{t("dashboard.adaptive_plan")}</span>
        <Link href="/settings" className="text-xs text-ink-3 font-syne hover:text-ink">{t("common.edit")} →</Link>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Link href="/flashcards" className={`p-3 rounded-lg border text-center transition-colors hover:border-ink-3 ${flashcardsDue > 0 ? "bg-amber-light border-amber/30" : "bg-green-light border-green/30"}`}>
          <div className={`font-syne font-black text-xl ${flashcardsDue > 0 ? "text-amber" : "text-green"}`}>
            {flashcardsDue > 0 ? flashcardsDue : "✓"}
          </div>
          <div className="font-serif text-[10px] text-ink-3 mt-0.5">
            {flashcardsDue > 0 ? t("dashboard.cards_due") : t("dashboard.cards_done")}
          </div>
        </Link>
        <Link href="/srs-review" className={`p-3 rounded-lg border text-center transition-colors hover:border-ink-3 ${srsDue > 0 ? "bg-blue/10 border-blue/30" : "bg-green-light border-green/30"}`}>
          <div className={`font-syne font-black text-xl ${srsDue > 0 ? "text-blue" : "text-green"}`}>
            {srsDue > 0 ? srsDue : "✓"}
          </div>
          <div className="font-serif text-[10px] text-ink-3 mt-0.5">
            {srsDue > 0 ? "lessons due" : "reviews done"}
          </div>
        </Link>
        <div className="p-3 rounded-lg border border-border text-center">
          <div className="font-syne font-black text-xl text-ink">{dailyGoalMinutes}</div>
          <div className="font-serif text-[10px] text-ink-3 mt-0.5">{t("settings.daily_goal_value", { goal: "" }).replace(" /", "").trim()} / {t("common.minutes")}</div>
        </div>
      </div>
    </div>
  );
}

// ── Main dashboard ──
export default function DashboardPage() {
  const t = useT();
  const { locale } = useI18n();
  const { user, updateUser } = useAuthStore();
  const role = user?.role ?? "student";
  const [specialties, setSpecialties] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [studentDashboard, setStudentDashboard] = useState<any>(null);
  const [recentModules, setRecentModules] = useState<any[]>([]);
  const [nclexReadiness, setNclexReadiness] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Always refresh XP/level — Zustand store persists stale cached values across sessions
    authApi.me().then((me: any) => updateUser(me)).catch(() => {});

    const roleSpecific = role === "doctor"
      ? contentApi.getDoctorDashboard().catch(() => null)
      : role === "student" || !["doctor", "professor", "teacher", "admin", "veterinarian"].includes(role)
      ? contentApi.getStudentDashboard().catch(() => null)
      : Promise.resolve(null);

    Promise.all([
      contentApi.getSpecialties().catch(() => []),
      progressApi.getStats().catch(() => null),
      contentApi.getDashboard().catch(() => null),
      roleSpecific,
      examApi.getReadiness().catch(() => null),
    ]).then(([modRes, statsRes, overviewRes, roleRes, readiness]) => {
      setSpecialties(modRes?.slice(0, 3) ?? []);
      setStats(statsRes);
      setRecentModules(overviewRes?.recent_modules ?? []);
      if (role === "student" || !["doctor", "professor", "teacher", "admin", "veterinarian"].includes(role)) {
        setStudentDashboard(roleRes);
      } else if (role === "doctor" && roleRes) {
        // Merge CME data into stats for DoctorPanel
        setStats((prev: any) => ({
          ...prev,
          cme_credits: roleRes?.cme?.total_credits ?? 0,
          cme_credits_this_year: roleRes?.cme?.credits_this_year ?? 0,
        }));
      }
      if (readiness?.score !== undefined || readiness?.questions_to_threshold !== undefined) {
        setNclexReadiness(readiness);
      }
      setLoading(false);
    });
  }, [role]);

  const level = user?.level ?? 1;
  const xp = user?.xp ?? 0;
  const xpInfo = xpToNextLevel(xp, level);

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6">
      {/* Header */}
      <div className="mb-4 sm:mb-6">
        <h1 className="font-syne font-black text-xl sm:text-2xl text-ink">
          {new Date().getHours() < 12
            ? t("dashboard.greeting_morning")
            : new Date().getHours() < 18
            ? t("dashboard.greeting_afternoon")
            : t("dashboard.greeting_evening")}, {user?.first_name} 👋
        </h1>
        <p className="font-serif text-ink-3 text-sm mt-0.5">
          {t("dashboard.subtitle")}
        </p>
      </div>

      {/* Teacher / Admin banner */}
      {(user?.role === 'teacher' || user?.role === 'admin') && (
        <div className="card p-4 mb-4 bg-purple-light border border-purple/20">
          <div className="flex items-center gap-3">
            <span className="text-2xl">👨‍🏫</span>
            <div>
              <div className="font-syne font-bold text-base text-ink">{t("dashboard.teacher_title")}</div>
              <div className="font-serif text-sm text-ink-3">{t("dashboard.teacher_manage")}</div>
            </div>
            <div className="ml-auto flex gap-2">
              <Link href="/teacher/dashboard" className="btn-secondary text-sm px-3 py-1.5">{t("dashboard.teacher_cabinet")}</Link>
              {user?.role === 'admin' && <Link href="/admin" className="btn-secondary text-sm px-3 py-1.5">{t("dashboard.admin_panel_link")}</Link>}
            </div>
          </div>
        </div>
      )}

      {/* XP Progress */}
      <div className="card px-5 py-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <div>
            <span className="font-syne font-bold text-sm text-ink">{t("common.level")} {level}</span>
            <span className="text-ink-3 font-serif text-xs ml-2">
              {xpInfo.current} / {xpInfo.needed} {t("dashboard.to_next_level")} {level + 1}
            </span>
          </div>
          <span className="font-syne font-black text-lg text-ink">{xp} {t("common.xp")}</span>
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
          { href: "/ai-tutor", icon: "🤖", labelKey: "nav.items.ai_tutor", color: "bg-blue-light border-blue/20 text-blue" },
          { href: "/flashcards", icon: "🃏", labelKey: "nav.items.flashcards", color: "bg-green-light border-green/20 text-green" },
          { href: "/quiz", icon: "📝", labelKey: "nav.items.quiz", color: "bg-amber-light border-amber/20 text-amber" },
          { href: "/modules", icon: "📚", labelKey: "nav.items.modules", color: "bg-red-light border-red/20 text-red" },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-col items-center gap-2 p-4 rounded-lg border ${item.color} hover:shadow-sm transition-shadow`}
          >
            <span className="text-2xl">{item.icon}</span>
            <span className="font-syne font-bold text-sm">{t(item.labelKey as Parameters<typeof t>[0])}</span>
          </Link>
        ))}
      </div>

      {/* Role-specific panel */}
      {role === "doctor" && (
        <>
          <StreakCalendar streakDays={stats?.streak_days ?? 0} longestStreak={stats?.longest_streak ?? user?.longest_streak} studiedToday={stats?.studied_today} />
          <TodaysPlan />
          <DoctorPanel stats={stats} />
        </>
      )}
      {(role === "professor" || role === "teacher" || role === "admin") && (
        <>
          <StreakCalendar streakDays={stats?.streak_days ?? 0} longestStreak={stats?.longest_streak ?? user?.longest_streak} studiedToday={stats?.studied_today} />
          <ProfessorPanel stats={stats} />
        </>
      )}
      {role === "veterinarian" && (
        <>
          <StreakCalendar streakDays={stats?.streak_days ?? 0} longestStreak={stats?.longest_streak ?? user?.longest_streak} studiedToday={stats?.studied_today} />
          <TodaysPlan />
          <VeterinarianPanel stats={stats} />
        </>
      )}

      {/* Default stats for students (or fallback) */}
      {(role === "student" || !["doctor", "professor", "teacher", "admin", "veterinarian"].includes(role)) && (
        <>
          {stats && (stats.lessons_completed ?? 0) === 0 ? (
            <NewUserWelcome firstName={user?.first_name} />
          ) : (
            <>
              {stats && (
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <StatCard value={stats.lessons_completed ?? 0} label={t("progress.lessons_completed")} />
                  <StatCard value={stats.cards_reviewed ?? 0} label={t("flashcards.my_cards")} />
                  <StatCard value={stats.mcqs_answered ?? 0} label={t("quiz.title")} />
                </div>
              )}
              {/* NCLEX Readiness mini-card */}
              {nclexReadiness && nclexReadiness.score !== undefined ? (
                <Link href="/nurses/nclex" className="block mb-4">
                  <div className="card p-4 border border-border hover:border-ink-3 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center font-syne font-black text-lg
                          ${nclexReadiness.score >= 75 ? "bg-green-light text-green" : nclexReadiness.score >= 62 ? "bg-amber-light text-amber" : "bg-red-light text-red"}`}>
                          {Math.round(nclexReadiness.score)}
                        </div>
                        <div>
                          <div className="font-syne font-bold text-sm text-ink">NCLEX Readiness</div>
                          <div className="font-serif text-xs text-ink-3">{nclexReadiness.level ?? "Borderline"}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        {user?.preferences?.exam_date
                          ? (() => {
                              const days = Math.ceil((new Date(user.preferences.exam_date as string).getTime() - Date.now()) / 86400000);
                              return days > 0 ? (
                                <div>
                                  <div className="font-syne font-black text-base text-ink">{days}</div>
                                  <div className="font-serif text-[10px] text-ink-3">days left</div>
                                </div>
                              ) : null;
                            })()
                          : <span className="font-syne text-xs text-ink-3">Practice →</span>
                        }
                      </div>
                    </div>
                  </div>
                </Link>
              ) : nclexReadiness && nclexReadiness.questions_to_threshold > 0 && (
                <Link href="/nurses/nclex" className="block mb-4">
                  <div className="card p-4 border border-dashed border-border hover:border-ink-3 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-surface-2 flex items-center justify-center flex-shrink-0">
                        <span className="font-syne font-black text-sm text-ink-3">
                          {nclexReadiness.questions_to_threshold}
                        </span>
                      </div>
                      <div>
                        <div className="font-syne font-bold text-sm text-ink">Unlock Readiness Score</div>
                        <div className="font-serif text-xs text-ink-3">
                          {nclexReadiness.questions_to_threshold} more practice questions to go
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              )}
              <ContinueLearning modules={recentModules} />
              <MyAssignments />
              <DailyGoalWidget
                flashcardsDue={studentDashboard?.today_plan?.flashcards_due ?? stats?.flashcards_due ?? 0}
                srsDue={studentDashboard?.today_plan?.srs_due ?? stats?.srs_due ?? 0}
                dailyGoalMinutes={studentDashboard?.today_plan?.daily_goal_minutes ?? 20}
              />
              <StreakCalendar streakDays={stats?.streak_days ?? 0} longestStreak={stats?.longest_streak ?? user?.longest_streak} studiedToday={stats?.studied_today} />
              <TodaysPlan />
              <MiniLeaderboard />
            </>
          )}
        </>
      )}

      {/* Specialties */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-syne font-bold text-base text-ink">{t("modules.filter_specialty")}</h2>
          <Link href="/modules" className="text-ink-3 font-syne text-xs hover:text-ink transition-colors">
            {t("common.view_all")} →
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
            <p className="font-serif text-ink-3 text-sm">{t("modules.no_modules")}</p>
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
                  <div className="font-serif text-ink-3 text-xs">{(() => {
                    const n = spec.module_count ?? 0;
                    if (locale === "ru") {
                      const r = new Intl.PluralRules("ru").select(n);
                      return `${n} ${({ one: "модуль", few: "модуля", many: "модулей", other: "модулей" } as Record<string,string>)[r]}`;
                    }
                    return `${n} ${n === 1 ? "module" : "modules"}`;
                  })()}</div>
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
