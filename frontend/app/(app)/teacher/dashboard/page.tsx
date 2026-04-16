"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

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

export default function TeacherDashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    teacherApi.getProfessorDashboard()
      .then(setData)
      .catch(() => setError("Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-ink-3 font-serif text-sm">Loading dashboard…</div>;
  if (error) return <div className="p-8 text-red font-serif text-sm">{error}</div>;
  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">Teaching Dashboard</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">Overview of your courses and students</p>
        </div>
        <div className="flex gap-2">
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

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { icon: "📚", value: data.courses.length, label: "Courses" },
          { icon: "👥", value: data.total_students, label: "Total students" },
          { icon: "🗂️", value: data.total_modules, label: "Modules" },
          { icon: "🔥", value: `${data.streak_days}d`, label: "Streak" },
        ].map(({ icon, value, label }) => (
          <div key={label} className="card text-center py-4 px-3">
            <div className="text-2xl mb-1">{icon}</div>
            <div className="font-syne font-black text-2xl text-ink">{value}</div>
            <div className="font-serif text-ink-3 text-xs mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { href: "/teacher/modules", icon: "✏️", label: "My Lessons" },
          { href: "/teacher/courses", icon: "📚", label: "My Courses" },
          { href: "/teacher/analytics", icon: "📊", label: "Analytics" },
          { href: "/imaging", icon: "🩻", label: "Media Library" },
        ].map(({ href, icon, label }) => (
          <Link key={href} href={href}
            className="card p-3 flex items-center gap-2 hover:border-ink-3 transition-colors">
            <span className="text-lg">{icon}</span>
            <span className="font-syne text-sm font-semibold text-ink">{label}</span>
          </Link>
        ))}
      </div>

      {/* Courses list */}
      <div>
        <h2 className="font-syne font-bold text-base text-ink mb-3">Your Courses</h2>
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
          <div className="space-y-3">
            {data.courses.map((course) => (
              <div key={course.id} className="card p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Link href={`/teacher/courses/${course.id}`}
                        className="font-syne font-bold text-ink hover:underline truncate">
                        {course.title}
                      </Link>
                      {!course.is_active && (
                        <span className="text-xs font-syne text-ink-3 bg-surface border border-border rounded px-1.5 py-0.5 shrink-0">
                          Archived
                        </span>
                      )}
                    </div>
                    <div className="flex gap-4 mt-1">
                      <span className="font-serif text-xs text-ink-3">
                        {course.student_count} student{course.student_count !== 1 ? "s" : ""}
                      </span>
                      <span className="font-serif text-xs text-ink-3">
                        {course.module_count} module{course.module_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Link href={`/teacher/courses/${course.id}/at-risk`}
                      className="text-xs font-syne text-amber border border-amber/30 rounded px-2.5 py-1.5 hover:bg-amber-light transition-colors">
                      ⚠️ At-risk
                    </Link>
                    <Link href={`/teacher/courses/${course.id}/analytics`}
                      className="text-xs font-syne text-ink-3 border border-border rounded px-2.5 py-1.5 hover:border-ink-3 transition-colors">
                      Analytics
                    </Link>
                    <Link href={`/teacher/courses/${course.id}`}
                      className="text-xs font-syne text-ink-3 border border-border rounded px-2.5 py-1.5 hover:border-ink-3 transition-colors">
                      Manage →
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
