import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "اختبار ترخيص التمريض السعودي SNLE 2025 — تحضير مع ذكاء اصطناعي | MedMind AI",
  description:
    "حضّر لاختبار SNLE السعودي بأسئلة تدريبية بتنسيق بروميتريك، شرح ذكاء اصطناعي، وخطة دراسة مخصصة. الهيئة السعودية للتخصصات الصحية SCHS — ١٠٠ سؤال، ٣ ساعات، نجاح ٦٥٪.",
  alternates: {
    canonical: `${SITE_URL}/ar/nclex-snle`,
    languages: {
      "en": `${SITE_URL}/exams/snle`,
      "ar": `${SITE_URL}/ar/nclex-snle`,
      "x-default": `${SITE_URL}/exams/snle`,
    },
  },
  openGraph: {
    title: "SNLE — اختبار ترخيص التمريض السعودي | MedMind AI",
    description: "١٠٠ سؤال · ٣ ساعات · نجاح ٦٥٪ · الهيئة السعودية للتخصصات الصحية",
    url: `${SITE_URL}/ar/nclex-snle`,
    siteName: "MedMind AI",
    type: "website",
    locale: "ar_SA",
  },
};

const CATEGORIES_AR = [
  "أساسيات التمريض",
  "التمريض الطبي والجراحي",
  "الصيدلانيات وإدارة الأدوية",
  "تمريض الأمومة وحديثي الولادة",
  "تمريض الأطفال",
  "الصحة النفسية",
  "الصحة المجتمعية والعامة",
  "القيادة والإدارة",
];

export default function ArabicSNLEPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink" dir="rtl" lang="ar">
      <ArticleNav />

      <section className="max-w-4xl mx-auto px-4 pt-16 pb-10">
        <div className="flex items-center gap-2 mb-4 justify-end">
          <span className="text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
            المملكة العربية السعودية
          </span>
          <span className="text-ink-3">·</span>
          <span className="text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
            GULF PROMETRIC
          </span>
        </div>

        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4 text-right">
          التحضير لاختبار SNLE 2025
          <br />
          <span className="text-xl font-bold text-ink-2">اختبار ترخيص التمريض السعودي</span>
        </h1>

        <p className="text-lg text-ink-2 leading-relaxed mb-6 text-right">
          استعد لاختبار SNLE الذي تُجريه الهيئة السعودية للتخصصات الصحية (SCHS)
          بأسئلة تدريبية أصلية بتنسيق بروميتريك، مع شرح مفصل بالذكاء الاصطناعي
          وخطة دراسة مخصصة حسب تاريخ امتحانك.
        </p>

        <div className="flex flex-wrap gap-3 mb-8 justify-end">
          <Link href="/register"
            className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            ابدأ التدريب مجاناً ←
          </Link>
          <Link href="/exams/snle"
            className="font-syne font-bold text-sm border border-border text-ink px-6 py-3 rounded-xl hover:bg-surface transition-colors">
            English
          </Link>
        </div>

        {/* Exam specs */}
        <div className="bg-surface border border-border rounded-2xl p-6 grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {[
            { label: "عدد الأسئلة", value: "١٠٠" },
            { label: "مدة الاختبار", value: "٣ ساعات" },
            { label: "درجة النجاح", value: "٦٥٪" },
            { label: "تنسيق الأسئلة", value: "٤ خيارات MCQ" },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="font-syne font-black text-2xl text-ink">{value}</div>
              <div className="text-xs font-syne text-ink-3 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Blueprint */}
      <section className="max-w-4xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-2 text-right">محاور الاختبار الثمانية</h2>
        <p className="text-sm text-ink-2 mb-5 text-right">
          اختبار SNLE يغطي ٨ محاور رئيسية — نفس المحاور التي يشترك فيها مع DHA وQCHP وبقية امتحانات الخليج.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {CATEGORIES_AR.map(cat => (
            <div key={cat} className="bg-surface border border-border rounded-xl p-3 text-center">
              <div className="font-syne font-semibold text-xs text-ink">{cat}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Tips */}
      <section className="max-w-4xl mx-auto px-4 py-10">
        <h2 className="font-syne font-bold text-xl text-ink mb-5 text-right">نصائح للنجاح في SNLE</h2>
        <div className="space-y-4">
          {[
            {
              title: "الاختبار باللغة الإنجليزية",
              desc: "اختبار SNLE يُجرى بالكامل باللغة الإنجليزية — تأكد من إتقان المصطلحات الطبية والتمريضية بالإنجليزية.",
            },
            {
              title: "التدريب على السيناريوهات السريرية",
              desc: "الأسئلة تعتمد على مواقف سريرية واقعية — تدرب على التفكير النقدي واتخاذ القرارات التمريضية.",
            },
            {
              title: "إدارة الوقت أساسية",
              desc: "١٠٠ سؤال في ١٨٠ دقيقة = ١.٨ دقيقة لكل سؤال. تدرب على الإيقاع الصحيح من اليوم الأول.",
            },
            {
              title: "تعرف على جميع محاور الخليج",
              desc: "الاستعداد لـ SNLE يجعلك مستعداً لـ DHA و QCHP وباقي الامتحانات بنسبة 80%+.",
            },
          ].map(tip => (
            <div key={tip.title} className="bg-surface border border-border rounded-xl p-5 text-right">
              <div className="font-syne font-bold text-sm text-ink mb-1">{tip.title}</div>
              <div className="text-sm text-ink-2 leading-relaxed">{tip.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center">
          <h2 className="font-syne font-bold text-lg text-ink mb-2">
            ابدأ التدريب على SNLE الآن
          </h2>
          <p className="text-sm text-ink-2 mb-5">
            ١٠ أسئلة مجانية بدون بطاقة ائتمان · أسئلة بتنسيق بروميتريك مع شرح فوري
          </p>
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-4 rounded-xl hover:bg-red transition-colors">
            سجّل مجاناً ←
          </Link>
          <div className="mt-4">
            <Link href="/ar/gulf" className="text-sm text-ink-3 underline underline-offset-2 hover:text-ink">
              ← عرض جميع امتحانات الخليج
            </Link>
          </div>
        </div>
      </section>

      {/* Other exams */}
      <section className="max-w-4xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-base text-ink mb-4 text-right">امتحانات خليجية أخرى</h2>
        <div className="flex flex-wrap gap-2 justify-end">
          {[
            { slug: "dha",     label: "DHA — دبي" },
            { slug: "qchp",   label: "QCHP — قطر" },
            { slug: "omsb",   label: "OMSB — عُمان" },
            { slug: "nhra",   label: "NHRA — البحرين" },
            { slug: "moh-uae", label: "MOH UAE — الإمارات" },
            { slug: "haad",   label: "DOH — أبوظبي" },
          ].map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`}
              className="font-syne font-bold text-xs border border-border text-ink px-4 py-2 rounded-lg hover:bg-surface transition-colors">
              {e.label}
            </Link>
          ))}
        </div>
      </section>

      {/* Disclaimer */}
      <section className="max-w-4xl mx-auto px-4 pb-10">
        <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-6 text-right">
          MedMind AI غير مرتبطة بالهيئة السعودية للتخصصات الصحية (SCHS) أو شركة بروميتريك ولا تمثلهما.
          بيانات الاختبار مستقاة من الوثائق الرسمية المتاحة للعموم.
          تحقق دائماً من المتطلبات الحالية على الموقع الرسمي للهيئة قبل التسجيل.
        </p>
      </section>

      <PublicFooter />
    </div>
  );
}
