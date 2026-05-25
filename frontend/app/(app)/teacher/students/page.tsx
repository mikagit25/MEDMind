"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

type StudentEntry = {
  id: string;
  name: string;
  email: string;
  courses: { id: string; title: string }[];
  xp: number;
  level: number;
  streak_days: number;
  completions: number;
  last_activity: string | null;
  enrolled_at: string | null;
};

function timeAgo(iso: string | null): string {
  if (!iso) return "Never";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function ActivityDot({ lastActivity }: { lastActivity: string | null }) {
  if (!lastActivity) return <span className="w-2 h-2 rounded-full bg-border inline-block" />;
  const days = (Date.now() - new Date(lastActivity).getTime()) / 86_400_000;
  const color = days < 3 ? "bg-green" : days < 14 ? "bg-amber" : "bg-red";
  return <span className={`w-2 h-2 rounded-full ${color} inline-block`} />;
}

export default function TeacherStudentsPage() {
  const [students, setStudents] = useState<StudentEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("enrolled_at");
  const [courseFilter, setCourseFilter] = useState("");
  const [courses, setCourses] = useState<{ id: string; title: string }[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(async (q?: string, s?: string, c?: string) => {
    setLoading(true);
    try {
      const r = await teacherApi.getAllStudents({
        search: q || undefined,
        sort: s || sort,
        course_id: c || undefined,
      });
      setStudents(r.students ?? []);
      setTotal(r.total ?? 0);
      // Collect unique courses
      const all: { id: string; title: string }[] = [];
      const seen = new Set<string>();
      for (const st of r.students ?? []) {
        for (const co of st.courses) {
          if (!seen.has(co.id)) { seen.add(co.id); all.push(co); }
        }
      }
      setCourses(all);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [sort]);

  useEffect(() => { load(); }, [load]);

  const handleSearch = () => load(search, sort, courseFilter);

  // Summary stats
  const activeCount = students.filter(s => s.last_activity && (Date.now() - new Date(s.last_activity).getTime()) < 7 * 86_400_000).length;
  const atRiskCount = students.filter(s => !s.last_activity || (Date.now() - new Date(s.last_activity).getTime()) > 14 * 86_400_000).length;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">All Students</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">
            {total} students across all your courses
          </p>
        </div>
        <Link href="/teacher/dashboard" className="text-xs font-syne text-ink-3 hover:text-ink">
          ← Dashboard
        </Link>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="card p-4 text-center">
          <div className="font-syne font-black text-2xl text-ink">{total}</div>
          <div className="font-serif text-xs text-ink-3 mt-0.5">Total enrolled</div>
        </div>
        <div className="card p-4 text-center border-green/30">
          <div className="font-syne font-black text-2xl text-green">{activeCount}</div>
          <div className="font-serif text-xs text-ink-3 mt-0.5">Active last 7 days</div>
        </div>
        <div className="card p-4 text-center border-amber/30">
          <div className="font-syne font-black text-2xl text-amber">{atRiskCount}</div>
          <div className="font-serif text-xs text-ink-3 mt-0.5">Inactive 14+ days</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-5 flex-wrap items-center">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSearch()}
          placeholder="Search name or email…"
          className="border border-border rounded-lg px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none focus:border-ink w-56"
        />
        <select
          value={courseFilter}
          onChange={e => { setCourseFilter(e.target.value); load(search, sort, e.target.value); }}
          className="border border-border rounded-lg px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none"
        >
          <option value="">All courses</option>
          {courses.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
        <select
          value={sort}
          onChange={e => { setSort(e.target.value); load(search, e.target.value, courseFilter); }}
          className="border border-border rounded-lg px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none"
        >
          <option value="enrolled_at">Sort: Newest enrolled</option>
          <option value="name">Sort: Name A–Z</option>
          <option value="xp">Sort: Top XP</option>
        </select>
        <button onClick={handleSearch} className="btn-primary text-xs px-4 py-1.5">Search</button>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-ink-3 font-serif text-sm">Loading…</div>
        ) : students.length === 0 ? (
          <div className="p-10 text-center">
            <div className="text-3xl mb-2">👥</div>
            <div className="font-syne font-semibold text-ink">No students yet</div>
            <p className="font-serif text-ink-3 text-sm mt-1">
              Share your course invite code to enroll students.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-2">
                  <th className="text-left px-4 py-2.5 font-syne font-semibold text-xs uppercase text-ink-3">Student</th>
                  <th className="text-left px-4 py-2.5 font-syne font-semibold text-xs uppercase text-ink-3">Courses</th>
                  <th className="text-center px-4 py-2.5 font-syne font-semibold text-xs uppercase text-ink-3">XP / Lv</th>
                  <th className="text-center px-4 py-2.5 font-syne font-semibold text-xs uppercase text-ink-3">Lessons done</th>
                  <th className="text-center px-4 py-2.5 font-syne font-semibold text-xs uppercase text-ink-3">Streak</th>
                  <th className="text-left px-4 py-2.5 font-syne font-semibold text-xs uppercase text-ink-3">Last active</th>
                </tr>
              </thead>
              <tbody>
                {students.map(s => (
                  <>
                    <tr
                      key={s.id}
                      className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors cursor-pointer"
                      onClick={() => setExpandedId(expandedId === s.id ? null : s.id)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <ActivityDot lastActivity={s.last_activity} />
                          <div>
                            <div className="font-syne font-semibold text-ink text-sm">{s.name}</div>
                            <div className="text-ink-3 text-xs font-serif">{s.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1 flex-wrap">
                          {s.courses.slice(0, 2).map(c => (
                            <Link
                              key={c.id}
                              href={`/teacher/courses/${c.id}`}
                              onClick={e => e.stopPropagation()}
                              className="text-[10px] font-syne border border-border rounded px-1.5 py-0.5 text-ink-3 hover:text-ink hover:border-ink-3 transition-colors"
                            >
                              {c.title.length > 20 ? c.title.slice(0, 18) + "…" : c.title}
                            </Link>
                          ))}
                          {s.courses.length > 2 && (
                            <span className="text-[10px] font-syne text-ink-3 self-center">+{s.courses.length - 2}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="font-syne font-bold text-ink text-sm">{s.xp.toLocaleString()}</div>
                        <div className="text-xs text-ink-3">Lv {s.level}</div>
                      </td>
                      <td className="px-4 py-3 text-center font-syne font-semibold text-ink">{s.completions}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-syne font-semibold text-sm ${s.streak_days >= 7 ? "text-green" : s.streak_days > 0 ? "text-amber" : "text-ink-3"}`}>
                          {s.streak_days}d
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-serif text-xs text-ink-3">{timeAgo(s.last_activity)}</span>
                      </td>
                    </tr>

                    {/* Expanded row */}
                    {expandedId === s.id && (
                      <tr key={`${s.id}-detail`} className="border-b border-border bg-surface-2">
                        <td colSpan={6} className="px-6 py-4">
                          <div className="flex items-center gap-6 flex-wrap">
                            <div>
                              <div className="text-xs font-syne text-ink-3 uppercase tracking-wider mb-0.5">Enrolled</div>
                              <div className="font-syne font-semibold text-ink text-sm">
                                {s.enrolled_at ? new Date(s.enrolled_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs font-syne text-ink-3 uppercase tracking-wider mb-0.5">Courses</div>
                              <div className="flex gap-1.5 flex-wrap">
                                {s.courses.map(c => (
                                  <Link
                                    key={c.id}
                                    href={`/teacher/courses/${c.id}`}
                                    className="text-xs font-syne border border-border rounded px-2 py-0.5 text-ink hover:border-ink-3 transition-colors"
                                  >
                                    {c.title}
                                  </Link>
                                ))}
                              </div>
                            </div>
                            <div className="ml-auto flex gap-2">
                              {s.courses.map(c => (
                                <Link
                                  key={c.id}
                                  href={`/teacher/courses/${c.id}`}
                                  className="text-xs font-syne font-semibold border border-border text-ink-2 rounded px-3 py-1.5 hover:bg-surface transition-colors"
                                >
                                  Course details →
                                </Link>
                              ))}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 text-xs font-serif text-ink-3">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green inline-block" /> Active last 3 days</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber inline-block" /> Active 4–14 days</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red inline-block" /> Inactive 14+ days</span>
      </div>
    </div>
  );
}
