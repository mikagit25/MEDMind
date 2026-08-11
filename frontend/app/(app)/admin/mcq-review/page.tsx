"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type FlaggedQuestion = {
  id: string;
  question: string;
  options: Record<string, string>;
  correct: string;
  explanation: string;
  rationales: Record<string, string> | null;
  key_takeaway: string | null;
  difficulty: string;
  question_type: string;
  nclex_client_needs: string | null;
  exam_slugs: string[];
  flag_reason: string | null;
  verification_report: Record<string, unknown>;
  created_at: string | null;
};

const EXAM_LABELS: Record<string, string> = {
  snle: "SNLE (Saudi)",
  dha: "DHA (Dubai)",
  haad: "HAAD (Abu Dhabi)",
  qchp: "QCHP (Qatar)",
  omsb: "OMSB (Oman)",
  nhra: "NHRA (Bahrain)",
  mohuae: "MOH UAE",
  moh_kw: "MOH Kuwait",
};

export default function McqReviewPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  const [questions, setQuestions] = useState<FlaggedQuestion[]>([]);
  const [filtered, setFiltered] = useState<FlaggedQuestion[]>([]);
  const [selected, setSelected] = useState<FlaggedQuestion | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filterSlug, setFilterSlug] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [stats, setStats] = useState({ total: 0, approved: 0, retired: 0 });

  useEffect(() => {
    if (user && user.role !== "admin" && user.role !== "superadmin") {
      router.replace("/dashboard");
    }
  }, [user, router]);

  const showToast = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get("/exam/admin/ai-flagged-questions", { params: { limit: 500 } }).then(r => r.data);
      setQuestions(data.questions ?? []);
    } catch {
      showToast("Failed to load flagged questions", false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadQuestions(); }, [loadQuestions]);

  useEffect(() => {
    const f = filterSlug === "all"
      ? questions
      : questions.filter(q => q.exam_slugs.includes(filterSlug));
    setFiltered(f);
    setSelectedIds(new Set());
    setSelected(null);
  }, [filterSlug, questions]);

  const examCounts = Object.keys(EXAM_LABELS).reduce<Record<string, number>>((acc, slug) => {
    acc[slug] = questions.filter(q => q.exam_slugs.includes(slug)).length;
    return acc;
  }, {});

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map(q => q.id)));
    }
  };

  const handleSingleApprove = async (q: FlaggedQuestion) => {
    setActionLoading(true);
    try {
      await api.post(`/exam/admin/ai-flagged-questions/${q.id}/approve`);
      showToast(`Approved: ${q.question.slice(0, 60)}…`);
      setSelected(null);
      setStats(s => ({ ...s, approved: s.approved + 1 }));
      setQuestions(prev => prev.filter(x => x.id !== q.id));
    } catch {
      showToast("Approve failed", false);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSingleRetire = async (q: FlaggedQuestion) => {
    setActionLoading(true);
    try {
      await api.post(`/exam/admin/ai-flagged-questions/${q.id}/retire`);
      showToast(`Retired: ${q.question.slice(0, 60)}…`, true);
      setSelected(null);
      setStats(s => ({ ...s, retired: s.retired + 1 }));
      setQuestions(prev => prev.filter(x => x.id !== q.id));
    } catch {
      showToast("Retire failed", false);
    } finally {
      setActionLoading(false);
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    setActionLoading(true);
    try {
      const data = await api.post("/exam/admin/ai-flagged-questions/bulk-approve", {
        question_ids: Array.from(selectedIds),
      }).then(r => r.data);
      showToast(`Approved ${data.approved} questions`);
      setStats(s => ({ ...s, approved: s.approved + data.approved }));
      setQuestions(prev => prev.filter(q => !selectedIds.has(q.id)));
      setSelectedIds(new Set());
      setSelected(null);
    } catch {
      showToast("Bulk approve failed", false);
    } finally {
      setActionLoading(false);
    }
  };

  const difficultyColor = (d: string) => {
    if (d === "easy") return "text-green-2 border-green-2/30 bg-green-2/5";
    if (d === "hard") return "text-red border-red/30 bg-red/5";
    return "text-amber-600 border-amber-500/30 bg-amber-500/5";
  };

  return (
    <div className="min-h-screen bg-bg p-6 lg:p-10">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl shadow-lg font-syne font-semibold text-sm ${toast.ok ? "bg-green-2 text-white" : "bg-red text-white"}`}>
          {toast.msg}
        </div>
      )}

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="font-syne font-black text-2xl text-ink">MCQ Review — AI-Flagged</h1>
            <p className="font-serif text-ink-3 text-sm mt-1">
              Questions flagged by AI verification pipeline as clinical edge cases — review and approve or retire.
            </p>
          </div>
          <div className="flex gap-3 text-center">
            <div className="bg-surface border border-border rounded-xl px-4 py-2.5">
              <div className="font-syne font-black text-xl text-amber-600">{filtered.length}</div>
              <div className="font-syne text-[10px] text-ink-3 uppercase tracking-wider">Pending</div>
            </div>
            <div className="bg-surface border border-green-2/30 rounded-xl px-4 py-2.5">
              <div className="font-syne font-black text-xl text-green-2">{stats.approved}</div>
              <div className="font-syne text-[10px] text-ink-3 uppercase tracking-wider">Approved</div>
            </div>
            <div className="bg-surface border border-red/30 rounded-xl px-4 py-2.5">
              <div className="font-syne font-black text-xl text-red">{stats.retired}</div>
              <div className="font-syne text-[10px] text-ink-3 uppercase tracking-wider">Retired</div>
            </div>
          </div>
        </div>

        {/* Exam filter tabs */}
        <div className="flex flex-wrap gap-2 mb-5">
          <button
            onClick={() => setFilterSlug("all")}
            className={`text-xs font-syne font-semibold px-3 py-1.5 rounded-full border transition-colors ${filterSlug === "all" ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink"}`}
          >
            All exams ({questions.length})
          </button>
          {Object.entries(EXAM_LABELS).filter(([slug]) => examCounts[slug] > 0).map(([slug, label]) => (
            <button
              key={slug}
              onClick={() => setFilterSlug(slug)}
              className={`text-xs font-syne font-semibold px-3 py-1.5 rounded-full border transition-colors ${filterSlug === slug ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink"}`}
            >
              {label} ({examCounts[slug]})
            </button>
          ))}
        </div>

        {/* Bulk actions toolbar */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-4 mb-4 bg-ink/5 border border-ink/20 rounded-xl px-4 py-3">
            <span className="font-syne font-semibold text-sm text-ink">{selectedIds.size} selected</span>
            <button
              onClick={handleBulkApprove}
              disabled={actionLoading}
              className="bg-green-2 text-white font-syne font-bold text-sm px-4 py-2 rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              ✅ Bulk Approve ({selectedIds.size})
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="text-ink-3 hover:text-ink text-sm font-syne transition-colors"
            >
              Clear selection
            </button>
          </div>
        )}

        <div className="flex gap-6">
          {/* Question list */}
          <div className="flex-1 min-w-0">
            {loading ? (
              <div className="text-center py-16 text-ink-3 font-serif">Loading flagged questions…</div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-16 bg-surface border border-border rounded-xl">
                <div className="text-4xl mb-3">✅</div>
                <div className="font-syne font-bold text-ink">No flagged questions</div>
                <div className="font-serif text-sm text-ink-3 mt-1">
                  {filterSlug !== "all" ? "Try a different exam filter" : "All questions are verified"}
                </div>
              </div>
            ) : (
              <>
                {/* Select all row */}
                <div className="flex items-center gap-3 mb-2 px-1">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === filtered.length && filtered.length > 0}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 accent-ink cursor-pointer"
                  />
                  <span className="font-syne text-xs text-ink-3">Select all {filtered.length}</span>
                </div>

                <div className="space-y-2">
                  {filtered.map((q) => (
                    <div
                      key={q.id}
                      className={`flex items-start gap-3 p-4 rounded-xl border transition-all cursor-pointer ${
                        selected?.id === q.id
                          ? "border-ink bg-surface"
                          : "border-border bg-surface hover:border-ink/40"
                      } ${selectedIds.has(q.id) ? "ring-1 ring-ink/20" : ""}`}
                      onClick={() => setSelected(selected?.id === q.id ? null : q)}
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.has(q.id)}
                        onChange={(e) => { e.stopPropagation(); toggleSelect(q.id); }}
                        onClick={e => e.stopPropagation()}
                        className="w-4 h-4 accent-ink cursor-pointer mt-0.5 flex-shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-syne text-sm text-ink line-clamp-2 leading-snug">{q.question}</p>
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {q.exam_slugs.map(s => (
                            <span key={s} className="text-[10px] font-syne font-semibold px-2 py-0.5 rounded-full border border-amber-500/30 bg-amber-500/5 text-amber-700">
                              {EXAM_LABELS[s] ?? s}
                            </span>
                          ))}
                          <span className={`text-[10px] font-syne font-semibold px-2 py-0.5 rounded-full border ${difficultyColor(q.difficulty)}`}>
                            {q.difficulty}
                          </span>
                          <span className="text-[10px] font-syne text-ink-3 px-2 py-0.5 rounded-full border border-border">
                            {q.question_type}
                          </span>
                        </div>
                        {q.flag_reason && (
                          <p className="font-serif text-[10px] text-amber-700 mt-1 line-clamp-1">
                            ⚠ {typeof q.flag_reason === "string" ? q.flag_reason : JSON.stringify(q.flag_reason).slice(0, 120)}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-col gap-1 flex-shrink-0">
                        <button
                          onClick={e => { e.stopPropagation(); handleSingleApprove(q); }}
                          disabled={actionLoading}
                          className="text-[10px] font-syne font-bold px-2.5 py-1 rounded-lg bg-green-2/10 text-green-2 border border-green-2/30 hover:bg-green-2 hover:text-white transition-colors disabled:opacity-50"
                        >
                          ✅ OK
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); handleSingleRetire(q); }}
                          disabled={actionLoading}
                          className="text-[10px] font-syne font-bold px-2.5 py-1 rounded-lg bg-red/10 text-red border border-red/30 hover:bg-red hover:text-white transition-colors disabled:opacity-50"
                        >
                          🗑 Retire
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Detail panel */}
          <div className="w-[440px] flex-shrink-0">
            {selected ? (
              <div className="bg-surface border border-border rounded-xl overflow-hidden sticky top-6">
                <div className="p-4 border-b border-border flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <div className="flex flex-wrap gap-1 mb-2">
                      {selected.exam_slugs.map(s => (
                        <span key={s} className="text-[10px] font-syne font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-700 border border-amber-500/20">
                          {EXAM_LABELS[s] ?? s}
                        </span>
                      ))}
                    </div>
                    <p className="font-syne font-semibold text-sm text-ink leading-snug">{selected.question}</p>
                  </div>
                  <button onClick={() => setSelected(null)} className="text-ink-3 hover:text-ink text-xl leading-none flex-shrink-0 ml-1">×</button>
                </div>

                {/* Flag reason */}
                {selected.flag_reason && (
                  <div className="p-4 border-b border-border bg-amber-500/5">
                    <div className="font-syne font-bold text-[10px] text-amber-700 uppercase tracking-wider mb-1">AI Flag Reason</div>
                    <p className="font-serif text-xs text-amber-900 leading-relaxed">
                      {typeof selected.flag_reason === "string" ? selected.flag_reason : JSON.stringify(selected.flag_reason, null, 2)}
                    </p>
                  </div>
                )}

                {/* Options */}
                <div className="p-4 border-b border-border">
                  <div className="font-syne font-bold text-[10px] text-ink-3 uppercase tracking-wider mb-2">Options</div>
                  <div className="space-y-1.5">
                    {Object.entries(selected.options || {}).map(([k, v]) => (
                      <div
                        key={k}
                        className={`flex gap-2 p-2 rounded-lg text-xs font-serif ${k === selected.correct ? "bg-green-2/10 border border-green-2/30 text-green-2 font-semibold" : "text-ink-2"}`}
                      >
                        <span className="font-syne font-bold flex-shrink-0">{k}.</span>
                        <span>{String(v)}</span>
                        {k === selected.correct && <span className="ml-auto font-syne font-bold text-green-2">✓</span>}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Explanation */}
                {selected.explanation && (
                  <div className="p-4 border-b border-border">
                    <div className="font-syne font-bold text-[10px] text-ink-3 uppercase tracking-wider mb-2">Explanation</div>
                    <p className="font-serif text-xs text-ink-2 leading-relaxed">{selected.explanation}</p>
                  </div>
                )}

                {/* Key takeaway */}
                {selected.key_takeaway && (
                  <div className="p-4 border-b border-border">
                    <div className="font-syne font-bold text-[10px] text-ink-3 uppercase tracking-wider mb-1">Key Takeaway</div>
                    <p className="font-serif text-xs text-ink-2 italic">{selected.key_takeaway}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="p-4 flex gap-3">
                  <button
                    onClick={() => handleSingleApprove(selected)}
                    disabled={actionLoading}
                    className="flex-1 bg-green-2 text-white font-syne font-bold text-sm py-2.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {actionLoading ? "…" : "✅ Approve"}
                  </button>
                  <button
                    onClick={() => handleSingleRetire(selected)}
                    disabled={actionLoading}
                    className="flex-1 border border-red text-red font-syne font-bold text-sm py-2.5 rounded-lg hover:bg-red/5 transition-colors disabled:opacity-50"
                  >
                    🗑 Retire
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-surface border border-border rounded-xl p-8 text-center sticky top-6">
                <div className="text-3xl mb-3">🔍</div>
                <div className="font-syne font-semibold text-sm text-ink-2">Click a question to inspect it</div>
                <div className="font-serif text-xs text-ink-3 mt-1">See options, explanation, and flag reason</div>
                {filtered.length > 0 && (
                  <button
                    onClick={() => { setSelectedIds(new Set(filtered.map(q => q.id))); }}
                    className="mt-4 text-xs font-syne font-semibold text-ink-3 hover:text-ink transition-colors underline"
                  >
                    Select all {filtered.length} for bulk approve
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
