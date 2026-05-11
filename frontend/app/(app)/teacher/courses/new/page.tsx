"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { teacherApi, contentApi } from "@/lib/api";

type Specialty = { id: string; code: string; name: string };

type LessonDraft = {
  title: string;
  key_concepts: string[];
  estimated_minutes: number;
  include_quiz: boolean;
  include_clinical_case: boolean;
  // after generation:
  lessonId?: string;
  status: "pending" | "generating" | "done" | "skipped" | "error";
};

type ModuleDraft = {
  title: string;
  description: string;
  estimated_hours: number;
  lessons: LessonDraft[];
  // after creation:
  moduleId?: string;
};

type Outline = {
  course_title: string;
  course_description: string;
  total_hours: number;
  modules: ModuleDraft[];
};

type Step = "basics" | "outline" | "generating" | "done";

// ── helpers ────────────────────────────────────────────────────────────────────
function Badge({ children, color = "default" }: { children: React.ReactNode; color?: "default" | "green" | "blue" | "amber" | "red" }) {
  const cls = {
    default: "bg-surface-2 text-ink-3",
    green:   "bg-green-light text-green",
    blue:    "bg-blue-light text-blue",
    amber:   "bg-amber-light text-amber",
    red:     "bg-red-light text-red",
  }[color];
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-syne text-[10px] font-semibold ${cls}`}>{children}</span>;
}

function ProgressBar({ value, total }: { value: number; total: number }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="w-full h-2 bg-border-2 rounded-full overflow-hidden">
      <div className="h-full bg-ink rounded-full transition-all duration-300" style={{ width: `${pct}%` }} />
    </div>
  );
}

// ── Step 1: Course basics ──────────────────────────────────────────────────────
function StepBasics({
  specialties,
  onManual,
  onAI,
}: {
  specialties: Specialty[];
  onManual: (data: { title: string; description: string }) => void;
  onAI: (data: { title: string; description: string; specialty: string; level: string; numModules: number; lessonsPerModule: number; includeQuiz: boolean; includeCase: boolean }) => void;
}) {
  const [title, setTitle]       = useState("");
  const [description, setDesc]  = useState("");
  const [specialty, setSpec]    = useState("");
  const [level, setLevel]       = useState("intermediate");
  const [numModules, setNM]     = useState(3);
  const [lpModule, setLPM]      = useState(3);
  const [includeQuiz, setIQ]    = useState(true);
  const [includeCase, setIC]    = useState(false);
  const [showAI, setShowAI]     = useState(false);
  const [saving, setSaving]     = useState(false);

  const canManual = title.trim().length >= 3;
  const canAI = canManual && specialty !== "";

  return (
    <div className="space-y-5">
      {/* Title + Description (shared by both paths) */}
      <div className="card p-5 space-y-4">
        <div>
          <label className="font-syne font-semibold text-xs text-ink-2 block mb-1.5">Course title *</label>
          <input
            autoFocus
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Cardiology — Acute Care 2026"
            className="w-full border border-border rounded-xl px-4 py-2.5 font-syne text-sm text-ink bg-surface focus:outline-none focus:border-ink transition-colors"
          />
        </div>
        <div>
          <label className="font-syne font-semibold text-xs text-ink-2 block mb-1.5">Description <span className="font-normal text-ink-3">(optional but helps AI)</span></label>
          <textarea
            value={description}
            onChange={e => setDesc(e.target.value)}
            placeholder="What will students learn? Who is this course for? Any specific focus areas?"
            rows={3}
            className="w-full border border-border rounded-xl px-4 py-2.5 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink transition-colors resize-none"
          />
        </div>
      </div>

      {/* Mode selection */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Manual path */}
        <button
          disabled={!canManual || saving}
          onClick={() => { setSaving(true); onManual({ title: title.trim(), description: description.trim() }); }}
          className="card p-5 text-left hover:border-ink-3 transition-all disabled:opacity-40 disabled:cursor-not-allowed group"
        >
          <div className="text-2xl mb-2">📝</div>
          <div className="font-syne font-bold text-sm text-ink mb-1">Create manually</div>
          <p className="font-serif text-xs text-ink-3 leading-relaxed">
            Create an empty course and add modules and lessons yourself. Full control over structure.
          </p>
        </button>

        {/* AI path */}
        <button
          onClick={() => setShowAI(v => !v)}
          disabled={!canManual}
          className={`card p-5 text-left transition-all disabled:opacity-40 disabled:cursor-not-allowed ${showAI ? "border-ink bg-ink text-white" : "hover:border-ink-3"}`}
        >
          <div className="text-2xl mb-2">✨</div>
          <div className={`font-syne font-bold text-sm mb-1 ${showAI ? "text-white" : "text-ink"}`}>
            Generate with AI
          </div>
          <p className={`font-serif text-xs leading-relaxed ${showAI ? "text-white/70" : "text-ink-3"}`}>
            AI designs the full structure — modules, lessons, and content. You review and edit at every step.
          </p>
        </button>
      </div>

      {/* AI options panel */}
      {showAI && (
        <div className="card p-5 space-y-4 border-ink/20 bg-surface-2 animate-fade-up">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">✨</span>
            <span className="font-syne font-bold text-sm text-ink">AI Course Generator</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-syne text-xs text-ink-3 block mb-1.5">Medical specialty *</label>
              <select
                value={specialty}
                onChange={e => setSpec(e.target.value)}
                className="w-full border border-border rounded-xl px-3 py-2 font-serif text-sm text-ink bg-bg focus:outline-none focus:border-ink"
              >
                <option value="">Select specialty…</option>
                {specialties.map(s => <option key={s.id} value={s.name}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="font-syne text-xs text-ink-3 block mb-1.5">Student level</label>
              <select
                value={level}
                onChange={e => setLevel(e.target.value)}
                className="w-full border border-border rounded-xl px-3 py-2 font-serif text-sm text-ink bg-bg focus:outline-none focus:border-ink"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-syne text-xs text-ink-3 block mb-1.5">Number of modules</label>
              <div className="flex gap-1">
                {[2, 3, 4, 5].map(n => (
                  <button key={n} type="button" onClick={() => setNM(n)}
                    className={`flex-1 py-1.5 rounded-lg font-syne text-xs font-bold border transition-colors ${numModules === n ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="font-syne text-xs text-ink-3 block mb-1.5">Lessons per module</label>
              <div className="flex gap-1">
                {[2, 3, 4, 5].map(n => (
                  <button key={n} type="button" onClick={() => setLPM(n)}
                    className={`flex-1 py-1.5 rounded-lg font-syne text-xs font-bold border transition-colors ${lpModule === n ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex gap-4 pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={includeQuiz} onChange={e => setIQ(e.target.checked)} className="w-4 h-4 accent-ink" />
              <span className="font-syne text-xs text-ink">Include quizzes</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={includeCase} onChange={e => setIC(e.target.checked)} className="w-4 h-4 accent-ink" />
              <span className="font-syne text-xs text-ink">Include clinical cases</span>
            </label>
          </div>

          <div className="pt-1">
            <p className="font-serif text-xs text-ink-3 mb-3">
              AI will generate ~{numModules * lpModule} lessons. You review the outline before any content is written.
            </p>
            <button
              disabled={!canAI}
              onClick={() => onAI({ title: title.trim(), description: description.trim(), specialty, level, numModules, lessonsPerModule: lpModule, includeQuiz, includeCase })}
              className="w-full btn-primary py-2.5 text-sm disabled:opacity-40"
            >
              ✨ Generate course outline →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Step 2: Review / edit outline ──────────────────────────────────────────────
function StepOutline({
  outline,
  specialty,
  level,
  onBack,
  onGenerate,
}: {
  outline: Outline;
  specialty: string;
  level: string;
  onBack: () => void;
  onGenerate: (outline: Outline) => void;
}) {
  const [draft, setDraft] = useState<Outline>(JSON.parse(JSON.stringify(outline)));

  const updateModuleTitle = (mi: number, val: string) =>
    setDraft(d => { const n = { ...d }; n.modules = [...d.modules]; n.modules[mi] = { ...n.modules[mi], title: val }; return n; });

  const updateModuleDesc = (mi: number, val: string) =>
    setDraft(d => { const n = { ...d }; n.modules = [...d.modules]; n.modules[mi] = { ...n.modules[mi], description: val }; return n; });

  const updateLessonTitle = (mi: number, li: number, val: string) =>
    setDraft(d => {
      const n = { ...d }; n.modules = [...d.modules];
      n.modules[mi] = { ...n.modules[mi], lessons: [...n.modules[mi].lessons] };
      n.modules[mi].lessons[li] = { ...n.modules[mi].lessons[li], title: val };
      return n;
    });

  const updateConcepts = (mi: number, li: number, val: string) =>
    setDraft(d => {
      const n = { ...d }; n.modules = [...d.modules];
      n.modules[mi] = { ...n.modules[mi], lessons: [...n.modules[mi].lessons] };
      n.modules[mi].lessons[li] = { ...n.modules[mi].lessons[li], key_concepts: val.split(",").map(s => s.trim()).filter(Boolean) };
      return n;
    });

  const removeLesson = (mi: number, li: number) =>
    setDraft(d => {
      const n = { ...d }; n.modules = [...d.modules];
      n.modules[mi] = { ...n.modules[mi], lessons: d.modules[mi].lessons.filter((_, i) => i !== li) };
      return n;
    });

  const addLesson = (mi: number) =>
    setDraft(d => {
      const n = { ...d }; n.modules = [...d.modules];
      n.modules[mi] = { ...n.modules[mi], lessons: [...d.modules[mi].lessons, { title: "New lesson", key_concepts: [], estimated_minutes: 20, include_quiz: true, include_clinical_case: false, status: "pending" as const }] };
      return n;
    });

  const removeModule = (mi: number) =>
    setDraft(d => ({ ...d, modules: d.modules.filter((_, i) => i !== mi) }));

  const addModule = () =>
    setDraft(d => ({
      ...d,
      modules: [...d.modules, { title: "New module", description: "", estimated_hours: 2, lessons: [{ title: "New lesson", key_concepts: [], estimated_minutes: 20, include_quiz: true, include_clinical_case: false, status: "pending" as const }] }],
    }));

  const totalLessons = draft.modules.reduce((s, m) => s + m.lessons.length, 0);

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="card p-4 flex items-center gap-4 bg-blue-light border-blue/20">
        <div className="text-3xl">📋</div>
        <div className="flex-1">
          <div className="font-syne font-bold text-sm text-ink">{draft.course_title}</div>
          <div className="font-serif text-xs text-ink-3 mt-0.5">
            {draft.modules.length} modules · {totalLessons} lessons · ~{draft.total_hours}h total
          </div>
        </div>
        <div className="text-right">
          <Badge color="blue">Review</Badge>
        </div>
      </div>

      <p className="font-serif text-xs text-ink-3 px-1">
        Review and edit the structure. You can rename modules and lessons, edit key concepts, add or remove items. Content is generated in the next step.
      </p>

      {/* Module list */}
      <div className="space-y-3">
        {draft.modules.map((mod, mi) => (
          <div key={mi} className="card p-4">
            {/* Module header */}
            <div className="flex items-start gap-2 mb-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-ink text-white flex items-center justify-center font-syne font-bold text-xs mt-0.5">
                {mi + 1}
              </div>
              <div className="flex-1 min-w-0">
                <input
                  value={mod.title}
                  onChange={e => updateModuleTitle(mi, e.target.value)}
                  className="w-full font-syne font-bold text-sm text-ink border-b border-transparent focus:border-ink-3 bg-transparent focus:outline-none pb-0.5 transition-colors"
                />
                <input
                  value={mod.description}
                  onChange={e => updateModuleDesc(mi, e.target.value)}
                  placeholder="Module description…"
                  className="w-full font-serif text-xs text-ink-3 border-b border-transparent focus:border-ink-3 bg-transparent focus:outline-none mt-1 pb-0.5 transition-colors"
                />
              </div>
              {draft.modules.length > 1 && (
                <button onClick={() => removeModule(mi)} className="text-ink-3 hover:text-red text-xs flex-shrink-0 mt-0.5 transition-colors" title="Remove module">✕</button>
              )}
            </div>

            {/* Lessons */}
            <div className="space-y-2 ml-8">
              {mod.lessons.map((lesson, li) => (
                <div key={li} className="flex items-start gap-2 p-2 rounded-lg bg-surface group">
                  <span className="font-serif text-xs text-ink-3 flex-shrink-0 mt-0.5">{li + 1}.</span>
                  <div className="flex-1 min-w-0">
                    <input
                      value={lesson.title}
                      onChange={e => updateLessonTitle(mi, li, e.target.value)}
                      className="w-full font-syne text-xs text-ink bg-transparent border-b border-transparent focus:border-ink-3 focus:outline-none pb-0.5 transition-colors"
                    />
                    <input
                      value={lesson.key_concepts.join(", ")}
                      onChange={e => updateConcepts(mi, li, e.target.value)}
                      placeholder="Key concepts (comma separated)…"
                      className="w-full font-serif text-[10px] text-ink-3 bg-transparent border-b border-transparent focus:border-ink-3 focus:outline-none mt-1 pb-0.5 transition-colors"
                    />
                  </div>
                  {mod.lessons.length > 1 && (
                    <button
                      onClick={() => removeLesson(mi, li)}
                      className="text-ink-3 hover:text-red text-xs flex-shrink-0 opacity-0 group-hover:opacity-100 transition-all"
                      title="Remove lesson"
                    >✕</button>
                  )}
                </div>
              ))}
              <button
                onClick={() => addLesson(mi)}
                className="text-xs font-syne text-ink-3 hover:text-ink ml-4 transition-colors"
              >
                + Add lesson
              </button>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={addModule}
        className="w-full card py-3 text-xs font-syne text-ink-3 hover:text-ink hover:border-ink-3 transition-all text-center"
      >
        + Add module
      </button>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button onClick={onBack} className="btn-secondary px-5 py-2.5 text-sm">← Back</button>
        <button
          onClick={() => onGenerate(draft)}
          className="btn-primary flex-1 py-2.5 text-sm flex items-center justify-center gap-2"
        >
          ✨ Generate {totalLessons} lessons →
        </button>
      </div>
    </div>
  );
}

// ── Step 3: Generating lessons ─────────────────────────────────────────────────
function StepGenerating({
  outline,
  courseId,
  specialty,
  level,
  onDone,
}: {
  outline: Outline;
  courseId: string;
  specialty: string;
  level: string;
  onDone: (moduleCount: number, lessonCount: number) => void;
}) {
  const [modules, setModules] = useState<(ModuleDraft & { moduleId?: string })[]>(
    outline.modules.map(m => ({
      ...m,
      lessons: m.lessons.map(l => ({ ...l, status: "pending" as const })),
    }))
  );
  const [currentModule, setCurrentModule] = useState(0);
  const [currentLesson, setCurrentLesson] = useState(0);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const totalLessons = modules.reduce((s, m) => s + m.lessons.length, 0);
  const doneLessons  = modules.reduce((s, m) => s + m.lessons.filter(l => l.status === "done" || l.status === "skipped").length, 0);

  const updateLesson = useCallback((mi: number, li: number, updates: Partial<LessonDraft>) => {
    setModules(prev => {
      const next = [...prev];
      next[mi] = { ...next[mi], lessons: [...next[mi].lessons] };
      next[mi].lessons[li] = { ...next[mi].lessons[li], ...updates };
      return next;
    });
  }, []);

  const runGeneration = useCallback(async () => {
    setRunning(true);
    setError("");
    let moduleCount = 0;
    let lessonCount = 0;

    for (let mi = 0; mi < modules.length; mi++) {
      setCurrentModule(mi);
      const mod = modules[mi];

      // Create module if not already created
      let moduleId = mod.moduleId;
      if (!moduleId) {
        try {
          const created = await teacherApi.createModule({
            title: mod.title,
            description: mod.description,
            specialty_code: "",
            level_label: level,
          });
          moduleId = created.id;
          setModules(prev => {
            const next = [...prev];
            next[mi] = { ...next[mi], moduleId };
            return next;
          });

          // Link module to course
          await teacherApi.addModuleToCourse(courseId, moduleId!);
          moduleCount++;
        } catch (e) {
          setError(`Failed to create module "${mod.title}"`);
          continue;
        }
      }

      // Generate each lesson
      for (let li = 0; li < mod.lessons.length; li++) {
        const lesson = mod.lessons[li];
        if (lesson.status === "done" || lesson.status === "skipped") continue;
        setCurrentLesson(li);
        updateLesson(mi, li, { status: "generating" });

        try {
          const generated = await teacherApi.aiGenerate(moduleId!, {
            title: lesson.title,
            specialty,
            key_concepts: lesson.key_concepts,
            target_level: level as "beginner" | "intermediate" | "advanced",
            estimated_minutes: lesson.estimated_minutes,
            include_quiz: lesson.include_quiz,
            include_clinical_case: lesson.include_clinical_case,
          });
          updateLesson(mi, li, { status: "done", lessonId: generated.id });
          lessonCount++;
        } catch {
          updateLesson(mi, li, { status: "error" });
        }
      }
    }

    setRunning(false);
    setDone(true);
    onDone(moduleCount, lessonCount);
  }, [modules, courseId, specialty, level, updateLesson, onDone]);

  // Auto-start on mount
  useEffect(() => { runGeneration(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const skipLesson = (mi: number, li: number) => {
    if (!running) updateLesson(mi, li, { status: "skipped" });
  };

  return (
    <div className="space-y-4">
      {/* Progress header */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="font-syne font-bold text-sm text-ink">
            {done ? "✅ All lessons generated!" : running ? "✨ Generating lessons…" : "Generation paused"}
          </span>
          <span className="font-syne text-xs text-ink-3">{doneLessons} / {totalLessons}</span>
        </div>
        <ProgressBar value={doneLessons} total={totalLessons} />
        {error && <p className="font-serif text-xs text-red mt-2">{error}</p>}
      </div>

      {/* Module tree */}
      <div className="space-y-3">
        {modules.map((mod, mi) => (
          <div key={mi} className="card p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                mod.lessons.every(l => l.status === "done" || l.status === "skipped") ? "bg-green text-white" : "bg-ink text-white"
              }`}>
                {mod.lessons.every(l => l.status === "done" || l.status === "skipped") ? "✓" : mi + 1}
              </div>
              <span className="font-syne font-bold text-sm text-ink">{mod.title}</span>
              {mod.moduleId && <Badge color="green">Created</Badge>}
            </div>

            <div className="space-y-2 ml-7">
              {mod.lessons.map((lesson, li) => (
                <div key={li} className="flex items-center gap-2 p-2 rounded-lg bg-surface">
                  <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                    {lesson.status === "done"      && <span className="text-green text-sm">✓</span>}
                    {lesson.status === "skipped"   && <span className="text-ink-3 text-sm">—</span>}
                    {lesson.status === "error"     && <span className="text-red text-sm">✗</span>}
                    {lesson.status === "generating" && <div className="w-3 h-3 border-2 border-ink border-t-transparent rounded-full animate-spin" />}
                    {lesson.status === "pending"   && <span className="text-ink-3 text-xs">○</span>}
                  </div>
                  <span className={`font-syne text-xs flex-1 ${lesson.status === "done" ? "text-ink" : lesson.status === "skipped" ? "text-ink-3 line-through" : "text-ink-2"}`}>
                    {lesson.title}
                  </span>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {lesson.status === "done" && lesson.lessonId && (
                      <a href={`/teacher/lessons/${lesson.lessonId}/edit`} target="_blank"
                        className="text-[10px] font-syne text-blue hover:underline">Edit</a>
                    )}
                    {lesson.status === "error" && (
                      <Badge color="red">Failed</Badge>
                    )}
                    {(lesson.status === "pending") && !running && (
                      <button onClick={() => skipLesson(mi, li)}
                        className="text-[10px] font-syne text-ink-3 hover:text-red">Skip</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main wizard ────────────────────────────────────────────────────────────────
export default function NewCoursePage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("basics");
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [outline, setOutline] = useState<Outline | null>(null);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [aiParams, setAiParams] = useState<{ specialty: string; level: string } | null>(null);
  const [generationDone, setGenerationDone] = useState<{ modules: number; lessons: number } | null>(null);
  const [loadingOutline, setLoadingOutline] = useState(false);
  const [outlineError, setOutlineError] = useState("");
  const [courseTitle, setCourseTitle] = useState("");

  useEffect(() => {
    Promise.all([contentApi.getSpecialties(false), contentApi.getSpecialties(true)])
      .then(([h, v]) => {
        const seen = new Set<string>();
        const all: Specialty[] = [];
        for (const s of [...(h ?? []), ...(v ?? [])]) {
          if (!seen.has(s.name)) { seen.add(s.name); all.push(s); }
        }
        setSpecialties(all.sort((a, b) => a.name.localeCompare(b.name)));
      });
  }, []);

  // Manual course creation
  const handleManual = useCallback(async (data: { title: string; description: string }) => {
    const course = await teacherApi.createCourse({ title: data.title, description: data.description });
    router.push(`/teacher/courses/${course.id}`);
  }, [router]);

  // AI path: Step 1 → generate outline
  const handleAI = useCallback(async (params: {
    title: string; description: string; specialty: string; level: string;
    numModules: number; lessonsPerModule: number; includeQuiz: boolean; includeCase: boolean;
  }) => {
    setCourseTitle(params.title);
    setAiParams({ specialty: params.specialty, level: params.level });
    setLoadingOutline(true);
    setOutlineError("");
    setStep("outline");

    try {
      const [course, gen] = await Promise.all([
        teacherApi.createCourse({ title: params.title, description: params.description }),
        teacherApi.aiGenerateCourseOutline({
          title: params.title,
          description: params.description,
          specialty: params.specialty,
          target_level: params.level,
          num_modules: params.numModules,
          lessons_per_module: params.lessonsPerModule,
          include_quiz: params.includeQuiz,
          include_clinical_case: params.includeCase,
          language: "ru",
        }),
      ]);
      setCourseId(course.id);
      setOutline(gen);
    } catch (e: any) {
      setOutlineError(e?.response?.data?.detail ?? "Failed to generate outline. Please try again.");
    } finally {
      setLoadingOutline(false);
    }
  }, []);

  // Step 2 → start generation
  const handleGenerate = useCallback((editedOutline: Outline) => {
    setOutline(editedOutline);
    setStep("generating");
  }, []);

  const handleDone = useCallback((moduleCount: number, lessonCount: number) => {
    setGenerationDone({ modules: moduleCount, lessons: lessonCount });
    setStep("done");
  }, []);

  const STEP_LABELS = {
    basics:     "1. Course details",
    outline:    "2. Review outline",
    generating: "3. Generating content",
    done:       "4. Done",
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-4 py-6">

        {/* Header */}
        <div className="mb-6">
          <Link href="/teacher/courses" className="font-syne text-xs text-ink-3 hover:text-ink transition-colors">
            ← My Courses
          </Link>
          <h1 className="font-syne font-black text-2xl text-ink mt-2">New Course</h1>

          {/* Step indicator */}
          <div className="flex items-center gap-2 mt-3">
            {(["basics", "outline", "generating", "done"] as Step[]).map((s, i) => (
              <div key={s} className="flex items-center gap-2">
                <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full font-syne text-xs font-semibold transition-all ${
                  step === s ? "bg-ink text-white" : (
                    ["basics", "outline", "generating", "done"].indexOf(step) > i
                      ? "bg-green text-white" : "bg-surface-2 text-ink-3"
                  )
                }`}>
                  {["basics", "outline", "generating", "done"].indexOf(step) > i ? "✓ " : ""}
                  {STEP_LABELS[s]}
                </div>
                {i < 3 && <span className="text-ink-3 text-xs">→</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Step 1 */}
        {step === "basics" && (
          <StepBasics specialties={specialties} onManual={handleManual} onAI={handleAI} />
        )}

        {/* Step 2 — loading or review */}
        {step === "outline" && (
          loadingOutline ? (
            <div className="card p-10 text-center">
              <div className="w-12 h-12 border-4 border-ink border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <div className="font-syne font-bold text-ink mb-1">Designing your course…</div>
              <p className="font-serif text-xs text-ink-3">AI is creating a structured curriculum for "{courseTitle}"</p>
            </div>
          ) : outlineError ? (
            <div className="card p-6 text-center">
              <div className="text-3xl mb-3">😕</div>
              <p className="font-syne font-bold text-red mb-4">{outlineError}</p>
              <button onClick={() => setStep("basics")} className="btn-secondary px-5 py-2 text-sm">← Try again</button>
            </div>
          ) : outline ? (
            <StepOutline
              outline={outline}
              specialty={aiParams?.specialty ?? ""}
              level={aiParams?.level ?? "intermediate"}
              onBack={() => setStep("basics")}
              onGenerate={handleGenerate}
            />
          ) : null
        )}

        {/* Step 3 */}
        {step === "generating" && outline && courseId && (
          <StepGenerating
            outline={outline}
            courseId={courseId}
            specialty={aiParams?.specialty ?? ""}
            level={aiParams?.level ?? "intermediate"}
            onDone={handleDone}
          />
        )}

        {/* Step 4 — Done */}
        {step === "done" && courseId && (
          <div className="card p-8 text-center">
            <div className="text-5xl mb-4">🎉</div>
            <h2 className="font-syne font-black text-2xl text-ink mb-2">Course ready!</h2>
            <p className="font-serif text-ink-3 text-sm mb-1">
              {generationDone && `${generationDone.modules} modules · ${generationDone.lessons} lessons generated`}
            </p>
            <p className="font-serif text-xs text-ink-3 mb-6">
              All lessons are saved as drafts — review and publish when ready.
            </p>
            <div className="flex gap-3 justify-center">
              <Link href={`/teacher/courses/${courseId}`} className="btn-primary px-6 py-2.5 text-sm">
                Open course →
              </Link>
              <Link href="/teacher/courses" className="btn-secondary px-5 py-2.5 text-sm">
                My courses
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
