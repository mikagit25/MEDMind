"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { teacherApi } from "@/lib/api";

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

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  pending_review: "In Review",
  published: "Published",
  rejected: "Rejected",
};

function nextPayoutDate(): string {
  const now = new Date();
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return next.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

export default function ArticleStatsPage() {
  const [data, setData] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    teacherApi.getMyArticleStats()
      .then(setData)
      .catch(() => setError("Failed to load stats. Please try again."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Link
          href="/teacher/articles"
          className="text-ink-3 hover:text-ink font-syne text-sm transition-colors"
        >
          ← My Articles
        </Link>
        <span className="text-border">|</span>
        <h1 className="font-syne font-black text-2xl text-ink">Author Earnings</h1>
      </div>

      {loading && (
        <div className="text-center py-20 text-ink-3 font-serif">Loading your stats…</div>
      )}

      {error && (
        <div className="bg-red-light border border-red/20 text-red rounded-xl p-4 font-serif text-sm mb-6">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="card p-5 text-center">
              <div className="text-3xl font-syne font-black text-ink mb-1">
                {data.total_views.toLocaleString()}
              </div>
              <div className="text-xs font-syne text-ink-3 uppercase tracking-widest">Total Views</div>
            </div>
            <div className="card p-5 text-center">
              <div className="text-3xl font-syne font-black text-ink mb-1">
                {data.published_articles}
              </div>
              <div className="text-xs font-syne text-ink-3 uppercase tracking-widest">Published</div>
            </div>
            <div className="card p-5 text-center">
              <div className="text-3xl font-syne font-black text-green mb-1">
                ${data.estimated_revenue_usd.toFixed(2)}
              </div>
              <div className="text-xs font-syne text-ink-3 uppercase tracking-widest">Est. Revenue</div>
            </div>
            <div className="card p-5 text-center">
              <div className="text-3xl font-syne font-black text-ink mb-1">
                ${data.revenue_per_1000_views.toFixed(2)}
              </div>
              <div className="text-xs font-syne text-ink-3 uppercase tracking-widest">RPM (USD)</div>
            </div>
          </div>

          {/* Revenue info */}
          <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border border-gold/30 rounded-xl p-5 mb-8">
            <div className="flex items-start gap-3">
              <span className="text-2xl">💰</span>
              <div>
                <h2 className="font-syne font-bold text-base text-ink mb-1">How Revenue Works</h2>
                <ul className="text-sm font-serif text-ink-2 space-y-1">
                  <li>• You earn <strong>70%</strong> of ad revenue from your articles (RPM ~$2.00 per 1,000 views)</li>
                  <li>• Articles are automatically translated to <strong>7 languages</strong>, multiplying your audience</li>
                  <li>• Revenue formula: <code className="bg-white/60 px-1 rounded text-xs">(views ÷ 1,000) × $2.00 × 70%</code></li>
                  <li>• <strong>Payouts processed monthly, minimum $10.</strong> Next payout: {nextPayoutDate()}</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Articles table */}
          {data.articles.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-3">📝</div>
              <div className="font-syne font-bold text-lg text-ink mb-2">No articles yet</div>
              <p className="text-ink-3 font-serif text-sm mb-5">Create and publish your first article to start earning.</p>
              <Link href="/teacher/articles/new" className="btn-primary">Write an Article</Link>
            </div>
          ) : (
            <div className="card overflow-hidden">
              <div className="px-5 py-3 border-b border-border bg-surface-2">
                <h3 className="font-syne font-semibold text-sm text-ink">Per-Article Breakdown</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left px-5 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Title</th>
                      <th className="text-right px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Views</th>
                      <th className="text-right px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Est. Revenue</th>
                      <th className="text-center px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.articles.map((a) => (
                      <tr key={a.id} className="border-t border-border hover:bg-surface-2 transition-colors">
                        <td className="px-5 py-3">
                          <div className="font-syne font-semibold text-ink text-sm leading-tight line-clamp-1">{a.title}</div>
                          {a.is_published && (
                            <a
                              href={`/articles/${a.slug}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-green font-serif hover:underline"
                            >
                              View live →
                            </a>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-syne font-bold text-ink">
                          {a.views.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-right font-syne font-bold text-green">
                          ${a.estimated_revenue_usd.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`border rounded-full px-2.5 py-0.5 text-xs font-syne font-semibold ${STATUS_STYLES[a.review_status] ?? ""}`}>
                            {STATUS_LABELS[a.review_status] ?? a.review_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 border-border bg-surface-2">
                      <td className="px-5 py-3 font-syne font-bold text-ink text-sm">Total</td>
                      <td className="px-4 py-3 text-right font-syne font-black text-ink">
                        {data.total_views.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right font-syne font-black text-green">
                        ${data.estimated_revenue_usd.toFixed(2)}
                      </td>
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
