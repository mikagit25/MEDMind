"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

type Lesson = {
  id: string;
  module_id: string;
  title: string;
  status: "draft" | "review" | "published" | "archived";
  estimated_minutes: number;
  content: Record<string, unknown>;
  review_notes?: string;
};

const AI_TASKS = [
  { value: "improve_clarity", label: "Improve clarity" },
  { value: "add_quiz", label: "Add quiz blocks" },
  { value: "simplify_language", label: "Simplify language" },
  { value: "add_clinical_case", label: "Add clinical case" },
  { value: "check_accuracy", label: "Check accuracy" },
];

const SPECIALTIES = [
  "Cardiology", "Neurology", "Surgery", "Obstetrics & Gynecology",
  "Pediatrics", "Internal Medicine", "Pharmacology", "Laboratory Diagnostics",
  "Respiratory Medicine", "Veterinary",
];

const LEVELS = ["beginner", "intermediate", "advanced"];

const STATUS_COLORS: Record<string, string> = {
  draft: "text-ink-3",
  review: "text-amber",
  published: "text-green",
  archived: "text-red",
};

export default function LessonEditPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [title, setTitle] = useState("");
  const [minutes, setMinutes] = useState(20);
  const [contentJson, setContentJson] = useState("");
  const [jsonError, setJsonError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [error, setError] = useState("");

  // AI Improve panel
  const [aiOpen, setAiOpen] = useState(false);
  const [aiTask, setAiTask] = useState("improve_clarity");
  const [aiSpecialty, setAiSpecialty] = useState("Cardiology");
  const [aiLevel, setAiLevel] = useState("intermediate");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState<{
    suggested: Record<string, unknown>;
    review_notes?: string;
    task: string;
  } | null>(null);

  // Workflow
  const [workflowLoading, setWorkflowLoading] = useState(false);

  useEffect(() => {
    teacherApi.getLesson(id)
      .then((l: Lesson) => {
        setLesson(l);
        setTitle(l.title);
        setMinutes(l.estimated_minutes);
        setContentJson(JSON.stringify(l.content, null, 2));
      })
      .catch(() => setError("Failed to load lesson"));
  }, [id]);

  async function handleSave() {
    if (!lesson) return;
    setJsonError("");
    let parsed: object;
    try {
      parsed = JSON.parse(contentJson);
    } catch {
      setJsonError("Invalid JSON");
      return;
    }
    setSaving(true);
    setSaveMsg("");
    try {
      const updated = await teacherApi.updateLesson(lesson.id, {
        title: title.trim(),
        content: parsed,
        estimated_minutes: minutes,
      });
      setLesson(updated);
      setSaveMsg("Saved");
      setTimeout(() => setSaveMsg(""), 2000);
    } catch {
      setError("Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleWorkflow(action: "submit" | "publish" | "unpublish") {
    if (!lesson) return;
    setWorkflowLoading(true);
    setError("");
    try {
      let updated: Lesson;
      if (action === "submit") updated = await teacherApi.submitForReview(lesson.id);
      else if (action === "publish") updated = await teacherApi.publishLesson(lesson.id);
      else updated = await teacherApi.unpublishLesson(lesson.id);
      setLesson(updated);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Action failed");
    } finally {
      setWorkflowLoading(false);
    }
  }

  async function handleAiImprove() {
    if (!lesson) return;
    setAiLoading(true);
    setAiSuggestion(null);
    setError("");
    try {
      const result = await teacherApi.aiImprove(lesson.id, {
        task: aiTask,
        specialty: aiSpecialty,
        target_level: aiLevel,
      });
      setAiSuggestion(result);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "AI improve failed");
    } finally {
      setAiLoading(false);
    }
  }

  function applyAiSuggestion() {
    if (!aiSuggestion) return;
    setContentJson(JSON.stringify(aiSuggestion.suggested, null, 2));
    setAiSuggestion(null);
    setAiOpen(false);
    setSaveMsg("Applied — remember to save");
    setTimeout(() => setSaveMsg(""), 3000);
  }

  if (!lesson && !error) return <div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>;
  if (error && !lesson) return <div className="p-6 text-red font-serif text-sm">{error}</div>;
  if (!lesson) return null;

  const isArchived = lesson.status === "archived";

  return (
    <div className="p-4 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <Link href={`/teacher/modules/${lesson.module_id}`} className="text-ink-3 text-sm font-syne hover:text-ink">
            ← Module
          </Link>
          <h1 className="font-syne font-black text-xl text-ink mt-1">{lesson.title}</h1>
          <span className={`font-syne text-sm font-semibold ${STATUS_COLORS[lesson.status]}`}>
            {lesson.status.toUpperCase()}
          </span>
        </div>

        {/* Workflow buttons */}
        {!isArchived && (
          <div className="flex gap-2 shrink-0">
            {lesson.status === "draft" && (
              <>
                <button
                  onClick={() => handleWorkflow("submit")}
                  disabled={workflowLoading}
                  className="text-sm border border-amber/40 text-amber rounded-lg px-3 py-1.5 font-syne font-semibold hover:bg-amber-light disabled:opacity-50"
                >
                  Submit for Review
                </button>
                <button
                  onClick={() => handleWorkflow("publish")}
                  disabled={workflowLoading}
                  className="btn-primary text-sm px-3 py-1.5 rounded-lg font-syne font-semibold disabled:opacity-50"
                >
                  Publish
                </button>
              </>
            )}
            {lesson.status === "review" && (
              <button
                onClick={() => handleWorkflow("publish")}
                disabled={workflowLoading}
                className="btn-primary text-sm px-3 py-1.5 rounded-lg font-syne font-semibold disabled:opacity-50"
              >
                Publish
              </button>
            )}
            {lesson.status === "published" && (
              <button
                onClick={() => handleWorkflow("unpublish")}
                disabled={workflowLoading}
                className="text-sm border border-border text-ink-3 rounded-lg px-3 py-1.5 font-syne hover:border-ink-3 disabled:opacity-50"
              >
                Unpublish
              </button>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="mb-3 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {saveMsg && (
        <div className="mb-3 p-2 rounded-lg bg-green-light border border-green/20 text-green text-sm font-syne">
          {saveMsg}
        </div>
      )}

      {/* Edit form */}
      <div className="card p-4 mb-4 space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <label className="block font-syne font-semibold text-sm text-ink mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isArchived}
              className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3 disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1">Minutes</label>
            <input
              type="number"
              value={minutes}
              onChange={(e) => setMinutes(Number(e.target.value))}
              min={5}
              max={180}
              disabled={isArchived}
              className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3 disabled:opacity-50"
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="font-syne font-semibold text-sm text-ink">Content (JSON)</label>
            {jsonError && <span className="text-red text-xs font-syne">{jsonError}</span>}
          </div>
          <textarea
            value={contentJson}
            onChange={(e) => { setContentJson(e.target.value); setJsonError(""); }}
            rows={16}
            disabled={isArchived}
            className="w-full border border-border rounded-lg px-3 py-2 font-mono text-xs text-ink bg-surface focus:outline-none focus:border-ink-3 resize-y disabled:opacity-50"
          />
        </div>

        {!isArchived && (
          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary py-2 px-5 rounded-lg font-syne font-semibold text-sm disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              onClick={() => setAiOpen((v) => !v)}
              className="border border-border rounded-lg px-4 py-2 font-syne font-semibold text-sm text-ink hover:border-ink-3 transition-colors"
            >
              {aiOpen ? "Hide AI Panel" : "AI Improve"}
            </button>
          </div>
        )}
      </div>

      {/* AI Improve Panel */}
      {aiOpen && !isArchived && (
        <div className="card p-4 border-blue/30 bg-blue-light/30 mb-4">
          <h3 className="font-syne font-bold text-sm text-ink mb-3">AI Improvement</h3>

          <div className="grid grid-cols-3 gap-3 mb-3">
            <div>
              <label className="block font-syne text-xs text-ink-3 mb-1">Task</label>
              <select
                value={aiTask}
                onChange={(e) => setAiTask(e.target.value)}
                className="w-full border border-border rounded-lg px-2 py-1.5 font-serif text-xs text-ink bg-surface focus:outline-none"
              >
                {AI_TASKS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-syne text-xs text-ink-3 mb-1">Specialty</label>
              <select
                value={aiSpecialty}
                onChange={(e) => setAiSpecialty(e.target.value)}
                className="w-full border border-border rounded-lg px-2 py-1.5 font-serif text-xs text-ink bg-surface focus:outline-none"
              >
                {SPECIALTIES.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-syne text-xs text-ink-3 mb-1">Level</label>
              <select
                value={aiLevel}
                onChange={(e) => setAiLevel(e.target.value)}
                className="w-full border border-border rounded-lg px-2 py-1.5 font-serif text-xs text-ink bg-surface focus:outline-none"
              >
                {LEVELS.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={handleAiImprove}
            disabled={aiLoading}
            className="btn-primary text-sm px-4 py-2 rounded-lg font-syne font-semibold disabled:opacity-50 mb-3"
          >
            {aiLoading ? "Analysing with Claude..." : "Run AI Improve"}
          </button>

          {aiSuggestion && (
            <div className="border border-green/30 rounded-lg p-3 bg-white/50">
              <div className="flex items-center justify-between mb-2">
                <span className="font-syne font-semibold text-sm text-ink">Suggestion ready</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setAiSuggestion(null)}
                    className="text-xs text-ink-3 font-syne hover:text-ink"
                  >
                    Discard
                  </button>
                  <button
                    onClick={applyAiSuggestion}
                    className="text-xs text-green font-syne font-semibold hover:underline"
                  >
                    Apply to editor
                  </button>
                </div>
              </div>
              {aiSuggestion.review_notes && (
                <p className="font-serif text-xs text-ink-3 mb-2">{aiSuggestion.review_notes}</p>
              )}
              <pre className="font-mono text-xs text-ink bg-surface rounded p-2 overflow-auto max-h-48">
                {JSON.stringify(aiSuggestion.suggested, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Review notes */}
      {lesson.review_notes && (
        <div className="card p-3 border-amber/30 bg-amber-light/40">
          <p className="font-syne font-semibold text-xs text-amber mb-1">Review Notes</p>
          <p className="font-serif text-sm text-ink">{lesson.review_notes}</p>
        </div>
      )}
    </div>
  );
}
