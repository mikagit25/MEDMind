"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useAuthStore } from "@/lib/store";

type TeacherNews = {
  id: string;
  slug: string;
  title: string;
  source_name: string;
  source_url: string;
  category: string;
  review_status: "draft" | "submitted" | "published" | "rejected";
  fetched_at: string;
  review_note: string | null;
};

const STATUS_STYLE: Record<string, string> = {
  draft:     "bg-surface-2 text-ink-3 border border-border",
  submitted: "bg-amber-100 text-amber-800 border border-amber-200",
  published: "bg-green-100 text-green-800 border border-green-200",
  rejected:  "bg-red-100 text-red-800 border border-red-200",
};
const STATUS_LABEL: Record<string, string> = {
  draft: "Draft", submitted: "Under review", published: "Published", rejected: "Rejected",
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export default function TeacherNewsPage() {
  const token = useAuthStore(s => s.token);
  const [news, setNews]     = useState<TeacherNews[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast]   = useState<{ msg: string; ok: boolean } | null>(null);
  const [busy, setBusy]     = useState<string | null>(null);

  const showToast = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/news/my`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setNews(await res.json());
    } catch { /* noop */ } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function submit(id: string) {
    setBusy(id);
    const res = await fetch(`${API}/news/my/${id}/submit`, {
      method: "POST", headers: { Authorization: `Bearer ${token}` },
    });
    setBusy(null);
    if (res.ok) { showToast("Submitted for review"); load(); }
    else showToast("Error submitting", false);
  }

  async function withdraw(id: string) {
    setBusy(id);
    const res = await fetch(`${API}/news/my/${id}/withdraw`, {
      method: "POST", headers: { Authorization: `Bearer ${token}` },
    });
    setBusy(null);
    if (res.ok) { showToast("Withdrawn to draft"); load(); }
    else showToast("Error", false);
  }

  async function del(id: string) {
    if (!confirm("Delete this news item?")) return;
    setBusy(id);
    const res = await fetch(`${API}/news/my/${id}`, {
      method: "DELETE", headers: { Authorization: `Bearer ${token}` },
    });
    setBusy(null);
    if (res.ok || res.status === 204) { showToast("Deleted"); load(); }
    else showToast("Error deleting", false);
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-lg font-syne font-semibold text-sm shadow-lg ${toast.ok ? "bg-green-600 text-white" : "bg-red-600 text-white"}`}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-syne font-extrabold text-2xl text-ink">My News Articles</h1>
          <p className="text-sm text-ink-2 mt-1">Contribute medical news — all items are reviewed before publishing.</p>
        </div>
        <Link href="/teacher/news/new"
          className="inline-flex items-center gap-2 font-syne font-bold text-sm bg-ink text-[#f0ede8] px-4 py-2.5 rounded-xl hover:bg-red transition-colors">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Add news
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-surface border border-border rounded-xl animate-pulse" />
          ))}
        </div>
      ) : news.length === 0 ? (
        <div className="text-center py-20 bg-surface border border-border rounded-2xl">
          <div className="text-4xl mb-4">📰</div>
          <p className="font-syne font-semibold text-ink-2 mb-2">No news items yet</p>
          <p className="text-sm text-ink-3 mb-6">Create your first news summary from a medical publication or press release.</p>
          <Link href="/teacher/news/new" className="inline-block font-syne font-bold text-sm bg-ink text-[#f0ede8] px-5 py-2.5 rounded-xl hover:bg-red transition-colors">
            Add first news →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {news.map(item => (
            <div key={item.id} className="bg-surface border border-border rounded-xl p-5 flex flex-col sm:flex-row sm:items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <span className={`text-xs font-syne font-bold px-2 py-0.5 rounded-full ${STATUS_STYLE[item.review_status]}`}>
                    {STATUS_LABEL[item.review_status]}
                  </span>
                  <span className="text-xs font-syne font-semibold text-red uppercase">{item.category.replace(/-/g, " ")}</span>
                  <span className="text-xs text-ink-3 font-syne">{item.source_name}</span>
                </div>
                <h3 className="font-syne font-bold text-sm text-ink leading-snug line-clamp-2 mb-1">{item.title}</h3>
                <a href={item.source_url} target="_blank" rel="noopener noreferrer"
                  className="text-xs text-ink-3 hover:text-ink truncate block max-w-sm">{item.source_url}</a>
                {item.review_status === "rejected" && item.review_note && (
                  <p className="text-xs text-red mt-1.5 font-syne">Rejection note: {item.review_note}</p>
                )}
              </div>

              <div className="flex flex-row sm:flex-col gap-2 flex-shrink-0">
                {item.review_status === "published" && (
                  <Link href={`/news/${item.slug}`}
                    className="text-xs font-syne font-semibold px-3 py-1.5 rounded-lg border border-border hover:border-ink transition-colors">
                    View →
                  </Link>
                )}
                {item.review_status === "draft" && (
                  <>
                    <Link href={`/teacher/news/new?edit=${item.id}`}
                      className="text-xs font-syne font-semibold px-3 py-1.5 rounded-lg border border-border hover:border-ink transition-colors">
                      Edit
                    </Link>
                    <button onClick={() => submit(item.id)} disabled={busy === item.id}
                      className="text-xs font-syne font-semibold px-3 py-1.5 rounded-lg bg-ink text-[#f0ede8] hover:bg-red transition-colors disabled:opacity-50">
                      Submit
                    </button>
                  </>
                )}
                {item.review_status === "submitted" && (
                  <button onClick={() => withdraw(item.id)} disabled={busy === item.id}
                    className="text-xs font-syne font-semibold px-3 py-1.5 rounded-lg border border-amber-300 text-amber-700 hover:bg-amber-50 transition-colors disabled:opacity-50">
                    Withdraw
                  </button>
                )}
                {item.review_status === "rejected" && (
                  <>
                    <Link href={`/teacher/news/new?edit=${item.id}`}
                      className="text-xs font-syne font-semibold px-3 py-1.5 rounded-lg border border-border hover:border-ink transition-colors">
                      Edit
                    </Link>
                    <button onClick={() => del(item.id)} disabled={busy === item.id}
                      className="text-xs font-syne font-semibold px-3 py-1.5 rounded-lg border border-red/30 text-red hover:bg-red/10 transition-colors disabled:opacity-50">
                      Delete
                    </button>
                  </>
                )}
                {(item.review_status === "draft") && (
                  <button onClick={() => del(item.id)} disabled={busy === item.id}
                    className="text-xs font-syne text-ink-3 hover:text-red transition-colors px-1">
                    ✕
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
