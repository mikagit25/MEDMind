// SYNC-GROUP: exams-hub
// /exams (EN) · /ar/exams (AR) · /es/exams (ES) · /ru/exams (RU) · /de/exams (DE) · /fr/exams (FR) · /tr/exams (TR) ← you are here: AR
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "التحضير لامتحانات ترخيص التمريض — NCLEX، خليجي، UKMLA | MedMind AI",
  description:
    "استعد لأي امتحان ترخيص للتمريض: NCLEX-RN، SNLE، DHA، QCHP، OMSB، NHRA، MOH UAE، HAAD، وUKMLA. أسئلة بمساعدة الذكاء الاصطناعي وخطط دراسية مخصصة.",
  alternates: {
    canonical: `${SITE_URL}/ar/exams`,
    languages: {
      "en":        `${SITE_URL}/exams`,
      "ar":        `${SITE_URL}/ar/exams`,
      "es":        `${SITE_URL}/es/exams`,
      "ru":        `${SITE_URL}/ru/exams`,
      "de":        `${SITE_URL}/de/exams`,
      "fr":        `${SITE_URL}/fr/exams`,
      "tr":        `${SITE_URL}/tr/exams`,
      "x-default": `${SITE_URL}/exams`,
    },
  },
  openGraph: {
    title: "التحضير لامتحانات ترخيص التمريض — MedMind AI",
    description: "منصة واحدة لجميع امتحانات ترخيص التمريض الكبرى.",
    url: `${SITE_URL}/ar/exams`,
    siteName: "MedMind AI",
    type: "website",
    locale: "ar_SA",
  },
};

const EXAM_FAMILIES = [
  {
    family: "NCLEX",
    flag: "🇺🇸",
    headline: "NCLEX-RN / NCLEX-PN",
    desc: "محاكاة CAT التكيّفية (75–145 سؤالاً)، SATA، NGN، شرح ذكاء اصطناعي لجميع فئات احتياجات العميل السبعة. المعيار الأمريكي لترخيص التمريض.",
    href: "/ar/nclex",
    cta: "NCLEX ←",
    color: "border-blue-200 bg-blue-50",
    exams: ["NCLEX-RN", "NCLEX-PN"],
  },
  {
    family: "Gulf",
    flag: "🌍",
    headline: "خليجي بروميتريك — 7 امتحانات",
    desc: "جميع امتحانات ترخيص التمريض الخليجية: SNLE (السعودية)، DHA (دبي)، QCHP (قطر)، OMSB (عُمان)، NHRA (البحرين)، MOH UAE، DOH/HAAD (أبوظبي). باقة واحدة لجميع الدول.",
    href: "/ar/gulf",
    cta: "امتحانات الخليج ←",
    color: "border-amber-200 bg-amber-50",
    exams: ["SNLE", "DHA", "QCHP", "OMSB", "NHRA", "MOH UAE", "DOH/HAAD"],
  },
  {
    family: "UK",
    flag: "🇬🇧",
    headline: "UKMLA / MLA",
    desc: "تقييم الترخيص الطبي البريطاني — أسئلة المعرفة السريرية للممرضين والأطباء الأجانب المسجلين في المملكة المتحدة.",
    href: "/nurses",
    cta: "UKMLA ←",
    color: "border-purple-200 bg-purple-50",
    exams: ["UKMLA", "MLA"],
  },
];

const GULF_EXAMS = [
  { slug: "snle",    label: "SNLE",     country: "المملكة العربية السعودية" },
  { slug: "dha",     label: "DHA",      country: "الإمارات — دبي" },
  { slug: "qchp",   label: "QCHP",     country: "قطر" },
  { slug: "omsb",   label: "OMSB",     country: "سلطنة عُمان" },
  { slug: "nhra",   label: "NHRA",     country: "البحرين" },
  { slug: "moh-uae", label: "MOH UAE", country: "الإمارات الشمالية" },
  { slug: "haad",   label: "DOH/HAAD", country: "أبوظبي، الإمارات" },
];

export default function ArabicExamsHubPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink" dir="rtl" lang="ar">
      <ArticleNav />

      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4 text-right">
          التحضير لامتحانات ترخيص التمريض
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-10 max-w-2xl mr-auto text-right">
          منصة واحدة لجميع امتحانات ترخيص التمريض الكبرى — تدريب تكيّفي، شرح بالذكاء الاصطناعي، وخطط دراسية مرتبطة بتاريخ امتحانك.
        </p>

        <div className="space-y-5 mb-14">
          {EXAM_FAMILIES.map(f => (
            <div key={f.family} className={`border ${f.color} rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center gap-5`}>
              <div className="flex-1 text-right">
                <div className="flex items-center gap-2 mb-1 justify-end">
                  <span className="font-syne font-black text-lg text-ink">{f.headline}</span>
                  <span className="text-xl">{f.flag}</span>
                </div>
                <p className="text-sm text-ink-2 leading-relaxed mb-3">{f.desc}</p>
                <div className="flex flex-wrap gap-2 justify-end">
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

        <h2 className="font-syne font-bold text-xl text-ink mb-5 text-right">امتحانات الخليج — روابط مباشرة</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-12">
          {GULF_EXAMS.map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`}
              className="bg-surface border border-border rounded-xl p-4 hover:border-ink/30 hover:shadow-sm transition-all text-right">
              <div className="font-syne font-bold text-sm text-ink">{e.label}</div>
              <div className="text-xs text-ink-3 mt-0.5">{e.country}</div>
            </Link>
          ))}
          <Link href="/ar/gulf"
            className="bg-ink text-white rounded-xl p-4 hover:bg-red transition-colors text-right">
            <div className="font-syne font-bold text-sm">مقارنة الكل ←</div>
            <div className="text-xs text-white/70 mt-0.5">حزمة الخليج</div>
          </Link>
        </div>

        <div className="text-center">
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-4 rounded-xl hover:bg-red transition-colors">
            ابدأ مجاناً — 10 أسئلة تدريبية ←
          </Link>
          <p className="text-xs font-serif text-ink-3 mt-3">لا حاجة لبطاقة ائتمانية</p>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
