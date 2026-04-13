"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { teacherApi } from "@/lib/api";
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

const STATUS_BADGE: Record<string, string> = {
  true: "bg-green-100 text-green-700 border-green-200",
  false: "bg-amber-100 text-amber-700 border-amber-200",
};

export default function TeacherModulesPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user && user.role !== "teacher" && user.role !== "admin") {
      router.replace("/dashboard");
      return;
    }
    teacherApi.listMyModules()
      .then(setModules)
      .catch(() => setError("Failed to load modules"))
      .finally(() => setLoading(false));
  }, [user, router]);

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
        <Link
          href="/teacher/modules/new"
          className="btn-primary text-sm px-4 py-2 rounded-lg font-syne font-semibold"
        >
          + New Module
        </Link>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">
          {error}
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
                  <span
                    className={`text-xs border rounded px-1.5 py-0.5 font-syne shrink-0 ${STATUS_BADGE[String(mod.is_published)]}`}
                  >
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
