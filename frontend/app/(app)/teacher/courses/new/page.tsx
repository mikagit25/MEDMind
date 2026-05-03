"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

export default function NewCoursePage() {
  const t = useT();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setError("");
    try {
      const course = await teacherApi.createCourse({ title: title.trim(), description: description.trim() || undefined });
      router.push(`/teacher/courses/${course.id}`);
    } catch {
      setError("Failed to create course");
      setSaving(false);
    }
  }

  return (
    <div className="p-4 max-w-lg mx-auto">
      <div className="mb-5">
        <Link href="/teacher/courses" className="text-ink-3 text-sm font-syne hover:text-ink">← My Courses</Link>
        <h1 className="font-syne font-black text-2xl text-ink mt-2">New Course</h1>
        <p className="font-serif text-ink-3 text-sm">A course groups your modules and gives students a single invite code to enroll.</p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="card p-5 space-y-4">
        <div>
          <label className="font-syne text-xs text-ink-3 block mb-1.5">Course title *</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Cardiology — Spring 2026"
            className="w-full border border-border rounded-lg px-3 py-2 font-syne text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            required
            autoFocus
          />
        </div>
        <div>
          <label className="font-syne text-xs text-ink-3 block mb-1.5">Description (optional)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What will students learn in this course?"
            rows={3}
            className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3 resize-none"
          />
        </div>

        <div className="flex gap-3 pt-1">
          <Link href="/teacher/courses" className="btn-ghost text-sm px-4 py-2">
            Cancel
          </Link>
          <button
            type="submit"
            disabled={!title.trim() || saving}
            className="btn-primary text-sm px-5 py-2 disabled:opacity-50"
          >
            {saving ? "Creating..." : "Create course"}
          </button>
        </div>
      </form>
    </div>
  );
}
