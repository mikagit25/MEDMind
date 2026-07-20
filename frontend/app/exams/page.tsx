import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Nursing Licensing Exams — NCLEX, Gulf Prometric, UKMLA | MedMind AI",
  description:
    "Prepare for any nursing licensing exam: NCLEX-RN, SNLE, DHA, QCHP, OMSB, NHRA, MOH UAE, HAAD, and UKMLA. AI-powered questions, rationales, and personalised study plans.",
  alternates: { canonical: `${SITE_URL}/exams` },
  openGraph: {
    title: "Nursing Licensing Exam Prep — MedMind AI",
    description: "All major nursing licensing exams in one platform.",
    url: `${SITE_URL}/exams`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const EXAM_FAMILIES = [
  {
    family: "NCLEX",
    flag: "🇺🇸",
    headline: "NCLEX-RN / NCLEX-PN",
    desc: "Adaptive CAT simulation (75–145 questions), SATA, NGN, AI explanations for all 7 Client Needs categories. The standard for US nursing licensure.",
    href: "/nclex",
    cta: "NCLEX Prep →",
    color: "border-blue-200 bg-blue-50",
    exams: ["NCLEX-RN", "NCLEX-PN"],
  },
  {
    family: "Gulf",
    flag: "🌍",
    headline: "Gulf Prometric — 7 Exams",
    desc: "All Gulf Prometric nursing licensing exams: SNLE (Saudi), DHA (Dubai), QCHP (Qatar), OMSB (Oman), NHRA (Bahrain), MOH UAE, DOH/HAAD (Abu Dhabi). One bundle, all countries.",
    href: "/exams/gulf",
    cta: "Gulf Exams →",
    color: "border-amber-200 bg-amber-50",
    exams: ["SNLE", "DHA", "QCHP", "OMSB", "NHRA", "MOH UAE", "DOH/HAAD"],
  },
  {
    family: "UK",
    flag: "🇬🇧",
    headline: "UKMLA / MLA",
    desc: "UK Medical Licensing Assessment — clinical knowledge questions aligned with the MLA blueprint. For nurses and internationally qualified doctors registering in the UK.",
    href: "/nurses",
    cta: "UK Prep →",
    color: "border-purple-200 bg-purple-50",
    exams: ["UKMLA", "MLA"],
  },
];

const GULF_EXAMS = [
  { slug: "snle",    label: "SNLE",     country: "Saudi Arabia" },
  { slug: "dha",     label: "DHA",      country: "Dubai, UAE" },
  { slug: "qchp",    label: "QCHP",     country: "Qatar" },
  { slug: "omsb",    label: "OMSB",     country: "Oman" },
  { slug: "nhra",    label: "NHRA",     country: "Bahrain" },
  { slug: "moh-uae", label: "MOH UAE",  country: "UAE (Northern Emirates)" },
  { slug: "haad",    label: "DOH/HAAD", country: "Abu Dhabi, UAE" },
];

export default function ExamsHubPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />

      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          Nursing Licensing Exam Prep
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-10 max-w-2xl">
          One platform for every major nursing licensing exam — adaptive practice,
          AI explanations, and study plans timed to your exam date.
        </p>

        {/* Exam family cards */}
        <div className="space-y-5 mb-14">
          {EXAM_FAMILIES.map(f => (
            <div key={f.family} className={`border ${f.color} rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center gap-5`}>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl">{f.flag}</span>
                  <span className="font-syne font-black text-lg text-ink">{f.headline}</span>
                </div>
                <p className="text-sm text-ink-2 leading-relaxed mb-3">{f.desc}</p>
                <div className="flex flex-wrap gap-2">
                  {f.exams.map(e => (
                    <span key={e} className="text-xs font-syne font-bold bg-white/80 border border-border px-2 py-0.5 rounded-full text-ink-2">
                      {e}
                    </span>
                  ))}
                </div>
              </div>
              <Link href={f.href}
                className="font-syne font-bold text-sm bg-ink text-white px-5 py-2.5 rounded-xl hover:bg-red transition-colors flex-shrink-0 text-center">
                {f.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* Quick links to individual Gulf exams */}
        <h2 className="font-syne font-bold text-xl text-ink mb-5">Gulf Prometric — Individual Exams</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-12">
          {GULF_EXAMS.map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`}
              className="bg-surface border border-border rounded-xl p-4 hover:border-ink/30 hover:shadow-sm transition-all">
              <div className="font-syne font-bold text-sm text-ink">{e.label}</div>
              <div className="text-xs text-ink-3 mt-0.5">{e.country}</div>
            </Link>
          ))}
          <Link href="/exams/gulf"
            className="bg-ink text-white rounded-xl p-4 hover:bg-red transition-colors">
            <div className="font-syne font-bold text-sm">Compare All →</div>
            <div className="text-xs text-white/70 mt-0.5">Gulf Bundle</div>
          </Link>
        </div>

        {/* CTA */}
        <div className="text-center">
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-4 rounded-xl hover:bg-red transition-colors">
            Start Free — 10 Practice Questions →
          </Link>
          <p className="text-xs font-serif text-ink-3 mt-3">No credit card required</p>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
