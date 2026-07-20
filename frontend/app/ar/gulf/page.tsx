// SYNC-GROUP: gulf-landing
// This page is part of a multilingual set. When content changes here,
// update all sibling pages to stay in sync:
//   /exams/gulf (EN)   /ru/gulf  (RU)   /tr/gulf  (TR)
//   /de/gulf  (DE)     /fr/gulf  (FR)   /es/gulf  (ES)
//   /ar/gulf  (AR) ← you are here
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "تحضير لامتحانات التمريض الخليجية — SNLE، DHA، QCHP، OMSB، NHRA | MedMind AI",
  description:
    "استعد لامتحانات ترخيص التمريض في الخليج العربي: SNLE السعودي، DHA دبي، QCHP قطر، OMSB عُمان، NHRA البحرين، وزارة الصحة الإمارات. أسئلة تدريبية بتنسيق بروميتريك مع شرح بالذكاء الاصطناعي.",
  alternates: {
    canonical: `${SITE_URL}/ar/gulf`,
    languages: {
      "en": `${SITE_URL}/exams/gulf`,
      "ar": `${SITE_URL}/ar/gulf`,
      "x-default": `${SITE_URL}/exams/gulf`,
    },
  },
  openGraph: {
    title: "امتحانات التمريض الخليجية — MedMind AI",
    description: "SNLE · DHA · QCHP · OMSB · NHRA · MOH UAE · DOH — كل امتحانات ترخيص التمريض في مكان واحد",
    url: `${SITE_URL}/ar/gulf`,
    siteName: "MedMind AI",
    type: "website",
    locale: "ar_SA",
  },
};

const GULF_EXAMS = [
  { slug: "snle",    nameAr: "SNLE — اختبار ترخيص التمريض السعودي",    country: "المملكة العربية السعودية", body: "الهيئة السعودية للتخصصات الصحية (SCHS)" },
  { slug: "dha",     nameAr: "DHA — هيئة الصحة في دبي",                 country: "الإمارات — دبي",          body: "هيئة الصحة في دبي (DHA)" },
  { slug: "qchp",   nameAr: "QCHP — مجلس الرعاية الصحية في قطر",       country: "قطر",                     body: "المجلس القطري للمهن الصحية (QCHP)" },
  { slug: "omsb",   nameAr: "OMSB — الهيئة العُمانية للتخصصات الطبية", country: "سلطنة عُمان",             body: "الهيئة العُمانية للتخصصات الطبية (OMSB)" },
  { slug: "nhra",   nameAr: "NHRA — الهيئة الوطنية لتنظيم المهن الصحية", country: "البحرين",                body: "الهيئة الوطنية لتنظيم المهن الصحية (NHRA)" },
  { slug: "moh-uae", nameAr: "MOH UAE — وزارة الصحة والوقاية",          country: "الإمارات — الإمارات الشمالية", body: "وزارة الصحة والوقاية (MOHAP)" },
  { slug: "haad",   nameAr: "DOH — دائرة الصحة أبوظبي",                 country: "الإمارات — أبوظبي",       body: "دائرة الصحة أبوظبي (DOH)" },
];

const CATEGORIES_AR: Record<string, string> = {
  fundamentals_nursing:    "أساسيات التمريض",
  medical_surgical:        "التمريض الطبي والجراحي",
  pharmacology:            "الصيدلانيات وإدارة الأدوية",
  maternal_newborn:        "تمريض الأمومة وحديثي الولادة",
  pediatrics:              "تمريض الأطفال",
  mental_health:           "الصحة النفسية",
  community_public_health: "الصحة المجتمعية والعامة",
  leadership_management:   "القيادة والإدارة",
};

