"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { teacherApi, contentApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type Module = {
  id: string;
  title: string;
  description?: string;
  level_label?: string;
  is_published: boolean;
  is_veterinary: boolean;
  created_at: string;
};

type Specialty = { id: string; name: string };

const STATUS_BADGE: Record<string, string> = {
  true: "bg-green-100 text-green-700 border-green-200",
  false: "bg-amber-100 text-amber-700 border-amber-200",
};

export default function TeacherModulesPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [modules, setModules] = useState<Module[]>([]);
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Import modal state
  const [importOpen, setImportOpen] = useState(false);
  const [importSpecialtyId, setImportSpecialtyId] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importData, setImportData] = useState<Record<string, unknown> | null>(null);
  const [importPreview, setImportPreview] = useState<{ title: string; lessons: number; flashcards: number } | null>(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [importSuccess, setImportSuccess] = useState("");

  useEffect(() => {
    if (user && user.role !== "teacher" && user.role !== "admin") {
      router.replace("/dashboard");
      return;
    }
    Promise.all([
      teacherApi.listMyModules(),
      contentApi.getSpecialties(),
    ]).then(([mods, specs]) => {
      setModules(mods);
      const specList: Specialty[] = (specs.data ?? specs ?? []);
      setSpecialties(specList);
      if (specList.length > 0) setImportSpecialtyId(specList[0].id);
    }).catch(() => setError("Failed to load modules"))
      .finally(() => setLoading(false));
  }, [user, router]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportFile(file);
    setImportError("");
    setImportPreview(null);
    setImportData(null);

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const json = JSON.parse(ev.target?.result as string);
        if (json.format !== "medmind_course_v1") {
          setImportError("Invalid format — expected a MedMind export file.");
          return;
        }
        setImportData(json);
        setImportPreview({
          title: json.module?.title ?? "Unknown",
          lessons: (json.lessons ?? []).length,
          flashcards: (json.flashcards ?? []).length,
        });
      } catch {
        setImportError("Could not parse file — ensure it is valid JSON.");
      }
    };
    reader.readAsText(file);
  }

  async function handleImport() {
    if (!importData || !importSpecialtyId) return;
    setImporting(true);
    setImportError("");
    try {
      const result = await teacherApi.importModule(importSpecialtyId, importData);
      setImportSuccess(`Imported "${result.title}" — ${result.lessons_imported} lessons, ${result.flashcards_imported} flashcards`);
      // Reload modules list
      const updated = await teacherApi.listMyModules();
      setModules(updated);
      setImportOpen(false);
      setImportFile(null);
      setImportData(null);
      setImportPreview(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (e: any) {
      setImportError(e?.response?.data?.detail ?? "Import failed");
    } finally {
      setImporting(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <div className="text-ink-3 font-serif text-sm">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">My Modules</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">Manage your teaching content</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setImportOpen(true); setImportError(""); setImportSuccess(""); }}
            className="text-sm border border-border text-ink-3 px-3 py-2 rounded-lg font-syne font-semibold hover:border-ink-3 transition-colors"
          >
            ⬆ Import
          </button>
          <Link
            href="/teacher/modules/new"
            className="btn-primary text-sm px-4 py-2 rounded-lg font-syne font-semibold"
          >
            + New Module
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">{error}</div>
      )}

      {importSuccess && (
        <div className="mb-4 p-3 rounded-lg bg-green-light border border-green/20 text-green text-sm font-serif">
          ✓ {importSuccess}
          <button onClick={() => setImportSuccess("")} className="ml-2 underline text-xs">dismiss</button>
        </div>
      )}

      {/* Import modal */}
      {importOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-syne font-bold text-lg text-ink">Import Module</h2>
              <button onClick={() => setImportOpen(false)} className="text-ink-3 hover:text-ink text-xl leading-none">×</button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="font-syne text-xs text-ink-3 block mb-1">Specialty</label>
                <select
                  value={importSpecialtyId}
                  onChange={(e) => setImportSpecialtyId(e.target.value)}
                  className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
                >
                  {specialties.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-syne text-xs text-ink-3 block mb-1">Module JSON file</label>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".json,application/json"
                  onChange={handleFileChange}
                  className="w-full font-serif text-sm text-ink-3 file:mr-3 file:py-1 file:px-3 file:rounded file:border file:border-border file:font-syne file:text-xs file:text-ink file:bg-surface hover:file:bg-bg-2"
                />
              </div>

              {importPreview && (
                <div className="bg-bg-2 rounded-lg p-3 border border-border">
                  <div className="font-syne font-semibold text-sm text-ink mb-1">Preview</div>
                  <div className="font-syne font-bold text-base text-ink">{importPreview.title}</div>
                  <div className="flex gap-4 mt-1">
                    <span className="font-serif text-xs text-ink-3">{importPreview.lessons} lesson{importPreview.lessons !== 1 ? "s" : ""}</span>
                    <span className="font-serif text-xs text-ink-3">{importPreview.flashcards} flashcard{importPreview.flashcards !== 1 ? "s" : ""}</span>
                  </div>
                  <p className="font-serif text-xs text-amber mt-2">Will be created as draft — review before publishing.</p>
                </div>
              )}

              {importError && (
                <p className="font-serif text-xs text-red">{importError}</p>
              )}

              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => setImportOpen(false)}
                  className="flex-1 border border-border text-ink-3 text-sm py-2 rounded-lg font-syne font-semibold hover:border-ink-3 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleImport}
                  disabled={!importData || !importSpecialtyId || importing}
                  className="flex-1 btn-primary text-sm py-2 disabled:opacity-40"
                >
                  {importing ? "Importing…" : "Import Module"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {modules.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="text-4xl mb-3">📚</div>
          <div className="font-syne font-semibold text-ink mb-1">No modules yet</div>
          <div className="font-serif text-ink-3 text-sm mb-4">Create your first teaching module to get started.</div>
          <Link href="/teacher/modules/new" className="btn-primary text-sm px-4 py-2 rounded-lg font-syne font-semibold">
            Create Module
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {modules.map((mod) => (
            <Link
              key={mod.id}
              href={`/teacher/modules/${mod.id}`}
              className="card p-4 flex items-center justify-between hover:border-ink-3 transition-colors block"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-syne font-semibold text-ink truncate">{mod.title}</span>
                  {mod.is_veterinary && (
                    <span className="text-xs bg-blue-light text-blue border border-blue/20 rounded px-1.5 py-0.5 font-syne shrink-0">VET</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs border rounded px-1.5 py-0.5 font-syne shrink-0 ${STATUS_BADGE[String(mod.is_published)]}`}>
                    {mod.is_published ? "Published" : "Draft"}
                  </span>
                  {mod.level_label && (
                    <span className="font-serif text-ink-3 text-xs">{mod.level_label}</span>
                  )}
                  <span className="font-serif text-ink-3 text-xs">
                    {new Date(mod.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <span className="text-ink-3 ml-3 shrink-0">→</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
