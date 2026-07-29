import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { CheckCircle2, XCircle, ExternalLink, ShieldCheck } from "lucide-react";

export const dynamic = "force-static";
export const revalidate = 3600; // revalidate hourly

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://medmind.pro/api/v1";

export const metadata: Metadata = {
  title: "Content Sources & Licenses | MedMind",
  description:
    "Transparent registry of all reference sources used by MedMind to generate and verify medical education content — including licenses, attribution requirements, and verification dates.",
  alternates: {
    canonical: `${SITE_URL}/content-sources`,
  },
  openGraph: {
    title: "Content Sources & Licenses | MedMind",
    description:
      "Every source MedMind uses is publicly listed with its license and verification date.",
    url: `${SITE_URL}/content-sources`,
    type: "website",
  },
};

interface ContentSource {
  slug: string;
  title: string;
  publisher: string;
  url: string;
  license: string;
  license_url: string | null;
  text_reuse_allowed: boolean;
  attribution_template: string | null;
  source_type: string;
  verified_at: string | null;
  notes: string | null;
}

const SOURCE_TYPE_LABEL: Record<string, string> = {
  reference: "Clinical Reference",
  guideline: "Clinical Guideline",
  gov_health: "Government Health Resource",
  official_exam_blueprint: "Official Exam Blueprint",
};

async function fetchSources(): Promise<ContentSource[]> {
  try {
    const res = await fetch(`${API_URL}/public/content-sources`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

function LicenseBadge({ source }: { source: ContentSource }) {
  const isOpen = source.text_reuse_allowed;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        isOpen
          ? "bg-emerald-100 text-emerald-800"
          : "bg-amber-100 text-amber-800"
      }`}
    >
      {isOpen ? (
        <CheckCircle2 className="w-3 h-3" />
      ) : (
        <XCircle className="w-3 h-3" />
      )}
      {isOpen ? "Text reuse allowed" : "Facts only"}
    </span>
  );
}

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    reference: "bg-blue-100 text-blue-800",
    guideline: "bg-purple-100 text-purple-800",
    gov_health: "bg-teal-100 text-teal-800",
    official_exam_blueprint: "bg-slate-100 text-slate-800",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[type] ?? "bg-gray-100 text-gray-700"}`}>
      {SOURCE_TYPE_LABEL[type] ?? type}
    </span>
  );
}

export default async function ContentSourcesPage() {
  const sources = await fetchSources();

  const byType = sources.reduce<Record<string, ContentSource[]>>((acc, s) => {
    (acc[s.source_type] ??= []).push(s);
    return acc;
  }, {});

  const typeOrder = [
    "gov_health",
    "reference",
    "guideline",
    "official_exam_blueprint",
  ];

  return (
    <div className="min-h-screen bg-surface">
      <ArticleNav />

      <main className="max-w-5xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-6 h-6 text-primary" />
            <span className="text-sm font-medium text-primary uppercase tracking-wide">
              Transparency
            </span>
          </div>
          <h1 className="text-3xl font-bold text-ink mb-4">
            Content Sources &amp; Licenses
          </h1>
          <p className="text-ink-2 text-lg max-w-2xl">
            Every source MedMind uses to generate and verify educational content
            is listed here with its license, terms of use, and the date we
            verified those terms. This registry is the foundation of our{" "}
            <Link href="/editorial-policy" className="text-primary underline">
              editorial policy
            </Link>
            .
          </p>
        </div>

        {/* Legend */}
        <div className="bg-white border border-border rounded-xl p-5 mb-8 flex flex-col sm:flex-row gap-4">
          <div className="flex items-start gap-3 flex-1">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-sm text-ink">Text reuse allowed</p>
              <p className="text-xs text-ink-3 mt-0.5">
                Public domain (US gov) or CC BY license. Text may be quoted or
                adapted with attribution.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 flex-1">
            <XCircle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-sm text-ink">Facts only</p>
              <p className="text-xs text-ink-3 mt-0.5">
                NC, ND, or unclear license. We use these as factual basis only —
                no text is reproduced or paraphrased from them.
              </p>
            </div>
          </div>
        </div>

        {/* Sources by type */}
        {sources.length === 0 ? (
          <p className="text-ink-3 text-center py-12">Loading sources…</p>
        ) : (
          <div className="space-y-10">
            {typeOrder
              .filter((t) => byType[t]?.length)
              .map((type) => (
                <section key={type}>
                  <h2 className="text-lg font-semibold text-ink mb-4 pb-2 border-b border-border">
                    {SOURCE_TYPE_LABEL[type] ?? type}
                  </h2>
                  <div className="divide-y divide-border rounded-xl border border-border overflow-hidden">
                    {byType[type].map((src) => (
                      <div key={src.slug} className="bg-white px-5 py-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex flex-wrap items-center gap-2 mb-1">
                              <a
                                href={src.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium text-ink hover:text-primary transition-colors inline-flex items-center gap-1"
                              >
                                {src.title}
                                <ExternalLink className="w-3.5 h-3.5 opacity-60" />
                              </a>
                            </div>
                            <p className="text-xs text-ink-3 mb-2">
                              {src.publisher}
                            </p>
                            <div className="flex flex-wrap items-center gap-2">
                              <LicenseBadge source={src} />
                              {src.license_url ? (
                                <a
                                  href={src.license_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-ink-3 hover:text-primary underline"
                                >
                                  {src.license}
                                </a>
                              ) : (
                                <span className="text-xs text-ink-3">
                                  {src.license}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="text-right shrink-0">
                            {src.verified_at && (
                              <p className="text-xs text-ink-3">
                                Verified {src.verified_at}
                              </p>
                            )}
                          </div>
                        </div>
                        {src.attribution_template && (
                          <p className="mt-2 text-xs text-ink-2 bg-emerald-50 border border-emerald-200 rounded px-3 py-2">
                            <span className="font-medium">Attribution: </span>
                            {src.attribution_template}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              ))}
          </div>
        )}

        {/* Footer note */}
        <div className="mt-12 p-5 bg-blue-50 border border-blue-200 rounded-xl text-sm text-ink-2">
          <p className="font-medium text-ink mb-1">Our commitment</p>
          <p>
            No content is copied from proprietary question banks. Questions are
            generated from scratch using verified facts from the sources above.
            Every generated question passes our automated claim-verification
            pipeline before publication.{" "}
            <Link href="/editorial-policy" className="text-primary underline">
              See editorial policy →
            </Link>
          </p>
        </div>
      </main>

      <PublicFooter locale="en" />
    </div>
  );
}
