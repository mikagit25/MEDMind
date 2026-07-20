import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";
import type { ExamDefinition } from "@/components/exam/ExamLandingTemplate";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const BACKEND_URL =
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export const metadata: Metadata = {
  title: "Gulf Nursing Exam Comparison 2025 — SNLE, DHA, QCHP, OMSB, NHRA, MOH UAE, HAAD | MedMind AI",
  description:
    "Compare all 7 Gulf Prometric nursing licensing exams side by side: questions, duration, pass mark, and regulatory body. One Gulf Bundle opens practice for all exams.",
  alternates: { canonical: `${SITE_URL}/exams/gulf` },
  openGraph: {
    title: "Gulf Nursing Exam Comparison — MedMind AI",
    description: "SNLE vs DHA vs QCHP vs OMSB vs NHRA vs MOH UAE vs HAAD — all in one place.",
    url: `${SITE_URL}/exams/gulf`,
    siteName: "MedMind AI",
    type: "website",
  },
};

async function fetchGulfExams(): Promise<ExamDefinition[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/exam/definitions?family=gulf&include_draft=true`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export default async function GulfComparisonPage() {
  const exams = await fetchGulfExams();

  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />

      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <div className="mb-2 text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
          Gulf Region · Prometric Licensing
        </div>
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          Gulf Nursing Exams — Complete Comparison
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-8 max-w-2xl">
          All 7 Gulf Prometric nursing licensing exams in one place. Many nurses prepare for
          multiple exams simultaneously — the country that accepts them first is where they go.
          The Gulf Bundle opens practice access to all 7 at once.
        </p>

        {/* Comparison table */}
        {exams.length > 0 ? (
          <div className="bg-surface border border-border rounded-2xl overflow-hidden mb-10">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-ink text-white">
                    <th className="text-left px-5 py-3 font-syne font-bold text-xs">Exam</th>
                    <th className="text-left px-4 py-3 font-syne font-bold text-xs">Country</th>
                    <th className="text-left px-4 py-3 font-syne font-bold text-xs">Authority</th>
                    <th className="text-center px-4 py-3 font-syne font-bold text-xs">Questions</th>
                    <th className="text-center px-4 py-3 font-syne font-bold text-xs">Duration</th>
                    <th className="text-center px-4 py-3 font-syne font-bold text-xs">Pass</th>
                    <th className="text-center px-4 py-3 font-syne font-bold text-xs"></th>
                  </tr>
                </thead>
                <tbody>
                  {exams.map((exam, i) => {
                    const hrs = Math.floor(exam.duration_min / 60);
                    const mns = exam.duration_min % 60;
                    const dur = hrs > 0 ? `${hrs}h${mns > 0 ? `${mns}m` : ""}` : `${mns}m`;
                    return (
                      <tr key={exam.slug} className={`border-t border-border ${i % 2 === 0 ? "bg-surface" : "bg-bg"}`}>
                        <td className="px-5 py-3">
                          <div className="font-syne font-bold text-sm text-ink">{exam.name.split(" — ")[0]}</div>
                          <div className="text-xs text-ink-3">{exam.slug.toUpperCase()}</div>
                        </td>
                        <td className="px-4 py-3 text-sm text-ink-2">{exam.country}</td>
                        <td className="px-4 py-3 text-xs text-ink-3 max-w-[160px]">
                          {exam.regulatory_body}
                        </td>
                        <td className="px-4 py-3 text-center font-syne font-bold text-ink">{exam.question_count}</td>
                        <td className="px-4 py-3 text-center text-sm text-ink-2">{dur}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="font-syne font-bold text-xs bg-green/10 text-green px-2 py-0.5 rounded-full">
                            {exam.passing_score_label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <Link href={`/exams/${exam.slug}`}
                            className="font-syne font-bold text-xs text-ink hover:text-red transition-colors">
                            Prep →
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-surface border border-border rounded-2xl p-8 text-center text-ink-3 mb-10">
            Exam data loading…
          </div>
        )}

        {/* Key insight */}
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 mb-10">
          <h2 className="font-syne font-bold text-base text-ink mb-2">
            Why nurses prepare for multiple exams at once
          </h2>
          <p className="text-sm text-ink-2 leading-relaxed">
            All Gulf Prometric nursing exams share the same blueprint categories — fundamentals,
            medical-surgical, pharmacology, maternal health, pediatrics, mental health, community
            health, and leadership. A nurse preparing for SNLE is already 80%+ ready for DHA, QCHP,
            and the others. The Gulf Bundle in MedMind AI lets you track readiness across all 7
            simultaneously with one shared question bank.
          </p>
        </div>

        {/* Individual exam cards */}
        <h2 className="font-syne font-bold text-xl text-ink mb-5">Explore Each Exam</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
          {exams.map(exam => (
            <Link key={exam.slug} href={`/exams/${exam.slug}`}
              className="bg-surface border border-border rounded-xl p-5 hover:border-ink/30 hover:shadow-sm transition-all">
              <div className="font-syne font-bold text-sm text-ink mb-1">
                {exam.name.split(" — ")[0]}
              </div>
              <div className="text-xs text-ink-3 mb-3">{exam.country} · {exam.regulatory_body.split(" (")[0]}</div>
              <div className="flex gap-3 text-xs font-syne text-ink-2">
                <span>{exam.question_count}Q</span>
                <span>·</span>
                <span>{Math.floor(exam.duration_min / 60)}h</span>
                <span>·</span>
                <span>Pass {exam.passing_score_label}</span>
              </div>
            </Link>
          ))}
        </div>

        {/* CTA */}
        <div className="text-center">
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-4 rounded-xl hover:bg-red transition-colors">
            Start Preparing — Free →
          </Link>
          <p className="text-xs font-serif text-ink-3 mt-3">
            No credit card required · 10 free practice questions
          </p>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="max-w-5xl mx-auto px-4 pb-10">
        <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-6">
          MedMind AI is not affiliated with, endorsed by, or connected to any Gulf regulatory body
          or Prometric. Exam parameters are sourced from publicly available official synopses.
          Always verify current requirements directly with the relevant authority before applying.
        </p>
      </section>

      <PublicFooter />
    </div>
  );
}
