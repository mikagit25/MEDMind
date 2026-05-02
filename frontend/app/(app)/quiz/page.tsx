"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { contentApi, progressApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

type Specialty = { id: string; name: string; module_count: number };
type Module = { id: string; title: string; code: string; lesson_count?: number; mcq_count?: number };
type ModuleProgress = {
  module_id: string;
  module_title: string;
  mcq_attempts: number;
  mcq_score: number;
  completion_percent: number;
};

export default function QuizListPage() {
  const t = useT();
  const router = useRouter();
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState("");
  const [modules, setModules] = useState<Module[]>([]);
  const [progress, setProgress] = useState<Record<string, ModuleProgress>>({});
  const [search, setSearch] = useState("");
  const [loadingModules, setLoadingModules] = useState(false);
  const [tab, setTab] = useState<"browse" | "history">("browse");

  // Load specialties + progress on mount
  useEffect(() => {
    contentApi.getSpecialties().then((data: any) => {
      setSpecialties(data ?? []);
    }).catch(() => {});

    progressApi.getModulesProgress?.().then((data: any) => {
      const map: Record<string, ModuleProgress> = {};
      for (const p of (data ?? [])) {
        if (p.mcq_attempts > 0) map[p.module_id] = p;
      }
      setProgress(map);
    }).catch(() => {});
  }, []);

  // Load modules when specialty changes
  useEffect(() => {
    if (!selectedSpecialty) { setModules([]); return; }
    setLoadingModules(true);
    contentApi.getModules(selectedSpecialty).then((data: any) => {
      setModules(data ?? []);
    }).catch(() => setModules([])).finally(() => setLoadingModules(false));
  }, [selectedSpecialty]);

  const filtered = modules.filter((m) =>
    !search || m.title.toLowerCase().includes(search.toLowerCase()) || m.code?.toLowerCase().includes(search.toLowerCase())
  );

  const historyModules = Object.values(progress).sort((a, b) => b.mcq_attempts - a.mcq_attempts);

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
      <h1 className="font-syne font-black text-2xl text-ink mb-1">{t("quiz.title")}</h1>
      <p className="font-serif text-ink-3 text-sm mb-6">{t("quiz.subtitle")}</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-bg-2 p-1 rounded-lg w-fit">
        {(["browse", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded font-syne font-semibold text-sm transition-all capitalize ${
              tab === t ? "bg-white shadow text-ink" : "text-ink-3 hover:text-ink"
            }`}
          >
            {t === "browse" ? "Browse Quizzes" : `History${historyModules.length ? ` (${historyModules.length})` : ""}`}
          </button>
        ))}
      </div>

      {tab === "browse" && (
        <div className="space-y-5">
          {/* AI Quick Quiz */}
          <AIQuizCard />

          {/* Specialty selector */}
          <div>
            <h2 className="font-syne font-bold text-sm text-ink mb-3">Quiz by Module</h2>
            <div className="flex flex-wrap gap-2 mb-4">
              {specialties.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedSpecialty(s.id === selectedSpecialty ? "" : s.id)}
                  className={`px-3 py-1.5 rounded-full font-syne font-semibold text-xs transition-all border ${
                    selectedSpecialty === s.id
                      ? "bg-ink text-white border-ink"
                      : "border-border text-ink-3 hover:border-ink hover:text-ink"
                  }`}
                >
                  {s.name}
                </button>
              ))}
            </div>

            {selectedSpecialty && (
              <>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter modules…"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink mb-3"
                />
                {loadingModules ? (
                  <p className="text-center font-serif text-ink-3 text-sm py-8">Loading modules…</p>
                ) : (
                  <div className="grid gap-2">
                    {filtered.map((m) => {
                      const p = progress[m.id];
                      return (
                        <ModuleQuizCard
                          key={m.id}
                          module={m}
                          progress={p}
                          onStart={() => router.push(`/quiz/${m.id}`)}
                        />
                      );
                    })}
                    {filtered.length === 0 && !loadingModules && (
                      <p className="text-center font-serif text-ink-3 text-sm py-6">No modules found.</p>
                    )}
                  </div>
                )}
              </>
            )}

            {!selectedSpecialty && (
              <p className="text-center font-serif text-ink-3 text-sm py-8">
                Select a specialty to browse available quizzes.
              </p>
            )}
          </div>
        </div>
      )}

      {tab === "history" && (
        <div className="space-y-3">
          {historyModules.length === 0 ? (
            <div className="card p-10 text-center">
              <div className="text-4xl mb-3">📝</div>
              <p className="font-syne font-bold text-sm text-ink">No quiz history yet</p>
              <p className="font-serif text-ink-3 text-xs mt-1">Complete a quiz to see your results here</p>
              <button
                onClick={() => setTab("browse")}
                className="btn-primary mt-4 text-sm"
              >
                Browse Quizzes
              </button>
            </div>
          ) : (
            <>
              <HistorySummary history={historyModules} />
              {historyModules.map((p) => (
                <HistoryCard
                  key={p.module_id}
                  entry={p}
                  onRetry={() => router.push(`/quiz/${p.module_id}`)}
                />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── AI Quick Quiz Card ────────────────────────────────────────────────────────

function AIQuizCard() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);

  const start = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      // Use AI quiz endpoint — generates questions on the fly
      router.push(`/ai-tutor?mode=quiz&topic=${encodeURIComponent(topic)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-5 border-2 border-dashed border-border">
      <div className="flex items-start gap-3">
        <span className="text-2xl">✨</span>
        <div className="flex-1">
          <div className="font-syne font-bold text-sm text-ink mb-1">AI Quick Quiz</div>
          <p className="font-serif text-ink-3 text-xs mb-3">
            Generate a custom quiz on any topic using AI
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && start()}
              placeholder="e.g. Heart failure, Antibiotics, Diabetes…"
              className="flex-1 px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink"
            />
            <button
              onClick={start}
              disabled={!topic.trim() || loading}
              className="btn-primary text-sm disabled:opacity-40"
            >
              {loading ? "…" : "Start"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Module Quiz Card ──────────────────────────────────────────────────────────

function ModuleQuizCard({
  module,
  progress,
  onStart,
}: {
  module: Module;
  progress?: ModuleProgress;
  onStart: () => void;
}) {
  const hasHistory = progress && progress.mcq_attempts > 0;
  const score = hasHistory ? Math.round(progress.mcq_score) : null;
  const scoreColor = score === null ? "" : score >= 80 ? "text-green" : score >= 60 ? "text-amber" : "text-red";

  return (
    <div className="card p-4 flex items-center gap-4">
      <div className="flex-1 min-w-0">
        <div className="font-syne font-bold text-sm text-ink truncate">{module.title}</div>
        <div className="font-serif text-ink-3 text-xs mt-0.5">{module.code}</div>
        {hasHistory && (
          <div className="flex items-center gap-3 mt-1.5">
            <span className={`font-syne font-bold text-xs ${scoreColor}`}>
              Best: {score}%
            </span>
            <span className="font-serif text-ink-3 text-xs">
              {progress.mcq_attempts} attempt{progress.mcq_attempts !== 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>
      <button
        onClick={onStart}
        className="btn-primary text-xs flex-shrink-0"
      >
        {hasHistory ? "Retry" : "Start Quiz"}
      </button>
    </div>
  );
}

// ── History Summary ───────────────────────────────────────────────────────────

function HistorySummary({ history }: { history: ModuleProgress[] }) {
  const totalAttempts = history.reduce((s, p) => s + p.mcq_attempts, 0);
  const avgScore = history.length
    ? Math.round(history.reduce((s, p) => s + p.mcq_score, 0) / history.length)
    : 0;
  const passed = history.filter((p) => p.mcq_score >= 80).length;

  return (
    <div className="grid grid-cols-3 gap-3 mb-2">
      <StatCard label="Total Attempts" value={String(totalAttempts)} />
      <StatCard label="Avg Score" value={`${avgScore}%`} color={avgScore >= 80 ? "text-green" : avgScore >= 60 ? "text-amber" : "text-red"} />
      <StatCard label="Passed (≥80%)" value={`${passed}/${history.length}`} />
    </div>
  );
}

function StatCard({ label, value, color = "text-ink" }: { label: string; value: string; color?: string }) {
  return (
    <div className="card p-3 text-center">
      <div className={`font-syne font-black text-xl ${color}`}>{value}</div>
      <div className="font-serif text-ink-3 text-xs mt-0.5">{label}</div>
    </div>
  );
}

// ── History Card ──────────────────────────────────────────────────────────────

function HistoryCard({ entry, onRetry }: { entry: ModuleProgress; onRetry: () => void }) {
  const score = Math.round(entry.mcq_score);
  const scoreColor = score >= 80 ? "text-green" : score >= 60 ? "text-amber" : "text-red";
  const scoreBg = score >= 80 ? "bg-green-light" : score >= 60 ? "bg-amber-light" : "bg-red-light";
  const grade = score >= 90 ? "A" : score >= 80 ? "B" : score >= 70 ? "C" : score >= 60 ? "D" : "F";

  return (
    <div className="card p-4 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg ${scoreBg} flex items-center justify-center flex-shrink-0`}>
        <span className={`font-syne font-black text-lg ${scoreColor}`}>{grade}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-syne font-bold text-sm text-ink truncate">{entry.module_title}</div>
        <div className="flex items-center gap-3 mt-1">
          <span className={`font-syne font-bold text-xs ${scoreColor}`}>{score}%</span>
          <span className="font-serif text-ink-3 text-xs">
            {entry.mcq_attempts} attempt{entry.mcq_attempts !== 1 ? "s" : ""}
          </span>
          {entry.completion_percent >= 100 && (
            <span className="font-serif text-green text-xs">✓ Module complete</span>
          )}
        </div>
        {/* Score bar */}
        <div className="mt-2 h-1.5 bg-bg-2 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${score >= 80 ? "bg-green" : score >= 60 ? "bg-amber" : "bg-red"}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>
      <button onClick={onRetry} className="text-ink-3 hover:text-ink font-syne text-xs flex-shrink-0">
        Retry →
      </button>
    </div>
  );
}
