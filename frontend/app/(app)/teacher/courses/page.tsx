"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

type Course = {
  id: string;
  title: string;
  description: string | null;
  invite_code: string;
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  module_count: number;
  student_count: number;
};

export default function TeacherCoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    teacherApi.listMyCourses()
      .then(setCourses)
      .catch(() => setError("Failed to load courses"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>;

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">My Courses</h1>
          <p className="font-serif text-ink-3 text-sm">Organize modules into courses for your students</p>
        </div>
        <Link
          href="/teacher/courses/new"
          className="btn-primary text-sm px-4 py-2"
        >
          + New course
        </Link>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">{error}</div>
      )}

      {courses.length === 0 ? (
        <div className="card p-10 text-center">
          <div className="text-4xl mb-3">📚</div>
          <div className="font-syne font-semibold text-ink text-lg">No courses yet</div>
          <div className="font-serif text-ink-3 text-sm mt-1 mb-5">
            Create a course, add your modules to it, and share the invite code with students.
          </div>
          <Link href="/teacher/courses/new" className="btn-primary text-sm px-5 py-2">
            Create first course
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {courses.map((course) => (
            <Link
              key={course.id}
              href={`/teacher/courses/${course.id}`}
              className="card p-4 flex items-center justify-between hover:shadow-md transition-shadow block"
            >
              <div className="flex-1 min-w-0 mr-4">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="font-syne font-bold text-sm text-ink truncate">{course.title}</span>
                  {!course.is_active && (
                    <span className="text-xs font-syne px-1.5 py-0.5 rounded bg-surface text-ink-3 border border-border">
                      archived
                    </span>
                  )}
                </div>
                {course.description && (
                  <p className="font-serif text-xs text-ink-3 line-clamp-1">{course.description}</p>
                )}
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="font-serif text-xs text-ink-3">{course.module_count} modules</span>
                  <span className="font-serif text-xs text-ink-3">{course.student_count} students</span>
                  <span className="font-mono text-xs text-ink-3 bg-surface px-1.5 py-0.5 rounded border border-border">
                    {course.invite_code}
                  </span>
                </div>
              </div>
              <span className="text-ink-3 text-sm">→</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
