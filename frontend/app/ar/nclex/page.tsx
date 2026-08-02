// SYNC-GROUP: nclex-landing
// /nclex (EN) · /ar/nclex (AR) · /es/nclex (ES) · /ru/nclex (RU) · /de/nclex (DE) · /fr/nclex (FR) · /tr/nclex (TR) ← you are here: AR
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "التحضير لامتحان NCLEX-RN 2025 — محاكاة CAT التكيّفية وشرح ذكاء اصطناعي | MedMind AI",
  description:
    "تدرّب على امتحان NCLEX-RN مع محاكاة CAT التكيّفية (75–145 سؤالاً)، SATA، NGN، وشرح ذكاء اصطناعي لكل سؤال. تتبّع أداءك عبر جميع فئات NCLEX السبعة — ابدأ مجاناً.",
  alternates: {
    canonical: `${SITE_URL}/ar/nclex`,
    languages: {
      "en":        `${SITE_URL}/nclex`,
      "ar":        `${SITE_URL}/ar/nclex`,
      "es":        `${SITE_URL}/es/nclex`,
      "ru":        `${SITE_URL}/ru/nclex`,
      "de":        `${SITE_URL}/de/nclex`,
      "fr":        `${SITE_URL}/fr/nclex`,
      "tr":        `${SITE_URL}/tr/nclex`,
      "x-default": `${SITE_URL}/nclex`,
    },
  },
  openGraph: {
    title: "التحضير لامتحان NCLEX-RN — MedMind AI",
    description: "محاكاة CAT التكيّفية · شرح ذكاء اصطناعي · تتبّع الأداء · 600+ سؤال بتنسيق NCLEX",
    url: `${SITE_URL}/ar/nclex`,
    siteName: "MedMind AI",
    type: "website",
    locale: "ar_SA",
  },
};

const MODES = [
  { id: "تجريبي مجاني",    questions: "10",      tag: "مجاني — بدون تسجيل",    desc: "جرّب قبل التسجيل. 10 أسئلة من جميع الفئات مع شرح ذكاء اصطناعي كامل.", free: true },
  { id: "NCLEX-RN 75",     questions: "75",      tag: "الحد الأدنى للنجاح",    desc: "محاكاة تكيّفية قياسية. ينتهي الامتحان هنا إذا كان الأداء واضحاً في النجاح أو الرسوب.", free: false },
  { id: "NCLEX-RN 85",     questions: "85",      tag: "محاكاة موسّعة",         desc: "اختبر المنطقة الحدية. أسئلة أصعب وتقييم أدق لمستوى الاستعداد.", free: false },
  { id: "NCLEX-RN 145",    questions: "145",     tag: "المحاكاة الكاملة",      desc: "محاكاة بكامل طولها. جميع الفئات بعمق. الأفضل لآخر أسبوع قبل الامتحان.", free: false },
  { id: "حسب الفئة",       questions: "10–30",   tag: "تدريب مركّز",           desc: "اختر إحدى فئات احتياجات العميل السبعة وتدرّب عليها بشكل مخصص.", free: false },
];

const FEATURES = [
  { title: "محاكاة CAT التكيّفية",    desc: "منطق NCLEX-RN الحقيقي: يتكيّف الامتحان مع كل إجابة. اختر 75 أو 85 أو 145 سؤالاً — نفس تنسيق Pearson VUE." },
  { title: "شرح ذكاء اصطناعي لكل سؤال", desc: "بعد كل إجابة، احصل على تحليل سريري كامل: لماذا الإجابة الصحيحة صحيحة، ولماذا كل خيار آخر خاطئ." },
  { title: "7 فئات احتياجات العميل",   desc: "كل سؤال مرتبط بإحدى فئات NCLEX السبعة. بعد الامتحان، اعرف درجتك في كل فئة بالضبط." },
  { title: "تتبّع مهارات CJMM",        desc: "تابع تطوّرك في 6 مهارات الحكم السريري: التعرّف على الأدلة، تحليلها، تحديد الأولويات، توليد الحلول، التنفيذ، وتقييم النتائج." },
  { title: "إعادة أسئلة الأخطاء",     desc: "بعد كل جلسة، أعد الأسئلة التي أخطأت فيها — تدريب مركّز على نقاط ضعفك الفعلية." },
  { title: "SATA والحسابات وNGN",      desc: "ليس فقط MCQ. تدرّب على اختر كل ما ينطبق، وحسابات IV، والترتيب المنطقي، وأسئلة الجيل القادم." },
];

