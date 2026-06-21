"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type QueueArticle = {
  id: string;
  slug: string;
  title: string;
  category: string;
  excerpt: string;
  verification_status: string;
  view_count: number;
  published_at: string | null;
  last_verified_at: string | null;
  reviewed_by: string | null;
};

type ArticleDetail = QueueArticle & {
  body: Record<string, unknown>[];
  sources: { title: string; url: string; pmid: string | null }[];
  faq: { question: string; answer: string }[];
  verification_report: Record<string, unknown> | string | null;
  review_note: string | null;
};

type QueueStats = {
  queue_depth: number;
  unresolved_feedback: number;
  human_reviewed_total: number;
};

export default function ReviewerQueuePage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  const [stats, setStats] = useState<QueueStats | null>(null);
  const [articles, setArticles] = useState<QueueArticle[]>([]);
  const [selected, setSelected] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectComment, setRejectComment] = useState("");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const PAGE_SIZE = 20;

  // Gate: only admin + reviewer
  useEffect(() => {
    if (user && user.role !== "admin" && user.role !== "reviewer") {
      router.replace("/dashboard");
    }
  }, [user, router]);

  const showToast = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const loadStats = useCallback(async () => {
    try {
      const data = await api.get("/admin/reviewer-queue/stats/summary").then(r => r.data);
      setStats(data);
    } catch {
      // non-fatal
    }
  }, []);

  const loadQueue = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const data = await api.get("/admin/reviewer-queue", { params: { page: p, page_size: PAGE_SIZE } }).then(r => r.data);
      setArticles(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch {
      showToast("Failed to load queue", false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadQueue(page);
  }, [loadStats, loadQueue, page]);

  const openDetail = async (article: QueueArticle) => {
    setDetailLoading(true);
    setSelected(null);
    try {
      const data = await api.get(`/admin/reviewer-queue/${article.id}`).then(r => r.data);
      setSelected(data);
    } catch {
      showToast("Failed to load article", false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!selected) return;
    setActionLoading(true);
    try {
      await api.post(`/admin/reviewer-queue/${selected.id}/approve`).then(r => r.data);
      showToast("Article approved — marked as human-reviewed");
      setSelected(null);
      loadStats();
      loadQueue(page);
    } catch {
      showToast("Approval failed", false);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestChanges = async () => {
    if (!selected || !rejectComment.trim()) return;
    setActionLoading(true);
    try {
      await api.post(`/admin/reviewer-queue/${selected.id}/request-changes`, { comment: rejectComment.trim() }).then(r => r.data);
      showToast("Changes requested — article hidden from public");
      setShowRejectModal(false);
      setRejectComment("");
      setSelected(null);
      loadStats();
      loadQueue(page);
    } catch {
      showToast("Request failed", false);
    } finally {
      setActionLoading(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="min-h-screen bg-bg p-6 lg:p-10">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl shadow-lg font-syne font-semibold text-sm ${toast.ok ? "bg-green text-white" : "bg-red text-white"}`}>
          {toast.msg}
        </div>
      )}

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-syne font-black text-2xl text-ink">Reviewer Queue</h1>
          <p className="font-serif text-ink-3 text-sm mt-1">
            Articles that passed AI verification and are awaiting specialist review
          </p>
        </div>

        {/* Stats bar */}
        {stats && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="font-syne font-black text-3xl text-amber">{stats.queue_depth}</div>
              <div className="font-syne text-xs text-ink-3 mt-1 uppercase tracking-wider">Awaiting Review</div>
            </div>
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="font-syne font-black text-3xl text-red">{stats.unresolved_feedback}</div>
              <div className="font-syne text-xs text-ink-3 mt-1 uppercase tracking-wider">Unresolved Feedback</div>
            </div>
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="font-syne font-black text-3xl text-green">{stats.human_reviewed_total}</div>
              <div className="font-syne text-xs text-ink-3 mt-1 uppercase tracking-wider">Human-Reviewed Total</div>
            </div>
          </div>
        )}

        <div className="flex gap-6">
          {/* Article list */}
          <div className="flex-1 min-w-0">
            {loading ? (
              <div className="text-center py-16 text-ink-3 font-serif">Loading queue…</div>
            ) : articles.length === 0 ? (
              <div className="text-center py-16 bg-surface border border-border rounded-xl">
                <div className="text-4xl mb-3">✅</div>
                <div className="font-syne font-bold text-ink">Queue is empty</div>
                <div className="font-serif text-sm text-ink-3 mt-1">No articles pending review</div>
              </div>
            ) : (
              <div className="space-y-2">
                {articles.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => openDetail(a)}
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      selected?.id === a.id
                        ? "border-ink bg-surface-2"
                        : "border-border bg-surface hover:border-ink hover:shadow-sm"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="font-syne font-semibold text-sm text-ink line-clamp-1">{a.title}</div>
                        <div className="font-serif text-xs text-ink-3 line-clamp-1 mt-0.5">{a.excerpt}</div>
                      </div>
                      <div className="flex flex-col items-end gap-1 flex-shrink-0">
                        <span className="text-[10px] font-syne font-semibold border border-border rounded-full px-2 py-0.5 text-ink-2 capitalize">
                          {a.category}
                        </span>
                        <span className="text-[10px] font-serif text-ink-3">{a.view_count.toLocaleString()} views</span>
                      </div>
                    </div>
                  </button>
                ))}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-3 pt-4">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="text-xs font-syne font-semibold px-3 py-1.5 border border-border rounded-lg disabled:opacity-40 hover:border-ink transition-colors"
                    >
                      ← Prev
                    </button>
                    <span className="text-xs font-serif text-ink-3">{page} / {totalPages}</span>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="text-xs font-syne font-semibold px-3 py-1.5 border border-border rounded-lg disabled:opacity-40 hover:border-ink transition-colors"
                    >
                      Next →
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Detail panel */}
          <div className="w-[480px] flex-shrink-0">
            {detailLoading ? (
              <div className="bg-surface border border-border rounded-xl p-8 text-center text-ink-3 font-serif">Loading…</div>
            ) : selected ? (
              <div className="bg-surface border border-border rounded-xl overflow-hidden sticky top-6">
                {/* Panel header */}
                <div className="p-5 border-b border-border">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h2 className="font-syne font-bold text-sm text-ink leading-snug line-clamp-2">{selected.title}</h2>
                    <button onClick={() => setSelected(null)} className="text-ink-3 hover:text-ink text-lg leading-none flex-shrink-0">×</button>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-syne font-semibold border border-border rounded-full px-2 py-0.5 text-ink-2 capitalize">{selected.category}</span>
                    <span className="text-[10px] font-serif text-ink-3">{selected.view_count.toLocaleString()} views</span>
                    {selected.last_verified_at && (
                      <span className="text-[10px] font-serif text-ink-3">
                        AI verified {new Date(selected.last_verified_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                      </span>
                    )}
                  </div>
                </div>

                {/* Verification report */}
                {selected.verification_report && (
                  <div className="p-4 border-b border-border bg-blue-50">
                    <div className="font-syne font-bold text-[10px] text-blue-700 uppercase tracking-wider mb-1">AI Verification Report</div>
                    <pre className="font-serif text-[10px] text-blue-800 whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto">
                      {typeof selected.verification_report === "string"
                        ? selected.verification_report
                        : JSON.stringify(selected.verification_report, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Prior review note */}
                {selected.review_note && (
                  <div className="p-4 border-b border-border bg-amber-light">
                    <div className="font-syne font-bold text-[10px] text-amber uppercase tracking-wider mb-1">Prior Review Note</div>
                    <p className="font-serif text-xs text-ink-2 leading-relaxed">{selected.review_note}</p>
                  </div>
                )}

                {/* Excerpt */}
                <div className="p-4 border-b border-border max-h-48 overflow-y-auto">
                  <div className="font-syne font-bold text-[10px] text-ink-3 uppercase tracking-wider mb-2">Excerpt</div>
                  <p className="font-serif text-xs text-ink-2 leading-relaxed">{selected.excerpt}</p>
                </div>

                {/* Sources */}
                {selected.sources?.length > 0 && (
                  <div className="p-4 border-b border-border">
                    <div className="font-syne font-bold text-[10px] text-ink-3 uppercase tracking-wider mb-2">References ({selected.sources.length})</div>
                    <ol className="space-y-1">
                      {selected.sources.slice(0, 5).map((s: any, i: number) => (
                        <li key={i} className="font-serif text-[10px] text-ink-3 leading-snug">
                          {i + 1}.{" "}
                          {s.url ? (
                            <a href={s.url} target="_blank" rel="noopener noreferrer" className="underline hover:text-ink">{s.title}</a>
                          ) : s.title}
                        </li>
                      ))}
                      {selected.sources.length > 5 && (
                        <li className="font-serif text-[10px] text-ink-3">+{selected.sources.length - 5} more</li>
                      )}
                    </ol>
                  </div>
                )}

                {/* Links */}
                <div className="p-4 border-b border-border flex gap-3">
                  <a
                    href={`/articles/${selected.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-syne font-semibold text-blue-600 hover:underline"
                  >
                    Preview article ↗
                  </a>
                </div>

                {/* Action buttons */}
                <div className="p-4 flex gap-3">
                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="flex-1 bg-green text-white font-syne font-bold text-sm py-2.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {actionLoading ? "…" : "✅ Approve"}
                  </button>
                  <button
                    onClick={() => setShowRejectModal(true)}
                    disabled={actionLoading}
                    className="flex-1 border border-red text-red font-syne font-bold text-sm py-2.5 rounded-lg hover:bg-red/5 transition-colors disabled:opacity-50"
                  >
                    Request Changes
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-surface border border-border rounded-xl p-8 text-center">
                <div className="text-3xl mb-3">📋</div>
                <div className="font-syne font-semibold text-sm text-ink-2">Select an article to review</div>
                <div className="font-serif text-xs text-ink-3 mt-1">Click any article in the list to open the review panel</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Request changes modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-bg rounded-2xl border border-border p-6 w-full max-w-md shadow-xl">
            <h3 className="font-syne font-bold text-base text-ink mb-2">Request Changes</h3>
            <p className="font-serif text-sm text-ink-3 mb-4">
              Describe what needs to be fixed. The article will be hidden from public until re-submitted.
            </p>
            <textarea
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              placeholder="Specific issues to address, factual errors, missing sources…"
              rows={5}
              className="w-full border border-border rounded-lg px-3 py-2.5 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => { setShowRejectModal(false); setRejectComment(""); }}
                className="flex-1 border border-border font-syne font-semibold text-sm py-2.5 rounded-lg hover:border-ink transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRequestChanges}
                disabled={actionLoading || !rejectComment.trim()}
                className="flex-1 bg-red text-white font-syne font-bold text-sm py-2.5 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {actionLoading ? "…" : "Send Feedback"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
