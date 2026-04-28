"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { teacherApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

type TeacherArticle = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  review_status: "draft" | "pending_review" | "published" | "rejected";
  reading_time_minutes: number;
  published_at: string | null;
  submitted_at: string | null;
  review_note: string | null;
  updated_at: string;
};

const STATUS_STYLES: Record<string, string> = {
  draft:          "bg-surface-2 text-ink-3 border-border",
  pending_review: "bg-amber-light text-amber border-amber/20",
  published:      "bg-green-light text-green border-green/20",
  rejected:       "bg-red-light text-red border-red/20",
};

// STATUS_LABELS resolved via t() in component

const CATEGORY_LABELS: Record<string, string> = {
  diseases: "Diseases", drugs: "Drugs", procedures: "Procedures", symptoms: "Symptoms",
  diagnostics: "Diagnostics", emergency: "Emergency", nutrition: "Nutrition", pediatrics: "Pediatrics",
  cardiology: "Cardiology", neurology: "Neurology", oncology: "Oncology", surgery: "Surgery",
  psychiatry: "Psychiatry", endocrinology: "Endocrinology", "infectious-diseases": "Infectious Diseases",
  veterinary: "Veterinary",
};

export default function TeacherArticlesPage() {
  const t = useT();
  const [articles, setArticles] = useState<TeacherArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const showToast = (msg: string, type: "ok" | "err" = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await teacherApi.listMyArticles();
      setArticles(Array.isArray(data) ? data : (data.articles ?? []));
    } catch {
      showToast(t("teacher.articles.toast.load_err"), "err");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const submit = async (id: string) => {
    setSubmitting(id);
    try {
      await teacherApi.submitArticleForReview(id);
      setArticles(prev => prev.map(a => a.id === id ? { ...a, review_status: "pending_review" } : a));
      showToast(t("teacher.articles.toast.submitted"));
    } catch (err: any) {
      showToast(err.response?.data?.detail ?? t("teacher.articles.toast.submit_err"), "err");
    } finally {
      setSubmitting(null);
    }
  };

  const withdraw = async (id: string) => {
    setSubmitting(id);
    try {
      await teacherApi.withdrawArticle(id);
      setArticles(prev => prev.map(a => a.id === id ? { ...a, review_status: "draft" } : a));
      showToast(t("teacher.articles.toast.withdrawn"));
    } catch (err: any) {
      showToast(err.response?.data?.detail ?? t("teacher.articles.toast.withdraw_err"), "err");
    } finally {
      setSubmitting(null);
    }
  };

  const remove = async (id: string, _title: string) => {
    if (!confirm(t("teacher.articles.delete_confirm"))) return;
    setDeleting(id);
    try {
      await teacherApi.deleteMyArticle(id);
      setArticles(prev => prev.filter(a => a.id !== id));
      showToast(t("teacher.articles.toast.deleted"));
    } catch {
      showToast(t("teacher.articles.toast.delete_err"), "err");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-2 rounded shadow font-syne font-semibold text-sm text-white animate-fade-up ${
          toast.type === "ok" ? "bg-green" : "bg-red"
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("teacher.articles.title")}</h1>
          <p className="text-ink-3 text-sm font-serif mt-0.5">{t("teacher.articles.subtitle")}</p>
        </div>
        <Link
          href="/teacher/articles/new"
          className="bg-ink text-white font-syne font-semibold text-sm px-4 py-2 rounded-lg hover:bg-ink-2 transition-colors"
        >
          {t("teacher.articles.new")}
        </Link>
      </div>

      {/* Workflow guide */}
      <div className="bg-surface border border-border rounded-xl p-4 mb-6 flex items-start gap-4 flex-wrap">
        {[
          { step: "1", label: t("teacher.articles.workflow.step1_label"), desc: t("teacher.articles.workflow.step1_desc") },
          { step: "2", label: t("teacher.articles.workflow.step2_label"), desc: t("teacher.articles.workflow.step2_desc") },
          { step: "3", label: t("teacher.articles.workflow.step3_label"), desc: t("teacher.articles.workflow.step3_desc") },
        ].map((s) => (
          <div key={s.step} className="flex items-start gap-2 min-w-[180px]">
            <span className="w-6 h-6 rounded-full bg-ink text-white font-syne font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">{s.step}</span>
            <div>
              <div className="font-syne font-semibold text-sm text-ink">{s.label}</div>
              <div className="text-xs font-serif text-ink-3">{s.desc}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Articles list */}
      {loading ? (
        <div className="text-center py-16 text-ink-3 font-serif">{t("common.loading")}</div>
      ) : articles.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3">📝</div>
          <div className="font-syne font-bold text-lg text-ink mb-2">{t("teacher.articles.empty_title")}</div>
          <p className="text-ink-3 font-serif text-sm mb-6">{t("teacher.articles.empty_desc")}</p>
          <Link href="/teacher/articles/new" className="btn-primary">{t("teacher.articles.empty_cta")}</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {articles.map((a) => (
            <div key={a.id} className="card p-5">
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`border rounded-full px-2.5 py-0.5 text-xs font-syne font-semibold ${STATUS_STYLES[a.review_status]}`}>
                      {t(`teacher.articles.status.${a.review_status}`)}
                    </span>
                    <span className="text-xs text-ink-3 font-syne capitalize">
                      {CATEGORY_LABELS[a.category] ?? a.category}
                    </span>
                    <span className="text-xs text-ink-3 font-serif">· {a.reading_time_minutes} min read</span>
                  </div>
                  <h2 className="font-syne font-bold text-base text-ink mb-1 leading-tight">{a.title}</h2>
                  <p className="font-serif text-ink-3 text-sm line-clamp-2">{a.excerpt}</p>

                  {/* Rejection note */}
                  {a.review_status === "rejected" && a.review_note && (
                    <div className="mt-2 bg-red-light border border-red/20 rounded-lg px-3 py-2 text-xs font-serif text-red">
                      <strong className="font-syne font-semibold">{t("teacher.articles.admin_note")}</strong> {a.review_note}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-1.5 flex-shrink-0">
                  <Link
                    href={`/teacher/articles/${a.id}/edit`}
                    className={`text-xs font-syne font-semibold border border-border rounded px-3 py-1.5 text-center hover:border-ink hover:text-ink transition-colors ${
                      a.review_status === "pending_review" ? "opacity-40 pointer-events-none" : ""
                    }`}
                  >
                    {t("common.edit")}
                  </Link>

                  {a.review_status === "draft" || a.review_status === "rejected" ? (
                    <button
                      onClick={() => submit(a.id)}
                      disabled={submitting === a.id}
                      className="text-xs font-syne font-semibold border border-ink/30 text-ink hover:bg-ink hover:text-white rounded px-3 py-1.5 transition-colors"
                    >
                      {submitting === a.id ? "…" : t("teacher.articles.submit")}
                    </button>
                  ) : a.review_status === "pending_review" ? (
                    <button
                      onClick={() => withdraw(a.id)}
                      disabled={submitting === a.id}
                      className="text-xs font-syne text-ink-3 hover:text-red border border-border rounded px-3 py-1.5 transition-colors"
                    >
                      {submitting === a.id ? "…" : t("teacher.articles.withdraw")}
                    </button>
                  ) : (
                    <a
                      href={`/articles/${a.slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-syne font-semibold border border-green/30 text-green bg-green-light rounded px-3 py-1.5 text-center hover:bg-green hover:text-white transition-colors"
                    >
                      {t("teacher.articles.view_live")}
                    </a>
                  )}

                  <button
                    onClick={() => remove(a.id, a.title)}
                    disabled={deleting === a.id || a.review_status === "pending_review"}
                    className="text-xs font-syne text-red/60 hover:text-red border border-transparent hover:border-red/20 rounded px-3 py-1.5 transition-colors disabled:opacity-30"
                  >
                    {t("common.delete")}
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border text-[11px] text-ink-3 font-serif">
                <span>Updated {new Date(a.updated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
                {a.published_at && (
                  <span>· Published {new Date(a.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
