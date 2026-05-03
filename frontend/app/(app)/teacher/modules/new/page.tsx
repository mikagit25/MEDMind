"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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

export default function NewModulePage() {
  const t = useT();
  const router = useRouter();
  const [form, setForm] = useState({
    title: "",
    description: "",
    specialty_code: "",
    level_label: "intermediate",
    is_veterinary: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function set(key: string, value: string | boolean) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const mod = await teacherApi.createModule({
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        specialty_code: form.specialty_code || undefined,
        level_label: form.level_label,
        is_veterinary: form.is_veterinary,
      });
      router.push(`/teacher/modules/${mod.id}`);
    } catch {
      setError("Failed to create module. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div className="p-4 max-w-xl mx-auto">
      <div className="mb-5">
        <Link href="/teacher/modules" className="text-ink-3 text-sm font-syne hover:text-ink">
          ← My Modules
        </Link>
        <h1 className="font-syne font-black text-2xl text-ink mt-2">New Module</h1>
        <p className="font-serif text-ink-3 text-sm">Create a new teaching module</p>
      </div>

      <form onSubmit={handleSubmit} className="card p-5 space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">
            {error}
          </div>
        )}

        <div>
          <label className="block font-syne font-semibold text-sm text-ink mb-1">Title *</label>
          <input
            type="text"
            value={form.title}
            onChange={(e) => set("title", e.target.value)}
            placeholder="e.g. Cardiology Fundamentals"
            className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            required
            minLength={2}
            maxLength={300}
          />
        </div>

        <div>
          <label className="block font-syne font-semibold text-sm text-ink mb-1">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            placeholder="Brief overview of what this module covers"
            rows={3}
            className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3 resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1">Specialty</label>
            <select
              value={form.specialty_code}
              onChange={(e) => set("specialty_code", e.target.value)}
              className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            >
              <option value="">— General —</option>
              {SPECIALTIES.map((s) => (
                <option key={s.code} value={s.code}>{s.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1">Level</label>
            <select
              value={form.level_label}
              onChange={(e) => set("level_label", e.target.value)}
              className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
            >
              {LEVELS.map((l) => (
                <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
              ))}
            </select>
          </div>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={form.is_veterinary}
            onChange={(e) => set("is_veterinary", e.target.checked)}
            className="w-4 h-4"
          />
          <span className="font-syne text-sm text-ink">Veterinary module</span>
        </label>

        <button
          type="submit"
          disabled={loading || !form.title.trim()}
          className="w-full btn-primary py-2.5 rounded-lg font-syne font-semibold text-sm disabled:opacity-50"
        >
          {loading ? "Creating..." : "Create Module"}
        </button>
      </form>
    </div>
  );
}