export default function ArabicGulfPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink" dir="rtl" lang="ar">
      <ArticleNav />

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <div className="mb-2 text-xs font-syne font-bold text-ink-3 uppercase tracking-widest text-right">
          منطقة الخليج · ترخيص التمريض بروميتريك
        </div>
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4 text-right">
          امتحانات ترخيص التمريض في دول الخليج
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-6 max-w-3xl mr-auto text-right">
          استعد لجميع امتحانات ترخيص التمريض الخليجية بنظام بروميتريك في مكان واحد.
          كثير من الممرضين يتقدمون لأكثر من امتحان في وقت واحد — الدولة التي تقبلهم أولاً هي وجهتهم.
          حزمة الخليج في MedMind AI تفتح لك التدريب على جميع الامتحانات السبعة دفعةً واحدة.
        </p>
        <div className="flex flex-wrap gap-3 mb-8 justify-end">
          <Link href="/register"
            className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            ابدأ مجاناً ←
          </Link>
          <Link href="/exams/gulf"
            className="font-syne font-bold text-sm border border-border text-ink px-6 py-3 rounded-xl hover:bg-surface transition-colors">
            English Version
          </Link>
        </div>

        {/* Key numbers */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {[
            { num: "٧",    label: "امتحانات خليجية" },
            { num: "٦٠٨+", label: "سؤال تدريبي" },
            { num: "٣ س",  label: "مدة كل امتحان" },
            { num: "٦٥٪",  label: "درجة النجاح" },
          ].map(({ num, label }) => (
            <div key={label} className="bg-surface border border-border rounded-2xl p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">{num}</div>
              <div className="text-xs font-syne text-ink-3 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Exam list */}
      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-5 text-right">الامتحانات المتاحة</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {GULF_EXAMS.map(exam => (
            <Link key={exam.slug} href={`/exams/${exam.slug}`}
              className="bg-surface border border-border rounded-xl p-5 hover:border-ink/30 hover:shadow-sm transition-all text-right">
              <div className="font-syne font-bold text-sm text-ink mb-1">{exam.nameAr}</div>
              <div className="text-xs text-ink-3 mb-3">{exam.country}</div>
              <div className="text-xs text-ink-2">{exam.body}</div>
              <div className="mt-3 text-xs font-syne text-ink-2 flex gap-3 justify-end">
                <span>١٠٠ سؤال</span>
                <span>·</span>
                <span>٣ ساعات</span>
                <span>·</span>
                <span>النجاح ٦٥٪</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Blueprint categories */}
      <section className="max-w-5xl mx-auto px-4 py-10">
        <h2 className="font-syne font-bold text-xl text-ink mb-2 text-right">محاور الامتحان</h2>
        <p className="text-sm text-ink-2 mb-5 text-right">
          جميع امتحانات الخليج تشترك في نفس المحاور الثمانية — الاستعداد لامتحان واحد يعني أنك مستعد بنسبة ٨٠٪+ لبقية الامتحانات.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.entries(CATEGORIES_AR).map(([key, label]) => (
            <div key={key} className="bg-surface border border-border rounded-xl p-3 text-center">
              <div className="font-syne font-semibold text-xs text-ink">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Why MedMind */}
      <section className="max-w-5xl mx-auto px-4 py-10">
        <h2 className="font-syne font-bold text-xl text-ink mb-6 text-right">لماذا MedMind AI؟</h2>
        <div className="grid sm:grid-cols-2 gap-5">
          {[
            {
              title: "أسئلة بتنسيق الامتحان الحقيقي",
              desc: "كل سؤال بنظام بروميتريك — ٤ خيارات، سيناريو سريري واقعي، لا أسئلة محفوظة من البنوك الرسمية.",
            },
            {
              title: "شرح بالذكاء الاصطناعي لكل سؤال",
              desc: "تعرف لماذا الإجابة الصحيحة صحيحة، ولماذا كل خيار خاطئ — تحليل سريري مفصّل.",
            },
            {
              title: "تتبع الأداء بالمحاور",
              desc: "معرفة نقاط ضعفك بدقة في كل محور من المحاور الثمانية بعد كل جلسة تدريب.",
            },
            {
              title: "خطة دراسة مخصصة",
              desc: "حدد تاريخ امتحانك واحصل على جدول دراسة يومي يتكيف مع مستواك ووقتك المتبقي.",
            },
          ].map(f => (
            <div key={f.title} className="bg-surface border border-border rounded-xl p-5 text-right">
              <div className="font-syne font-bold text-sm text-ink mb-2">{f.title}</div>
              <div className="text-sm text-ink-2 leading-relaxed">{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Target audience note */}
      <section className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-right">
          <h2 className="font-syne font-bold text-base text-ink mb-2">
            مخصص للممرضين الراغبين في العمل بدول الخليج
          </h2>
          <p className="text-sm text-ink-2 leading-relaxed mb-4">
            سواء كنت ممرضاً فلبينياً، هندياً، أفريقياً، أو عربياً — إذا كنت تسعى للحصول على ترخيص
            في المملكة العربية السعودية أو الإمارات أو قطر أو عُمان أو البحرين،
            فإن MedMind AI مصمم لمساعدتك في الاجتياز من المحاولة الأولى.
          </p>
          <Link href="/register"
            className="inline-block font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            سجّل مجاناً — ١٠ أسئلة بدون بطاقة ائتمان ←
          </Link>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="max-w-5xl mx-auto px-4 pb-10">
        <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-6 text-right">
          MedMind AI غير مرتبطة بأي هيئة تنظيمية خليجية أو شركة بروميتريك ولا تمثلها ولا تدعمها.
          معلومات الامتحانات مستقاة من الوثائق الرسمية المتاحة للعموم.
          تحقق دائماً من المتطلبات الحالية مباشرةً مع الجهة المختصة قبل التقديم.
        </p>
      </section>

      <PublicFooter />
    </div>
  );
}
