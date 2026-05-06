"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, teacherApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

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

type Assignment = {
  id: string;
  module_id: string;
  title: string;
  due_date: string | null;
  max_score: number;
  created_at: string;
};

type LeaderEntry = {
  rank: number;
  student_id: string;
  name: string;
  xp: number;
  level: number;
  streak_days: number;
  completion_percent: number;
};

type AtRiskStudent = {
  student_id: string;
  name: string;
  email: string;
  risk_score: number;
  risk_factors: string[];
  last_active: string | null;
  completion_percent: number;
};

type Tab = "modules" | "students" | "assignments" | "leaderboard";

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
      <button onClick={copy} className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded px-2 py-1 transition-colors">
        {copied ? "Copied!" : "Copy"}
      </button>
    </div>
  );
}

export default function CourseDetailPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [course, setCourse] = useState<Course | null>(null);
  const [myModules, setMyModules] = useState<MyModule[]>([]);
  const [students, setStudents] = useState<StudentProgress[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderEntry[]>([]);
  const [atRiskCount, setAtRiskCount] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("modules");
  const [loading, setLoading] = useState(true);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [assignmentsLoading, setAssignmentsLoading] = useState(false);
  const [leaderboardLoading, setLeaderboardLoading] = useState(false);
  const [addingModule, setAddingModule] = useState(false);
  const [selectedModuleId, setSelectedModuleId] = useState("");
  const [reordering, setReordering] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  // Assignment form
  const [assignModuleId, setAssignModuleId] = useState("");
  const [assignTitle, setAssignTitle] = useState("");
  const [assignDueDate, setAssignDueDate] = useState("");
  const [assignMaxScore, setAssignMaxScore] = useState(100);
  const [creatingAssignment, setCreatingAssignment] = useState(false);

  // Grade tracking
  const [gradesMap, setGradesMap] = useState<Record<string, Record<string, { score: number; feedback?: string }>>>({});
  const [gradeInputs, setGradeInputs] = useState<Record<string, string>>({});
  const [savingGrade, setSavingGrade] = useState<string | null>(null);
  const [expandedAssignment, setExpandedAssignment] = useState<string | null>(null);

  const loadCourse = useCallback(async () => {
    try {
      const data = await teacherApi.getCourse(id);
      setCourse(data);
      // Seed assignments from course detail (already eager-loaded)
      if (data.assignments?.length > 0) {
        setAssignments(data.assignments);
      }
    } catch {
      setError("Failed to load course");
    }
  }, [id]);

  useEffect(() => {
    Promise.all([
      loadCourse(),
      teacherApi.listMyModules().then(setMyModules),
      // Load at-risk count in background for badge
      teacherApi.getAtRiskStudents(id)
        .then((data: { at_risk: AtRiskStudent[] }) => setAtRiskCount((data.at_risk ?? []).length))
        .catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [loadCourse, id]);

  useEffect(() => {
    if (tab === "students" && students.length === 0) {
      setStudentsLoading(true);
      teacherApi.getCourseStudents(id)
        .then(setStudents)
        .catch(() => setActionError("Failed to load students"))
        .finally(() => setStudentsLoading(false));
    }
    if (tab === "assignments" && assignments.length === 0) {
      setAssignmentsLoading(true);
      teacherApi.getCourseAssignments(id)
        .then(setAssignments)
        .catch(() => setActionError("Failed to load assignments"))
        .finally(() => setAssignmentsLoading(false));
    }
    if (tab === "leaderboard" && leaderboard.length === 0) {
      setLeaderboardLoading(true);
      teacherApi.getCourseLeaderboard(id)
        .then((data: any) => setLeaderboard(data.leaderboard ?? data ?? []))
        .catch(() => setActionError("Failed to load leaderboard"))
        .finally(() => setLeaderboardLoading(false));
    }
  }, [tab, id, students.length, assignments.length, leaderboard.length]);

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

  async function handleMoveModule(moduleId: string, direction: "up" | "down") {
    if (!course) return;
    const modules = [...course.modules].sort((a, b) => a.module_order - b.module_order);
    const idx = modules.findIndex((m) => m.id === moduleId);
    if (direction === "up" && idx === 0) return;
    if (direction === "down" && idx === modules.length - 1) return;
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    [modules[idx], modules[swapIdx]] = [modules[swapIdx], modules[idx]];
    const newIds = modules.map((m) => m.id);
    setReordering(true);
    try {
      await teacherApi.reorderModules(id, newIds);
      await loadCourse();
    } catch {
      setActionError("Failed to reorder modules");
    } finally {
      setReordering(false);
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
      setActionError("Export failed");
    }
  }

  async function handleCreateAssignment() {
    if (!assignModuleId || !assignTitle.trim()) return;
    setCreatingAssignment(true);
    setActionError("");
    try {
      const created = await teacherApi.createAssignment(id, {
        module_id: assignModuleId,
        title: assignTitle.trim(),
        due_date: assignDueDate || undefined,
        max_score: assignMaxScore,
      });
      setAssignments((prev) => [created, ...prev]);
      setAssignTitle("");
      setAssignDueDate("");
      setAssignMaxScore(100);
      setAssignModuleId("");
    } catch {
      setActionError("Failed to create assignment");
    } finally {
      setCreatingAssignment(false);
    }
  }

  async function handleDeleteAssignment(assignmentId: string) {
    if (!confirm("Delete this assignment?")) return;
    setActionError("");
    try {
      await teacherApi.deleteAssignment(id, assignmentId);
      setAssignments((prev) => prev.filter((a) => a.id !== assignmentId));
    } catch {
      setActionError("Failed to delete assignment");
    }
  }

  async function loadGrades(assignmentId: string) {
    try {
      const data = await teacherApi.getAssignmentGrades(id, assignmentId);
      const gradesByStudent: Record<string, { score: number; feedback?: string }> = {};
      for (const g of (data.grades ?? [])) {
        gradesByStudent[g.student_id] = { score: g.score, feedback: g.feedback };
      }
      setGradesMap((prev) => ({ ...prev, [assignmentId]: gradesByStudent }));
    } catch {
      // ignore
    }
  }

  async function handleSaveGrade(assignmentId: string, studentId: string, maxScore: number) {
    const key = `${assignmentId}:${studentId}`;
    const raw = gradeInputs[key];
    if (raw === undefined || raw === "") return;
    const score = Math.min(maxScore, Math.max(0, parseFloat(raw)));
    if (isNaN(score)) return;
    setSavingGrade(key);
    try {
      await teacherApi.upsertGrade(id, assignmentId, { student_id: studentId, score });
      setGradesMap((prev) => ({
        ...prev,
        [assignmentId]: { ...(prev[assignmentId] ?? {}), [studentId]: { score } },
      }));
    } catch {
      setActionError("Failed to save grade");
    } finally {
      setSavingGrade(null);
    }
  }

  function toggleAssignmentGrades(assignmentId: string) {
    if (expandedAssignment === assignmentId) {
      setExpandedAssignment(null);
    } else {
      setExpandedAssignment(assignmentId);
      if (!gradesMap[assignmentId]) loadGrades(assignmentId);
      // Ensure students are loaded
      if (students.length === 0) {
        setStudentsLoading(true);
        teacherApi.getCourseStudents(id)
          .then(setStudents)
          .catch(() => {})
          .finally(() => setStudentsLoading(false));
      }
    }
  }

  if (loading) return <div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>;
  if (!course) return <div className="p-6 text-red font-serif text-sm">{error || "Course not found"}</div>;

  const courseModuleIds = new Set(course.modules.map((m) => m.id));
  const availableModules = myModules.filter((m) => !courseModuleIds.has(m.id));
  const sortedModules = [...course.modules].sort((a, b) => a.module_order - b.module_order);

  const tabDefs: { key: Tab; label: string }[] = [
    { key: "modules", label: `Modules (${course.module_count})` },
    {
      key: "students",
      label: `Students (${course.student_count})${atRiskCount ? ` ⚠️${atRiskCount}` : ""}`,
    },
    { key: "assignments", label: `Assignments${assignments.length ? ` (${assignments.length})` : ""}` },
    { key: "leaderboard", label: "🏆 Leaderboard" },
  ];

  return (
    <div className="p-4 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-5">
        <Link href="/teacher/courses" className="text-ink-3 text-sm font-syne hover:text-ink">← My Courses</Link>
        <div className="flex items-start justify-between mt-2 gap-4 flex-wrap">
          <div>
            <h1 className="font-syne font-black text-2xl text-ink">{course.title}</h1>
            {course.description && (
              <p className="font-serif text-ink-3 text-sm mt-0.5">{course.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
            <Link href={`/teacher/courses/${id}/at-risk`}
              className="text-xs font-syne text-amber hover:bg-amber-light border border-amber/30 rounded px-2 py-1 transition-colors">
              ⚠️ At-Risk{atRiskCount !== null && atRiskCount > 0 ? ` (${atRiskCount})` : ""}
            </Link>
            <Link href={`/teacher/courses/${id}/insights`}
              className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded px-2 py-1 transition-colors">
              📊 Insights
            </Link>
            <Link href={`/teacher/courses/${id}/analytics`}
              className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded px-2 py-1 transition-colors">
              Analytics
            </Link>
            <button onClick={handleArchiveCourse}
              className="text-xs font-syne text-ink-3 hover:text-red border border-border rounded px-2 py-1 transition-colors">
              Archive
            </button>
          </div>
        </div>
      </div>

      {/* Summary card */}
      <div className="card p-4 mb-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="font-syne font-bold text-xs text-ink-3 mb-1">Student invite code</div>
            <InviteCodeBadge code={course.invite_code} />
          </div>
          <div className="flex gap-5 text-center">
            <div>
              <div className="font-syne font-black text-xl text-ink">{course.module_count}</div>
              <div className="font-serif text-xs text-ink-3">Modules</div>
            </div>
            <div>
              <div className="font-syne font-black text-xl text-ink">{course.student_count}</div>
              <div className="font-serif text-xs text-ink-3">Students</div>
            </div>
            {atRiskCount !== null && atRiskCount > 0 && (
              <div>
                <div className="font-syne font-black text-xl text-red">{atRiskCount}</div>
                <div className="font-serif text-xs text-ink-3">At risk</div>
              </div>
            )}
          </div>
        </div>
        {!course.is_active && (
          <div className="mt-3 p-2 rounded bg-amber-light border border-amber/20 text-amber text-xs font-syne">
            This course is archived — students cannot join.
          </div>
        )}
      </div>

      {actionError && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif flex justify-between">
          {actionError}
          <button onClick={() => setActionError("")} className="text-xs underline ml-2 shrink-0">dismiss</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-0 mb-5 border-b border-border overflow-x-auto">
        {tabDefs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 font-syne text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors ${
              tab === t.key ? "border-ink text-ink" : "border-transparent text-ink-3 hover:text-ink"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Modules tab ─────────────────────────────────────────────── */}
      {tab === "modules" && (
        <div>
          {availableModules.length > 0 && (
            <div className="card p-3 mb-4 flex items-center gap-3">
              <select value={selectedModuleId} onChange={(e) => setSelectedModuleId(e.target.value)}
                className="flex-1 border border-border rounded-lg px-3 py-2 font-syne text-sm text-ink bg-surface focus:outline-none focus:border-ink-3">
                <option value="">Select a module to add...</option>
                {availableModules.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title}{!m.is_published ? " (unpublished)" : ""}
                  </option>
                ))}
              </select>
              <button onClick={handleAddModule} disabled={!selectedModuleId || addingModule}
                className="btn-primary text-sm px-4 py-2 disabled:opacity-50 shrink-0">
                {addingModule ? "Adding..." : "Add"}
              </button>
            </div>
          )}

          {sortedModules.length === 0 ? (
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
                {sortedModules.map((mod, idx) => (
                  <div key={mod.id} className="flex items-center gap-3 px-4 py-3">
                    {/* Reorder buttons */}
                    <div className="flex flex-col gap-0.5 shrink-0">
                      <button onClick={() => handleMoveModule(mod.id, "up")}
                        disabled={idx === 0 || reordering}
                        className="text-ink-3 hover:text-ink disabled:opacity-20 text-xs leading-none px-1">
                        ▲
                      </button>
                      <button onClick={() => handleMoveModule(mod.id, "down")}
                        disabled={idx === sortedModules.length - 1 || reordering}
                        className="text-ink-3 hover:text-ink disabled:opacity-20 text-xs leading-none px-1">
                        ▼
                      </button>
                    </div>
                    <span className="font-syne font-bold text-xs text-ink-3 w-5 text-center">{idx + 1}</span>
                    <div className="flex-1 min-w-0">
                      <Link href={`/teacher/modules/${mod.id}`}
                        className="font-syne text-sm font-semibold text-ink hover:underline line-clamp-1">
                        {mod.title}
                      </Link>
                      {mod.description && (
                        <p className="font-serif text-xs text-ink-3 line-clamp-1">{mod.description}</p>
                      )}
                    </div>
                    <button onClick={() => handleExportModule(mod.id, mod.title)}
                      className="text-ink-3 hover:text-ink text-xs font-syne px-2 py-1 rounded transition-colors shrink-0"
                      title="Export module as JSON">
                      Export
                    </button>
                    <button onClick={() => handleRemoveModule(mod.id)}
                      className="text-ink-3 hover:text-red text-xs font-syne px-2 py-1 rounded transition-colors shrink-0">
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Students tab ────────────────────────────────────────────── */}
      {tab === "students" && (
        <div>
          {atRiskCount !== null && atRiskCount > 0 && (
            <Link href={`/teacher/courses/${id}/at-risk`}
              className="flex items-center gap-3 card p-3 mb-4 border-amber/30 bg-amber-light/30 hover:bg-amber-light/50 transition-colors">
              <span className="text-xl">⚠️</span>
              <div className="flex-1">
                <div className="font-syne font-bold text-sm text-amber">
                  {atRiskCount} student{atRiskCount !== 1 ? "s" : ""} at risk
                </div>
                <div className="font-serif text-xs text-ink-3">Inactive or low completion — click to view details</div>
              </div>
              <span className="text-amber font-syne text-xs">View →</span>
            </Link>
          )}

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
                            <div className={`h-full rounded-full transition-all ${
                              avgProgress >= 80 ? "bg-green" : avgProgress >= 40 ? "bg-amber" : "bg-red"
                            }`} style={{ width: `${Math.round(avgProgress)}%` }} />
                          </div>
                          <span className="font-syne text-xs text-ink-3 shrink-0">{Math.round(avgProgress)}%</span>
                        </div>
                      </div>
                      <div className="col-span-2 text-right">
                        <button onClick={() => handleRemoveStudent(s.student_id, s.email)}
                          className="text-xs font-syne text-ink-3 hover:text-red transition-colors">
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

      {/* ── Assignments tab ──────────────────────────────────────────── */}
      {tab === "assignments" && (
        <div>
          <div className="card p-4 mb-5">
            <h3 className="font-syne font-bold text-sm text-ink mb-3">Create Assignment</h3>
            <div className="space-y-3">
              <div>
                <label className="font-syne text-xs text-ink-3 block mb-1">Module</label>
                <select value={assignModuleId} onChange={(e) => setAssignModuleId(e.target.value)}
                  className="w-full border border-border rounded-lg px-3 py-2 font-syne text-sm text-ink bg-surface focus:outline-none focus:border-ink-3">
                  <option value="">Select module...</option>
                  {course.modules.map((m) => (
                    <option key={m.id} value={m.id}>{m.title}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="font-syne text-xs text-ink-3 block mb-1">Assignment title</label>
                <input type="text" value={assignTitle} onChange={(e) => setAssignTitle(e.target.value)}
                  placeholder="e.g. Complete Cardiology Module by Week 3"
                  className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3" />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="font-syne text-xs text-ink-3 block mb-1">Due date (optional)</label>
                  <input type="datetime-local" value={assignDueDate} onChange={(e) => setAssignDueDate(e.target.value)}
                    className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3" />
                </div>
                <div>
                  <label className="font-syne text-xs text-ink-3 block mb-1">Max score</label>
                  <input type="number" value={assignMaxScore} onChange={(e) => setAssignMaxScore(Number(e.target.value))}
                    min={1} max={1000}
                    className="w-24 border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3" />
                </div>
              </div>
              <button onClick={handleCreateAssignment} disabled={!assignModuleId || !assignTitle.trim() || creatingAssignment}
                className="btn-primary text-sm px-4 py-2 disabled:opacity-50 w-full">
                {creatingAssignment ? "Creating..." : "Create Assignment"}
              </button>
            </div>
          </div>

          {assignmentsLoading ? (
            <div className="text-ink-3 font-serif text-sm p-4">Loading assignments...</div>
          ) : assignments.length === 0 ? (
            <div className="card p-8 text-center">
              <div className="text-3xl mb-2">📋</div>
              <div className="font-syne font-semibold text-ink">No assignments yet</div>
              <div className="font-serif text-ink-3 text-sm mt-1">
                Create an assignment above to give students a module to complete by a deadline.
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {assignments.map((a) => {
                const moduleTitle = course.modules.find((m) => m.id === a.module_id)?.title ?? "Unknown module";
                const isOverdue = a.due_date && new Date(a.due_date) < new Date();
                // Count students who completed this module
                const completedCount = students.filter((s) =>
                  s.modules_progress.some((mp) => mp.module_id === a.module_id && mp.completion_percent >= 100)
                ).length;
                const totalStudents = students.length;
                return (
                  <div key={a.id} className="card p-4">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex-1 min-w-0">
                        <div className="font-syne font-semibold text-sm text-ink">{a.title}</div>
                        <div className="font-serif text-xs text-ink-3 mt-0.5">📚 {moduleTitle}</div>
                        {a.due_date && (
                          <div className={`font-serif text-xs mt-0.5 ${isOverdue ? "text-red font-syne font-semibold" : "text-ink-3"}`}>
                            {isOverdue ? "⚠ Overdue: " : "Due: "}
                            {new Date(a.due_date).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}
                          </div>
                        )}
                      </div>
                      <button onClick={() => handleDeleteAssignment(a.id)}
                        className="text-xs font-syne text-ink-3 hover:text-red transition-colors shrink-0">
                        Delete
                      </button>
                    </div>
                    {totalStudents > 0 && (
                      <div className="mb-2">
                        <div className="flex justify-between font-syne text-xs text-ink-3 mb-1">
                          <span>Module completion</span>
                          <span>{completedCount}/{totalStudents}</span>
                        </div>
                        <div className="h-1.5 bg-bg-2 rounded-full overflow-hidden">
                          <div className="h-full bg-green rounded-full transition-all"
                            style={{ width: totalStudents > 0 ? `${(completedCount / totalStudents) * 100}%` : "0%" }} />
                        </div>
                      </div>
                    )}

                    {/* Grade tracking toggle */}
                    <button
                      onClick={() => toggleAssignmentGrades(a.id)}
                      className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded px-2 py-1 transition-colors"
                    >
                      {expandedAssignment === a.id ? "Hide grades ▲" : "Grade students ▼"}
                    </button>

                    {expandedAssignment === a.id && (
                      <div className="mt-3 border-t border-border pt-3">
                        {students.length === 0 ? (
                          <p className="font-serif text-xs text-ink-3">Load students tab first to grade.</p>
                        ) : (
                          <div className="space-y-2">
                            {students.map((s) => {
                              const name = [s.first_name, s.last_name].filter(Boolean).join(" ") || s.email;
                              const key = `${a.id}:${s.student_id}`;
                              const savedGrade = gradesMap[a.id]?.[s.student_id];
                              const modProg = s.modules_progress.find((mp) => mp.module_id === a.module_id);
                              const pct = modProg ? Math.round(modProg.completion_percent) : 0;
                              return (
                                <div key={s.student_id} className="flex items-center gap-3 py-1">
                                  <div className="flex-1 min-w-0">
                                    <div className="font-syne text-xs font-semibold text-ink truncate">{name}</div>
                                    <div className="flex items-center gap-2 mt-0.5">
                                      <div className="h-1 w-16 bg-bg-2 rounded-full overflow-hidden">
                                        <div className={`h-full rounded-full ${pct >= 100 ? "bg-green" : pct >= 50 ? "bg-amber" : "bg-red"}`}
                                          style={{ width: `${pct}%` }} />
                                      </div>
                                      <span className="font-serif text-xs text-ink-3">{pct}%</span>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-1.5 shrink-0">
                                    {savedGrade && (
                                      <span className="font-syne font-bold text-xs text-green">
                                        {savedGrade.score}/{a.max_score}
                                      </span>
                                    )}
                                    <input
                                      type="number"
                                      min={0}
                                      max={a.max_score}
                                      placeholder={String(a.max_score)}
                                      value={gradeInputs[key] ?? ""}
                                      onChange={(e) => setGradeInputs((prev) => ({ ...prev, [key]: e.target.value }))}
                                      className="w-16 border border-border rounded px-2 py-0.5 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3"
                                    />
                                    <button
                                      onClick={() => handleSaveGrade(a.id, s.student_id, a.max_score)}
                                      disabled={savingGrade === key || !gradeInputs[key]}
                                      className="text-xs font-syne text-green border border-green/40 rounded px-2 py-0.5 hover:bg-green-light transition-colors disabled:opacity-40"
                                    >
                                      {savingGrade === key ? "…" : "Save"}
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Leaderboard tab ──────────────────────────────────────────── */}
      {tab === "leaderboard" && (
        <div>
          {leaderboardLoading ? (
            <div className="text-ink-3 font-serif text-sm p-4">Loading leaderboard...</div>
          ) : leaderboard.length === 0 ? (
            <div className="card p-8 text-center">
              <div className="text-3xl mb-2">🏆</div>
              <div className="font-syne font-semibold text-ink">No leaderboard data yet</div>
              <div className="font-serif text-ink-3 text-sm mt-1">Students need to complete lessons to appear here.</div>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Top 3 highlight */}
              {leaderboard.length >= 3 && (
                <div className="grid grid-cols-3 gap-3 mb-5">
                  {[leaderboard[1], leaderboard[0], leaderboard[2]].map((entry, i) => {
                    if (!entry) return <div key={i} />;
                    const medals = ["🥈", "🥇", "🥉"];
                    const heights = ["h-16", "h-20", "h-14"];
                    const bgs = ["bg-slate-100", "bg-amber-light", "bg-orange-50"];
                    return (
                      <div key={entry.student_id} className="flex flex-col items-center gap-1 text-center">
                        <div className="text-xl">{medals[i]}</div>
                        <div className="font-syne font-bold text-xs text-ink truncate w-full px-1">
                          {entry.name?.split(" ")[0] ?? "Student"}
                        </div>
                        <div className={`w-full ${heights[i]} ${bgs[i]} rounded-t-lg flex items-center justify-center`}>
                          <div>
                            <div className="font-syne font-black text-sm text-ink">
                              {entry.xp >= 1000 ? `${(entry.xp / 1000).toFixed(1)}k` : entry.xp} XP
                            </div>
                            <div className="font-serif text-xs text-ink-3">{Math.round(entry.completion_percent ?? 0)}%</div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {/* Full list */}
              <div className="card overflow-hidden">
                <div className="divide-y divide-border">
                  {leaderboard.map((entry) => (
                    <div key={entry.student_id} className="flex items-center gap-3 px-4 py-3">
                      <div className="w-8 font-syne font-bold text-sm text-ink-3 text-center shrink-0">
                        {entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : `#${entry.rank}`}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-syne font-semibold text-sm text-ink truncate">{entry.name || "Student"}</div>
                        <div className="font-serif text-xs text-ink-3 mt-0.5">
                          Level {entry.level}{entry.streak_days > 0 ? ` · 🔥 ${entry.streak_days}d` : ""}
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <div className="text-right">
                          <div className="font-syne font-bold text-sm text-ink">{entry.xp.toLocaleString()} XP</div>
                          <div className="font-serif text-xs text-ink-3">{Math.round(entry.completion_percent ?? 0)}% done</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
