"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { teacherApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface CourseOverview {
  id: string;
  title: string;
  student_count: number;
  module_count: number;
  is_active: boolean;
}

interface DashboardData {
  courses: CourseOverview[];
  total_students: number;
  total_modules: number;
  xp: number;
  level: number;
  streak_days: number;
  total_achievements: number;
}

interface ArticleStats {
  draft: number;
  pending: number;
  published: number;
  total: number;
}

interface AtRiskEntry {
  student_id: string;
  name: string;
  risk_score: number;
}

interface StudentEntry {
  student_id: string;
  name?: string;
  first_name?: string | null;
  last_name?: string | null;
  email?: string;
  last_activity?: string | null;
  modules_progress?: { last_activity: string | null }[];
  completion_percent?: number;
}

interface CourseAtRisk {
  courseId: string;
  courseTitle: string;
  students: AtRiskEntry[];
}

interface RecentActivity {
  studentName: string;
  courseTitle: string;
  courseId: string;
  lastActivity: Date;
}

export default function TeacherDashboardPage() {
  const t = useT();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [atRiskByCourse, setAtRiskByCourse] = useState<CourseAtRisk[]>([]);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loadingSecondary, setLoadingSecondary] = useState(false);
  const [articleStats, setArticleStats] = useState<ArticleStats>({ draft: 0, pending: 0, published: 0, total: 0 });

  useEffect(() => {
    // Load article stats in parallel with dashboard
    teacherApi.listMyArticles().then((articles: { review_status: string }[]) => {
      const list = Array.isArray(articles) ? articles : [];
      setArticleStats({
        draft:     list.filter(a => a.review_status === "draft").length,
        pending:   list.filter(a => a.review_status === "pending_review").length,
        published: list.filter(a => a.review_status === "published").length,
        total:     list.length,
      });
    }).catch(() => {/* non-critical */});

    teacherApi.getProfessorDashboard()
      .then(async (d: DashboardData) => {
        setData(d);
        if (d.courses.length > 0) {
          setLoadingSecondary(true);
          // Fetch at-risk + students for all courses in parallel
          const results = await Promise.allSettled(
            d.courses.map(async (c) => {
              const [arData, studData] = await Promise.allSettled([
                teacherApi.getAtRiskStudents(c.id),
                teacherApi.getCourseStudents(c.id),
              ]);
              return {
                courseId: c.id,
                courseTitle: c.title,
                atRisk: arData.status === "fulfilled"
                  ? (arData.value?.at_risk ?? arData.value?.data ?? arData.value ?? [])
                  : [],
                students: studData.status === "fulfilled"
                  ? (studData.value?.data ?? studData.value ?? [])
                  : [],
              };
            })
          );

          const arByCourse: CourseAtRisk[] = [];
          const activities: RecentActivity[] = [];

          for (const r of results) {
            if (r.status !== "fulfilled") continue;
            const { courseId, courseTitle, atRisk, students } = r.value;

            if (atRisk.length > 0) {
              arByCourse.push({ courseId, courseTitle, students: atRisk });
            }

            for (const s of students as StudentEntry[]) {
              // Activity comes from most recent module progress entry
              const lastActivity = s.last_activity
                ?? s.modules_progress
                    ?.map((mp) => mp.last_activity)
                    .filter(Boolean)
                    .sort()
                    .pop()
                ?? null;
              if (lastActivity) {
                const name = s.name
                  ?? ([s.first_name, s.last_name].filter(Boolean).join(" ") || s.email)
                  ?? "Student";
                activities.push({
                  studentName: name,
                  courseTitle,
                  courseId,
                  lastActivity: new Date(lastActivity),
                });
              }
            }
          }

          // Sort activities by most recent
          activities.sort((a, b) => b.lastActivity.getTime() - a.lastActivity.getTime());

          setAtRiskByCourse(arByCourse);
          setRecentActivity(activities.slice(0, 6));
          setLoadingSecondary(false);
        }
      })
      .catch(() => setError("Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-ink-3 font-serif text-sm">Loading dashboard…</div>;
  if (error) return <div className="p-8 text-red font-serif text-sm">{error}</div>;
  if (!data) return null;

  const totalAtRisk = atRiskByCourse.reduce((s, c) => s + c.students.length, 0);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("teacher.dashboard.title")}</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">Overview of your courses and students</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Link href="/teacher/modules/new"
            className="btn-primary text-sm px-4 py-2 rounded-lg font-syne font-semibold">
            + New Module
          </Link>
          <Link href="/teacher/courses/new"
            className="border border-border text-ink text-sm px-4 py-2 rounded-lg font-syne font-semibold hover:border-ink-3 transition-colors">
            + New Course
          </Link>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { icon: "📚", value: data.courses.length, label: "Courses", sub: `${data.courses.filter(c => c.is_active).length} active` },
          { icon: "👥", value: data.total_students, label: "Students", sub: "enrolled total" },
          { icon: "🗂️", value: data.total_modules, label: "Modules", sub: "across courses" },
          { icon: "🔥", value: `${data.streak_days}d`, label: "Streak", sub: `Lv ${data.level} · ${data.xp} XP` },
        ].map(({ icon, value, label, sub }) => (
          <div key={label} className="card text-center py-4 px-3">
            <div className="text-2xl mb-1">{icon}</div>
            <div className="font-syne font-black text-2xl text-ink">{value}</div>
            <div className="font-serif text-ink-3 text-xs mt-0.5">{label}</div>
            <div className="font-serif text-ink-3/60 text-xs">{sub}</div>
          </div>
        ))}
      </div>

      {/* At-risk alert banner */}
      {!loadingSecondary && totalAtRisk > 0 && (
        <div className="card border-l-4 border-l-amber p-4 mb-6 flex items-start gap-3">
          <span className="text-xl mt-0.5">⚠️</span>
          <div className="flex-1">
            <div className="font-syne font-bold text-sm text-ink mb-1">
              {totalAtRisk} student{totalAtRisk !== 1 ? "s" : ""} at risk across {atRiskByCourse.length} course{atRiskByCourse.length !== 1 ? "s" : ""}
            </div>
            <div className="flex flex-wrap gap-2">
              {atRiskByCourse.map((c) => (
                <Link
                  key={c.courseId}
                  href={`/teacher/courses/${c.courseId}/at-risk`}
                  className="text-xs font-syne text-amber border border-amber/30 rounded px-2 py-1 hover:bg-amber-light transition-colors"
                >
                  {c.courseTitle} ({c.students.length})
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Two-column section: Quick Actions + Recent Activity */}
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* Quick Actions */}
        <div>
          <h2 className="font-syne font-bold text-sm text-ink mb-3">Quick Actions</h2>
          <div className="grid grid-cols-3 gap-2">
            {[
              { href: "/teacher/modules/new", icon: "✏️", label: "New Lesson", desc: "Create content" },
              { href: "/teacher/courses/new", icon: "📚", label: "New Course", desc: "Set up course" },
              { href: "/teacher/articles/new", icon: "📰", label: "Write Article", desc: "Share expertise" },
              { href: "/teacher/modules", icon: "🗂️", label: "My Modules", desc: "Manage content" },
              { href: "/teacher/analytics", icon: "📊", label: "Analytics", desc: "View insights" },
              { href: "/teacher/articles", icon: "🗒️", label: "My Articles", desc: "Drafts & published" },
            ].map(({ href, icon, label, desc }) => (
              <Link key={href} href={href}
                className="card p-3 hover:border-ink-3 transition-colors">
                <div className="text-xl mb-1">{icon}</div>
                <div className="font-syne text-sm font-bold text-ink">{label}</div>
                <div className="font-serif text-ink-3 text-xs">{desc}</div>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div>
          <h2 className="font-syne font-bold text-sm text-ink mb-3">Recent Student Activity</h2>
          {loadingSecondary ? (
            <div className="card p-4 text-center">
              <p className="font-serif text-ink-3 text-sm">Loading activity…</p>
            </div>
          ) : recentActivity.length === 0 ? (
            <div className="card p-4 text-center">
              <p className="font-serif text-ink-3 text-sm">No recent activity yet</p>
            </div>
          ) : (
            <div className="card divide-y divide-border">
              {recentActivity.map((a, i) => (
                <div key={i} className="px-4 py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-syne font-semibold text-xs text-ink truncate">{a.studentName}</div>
                    <Link href={`/teacher/courses/${a.courseId}`}
                      className="font-serif text-ink-3 text-xs hover:text-ink truncate block">
                      {a.courseTitle}
                    </Link>
                  </div>
                  <div className="font-serif text-ink-3 text-xs shrink-0">
                    {formatTimeAgo(a.lastActivity)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Articles summary widget */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-syne font-bold text-base text-ink">My Articles</h2>
          <Link href="/teacher/articles" className="font-serif text-ink-3 text-xs hover:text-ink">
            View all →
          </Link>
        </div>
        {articleStats.total === 0 ? (
          <div className="card p-6 flex items-center gap-4">
            <div className="text-3xl">📰</div>
            <div className="flex-1">
              <div className="font-syne font-semibold text-sm text-ink">No articles yet</div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">Share your clinical knowledge with medical learners worldwide.</div>
            </div>
            <Link href="/teacher/articles/new"
              className="shrink-0 bg-ink text-white font-syne font-semibold text-xs px-3 py-2 rounded-lg hover:bg-ink-2 transition-colors">
              Write Article
            </Link>
          </div>
        ) : (
          <div className="card p-4 flex items-center gap-6 flex-wrap">
            <div className="flex gap-6 flex-1">
              {[
                { label: "Drafts",    value: articleStats.draft,     color: "text-ink-3" },
                { label: "In Review", value: articleStats.pending,   color: "text-amber" },
                { label: "Published", value: articleStats.published, color: "text-green" },
              ].map(({ label, value, color }) => (
                <div key={label}>
                  <div className={`font-syne font-black text-xl ${color}`}>{value}</div>
                  <div className="font-serif text-ink-3 text-xs">{label}</div>
                </div>
              ))}
            </div>
            <div className="flex gap-2 shrink-0">
              {articleStats.pending > 0 && (
                <span className="text-xs font-syne text-amber bg-amber-light border border-amber/20 rounded-full px-2.5 py-1">
                  {articleStats.pending} awaiting review
                </span>
              )}
              <Link href="/teacher/articles/new"
                className="text-xs font-syne font-semibold border border-ink/30 text-ink rounded px-3 py-1.5 hover:bg-ink hover:text-white transition-colors">
                + New Article
              </Link>
              <Link href="/teacher/articles"
                className="text-xs font-syne text-ink-3 border border-border rounded px-3 py-1.5 hover:border-ink hover:text-ink transition-colors">
                Manage →
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Courses list */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-syne font-bold text-base text-ink">Your Courses</h2>
          <Link href="/teacher/courses" className="font-serif text-ink-3 text-xs hover:text-ink">
            View all →
          </Link>
        </div>

        {data.courses.length === 0 ? (
          <div className="card p-8 text-center">
            <div className="text-3xl mb-2">📚</div>
            <div className="font-syne font-semibold text-ink">No courses yet</div>
            <div className="font-serif text-ink-3 text-sm mt-1">Create your first course to start teaching.</div>
            <Link href="/teacher/courses/new"
              className="inline-block mt-3 btn-primary text-sm px-4 py-2 rounded-lg font-syne font-semibold">
              Create Course
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {data.courses.map((course) => {
              const courseAtRisk = atRiskByCourse.find(c => c.courseId === course.id);
              return (
                <div key={course.id} className="card p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Link href={`/teacher/courses/${course.id}`}
                          className="font-syne font-bold text-sm text-ink hover:underline truncate">
                          {course.title}
                        </Link>
                        {!course.is_active && (
                          <span className="text-xs font-syne text-ink-3 bg-surface border border-border rounded px-1.5 py-0.5 shrink-0">
                            Archived
                          </span>
                        )}
                        {courseAtRisk && (
                          <span className="text-xs font-syne text-amber bg-amber-light rounded px-1.5 py-0.5 shrink-0">
                            ⚠️ {courseAtRisk.students.length} at risk
                          </span>
                        )}
                      </div>
                      <div className="flex gap-4 mt-0.5">
                        <span className="font-serif text-xs text-ink-3">
                          {course.student_count} student{course.student_count !== 1 ? "s" : ""}
                        </span>
                        <span className="font-serif text-xs text-ink-3">
                          {course.module_count} module{course.module_count !== 1 ? "s" : ""}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Link href={`/teacher/courses/${course.id}/insights`}
                        className="text-xs font-syne text-ink-3 border border-border rounded px-2.5 py-1.5 hover:border-ink-3 transition-colors">
                        Insights
                      </Link>
                      <Link href={`/teacher/courses/${course.id}`}
                        className="text-xs font-syne text-ink-3 border border-border rounded px-2.5 py-1.5 hover:border-ink-3 transition-colors">
                        Manage →
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function formatTimeAgo(date: Date): string {
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
