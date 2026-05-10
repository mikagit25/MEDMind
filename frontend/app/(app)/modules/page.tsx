"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import Link from "next/link";
import { contentApi, progressApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

// ── Types ──────────────────────────────────────────────────────────────────────
type Module = {
  id: string;
  title: string;
  description?: string;
  specialty_name?: string;
  is_fundamental: boolean;
  lesson_count: number;
  flashcard_count: number;
  mcq_count: number;
  duration_hours?: number;
  level_label?: string;
};

type ModuleProgress = {
  module_id: string;
  module_title: string;
  completion_percent: number;
  lessons_completed: number;
  last_activity_at?: string;
};

const LEVEL_COLORS: Record<string, string> = {
  beginner:     "bg-green-light text-green",
  intermediate: "bg-blue-light text-blue",
  advanced:     "bg-amber-light text-amber",
};

function ProgressRing({ pct }: { pct: number }) {
  const r = 16, c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  return (
    <svg width={40} height={40} className="flex-shrink-0 -rotate-90">
      <circle cx={20} cy={20} r={r} fill="none" stroke="var(--color-border)" strokeWidth={4} />
      <circle cx={20} cy={20} r={r} fill="none" stroke="var(--color-ink)" strokeWidth={4}
        strokeDasharray={`${dash} ${c}`} strokeLinecap="round" />
      <text x={20} y={20} className="fill-ink font-syne font-bold" fontSize={9}
        textAnchor="middle" dominantBaseline="central" style={{ transform: "rotate(90deg)", transformOrigin: "20px 20px" }}>
        {Math.round(pct)}%
      </text>
    </svg>
  );
}

function ModuleCard({
  mod,
  progress,
}: {
  mod: Module;
  progress?: ModuleProgress;
}) {
  const pct = progress?.completion_percent ?? 0;

  return (
    <Link
      href={`/modules/${mod.id}`}
      className="card group flex flex-col gap-3 p-4 hover:border-ink hover:shadow-md transition-all"
    >
      {/* Top row */}
      <div className="flex items-start gap-3">
        {progress && <ProgressRing pct={pct} />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {mod.specialty_name && (
              <span className="font-syne text-[10px] font-semibold text-ink-3 uppercase tracking-wide truncate max-w-[140px]">
                {mod.specialty_name}
              </span>
            )}
            {mod.is_fundamental && (
              <span className="badge bg-green-light text-green text-[10px]">Free</span>
            )}
            {mod.level_label && (
              <span className={`badge text-[10px] ${LEVEL_COLORS[mod.level_label] ?? "bg-surface-2 text-ink-3"}`}>
                {mod.level_label}
              </span>
            )}
          </div>
          <h3 className="font-syne font-bold text-sm text-ink leading-snug group-hover:text-accent transition-colors line-clamp-2">
            {mod.title}
          </h3>
          {mod.description && (
            <p className="font-serif text-[11px] text-ink-3 mt-1 line-clamp-2 leading-relaxed">
              {mod.description}
            </p>
          )}
        </div>
      </div>

      {/* Progress bar (if in progress) */}
      {progress && pct > 0 && (
        <div className="w-full h-1.5 bg-border-2 rounded-full overflow-hidden">
          <div className="h-full bg-ink rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
      )}

      {/* Stats row */}
      <div className="flex items-center gap-3 text-[11px] font-syne text-ink-3">
        {mod.lesson_count > 0 && <span>📖 {mod.lesson_count}</span>}
        {mod.flashcard_count > 0 && <span>🃏 {mod.flashcard_count}</span>}
        {mod.mcq_count > 0 && <span>❓ {mod.mcq_count}</span>}
        <span className="ml-auto text-[10px] font-semibold text-accent group-hover:underline">
          {progress ? (pct >= 100 ? "Review →" : "Continue →") : "Start →"}
        </span>
      </div>
    </Link>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
function ModulesInner() {
  const { user } = useAuthStore();
  const t = useT();

  const [allModules, setAllModules]     = useState<Module[]>([]);
  const [myProgress, setMyProgress]     = useState<ModuleProgress[]>([]);
  const [loading, setLoading]           = useState(true);
  const [activeSpecialty, setActiveSpecialty] = useState<string>("all");
  const [searchQ, setSearchQ]           = useState("");
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [searchResults, setSearchResults] = useState<Module[] | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);

  // Load all modules + user progress in parallel on mount
  useEffect(() => {
    setLoading(true);
    Promise.all([
      contentApi.getAllModules({ vet: false }),
      progressApi.getModulesProgress().catch(() => []),
    ]).then(([mods, prog]) => {
      setAllModules(mods ?? []);
      setMyProgress(prog ?? []);
    }).finally(() => setLoading(false));
  }, []);

  // Debounced search
  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!searchQ.trim()) { setSearchResults(null); return; }
    searchTimer.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await contentApi.getAllModules({ search: searchQ.trim(), vet: false });
        setSearchResults(res ?? []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 350);
  }, [searchQ]);

  // Build data structures
  const progressMap = new Map(myProgress.map(p => [p.module_id, p]));
  const inProgressModules = allModules.filter(m => {
    const p = progressMap.get(m.id);
    return p && p.completion_percent > 0 && p.completion_percent < 100;
  }).sort((a, b) => {
    const pa = progressMap.get(a.id)?.last_activity_at ?? "";
    const pb = progressMap.get(b.id)?.last_activity_at ?? "";
    return pb.localeCompare(pa);
  });
  const completedModules = allModules.filter(m => (progressMap.get(m.id)?.completion_percent ?? 0) >= 100);

  // Build specialty list from modules
  const specialties = Array.from(
    new Map(
      allModules
        .filter(m => m.specialty_name)
        .map(m => [m.specialty_name!, m.specialty_name!])
    ).entries()
  ).sort((a, b) => a[0].localeCompare(b[0], "ru"));

  // Filter modules for browse section
  const browseMods = allModules.filter(m => {
    if (activeSpecialty === "all") return true;
    if (activeSpecialty === "free") return m.is_fundamental;
    return m.specialty_name === activeSpecialty;
  });

  const isSearching = searchQ.trim().length >= 2;
  const displayMods = isSearching ? (searchResults ?? []) : browseMods;

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="card h-32 animate-pulse bg-surface-2" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-3 sm:px-6 py-4 sm:py-6">

        {/* Header */}
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <h1 className="font-syne font-black text-xl sm:text-2xl text-ink">
              {t("modules.title") || "Learning Modules"}
            </h1>
            <p className="font-serif text-xs text-ink-3 mt-0.5">
              {allModules.length} {t("modules.modules_available") || "modules available"}
              {inProgressModules.length > 0 && ` · ${inProgressModules.length} in progress`}
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-5">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none text-sm">🔍</span>
          <input
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            placeholder={t("modules.search_placeholder") || "Search modules…"}
            className="w-full bg-surface border border-border rounded-xl pl-9 pr-9 py-2.5 text-ink text-sm font-serif focus:outline-none focus:border-ink transition-colors"
          />
          {searchQ && (
            <button onClick={() => setSearchQ("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">✕</button>
          )}
        </div>

        {/* Search results */}
        {isSearching ? (
          <div>
            {searchLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1,2,3].map(i => <div key={i} className="card h-28 animate-pulse bg-surface-2" />)}
              </div>
            ) : displayMods.length === 0 ? (
              <div className="text-center py-16 text-ink-3 font-serif text-sm">
                {t("modules.no_results") || `No modules found for "${searchQ}"`}
              </div>
            ) : (
              <>
                <p className="font-syne text-xs text-ink-3 mb-3">
                  {displayMods.length} result{displayMods.length !== 1 ? "s" : ""} for «{searchQ}»
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {displayMods.map(m => (
                    <ModuleCard key={m.id} mod={m} progress={progressMap.get(m.id)} />
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <>
            {/* ── Section: In Progress ──────────────────────────── */}
            {inProgressModules.length > 0 && (
              <section className="mb-7">
                <h2 className="font-syne font-bold text-base text-ink mb-3 flex items-center gap-2">
                  <span>▶️</span>
                  {t("modules.in_progress") || "Continue learning"}
                  <span className="font-normal text-ink-3 text-xs">({inProgressModules.length})</span>
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {inProgressModules.map(m => (
                    <ModuleCard key={m.id} mod={m} progress={progressMap.get(m.id)} />
                  ))}
                </div>
              </section>
            )}

            {/* ── Section: Completed ───────────────────────────── */}
            {completedModules.length > 0 && (
              <section className="mb-7">
                <h2 className="font-syne font-bold text-base text-ink mb-3 flex items-center gap-2">
                  <span>✅</span>
                  {t("modules.completed") || "Completed"}
                  <span className="font-normal text-ink-3 text-xs">({completedModules.length})</span>
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {completedModules.map(m => (
                    <ModuleCard key={m.id} mod={m} progress={progressMap.get(m.id)} />
                  ))}
                </div>
              </section>
            )}

            {/* ── Section: Browse / Recommended ────────────────── */}
            <section>
              <h2 className="font-syne font-bold text-base text-ink mb-3 flex items-center gap-2">
                <span>📚</span>
                {inProgressModules.length > 0 || completedModules.length > 0
                  ? (t("modules.all_modules") || "All modules")
                  : (t("modules.recommended") || "Recommended modules")}
              </h2>

              {/* Specialty filter pills */}
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  onClick={() => setActiveSpecialty("all")}
                  className={`px-3 py-1.5 rounded-full font-syne text-xs font-semibold border transition-colors ${
                    activeSpecialty === "all"
                      ? "bg-ink text-white border-ink"
                      : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
                  }`}
                >
                  {t("modules.all") || "All"}
                  <span className="ml-1 opacity-60">{allModules.length}</span>
                </button>
                <button
                  onClick={() => setActiveSpecialty("free")}
                  className={`px-3 py-1.5 rounded-full font-syne text-xs font-semibold border transition-colors ${
                    activeSpecialty === "free"
                      ? "bg-green text-white border-green"
                      : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
                  }`}
                >
                  ✓ Free
                </button>
                {specialties.map(([name]) => (
                  <button
                    key={name}
                    onClick={() => setActiveSpecialty(name)}
                    className={`px-3 py-1.5 rounded-full font-syne text-xs font-semibold border transition-colors ${
                      activeSpecialty === name
                        ? "bg-ink text-white border-ink"
                        : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
                    }`}
                  >
                    {name}
                  </button>
                ))}
              </div>

              {/* Module grid */}
              {browseMods.length === 0 ? (
                <div className="text-center py-12 text-ink-3 font-serif text-sm">
                  {t("modules.no_modules") || "No modules in this specialty yet"}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {browseMods.map(m => (
                    <ModuleCard key={m.id} mod={m} progress={progressMap.get(m.id)} />
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

export default function ModulesPage() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex items-center justify-center">
        <span className="font-serif text-ink-3 text-sm animate-pulse">Loading modules…</span>
      </div>
    }>
      <ModulesInner />
    </Suspense>
  );
}
