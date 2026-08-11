"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuthStore } from "@/lib/store";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

type HealthSummary = {
  total_active: number;
  calibrated: number;
  calibration_pct: number;
  health_distribution: Record<string, number>;
  avg_discrimination: number | null;
};

type QuestionItem = {
  id: string;
  question: string;
  correct: string;
  difficulty: string;
  status: string;
  is_flagged: boolean;
  flag_reason: string | null;
  pending_regeneration: boolean;
  stats: {
    attempts: number;
    p_value: number | null;
    discrimination: number | null;
    computed_difficulty: string | null;
    avg_time_seconds: number | null;
    health: string;
    sample_size_ok: boolean;
    option_distribution: Record<string, number> | null;
  } | null;
};

type QuestionDetail = QuestionItem & {
  options: Record<string, string>;
  key_takeaway: string | null;
  rationales: Record<string, { text: string; why: string }> | null;
  verification_status: string;
  audit_log: Array<{
    action: string;
    note: string | null;
    before: Record<string, unknown>;
    after: Record<string, unknown>;
    created_at: string;
  }>;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const HEALTH_LABELS: Record<string, { label: string; color: string }> = {
  ok: { label: "OK", color: "bg-emerald-100 text-emerald-800" },
  review_low_p: { label: "Low P-value", color: "bg-orange-100 text-orange-800" },
  review_high_p: { label: "Too Easy", color: "bg-yellow-100 text-yellow-700" },
  review_low_discrimination: { label: "Low Discrimination", color: "bg-red-100 text-red-800" },
  review_dead_distractor: { label: "Dead Distractor", color: "bg-purple-100 text-purple-800" },
  review_key_suspect: { label: "Key Suspect ⚠️", color: "bg-red-200 text-red-900" },
};

function HealthBadge({ health }: { health: string }) {
  const { label, color } = HEALTH_LABELS[health] ?? { label: health, color: "bg-gray-100 text-gray-700" };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>{label}</span>;
}

function OptionBar({ opt, count, total, isCorrect }: { opt: string; count: number; total: number; isCorrect: boolean }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={`w-6 font-bold ${isCorrect ? "text-emerald-600" : "text-gray-500"}`}>{opt}</span>
      <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
        <div
          className={`h-full rounded ${isCorrect ? "bg-emerald-400" : "bg-blue-300"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-12 text-right text-gray-600">{count} ({pct}%)</span>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function QuestionHealthPage() {
  const { accessToken: token, user } = useAuthStore();
  const [summary, setSummary] = useState<HealthSummary | null>(null);
  const [queue, setQueue] = useState<QuestionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filterHealth, setFilterHealth] = useState("");
  const [detail, setDetail] = useState<QuestionDetail | null>(null);
  const [actionInFlight, setActionInFlight] = useState(false);
  const [actionNote, setActionNote] = useState("");
  const [newCorrect, setNewCorrect] = useState("");
  const [psychRunning, setPsychRunning] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const loadSummary = useCallback(async () => {
    const res = await api.get("/admin/question-health/summary");
    setSummary(res.data);
  }, []);

  const loadQueue = useCallback(async (p = 1, health = "") => {
    const params = new URLSearchParams({ page: String(p), per_page: "25" });
    if (health) params.append("health", health);
    const res = await api.get(`/admin/question-health/queue?${params}`);
    setQueue(res.data.items);
    setTotal(res.data.total);
    setPage(p);
  }, []);

  useEffect(() => {
    if (user?.role !== "admin") return;
    loadSummary();
    loadQueue();
  }, [user, loadSummary, loadQueue]);

  const openDetail = async (qid: string) => {
    const res = await api.get(`/admin/question-health/${qid}`);
    setDetail(res.data);
    setActionNote("");
    setNewCorrect("");
  };

  const doAction = async (action: string) => {
    if (!detail) return;
    setActionInFlight(true);
    try {
      await api.post(`/admin/question-health/${detail.id}/action`, {
        action,
        new_correct: action === "fix_key" ? newCorrect : undefined,
        note: actionNote || undefined,
      });
      showToast(`Action "${action}" applied.`);
      setDetail(null);
      await loadSummary();
      await loadQueue(page, filterHealth);
    } catch (e: any) {
      showToast(`Error: ${e?.response?.data?.detail ?? e.message}`);
    } finally {
      setActionInFlight(false);
    }
  };

  const runPsychometrics = async () => {
    setPsychRunning(true);
    try {
      const res = await api.post("/admin/question-health/run-psychometrics");
      showToast(`Psychometrics done: ${res.data.computed} computed`);
      await loadSummary();
      await loadQueue(1, filterHealth);
    } catch (e: any) {
      showToast(`Error: ${e?.response?.data?.detail ?? e.message}`);
    } finally {
      setPsychRunning(false);
    }
  };

  if (user?.role !== "admin") {
    return <div className="p-8 text-gray-500">Admin access required.</div>;
  }

  const PER_PAGE = 25;
  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          {toast}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Question Bank Health</h1>
          <p className="text-sm text-gray-500 mt-1">
            Psychometric quality — review flagged questions before they affect more students.
          </p>
        </div>
        <button
          onClick={runPsychometrics}
          disabled={psychRunning}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {psychRunning ? "Computing…" : "Run Psychometrics Now"}
        </button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-gray-900">{summary.total_active.toLocaleString()}</div>
            <div className="text-sm text-gray-500">Active Questions</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-indigo-600">{summary.calibrated.toLocaleString()}</div>
            <div className="text-sm text-gray-500">Calibrated ({summary.calibration_pct}%)</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className={`text-2xl font-bold ${(summary.avg_discrimination ?? 0) >= 0.3 ? "text-emerald-600" : (summary.avg_discrimination ?? 0) >= 0.15 ? "text-yellow-600" : "text-red-600"}`}>
              {summary.avg_discrimination?.toFixed(2) ?? "–"}
            </div>
            <div className="text-sm text-gray-500">Avg Discrimination</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-red-600">
              {(summary.health_distribution["review_key_suspect"] ?? 0) + (summary.health_distribution["review_low_discrimination"] ?? 0)}
            </div>
            <div className="text-sm text-gray-500">Critical Flags</div>
          </div>
        </div>
      )}

      {/* Health filter chips */}
      <div className="flex flex-wrap gap-2">
        {["", "review_key_suspect", "review_low_discrimination", "review_low_p", "review_high_p", "review_dead_distractor"].map((h) => (
          <button
            key={h}
            onClick={() => { setFilterHealth(h); loadQueue(1, h); }}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${filterHealth === h ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200 hover:border-indigo-400"}`}
          >
            {h === "" ? "All Issues" : (HEALTH_LABELS[h]?.label ?? h)}
            {h !== "" && summary?.health_distribution[h] ? ` (${summary.health_distribution[h]})` : ""}
          </button>
        ))}
      </div>

      {/* Queue table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Question</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600 w-32">Health</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 w-20">Attempts</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 w-20">P-value</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600 w-24">Discrim.</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {queue.map((q) => (
              <tr
                key={q.id}
                onClick={() => openDetail(q.id)}
                className="hover:bg-indigo-50 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900 truncate max-w-lg">{q.question}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {q.difficulty} · correct: {q.correct}
                    {q.is_flagged && <span className="ml-2 text-orange-500">🏴 flagged</span>}
                    {q.pending_regeneration && <span className="ml-2 text-purple-500">⚙ regen</span>}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <HealthBadge health={q.stats?.health ?? "ok"} />
                </td>
                <td className="px-4 py-3 text-right text-gray-700">{q.stats?.attempts ?? 0}</td>
                <td className="px-4 py-3 text-right text-gray-700">
                  {q.stats?.p_value != null ? (q.stats.p_value * 100).toFixed(0) + "%" : "–"}
                </td>
                <td className={`px-4 py-3 text-right font-medium ${(q.stats?.discrimination ?? 1) < 0 ? "text-red-600" : "text-gray-700"}`}>
                  {q.stats?.discrimination != null ? q.stats.discrimination.toFixed(2) : "–"}
                </td>
              </tr>
            ))}
            {queue.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                  No questions in this queue.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t text-sm text-gray-500">
            <span>{total} total</span>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => loadQueue(page - 1, filterHealth)}
                className="px-3 py-1 rounded border disabled:opacity-40 hover:bg-gray-50">← Prev</button>
              <span className="px-2 py-1">{page} / {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => loadQueue(page + 1, filterHealth)}
                className="px-3 py-1 rounded border disabled:opacity-40 hover:bg-gray-50">Next →</button>
            </div>
          </div>
        )}
      </div>

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b flex items-start justify-between">
              <div className="flex-1 pr-4">
                <div className="flex items-center gap-2 mb-1">
                  <HealthBadge health={detail.stats?.health ?? "ok"} />
                  <span className="text-xs text-gray-400">
                    {detail.stats?.attempts ?? 0} attempts · disc {detail.stats?.discrimination?.toFixed(2) ?? "–"}
                  </span>
                </div>
                <p className="font-medium text-gray-900">{detail.question}</p>
              </div>
              <button onClick={() => setDetail(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
            </div>

            <div className="p-6 space-y-5">
              {/* Options + distribution */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-gray-700">Options &amp; Selection Rate</h3>
                {detail.options && Object.entries(detail.options).map(([opt, text]) => (
                  <div key={opt} className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`font-bold text-sm ${opt === detail.correct ? "text-emerald-600" : "text-gray-500"}`}>
                        {opt}{opt === detail.correct ? " ✓" : ""}
                      </span>
                      <span className="text-sm text-gray-800">{text}</span>
                    </div>
                    {detail.stats?.option_distribution && (
                      <OptionBar
                        opt={opt}
                        count={detail.stats.option_distribution[opt] ?? 0}
                        total={detail.stats.attempts}
                        isCorrect={opt === detail.correct}
                      />
                    )}
                  </div>
                ))}
              </div>

              {/* Key takeaway */}
              {detail.key_takeaway && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-900">
                  <strong>Key Takeaway:</strong> {detail.key_takeaway}
                </div>
              )}

              {/* Psychometric stats */}
              {detail.stats && (
                <div className="grid grid-cols-3 gap-3 text-center">
                  {[
                    { label: "P-value", value: detail.stats.p_value != null ? (detail.stats.p_value * 100).toFixed(0) + "%" : "–" },
                    { label: "Discrimination", value: detail.stats.discrimination?.toFixed(2) ?? "–" },
                    { label: "Avg Time", value: detail.stats.avg_time_seconds ? `${detail.stats.avg_time_seconds.toFixed(0)}s` : "–" },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-gray-50 rounded-lg p-3">
                      <div className="text-lg font-bold text-gray-900">{value}</div>
                      <div className="text-xs text-gray-500">{label}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="border-t pt-4 space-y-3">
                <h3 className="text-sm font-semibold text-gray-700">Actions</h3>
                <textarea
                  value={actionNote}
                  onChange={(e) => setActionNote(e.target.value)}
                  placeholder="Optional note for audit log…"
                  className="w-full border rounded-lg px-3 py-2 text-sm resize-none h-16 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => doAction("approve")}
                    disabled={actionInFlight}
                    className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
                  >
                    ✓ Approve as Is
                  </button>
                  <button
                    onClick={() => doAction("retire")}
                    disabled={actionInFlight}
                    className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-300 disabled:opacity-50"
                  >
                    Retire Question
                  </button>
                  <div className="flex items-center gap-1">
                    <input
                      value={newCorrect}
                      onChange={(e) => setNewCorrect(e.target.value.toUpperCase())}
                      placeholder="B"
                      maxLength={1}
                      className="border rounded px-2 py-1 w-12 text-center text-sm"
                    />
                    <button
                      onClick={() => doAction("fix_key")}
                      disabled={actionInFlight || !newCorrect}
                      className="px-3 py-1.5 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50"
                    >
                      Fix Key
                    </button>
                  </div>
                  <button
                    onClick={() => doAction("send_regeneration")}
                    disabled={actionInFlight}
                    className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
                  >
                    Send to Regeneration
                  </button>
                </div>
              </div>

              {/* Audit log */}
              {detail.audit_log.length > 0 && (
                <div className="border-t pt-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Audit Log</h3>
                  <div className="space-y-1 text-xs text-gray-500">
                    {detail.audit_log.map((a, i) => (
                      <div key={i} className="flex gap-2">
                        <span className="text-gray-400">{new Date(a.created_at).toLocaleDateString()}</span>
                        <span className="font-medium text-gray-700">{a.action}</span>
                        {a.note && <span>— {a.note}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
