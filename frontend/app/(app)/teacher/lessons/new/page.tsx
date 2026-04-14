"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

const SPECIALTIES = [
  { code: "cardiology", name: "Cardiology" },
  { code: "neurology", name: "Neurology" },
  { code: "surgery", name: "Surgery" },
  { code: "obstetrics", name: "Obstetrics & Gynecology" },
  { code: "pediatrics", name: "Pediatrics" },
  { code: "therapy", name: "Internal Medicine" },
  { code: "pharmacology", name: "Pharmacology" },
  { code: "lab_diagnostics", name: "Laboratory Diagnostics" },
  { code: "respiratory", name: "Respiratory Medicine" },
  { code: "veterinary", name: "Veterinary" },
];

const LEVELS = ["beginner", "intermediate", "advanced"];

// ─── Lesson templates ──────────────────────────────────────────────────────
const TEMPLATES = [
  {
    id: "pharmacology",
    label: "Pharmacology",
    icon: "💊",
    description: "MOA → Indications → Side effects → Quiz",
    content: {
      title: "",
      estimated_minutes: 20,
      learning_objectives: [
        "Understand the mechanism of action",
        "List key indications and contraindications",
        "Recognise common adverse effects",
      ],
      blocks: [
        { type: "text", order: 0, content: { heading: "Mechanism of Action", text: "Describe the pharmacodynamics here..." } },
        { type: "text", order: 1, content: { heading: "Indications & Contraindications", text: "List clinical uses and when to avoid..." } },
        { type: "text", order: 2, content: { heading: "Side Effects & Monitoring", text: "Cover adverse effects and what to monitor..." } },
        { type: "quiz", order: 3, content: { question: "What is the primary mechanism of action?", options: { A: "", B: "", C: "", D: "" }, correct: "A", explanation: "" } },
      ],
    },
  },
  {
    id: "clinical_case",
    label: "Clinical Case",
    icon: "🩺",
    description: "Intro → Case presentation → Discussion → Teaching points",
    content: {
      title: "",
      estimated_minutes: 25,
      learning_objectives: [
        "Apply clinical reasoning to a real-world scenario",
        "Identify key diagnostic features",
        "Select appropriate management",
      ],
      blocks: [
        { type: "text", order: 0, content: { heading: "Introduction", text: "Brief overview of the condition or topic..." } },
        { type: "case", order: 1, content: { presentation: "A 45-year-old patient presents with...", questions: ["What is the most likely diagnosis?", "What investigations would you order?"], teaching_points: ["Key feature 1", "Key feature 2"] } },
        { type: "text", order: 2, content: { heading: "Management Principles", text: "Evidence-based management approach..." } },
        { type: "quiz", order: 3, content: { question: "Which is the first-line treatment?", options: { A: "", B: "", C: "", D: "" }, correct: "A", explanation: "" } },
      ],
    },
  },
  {
    id: "anatomy",
    label: "Anatomy",
    icon: "🫀",
    description: "Overview → Image → Structure detail → Quiz",
    content: {
      title: "",
      estimated_minutes: 20,
      learning_objectives: [
        "Identify key anatomical structures",
        "Describe functional relationships",
        "Apply anatomy to clinical scenarios",
      ],
      blocks: [
        { type: "text", order: 0, content: { heading: "Overview", text: "Introduce the anatomical region or system..." } },
        { type: "image", order: 1, content: { url: "", caption: "Anatomical diagram — replace with actual image" } },
        { type: "text", order: 2, content: { heading: "Key Structures", text: "Describe the main structures and their relationships..." } },
        { type: "text", order: 3, content: { heading: "Clinical Relevance", text: "Explain how this anatomy applies clinically..." } },
        { type: "quiz", order: 4, content: { question: "Which structure is most clinically significant?", options: { A: "", B: "", C: "", D: "" }, correct: "A", explanation: "" } },
      ],
    },
  },
  {
    id: "pathophysiology",
    label: "Pathophysiology",
    icon: "🔬",
    description: "Normal → Pathology → Consequences → Quiz",
    content: {
      title: "",
      estimated_minutes: 25,
      learning_objectives: [
        "Describe normal physiology",
        "Explain the pathophysiological mechanism",
        "Link mechanism to clinical features",
      ],
      blocks: [
        { type: "text", order: 0, content: { heading: "Normal Physiology", text: "Briefly describe how the system normally functions..." } },
        { type: "text", order: 1, content: { heading: "Pathological Mechanism", text: "Explain the disruption and its cascade..." } },
        { type: "text", order: 2, content: { heading: "Clinical Manifestations", text: "Describe symptoms and signs arising from the pathology..." } },
        { type: "quiz", order: 3, content: { question: "What is the primary pathophysiological mechanism?", options: { A: "", B: "", C: "", D: "" }, correct: "A", explanation: "" } },
      ],
    },
  },
];

function NewLessonInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const moduleId = searchParams.get("module_id") ?? "";
  const initialMode = searchParams.get("mode") === "ai" ? "ai" : "manual";

  const [mode, setMode] = useState<"manual" | "ai">(initialMode);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Manual form
  const [manualTitle, setManualTitle] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [manualMinutes, setManualMinutes] = useState(20);

  // AI form
  const [aiTitle, setAiTitle] = useState("");
  const [aiSpecialty, setAiSpecialty] = useState("");
  const [aiConcepts, setAiConcepts] = useState("");
  const [aiLevel, setAiLevel] = useState("intermediate");
  const [aiMinutes, setAiMinutes] = useState(20);
  const [includeQuiz, setIncludeQuiz] = useState(true);
  const [includeCase, setIncludeCase] = useState(false);

  async function handleManual(e: React.FormEvent) {
    e.preventDefault();
    if (!moduleId) return;
    setLoading(true);
    setError("");
    try {
      const tmpl = TEMPLATES.find((t) => t.id === selectedTemplate);
      const content = tmpl
        ? { ...tmpl.content, title: manualTitle.trim(), estimated_minutes: manualMinutes }
        : {
            title: manualTitle.trim(),
            blocks: [{ type: "text", order: 0, content: { text: "" } }],
            estimated_minutes: manualMinutes,
            learning_objectives: [],
          };
      const lesson = await teacherApi.createLesson(moduleId, {
        title: manualTitle.trim(),
        content,
        estimated_minutes: manualMinutes,
      });
      router.push(`/teacher/lessons/${lesson.id}/edit`);
    } catch {
      setError("Failed to create lesson.");
      setLoading(false);
    }
  }

  async function handleAiGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!moduleId || !aiTitle.trim() || !aiSpecialty) return;
    setLoading(true);
    setError("");
    try {
      const lesson = await teacherApi.aiGenerate(moduleId, {
        title: aiTitle.trim(),
        specialty: aiSpecialty,
        key_concepts: aiConcepts.split(",").map((s) => s.trim()).filter(Boolean),
        target_level: aiLevel as "beginner" | "intermediate" | "advanced",
        estimated_minutes: aiMinutes,
        include_quiz: includeQuiz,
        include_clinical_case: includeCase,
      });
      router.push(`/teacher/lessons/${lesson.id}/edit`);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "AI generation failed. Try again.");
      setLoading(false);
    }
  }

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <div className="mb-5">
        <Link href={moduleId ? `/teacher/modules/${moduleId}` : "/teacher/modules"} className="text-ink-3 text-sm font-syne hover:text-ink">
          ← Module
        </Link>
        <h1 className="font-syne font-black text-2xl text-ink mt-2">New Lesson</h1>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 mb-5 p-1 bg-surface border border-border rounded-xl">
        <button
          onClick={() => setMode("manual")}
          className={`flex-1 py-2 rounded-lg font-syne font-semibold text-sm transition-colors ${mode === "manual" ? "bg-ink text-white" : "text-ink-3 hover:text-ink"}`}
        >
          Manual
        </button>
        <button
          onClick={() => setMode("ai")}
          className={`flex-1 py-2 rounded-lg font-syne font-semibold text-sm transition-colors ${mode === "ai" ? "bg-ink text-white" : "text-ink-3 hover:text-ink"}`}
        >
          AI Generate
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">
          {error}
        </div>
      )}

      {mode === "manual" ? (
        <form onSubmit={handleManual} className="space-y-4">
          <div className="card p-5 space-y-4">
            <div>
              <label className="block font-syne font-semibold text-sm text-ink mb-1">Title *</label>
              <input
                type="text"
                value={manualTitle}
                onChange={(e) => setManualTitle(e.target.value)}
                placeholder="Lesson title"
                required
                minLength={2}
                maxLength={300}
                className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
              />
            </div>
            <div>
              <label className="block font-syne font-semibold text-sm text-ink mb-1">Estimated minutes</label>
              <input
                type="number"
                value={manualMinutes}
                onChange={(e) => setManualMinutes(Number(e.target.value))}
                min={5}
                max={180}
                className="w-24 border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
              />
            </div>
          </div>

          {/* Template picker */}
          <div>
            <p className="font-syne font-semibold text-sm text-ink mb-2">
              Start from template <span className="text-ink-3 font-normal">(optional)</span>
            </p>
            <div className="grid grid-cols-2 gap-2">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setSelectedTemplate(selectedTemplate === t.id ? null : t.id)}
                  className={`text-left p-3 rounded-xl border transition-colors ${
                    selectedTemplate === t.id
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-surface hover:border-ink-3"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-lg">{t.icon}</span>
                    <span className="font-syne font-semibold text-sm">{t.label}</span>
                  </div>
                  <p className={`font-serif text-xs ${selectedTemplate === t.id ? "text-white/70" : "text-ink-3"}`}>
                    {t.description}
                  </p>
                </button>
              ))}
            </div>
            {!selectedTemplate && (
              <p className="font-serif text-xs text-ink-3 mt-2">No template — starts with a blank text block.</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !manualTitle.trim()}
            className="w-full btn-primary py-2.5 rounded-lg font-syne font-semibold text-sm disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create & Open Editor"}
          </button>
        </form>
      ) : (
        <form onSubmit={handleAiGenerate} className="card p-5 space-y-4">
          <div className="p-3 rounded-lg bg-blue-light border border-blue/20">
            <p className="font-syne font-semibold text-sm text-blue mb-0.5">AI Generation</p>
            <p className="font-serif text-xs text-ink-3">
              Claude will generate a complete, evidence-based lesson draft. You can edit it afterwards.
            </p>
          </div>

          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1">Lesson title *</label>
            <input
              type="text"
              value={aiTitle}
              onChange={(e) => setAiTitle(e.target.value)}
              placeholder="e.g. Beta-blockers in Heart Failure"
              required
              minLength={2}
              maxLength={300}
              className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-syne font-semibold text-sm text-ink mb-1">Specialty *</label>
              <select
                value={aiSpecialty}
                onChange={(e) => setAiSpecialty(e.target.value)}
                required
                className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
              >
                <option value="">Select specialty</option>
                {SPECIALTIES.map((s) => (
                  <option key={s.code} value={s.name}>{s.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-syne font-semibold text-sm text-ink mb-1">Level</label>
              <select
                value={aiLevel}
                onChange={(e) => setAiLevel(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
              >
                {LEVELS.map((l) => (
                  <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1">
              Key concepts <span className="text-ink-3 font-normal">(comma separated)</span>
            </label>
            <input
              type="text"
              value={aiConcepts}
              onChange={(e) => setAiConcepts(e.target.value)}
              placeholder="e.g. mechanism of action, contraindications, dosing"
              className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            />
          </div>

          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1">Estimated minutes</label>
            <input
              type="number"
              value={aiMinutes}
              onChange={(e) => setAiMinutes(Number(e.target.value))}
              min={5}
              max={90}
              className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            />
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeQuiz}
                onChange={(e) => setIncludeQuiz(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="font-syne text-sm text-ink">Include quiz blocks</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeCase}
                onChange={(e) => setIncludeCase(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="font-syne text-sm text-ink">Include clinical case</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading || !aiTitle.trim() || !aiSpecialty}
            className="w-full btn-primary py-2.5 rounded-lg font-syne font-semibold text-sm disabled:opacity-50"
          >
            {loading ? "Generating with AI... (may take 20–40s)" : "Generate Lesson with AI"}
          </button>
        </form>
      )}
    </div>
  );
}

export default function NewLessonPage() {
  return (
    <Suspense fallback={<div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>}>
      <NewLessonInner />
    </Suspense>
  );
}
