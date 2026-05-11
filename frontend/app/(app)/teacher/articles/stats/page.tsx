"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { teacherApi } from "@/lib/api";
import { useT, useI18n } from "@/lib/i18n";

type ArticleStat = {
  id: string;
  slug: string;
  title: string;
  views: number;
  revenue_share_pct: number;
  estimated_revenue_usd: number;
  review_status: string;
  is_published: boolean;
  published_at: string | null;
};

type StatsData = {
  total_views: number;
  total_articles: number;
  published_articles: number;
  estimated_revenue_usd: number;
  revenue_per_1000_views: number;
  articles: ArticleStat[];
};

const STATUS_STYLES: Record<string, string> = {
  draft:          "bg-surface-2 text-ink-3 border-border",
  pending_review: "bg-amber-light text-amber border-amber/20",
  published:      "bg-green-light text-green border-green/20",
  rejected:       "bg-red-light text-red border-red/20",
};

function nextPayoutDate(locale: string): string {
  const now = new Date();
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  const loc = locale === "ru" ? "ru-RU" : locale === "ar" ? "ar-SA" : locale === "de" ? "de-DE"
    : locale === "fr" ? "fr-FR" : locale === "es" ? "es-ES" : locale === "tr" ? "tr-TR" : "en-US";
  return next.toLocaleDateString(loc, { month: "long", day: "numeric", year: "numeric" });
}

export default function ArticleStatsPage() {
  const t = useT();
  const { locale } = useI18n();
  const [data, setData] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const statusLabels: Record<string, string> = {
    draft:          t("teacher.articles.status.draft"),
    pending_review: t("teacher.articles.status.pending_review"),
    published:      t("teacher.articles.status.published"),
    rejected:       t("teacher.articles.status.rejected"),
  };

  useEffect(() => {
    teacherApi.getMyArticleStats()
      .then(setData)
      .catch(() => setError(t("teacher.articles.stats.load_err")))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/teacher/articles" className="text-ink-3 hover:text-ink font-syne text-sm transition-colors">
          {t("teacher.articles.stats.back")}
        </Link>
        <span className="text-border">|</span>
        <h1 className="font-syne font-black text-2xl text-ink">{t("teacher.articles.stats.title")}</h1>
      </div>

      {loading && (
        <div className="text-center py-20 text-ink-3 font-serif">{t("teacher.articles.stats.loading")}</div>
      )}

      {error && (
        <div className="bg-red-light border border-red/20 text-red rounded-xl p-4 font-serif text-sm mb-6">{error}</div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { value: data.total_views.toLocaleString(), label: t("teacher.articles.stats.total_views"), color: "text-ink" },
              { value: data.published_articles.toString(), label: t("teacher.articles.stats.published"), color: "text-ink" },
              { value: `$${data.estimated_revenue_usd.toFixed(2)}`, label: t("teacher.articles.stats.est_revenue"), color: "text-green" },
              { value: `$${data.revenue_per_1000_views.toFixed(2)}`, label: t("teacher.articles.stats.rpm"), color: "text-ink" },
            ].map((card, i) => (
              <div key={i} className="card p-5 text-center">
                <div className={`text-3xl font-syne font-black mb-1 ${card.color}`}>{card.value}</div>
                <div className="text-xs font-syne text-ink-3 uppercase tracking-widest">{card.label}</div>
              </div>
            ))}
          </div>

          <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border border-gold/30 rounded-xl p-5 mb-8">
            <div className="flex items-start gap-3">
              <span className="text-2xl">💰</span>
              <div>
                <h2 className="font-syne font-bold text-base text-ink mb-1">{t("teacher.articles.stats.how_revenue")}</h2>
                <ul className="text-sm font-serif text-ink-2 space-y-1">
                  <li dangerouslySetInnerHTML={{ __html: `• ${t("teacher.articles.stats.revenue_40pct")}` }} />
                  <li dangerouslySetInnerHTML={{ __html: `• ${t("teacher.articles.stats.translated_7")}` }} />
                  <li>• {t("teacher.articles.stats.formula")} <code className="bg-white/60 px-1 rounded text-xs">(views ÷ 1,000) × $2.00 × 40%</code></li>
                  <li dangerouslySetInnerHTML={{ __html: `• ${t("teacher.articles.stats.payout_info")} ${nextPayoutDate(locale)}` }} />
                </ul>
              </div>
            </div>
          </div>

          {data.articles.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-3">📝</div>
              <div className="font-syne font-bold text-lg text-ink mb-2">{t("teacher.articles.stats.no_articles")}</div>
              <p className="text-ink-3 font-serif text-sm mb-5">{t("teacher.articles.stats.no_articles_desc")}</p>
              <Link href="/teacher/articles/new" className="btn-primary">{t("teacher.articles.stats.write_article")}</Link>
            </div>
          ) : (
            <div className="card overflow-hidden">
              <div className="px-5 py-3 border-b border-border bg-surface-2">
                <h3 className="font-syne font-semibold text-sm text-ink">{t("teacher.articles.stats.breakdown")}</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      {[
                        t("teacher.articles.stats.col_title"),
                        t("teacher.articles.stats.col_views"),
                        t("teacher.articles.stats.col_revenue"),
                        t("teacher.articles.stats.col_status"),
                      ].map((h, i) => (
                        <th key={i} className={`${i === 0 ? "text-left px-5" : i === 3 ? "text-center px-4" : "text-right px-4"} py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider`}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.articles.map((a) => (
                      <tr key={a.id} className="border-t border-border hover:bg-surface-2 transition-colors">
                        <td className="px-5 py-3">
                          <div className="font-syne font-semibold text-ink text-sm leading-tight line-clamp-1">{a.title}</div>
                          {a.is_published && (
                            <a href={`/articles/${a.slug}`} target="_blank" rel="noopener noreferrer"
                              className="text-xs text-green font-serif hover:underline">
                              {t("teacher.articles.stats.view_live")}
                            </a>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-syne font-bold text-ink">{a.views.toLocaleString()}</td>
                        <td className="px-4 py-3 text-right font-syne font-bold text-green">${a.estimated_revenue_usd.toFixed(2)}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`border rounded-full px-2.5 py-0.5 text-xs font-syne font-semibold ${STATUS_STYLES[a.review_status] ?? ""}`}>
                            {statusLabels[a.review_status] ?? a.review_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 border-border bg-surface-2">
                      <td className="px-5 py-3 font-syne font-bold text-ink text-sm">{t("teacher.articles.stats.total")}</td>
                      <td className="px-4 py-3 text-right font-syne font-black text-ink">{data.total_views.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right font-syne font-black text-green">${data.estimated_revenue_usd.toFixed(2)}</td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
