"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { teacherApi } from "@/lib/api";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

type Module = {
  id: string;
  title: string;
  description?: string;
  level_label?: string;
  is_published: boolean;
  is_veterinary: boolean;
  created_at: string;
};

type Lesson = {
  id: string;
  title: string;
  status: "draft" | "review" | "published" | "archived";
  lesson_order: number;
  estimated_minutes: number;
  published_at?: string;
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-surface text-ink-3 border-border",
  review: "bg-amber-light text-amber border-amber/30",
  published: "bg-green-light text-green border-green/30",
  archived: "bg-red-light text-red border-red/30",
};

export default function ModuleDetailPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [mod, setMod] = useState<Module | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [mods, lsns] = await Promise.all([
        teacherApi.listMyModules(),
        teacherApi.listLessons(id, true),
      ]);
      const found = mods.find((m: Module) => m.id === id);
      if (!found) { router.replace("/teacher/modules"); return; }
      setMod(found);
      setLessons(lsns.filter((l: Lesson) => l.status !== "archived"));
    } catch {
      setError("Failed to load module");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function handleExport() {
    if (!mod) return;
    setExporting(true);
    try {
      const blob = await teacherApi.exportModule(mod.id);
      const filename = `medmind_module_${mod.title.replace(/\s+/g, "_").toLowerCase()}.json`;
      downloadBlob(blob, filename);
    } catch {
      setError("Export failed. Try again.");
    } finally {
      setExporting(false);
    }
  }

  async function handlePublish() {
    if (!mod) return;
    setPublishing(true);
    setError("");
    try {
      const updated = await teacherApi.publishModule(mod.id);
      setMod(updated);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Cannot publish: ensure at least one lesson is published.");
    } finally {
      setPublishing(false);
    }
  }

  async function handleWorkflow(lessonId: string, action: "submit" | "publish" | "unpublish") {
    try {
      let updated: Lesson;
      if (action === "submit") updated = await teacherApi.submitForReview(lessonId);
      else if (action === "publish") updated = await teacherApi.publishLesson(lessonId);
      else updated = await teacherApi.unpublishLesson(lessonId);
      setLessons((ls) => ls.map((l) => (l.id === lessonId ? { ...l, ...updated } : l)));
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Action failed");
    }
  }

  if (loading) return <div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>;
  if (!mod) return null;

  const publishedCount = lessons.filter((l) => l.status === "published").length;

  return (
    <div className="p-4 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-5">
        <Link href="/teacher/modules" className="text-ink-3 text-sm font-syne hover:text-ink">
          ← My Modules
        </Link>
        <div className="flex items-start justify-between mt-2 gap-3">
          <div>
            <h1 className="font-syne font-black text-2xl text-ink">{mod.title}</h1>
            {mod.description && (
              <p className="font-serif text-ink-3 text-sm mt-0.5">{mod.description}</p>
            )}
            <div className="flex items-center gap-2 mt-1.5">
              <span className={`text-xs border rounded px-1.5 py-0.5 font-syne ${mod.is_published ? "bg-green-light text-green border-green/30" : "bg-amber-light text-amber border-amber/30"}`}>
                {mod.is_published ? "Published" : "Unpublished"}
              </span>
              {mod.level_label && <span className="font-serif text-ink-3 text-xs">{mod.level_label}</span>}
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              onClick={handleExport}
              disabled={exporting}
              className="text-sm border border-border text-ink-3 px-3 py-1.5 rounded-lg font-syne font-semibold hover:border-ink-3 transition-colors disabled:opacity-40"
            >
              {exporting ? "Exporting…" : "⬇ Export"}
            </button>
            <Link
              href={`/teacher/analytics?module=${mod.id}`}
              className="text-sm border border-border text-ink-3 px-3 py-1.5 rounded-lg font-syne font-semibold hover:border-ink-3 transition-colors"
            >
              📊 Analytics
            </Link>
            {!mod.is_published && (
              <button
                onClick={handlePublish}
                disabled={publishing || publishedCount === 0}
                title={publishedCount === 0 ? "Publish at least one lesson first" : ""}
                className="btn-primary text-sm px-4 py-2 rounded-lg font-syne font-semibold disabled:opacity-40"
              >
                {publishing ? "Publishing..." : "Publish Module"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Summary stats */}
      {lessons.length > 0 && (
        <div className="flex gap-6 mb-4 p-3 bg-bg-2 rounded-lg">
          {[
            { label: "Total lessons", value: lessons.length },
            { label: "Published", value: publishedCount, color: publishedCount > 0 ? "text-green" : "text-ink" },
            { label: "Drafts", value: lessons.filter(l => l.status === "draft").length },
            { label: "Est. duration", value: `${lessons.reduce((s, l) => s + (l.estimated_minutes || 0), 0)} min` },
          ].map(({ label, value, color }) => (
            <div key={label}>
              <div className={`font-syne font-bold text-sm ${color ?? "text-ink"}`}>{value}</div>
              <div className="font-serif text-ink-3 text-xs">{label}</div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* Lessons */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-syne font-bold text-base text-ink">
          Lessons ({lessons.length})
          {publishedCount > 0 && <span className="text-green font-normal text-sm ml-2">{publishedCount} published</span>}
        </h2>
        <div className="flex gap-2">
          <Link
            href={`/teacher/lessons/new?module_id=${mod.id}&mode=manual`}
            className="text-sm border border-border rounded-lg px-3 py-1.5 font-syne font-semibold text-ink hover:border-ink-3 transition-colors"
          >
            + Manual
          </Link>
          <Link
            href={`/teacher/lessons/new?module_id=${mod.id}&mode=ai`}
            className="btn-primary text-sm px-3 py-1.5 rounded-lg font-syne font-semibold"
          >
            + AI Generate
          </Link>
        </div>
      </div>

      {lessons.length === 0 ? (
        <div className="card p-6 text-center">
          <div className="text-3xl mb-2">📝</div>
          <div className="font-syne font-semibold text-ink mb-1">No lessons yet</div>
          <div className="font-serif text-ink-3 text-sm mb-3">Add lessons to this module manually or generate them with AI.</div>
          <div className="flex justify-center gap-2">
            <Link href={`/teacher/lessons/new?module_id=${mod.id}&mode=manual`} className="border border-border rounded-lg px-3 py-1.5 font-syne text-sm hover:border-ink-3">
              Manual
            </Link>
            <Link href={`/teacher/lessons/new?module_id=${mod.id}&mode=ai`} className="btn-primary text-sm px-3 py-1.5 rounded-lg font-syne font-semibold">
              AI Generate
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {lessons
            .sort((a, b) => a.lesson_order - b.lesson_order)
            .map((lesson) => (
              <div key={lesson.id} className="card p-3 flex items-center gap-3">
                <div className="text-ink-3 font-syne text-xs w-5 text-center shrink-0">
                  {lesson.lesson_order + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-syne font-semibold text-sm text-ink truncate">{lesson.title}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs border rounded px-1.5 py-0.5 font-syne ${STATUS_COLORS[lesson.status]}`}>
                      {lesson.status}
                    </span>
                    <span className="font-serif text-ink-3 text-xs">{lesson.estimated_minutes} min</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {lesson.status === "draft" && (
                    <>
                      <button
                        onClick={() => handleWorkflow(lesson.id, "publish")}
                        className="text-xs text-green font-syne hover:underline px-2 py-1"
                      >
                        Publish
                      </button>
                      <button
                        onClick={() => handleWorkflow(lesson.id, "submit")}
                        className="text-xs text-amber font-syne hover:underline px-2 py-1"
                      >
                        Review
                      </button>
                    </>
                  )}
                  {lesson.status === "review" && (
                    <button
                      onClick={() => handleWorkflow(lesson.id, "publish")}
                      className="text-xs text-green font-syne hover:underline px-2 py-1"
                    >
                      Publish
                    </button>
                  )}
                  {lesson.status === "published" && (
                    <button
                      onClick={() => handleWorkflow(lesson.id, "unpublish")}
                      className="text-xs text-ink-3 font-syne hover:underline px-2 py-1"
                    >
                      Unpublish
                    </button>
                  )}
                  <Link
                    href={`/teacher/lessons/${lesson.id}/edit`}
                    className="text-xs text-ink font-syne border border-border rounded px-2 py-1 hover:border-ink-3 transition-colors"
                  >
                    Edit
                  </Link>
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