const FAQ = [
  {
    q: "هل التجربة المجانية فعلاً مجانية؟",
    a: "نعم. لا يتطلب الوصول للتجربة إنشاء حساب. 10 أسئلة مع شرح ذكاء اصطناعي كامل وتحليل النتائج — بلا بطاقة ائتمانية ولا بريد إلكتروني.",
  },
  {
    q: "هل الأسئلة باللغة العربية؟",
    a: "أسئلة التدريب باللغة الإنجليزية (لأن الامتحان الحقيقي بالإنجليزية)، لكن شرح الذكاء الاصطناعي والنقاط الرئيسية متاحة باللغة العربية. هذا يساعدك على فهم المفاهيم بلغتك والتعوّد في آن على المصطلحات الإنجليزية اللازمة للامتحان.",
  },
  {
    q: "هل الأسئلة محدّثة لتغييرات NCLEX 2024/2025؟",
    a: "نعم. بنك الأسئلة يتضمن أنواع أسئلة Next Generation NCLEX (NGN) المستحدثة في 2023 — SATA والترتيب والحسابات. الخوارزمية التكيّفية تحاكي منطق CAT الخاص بـ Pearson VUE.",
  },
  {
    q: "هل MedMind AI معتمد من NCSBN أو NCLEX؟",
    a: "لا. MedMind AI منصة تحضير مستقلة وليس لها أي ارتباط أو اعتماد من NCSBN أو برنامج NCLEX.",
  },
];

