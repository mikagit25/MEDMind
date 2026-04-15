"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, teacherApi } from "@/lib/api";

type CourseModule = {
  id: string;
  title: string;
  description: string | null;
  module_order: number;
};

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
  modules: CourseModule[];
};

type MyModule = { id: string; title: string; is_published: boolean };

type StudentProgress = {
  student_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  enrolled_at: string;
  status: string;
  modules_progress: {
    module_id: string;
    title: string;
    completion_percent: number;
    lessons_done: number;
    last_activity: string | null;
  }[];
};

type Tab = "modules" | "students";

function InviteCodeBadge({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-sm font-bold text-ink tracking-widest bg-surface border border-border rounded-lg px-3 py-1.5">
        {code}
      </span>
      <button
        onClick={copy}
        className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded px-2 py-1 transition-colors"
      >
        {copied ? "Copied!" : "Copy"}
      </button>
    </div>
  );
}

export default function CourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [course, setCourse] = useState<Course | null>(null);
  const [myModules, setMyModules] = useState<MyModule[]>([]);
  const [students, setStudents] = useState<StudentProgress[]>([]);
  const [tab, setTab] = useState<Tab>("modules");
  const [loading, setLoading] = useState(true);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [addingModule, setAddingModule] = useState(false);
  const [selectedModuleId, setSelectedModuleId] = useState("");
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  const loadCourse = useCallback(async () => {
    try {
      const data = await teacherApi.getCourse(id);
      setCourse(data);
    } catch {
      setError("Failed to load course");
    }
  }, [id]);

  useEffect(() => {
    Promise.all([
      loadCourse(),
      teacherApi.listMyModules().then(setMyModules),
    ]).finally(() => setLoading(false));
  }, [loadCourse]);

  useEffect(() => {
    if (tab === "students" && students.length === 0) {
      setStudentsLoading(true);
      teacherApi.getCourseStudents(id)
        .then(setStudents)
        .catch(() => setActionError("Failed to load students"))
        .finally(() => setStudentsLoading(false));
    }
  }, [tab, id, students.length]);

  async function handleAddModule() {
    if (!selectedModuleId || !course) return;
    setAddingModule(true);
    setActionError("");
    try {
      await teacherApi.addModuleToCourse(id, selectedModuleId);
      await loadCourse();
      setSelectedModuleId("");
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || "Failed to add module");
    } finally {
      setAddingModule(false);
    }
  }

  async function handleRemoveModule(moduleId: string) {
    if (!confirm("Remove this module from the course?")) return;
    setActionError("");
    try {
      await teacherApi.removeModuleFromCourse(id, moduleId);
      await loadCourse();
    } catch {
      setActionError("Failed to remove module");
    }
  }

  async function handleRemoveStudent(studentId: string, email: string) {
    if (!confirm(`Remove ${email} from the course?`)) return;
    setActionError("");
    try {
      await teacherApi.removeStudentFromCourse(id, studentId);
      setStudents((prev) => prev.filter((s) => s.student_id !== studentId));
    } catch {
      setActionError("Failed to remove student");
    }
  }

  async function handleArchiveCourse() {
    if (!confirm("Archive this course? Students will lose access.")) return;
    try {
      await teacherApi.updateCourse(id, { is_active: false });
      router.push("/teacher/courses");
    } catch {
      setActionError("Failed to archive course");
    }
  }

  async function handleExportModule(moduleId: string, moduleTitle: string) {
    try {
      const response = await api.get(`/lessons/modules/${moduleId}/export`);
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `medmind_${moduleTitle.replace(/\s+/g, "_").toLowerCase()}_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Export failed");
    }
  }

  if (loading) return <div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>;
  if (!course) return <div className="p-6 text-red font-serif text-sm">{error || "Course not found"}</div>;

  const courseModuleIds = new Set(course.modules.map((m) => m.id));
  const availableModules = myModules.filter((m) => !courseModuleIds.has(m.id));

  return (
    <div className="p-4 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-5">
        <Link href="/teacher/courses" className="text-ink-3 text-sm font-syne hover:text-ink">← My Courses</Link>
        <div className="flex items-start justify-between mt-2">
          <div>
            <h1 className="font-syne font-black text-2xl text-ink">{course.title}</h1>
            {course.description && (
              <p className="font-serif text-ink-3 text-sm mt-0.5">{course.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 ml-4 shrink-0">
            <Link
              href={`/teacher/courses/${id}/analytics`}
              className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded px-2 py-1 transition-colors"
            >
              Analytics
            </Link>
            <button
              onClick={handleArchiveCourse}
              className="text-xs font-syne text-ink-3 hover:text-red border border-border rounded px-2 py-1 transition-colors"
            >
              Archive
            </button>
          </div>
        </div>
      </div>

      {/* Invite code card */}
      <div className="card p-4 mb-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="font-syne font-bold text-xs text-ink-3 mb-1">Student invite code</div>
            <InviteCodeBadge code={course.invite_code} />
          </div>
          <div className="flex gap-4 text-center">
            <div>
              <div className="font-syne font-black text-xl text-ink">{course.module_count}</div>
              <div className="font-serif text-xs text-ink-3">Modules</div>
            </div>
            <div>
              <div className="font-syne font-black text-xl text-ink">{course.student_count}</div>
              <div className="font-serif text-xs text-ink-3">Students</div>
            </div>
          </div>
        </div>
        {!course.is_active && (
          <div className="mt-3 p-2 rounded bg-amber-light border border-amber/20 text-amber text-xs font-syne">
            This course is archived — students cannot join.
          </div>
        )}
      </div>

      {actionError && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">{actionError}</div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-border">
        {(["modules", "students"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 font-syne text-sm font-semibold capitalize border-b-2 -mb-px transition-colors ${
              tab === t
                ? "border-ink text-ink"
                : "border-transparent text-ink-3 hover:text-ink"
            }`}
          >
            {t === "modules" ? `Modules (${course.module_count})` : `Students (${course.student_count})`}
          </button>
        ))}
      </div>

      {/* Modules tab */}
      {tab === "modules" && (
        <div>
          {/* Add module */}
          {availableModules.length > 0 && (
            <div className="card p-3 mb-4 flex items-center gap-3">
              <select
                value={selectedModuleId}
                onChange={(e) => setSelectedModuleId(e.target.value)}
                className="flex-1 border border-border rounded-lg px-3 py-2 font-syne text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
              >
                <option value="">Select a module to add...</option>
                {availableModules.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title}{!m.is_published ? " (unpublished)" : ""}
                  </option>
                ))}
              </select>
              <button
                onClick={handleAddModule}
                disabled={!selectedModuleId || addingModule}
                className="btn-primary text-sm px-4 py-2 disabled:opacity-50 shrink-0"
              >
                {addingModule ? "Adding..." : "Add"}
              </button>
            </div>
          )}

          {course.modules.length === 0 ? (
            <div className="card p-8 text-center">
              <div className="text-3xl mb-2">📂</div>
              <div className="font-syne font-semibold text-ink">No modules yet</div>
              <div className="font-serif text-ink-3 text-sm mt-1">
                {availableModules.length > 0
                  ? "Select a module above to add it to this course."
                  : "Create some modules first, then add them here."}
              </div>
              {availableModules.length === 0 && (
                <Link href="/teacher/modules" className="inline-block mt-3 text-sm font-syne text-ink-3 hover:text-ink underline">
                  Go to My Lessons →
                </Link>
              )}
            </div>
          ) : (
            <div className="card overflow-hidden">
              <div className="divide-y divide-border">
                {course.modules.map((mod, idx) => (
                  <div key={mod.id} className="flex items-center gap-3 px-4 py-3">
                    <span className="font-syne font-bold text-xs text-ink-3 w-5 text-center">{idx + 1}</span>
                    <div className="flex-1 min-w-0">
                      <Link
                        href={`/teacher/modules/${mod.id}`}
                        className="font-syne text-sm font-semibold text-ink hover:underline line-clamp-1"
                      >
                        {mod.title}
                      </Link>
                      {mod.description && (
                        <p className="font-serif text-xs text-ink-3 line-clamp-1">{mod.description}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleExportModule(mod.id, mod.title)}
                      className="text-ink-3 hover:text-ink text-xs font-syne px-2 py-1 rounded transition-colors shrink-0"
                      title="Export module as JSON"
                    >
                      Export
                    </button>
                    <button
                      onClick={() => handleRemoveModule(mod.id)}
                      className="text-ink-3 hover:text-red text-xs font-syne px-2 py-1 rounded transition-colors shrink-0"
                      title="Remove from course"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Students tab */}
      {tab === "students" && (
        <div>
          {studentsLoading ? (
            <div className="text-ink-3 font-serif text-sm p-4">Loading students...</div>
          ) : students.length === 0 ? (
            <div className="card p-8 text-center">
              <div className="text-3xl mb-2">👥</div>
              <div className="font-syne font-semibold text-ink">No students yet</div>
              <div className="font-serif text-ink-3 text-sm mt-1">
                Share the invite code <span className="font-mono font-bold">{course.invite_code}</span> so students can join.
              </div>
            </div>
          ) : (
            <div className="card overflow-hidden">
              {/* Header */}
              <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-surface text-xs font-syne text-ink-3 border-b border-border">
                <div className="col-span-4">Student</div>
                <div className="col-span-3">Enrolled</div>
                <div className="col-span-3">Avg progress</div>
                <div className="col-span-2"></div>
              </div>
              <div className="divide-y divide-border">
                {students.map((s) => {
                  const avgProgress = s.modules_progress.length > 0
                    ? s.modules_progress.reduce((sum, m) => sum + m.completion_percent, 0) / s.modules_progress.length
                    : 0;
                  const name = [s.first_name, s.last_name].filter(Boolean).join(" ") || s.email;

                  return (
                    <div key={s.student_id} className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-surface/50 transition-colors">
                      <div className="col-span-4 min-w-0">
                        <div className="font-syne text-sm text-ink truncate">{name}</div>
                        {name !== s.email && (
                          <div className="font-serif text-xs text-ink-3 truncate">{s.email}</div>
                        )}
                      </div>
                      <div className="col-span-3">
                        <span className="font-serif text-xs text-ink-3">
                          {new Date(s.enrolled_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="col-span-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green rounded-full transition-all"
                              style={{ width: `${Math.round(avgProgress)}%` }}
                            />
                          </div>
                          <span className="font-syne text-xs text-ink-3 shrink-0">{Math.round(avgProgress)}%</span>
                        </div>
                      </div>
                      <div className="col-span-2 text-right">
                        <button
                          onClick={() => handleRemoveStudent(s.student_id, s.email)}
                          className="text-xs font-syne text-ink-3 hover:text-red transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
