"use client";

import { notFound } from "next/navigation";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { CalculatorWidget } from "@/components/calculators/CalculatorWidget";
import { getCalc, CALC_SLUGS, UI, INDEX_T } from "@/components/calculators/data";
import type { Lang } from "@/components/calculators/data";

const LANGS = [
  { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" }, { value: "de", flag: "🇩🇪" },
  { value: "fr", flag: "🇫🇷" }, { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" }, { value: "es", flag: "🇪🇸" },
] as const;

function t(obj: Record<Lang, string>, lang: string): string {
  return (obj as Record<string, string>)[lang] ?? obj.en;
}

type NumericCalcMeta = {
  name: Record<Lang, string>;
  subtitle: Record<Lang, string>;
  category: Record<Lang, string>;
  icon: string;
  seoDescription: string;
};

const NUMERIC_CALCS: Record<string, NumericCalcMeta> = {
  "egfr-ckd-epi": {
    name:     { en: "eGFR (CKD-EPI 2021)", ru: "рСКФ (CKD-EPI 2021)", ar: "معدل الترشيح الكبيبي التقديري (CKD-EPI 2021)", tr: "eGFR (CKD-EPI 2021)", de: "eGFR (CKD-EPI 2021)", fr: "DFGe (CKD-EPI 2021)", es: "TFGe (CKD-EPI 2021)" },
    subtitle: { en: "Kidney function and CKD staging", ru: "Функция почек и стадия ХБП", ar: "وظائف الكلى وتصنيف مرض الكلى المزمن", tr: "Böbrek fonksiyonu ve KBH evrelemesi", de: "Nierenfunktion und CKD-Stadienbestimmung", fr: "Fonction rénale et stadification de l'IRC", es: "Función renal y estadificación de ERC" },
    category: { en: "Nephrology", ru: "Нефрология", ar: "أمراض الكلى", tr: "Nefroloji", de: "Nephrologie", fr: "Néphrologie", es: "Nefrología" },
    icon: "🫘",
    seoDescription: "eGFR calculator using CKD-EPI 2021 equation. Estimates kidney function and determines CKD stage. Free, multilingual.",
  },
  "bmi": {
    name:     { en: "BMI Calculator", ru: "Индекс массы тела", ar: "مؤشر كتلة الجسم", tr: "Vücut Kitle İndeksi", de: "BMI-Rechner", fr: "Calculateur IMC", es: "Calculadora IMC" },
    subtitle: { en: "Body mass index and obesity classification (WHO)", ru: "Индекс массы тела и классификация ожирения (ВОЗ)", ar: "مؤشر كتلة الجسم وتصنيف السمنة (WHO)", tr: "Vücut kitle indeksi ve obezite sınıflaması (WHO)", de: "Body-Mass-Index und Adipositas-Klassifikation (WHO)", fr: "Indice de masse corporelle et classification obésité (OMS)", es: "Índice de masa corporal y clasificación de obesidad (OMS)" },
    category: { en: "General", ru: "Общее", ar: "عام", tr: "Genel", de: "Allgemein", fr: "Général", es: "General" },
    icon: "⚖️",
    seoDescription: "BMI calculator with WHO obesity classification (underweight, normal, overweight, obese). Free, multilingual.",
  },
  "corrected-calcium": {
    name:     { en: "Corrected Calcium", ru: "Скорр. кальций", ar: "الكالسيوم المصحح", tr: "Düzeltilmiş Kalsiyum", de: "Korrigiertes Kalzium", fr: "Calcium corrigé", es: "Calcio corregido" },
    subtitle: { en: "Calcium correction for hypoalbuminaemia", ru: "Коррекция кальция при гипоальбуминемии", ar: "تصحيح الكالسيوم في نقص ألبومين الدم", tr: "Hipoalbüminemi için kalsiyum düzeltmesi", de: "Kalziumkorrektur bei Hypoalbuminämie", fr: "Correction calcique pour hypoalbuminémie", es: "Corrección de calcio por hipoalbuminemia" },
    category: { en: "Biochemistry", ru: "Биохимия", ar: "الكيمياء الحيوية", tr: "Biyokimya", de: "Biochemie", fr: "Biochimie", es: "Bioquímica" },
    icon: "🧪",
    seoDescription: "Corrected calcium calculator adjusting for hypoalbuminaemia using the Payne formula. Free, multilingual.",
  },
  "anion-gap": {
    name:     { en: "Anion Gap", ru: "Анионный разрыв", ar: "الفجوة الأيونية", tr: "Anyon Açığı", de: "Anionenlücke", fr: "Trou anionique", es: "Brecha aniónica" },
    subtitle: { en: "Metabolic acidosis classification with albumin correction", ru: "Классификация метаболического ацидоза с поправкой на альбумин", ar: "تصنيف الحماض الأيضي مع تصحيح الألبومين", tr: "Albumin düzeltmeli metabolik asidoz sınıflaması", de: "Metabolische Azidose-Klassifikation mit Albumin-Korrektur", fr: "Classification de l'acidose métabolique avec correction albumine", es: "Clasificación acidosis metabólica con corrección albúmina" },
    category: { en: "Biochemistry", ru: "Биохимия", ar: "الكيمياء الحيوية", tr: "Biyokimya", de: "Biochemie", fr: "Biochimie", es: "Bioquímica" },
    icon: "⚗️",
    seoDescription: "Anion gap calculator with albumin correction for metabolic acidosis classification. Free, multilingual.",
  },
  "meld": {
    name:     { en: "MELD / MELD-Na Score", ru: "Шкала MELD / MELD-Na", ar: "مقياس MELD / MELD-Na", tr: "MELD / MELD-Na Skoru", de: "MELD / MELD-Na Score", fr: "Score MELD / MELD-Na", es: "Puntuación MELD / MELD-Na" },
    subtitle: { en: "Liver disease severity and transplant priority (UNOS)", ru: "Тяжесть заболевания печени и приоритет трансплантации (UNOS)", ar: "شدة مرض الكبد وأولوية زرع الأعضاء (UNOS)", tr: "Karaciğer hastalığı şiddeti ve nakil önceliği (UNOS)", de: "Schweregrad der Lebererkrankung und Transplantationspriorität (UNOS)", fr: "Sévérité de l'hépatopathie et priorité transplantation (UNOS)", es: "Gravedad hepatopatía y prioridad trasplante (UNOS)" },
    category: { en: "Hepatology", ru: "Гепатология", ar: "أمراض الكبد", tr: "Hepatoloji", de: "Hepatologie", fr: "Hépatologie", es: "Hepatología" },
    icon: "🫀",
    seoDescription: "MELD and MELD-Na score calculator for liver disease severity and transplant prioritisation. Free, multilingual.",
  },
  "cockcroft-gault": {
    name:     { en: "Cockcroft-Gault CrCl", ru: "Клиренс креатинина (Кокрофт-Голт)", ar: "تصفية الكرياتينين (كوكروفت-غولت)", tr: "Cockcroft-Gault KrKl", de: "Cockcroft-Gault-KrCl", fr: "Clairance créatinine Cockcroft-Gault", es: "ClCr Cockcroft-Gault" },
    subtitle: { en: "Kidney function and drug dosing adjustment", ru: "Функция почек и коррекция доз препаратов", ar: "وظائف الكلى وتعديل جرعة الدواء", tr: "Böbrek fonksiyonu ve ilaç doz ayarlaması", de: "Nierenfunktion und Medikamentendosisanpassung", fr: "Fonction rénale et adaptation posologique", es: "Función renal y ajuste de dosis farmacológica" },
    category: { en: "Nephrology", ru: "Нефрология", ar: "أمراض الكلى", tr: "Nefroloji", de: "Nephrologie", fr: "Néphrologie", es: "Nefrología" },
    icon: "💊",
    seoDescription: "Cockcroft-Gault creatinine clearance calculator for drug dosing in renal impairment. Free, multilingual.",
  },
};

export default function CalculatorPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const { locale, setLocale } = useI18n();
  const lang = locale as string;

  const validSlugs: readonly string[] = CALC_SLUGS;
  if (!validSlugs.includes(slug)) notFound();

  const calc = getCalc(slug);
  const numericMeta = NUMERIC_CALCS[slug];
  const isNumeric = !!numericMeta;

  const name = isNumeric ? t(numericMeta.name, lang) : t(calc!.nameI18n, lang);
  const subtitle = isNumeric ? t(numericMeta.subtitle, lang) : t(calc!.subtitle, lang);
  const category = isNumeric ? t(numericMeta.category, lang) : t(calc!.categoryI18n, lang);
  const icon = isNumeric ? numericMeta.icon : calc!.icon;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "MedicalWebPage",
    name: `${name} — MedMind AI`,
    description: isNumeric ? numericMeta.seoDescription : t(calc!.seoDescription, "en"),
    url: `https://medmind.pro/calculators/${slug}`,
    audience: { "@type": "MedicalAudience", audienceType: "Clinician" },
  };

  return (
    <div className="min-h-screen bg-bg">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <Link href="/calculators" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {t(INDEX_T.all_calculators, lang)}
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <select value={locale} onChange={e => setLocale(e.target.value as Lang)}
              className="hidden sm:block text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none">
              {LANGS.map(l => <option key={l.value} value={l.value}>{l.flag}</option>)}
            </select>
            <Link href="/login" className="hidden sm:block font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {locale === "ru" ? "Войти" : locale === "ar" ? "تسجيل الدخول" : locale === "de" ? "Anmelden" : locale === "fr" ? "Connexion" : locale === "es" ? "Iniciar sesión" : locale === "tr" ? "Giriş yap" : "Sign in"}
            </Link>
            <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-3 sm:px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">
              {locale === "ru" ? "Регистрация" : locale === "ar" ? "إنشاء حساب" : locale === "de" ? "Registrieren" : locale === "fr" ? "S'inscrire" : locale === "es" ? "Registrarse" : locale === "tr" ? "Kayıt ol" : "Register"}
            </Link>
          </div>
        </div>
      </nav>

      {/* Header */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-10 pb-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-xs font-syne text-ink-3 mb-6">
          <Link href="/calculators" className="hover:text-ink transition-colors">{t(INDEX_T.all_calculators, lang)}</Link>
          <span>/</span>
          <span className="text-ink">{name}</span>
        </nav>

        <div className="flex items-start gap-4 mb-2">
          <span className="text-3xl">{icon}</span>
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h1 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink leading-tight">{name}</h1>
              <span className="text-xs font-syne font-semibold text-ink-3 bg-surface border border-border px-2 py-0.5 rounded-full">
                {category}
              </span>
            </div>
            <p className="text-ink-2 text-sm sm:text-base leading-relaxed">{subtitle}</p>
          </div>
        </div>
      </section>

      {/* Calculator */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
        <CalculatorWidget slug={slug} />
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Link href="/" className="font-syne font-extrabold text-base text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">AI Education Platform</span>
          </Link>
          <p className="text-ink-3 text-xs text-center max-w-md">
            {t(INDEX_T.footer_note, lang)}
          </p>
          <div className="text-ink-3 text-xs font-syne">© 2026 MedMind AI.</div>
        </div>
      </footer>
    </div>
  );
}