export default function ArabicNclexPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink" dir="rtl" lang="ar">
      <ArticleNav />

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-12 sm:pb-16">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div className="text-right">
            <div className="inline-flex items-center gap-2 bg-red/10 border border-red/20 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
              NCLEX-RN 2025
            </div>
            <h1 className="font-syne font-extrabold text-3xl sm:text-4xl lg:text-5xl text-ink mb-4 leading-tight">
              اجتز امتحان NCLEX-RN<br />من المحاولة الأولى.
            </h1>
            <p className="text-ink-2 text-base sm:text-lg leading-relaxed mb-8 max-w-lg mr-auto">
              محاكاة CAT التكيّفية، تحليل الاستدلال السريري بالذكاء الاصطناعي، وتحليلات أداء شاملة — مبنية على طريقة تعلّم الممرضين الحقيقية.
            </p>
            <div className="flex flex-wrap gap-3 justify-end">
              <Link href="/register"
                className="inline-block font-syne font-bold text-base bg-red text-white px-8 py-4 rounded-xl hover:bg-ink transition-colors">
                ابدأ مجاناً ←
              </Link>
              <Link href="/login"
                className="inline-block font-syne font-semibold text-base border border-border text-ink-2 px-8 py-4 rounded-xl hover:border-ink hover:text-ink transition-colors">
                تسجيل الدخول
              </Link>
            </div>
            <p className="text-xs text-ink-3 mt-4 font-syne text-right">حساب مجاني · 5 أسئلة ذكاء اصطناعي/يوم · بلا بطاقة ائتمانية</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { value: "600+", label: "سؤال NCLEX", sub: "SATA · CAT · NGN · حسابات" },
              { value: "12",   label: "وحدة تمريضية", sub: "محتوى مبني على الأدلة" },
              { value: "7",    label: "فئات Client Needs", sub: "تغطية كاملة" },
              { value: "6",    label: "مهارات CJMM", sub: "تتبّع الحكم السريري" },
            ].map((s) => (
              <div key={s.label} className="bg-surface border border-border rounded-xl p-5 flex flex-col gap-1 text-right">
                <span className="font-syne font-extrabold text-3xl sm:text-4xl text-ink">{s.value}</span>
                <span className="font-syne font-semibold text-sm text-ink leading-tight">{s.label}</span>
                <span className="text-xs text-ink-3">{s.sub}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Exam modes */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
          <div className="mb-8 text-right">
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">خمسة أنماط تدريب</h2>
            <p className="text-ink-3 text-sm">من تجربة مجانية بـ 10 أسئلة إلى محاكاة كاملة بـ 145 سؤالاً.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODES.map((m) => (
              <div key={m.id} className={`rounded-xl border p-5 flex flex-col gap-3 text-right ${m.free ? "border-red/30 bg-red/5" : "border-border bg-bg"}`}>
                <div className="flex items-start justify-between gap-2 flex-row-reverse">
                  <span className="font-syne font-extrabold text-xl text-ink">{m.questions}</span>
                  <span className={`text-xs font-syne font-semibold px-2 py-0.5 rounded-full border ${m.free ? "bg-red/10 border-red/20 text-red" : "bg-surface border-border text-ink-3"}`}>
                    {m.tag}
                  </span>
                </div>
                <div>
                  <h3 className="font-syne font-bold text-base text-ink mb-1">{m.id}</h3>
                  <p className="text-ink-3 text-sm leading-snug">{m.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="mb-10 text-right">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">كل ما تحتاجه للنجاح</h2>
          <p className="text-ink-3 text-sm max-w-xl mr-auto">كل ميزة مبنية لهدف واحد: اجتز NCLEX-RN بثقة، لا بالحظ.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex flex-col gap-3 text-right">
              <div>
                <h3 className="font-syne font-bold text-base text-ink mb-1">{f.title}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-10 text-center">كيف يعمل؟</h2>
          <div className="grid sm:grid-cols-3 gap-8">
            {[
              { step: "01", title: "اختر النمط", desc: "ابدأ بالتجربة المجانية (10 أسئلة)، أو اختر محاكاة CAT كاملة (75 / 85 / 145 سؤالاً) أو تدريباً على فئة محددة." },
              { step: "02", title: "أجب وراجع", desc: "بعد كل سؤال، اضغط على «شرح بالذكاء الاصطناعي» للحصول على تحليل سريري كامل — لماذا إجابتك صحيحة أو خاطئة وما المفهوم الذي يجب تذكّره." },
              { step: "03", title: "تابع وحسّن", desc: "تبوّيب الأداء يظهر معدل نجاحك حسب فئة Client Needs ومهارة CJMM. أعد الأسئلة الخاطئة بنقرة واحدة." },
            ].map((s) => (
              <div key={s.step} className="flex flex-col gap-3 text-right">
                <span className="font-syne font-extrabold text-5xl text-ink/10 leading-none">{s.step}</span>
                <h3 className="font-syne font-bold text-base text-ink">{s.title}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-8 text-center">أسئلة شائعة</h2>
          <div className="space-y-6">
            {FAQ.map((item) => (
              <div key={item.q} className="border-b border-border pb-6 last:border-0 last:pb-0 text-right">
                <h3 className="font-syne font-bold text-base text-ink mb-2">{item.q}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="bg-ink text-white">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">مستعد للبدء؟</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            جرّب التجربة المجانية الآن — 10 أسئلة، شرح ذكاء اصطناعي كامل، بدون حساب. أنشئ حساباً لفتح محاكاة CAT الكاملة والتحليلات الشخصية.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/register"
              className="inline-block font-syne font-bold text-base bg-white text-ink px-8 py-4 rounded-xl hover:bg-red hover:text-white transition-colors">
              ابدأ مجاناً ←
            </Link>
          </div>
          <p className="text-white/30 text-xs mt-5 font-syne">بلا بطاقة ائتمانية · الخطة المجانية تتضمن 5 أسئلة ذكاء اصطناعي/يوم</p>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
