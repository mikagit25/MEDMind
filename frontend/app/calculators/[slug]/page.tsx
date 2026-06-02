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

const EGFR_META = {
  name: { en: "eGFR (CKD-EPI 2021)", ru: "рСКФ (CKD-EPI 2021)", ar: "معدل الترشيح الكبيبي التقديري (CKD-EPI 2021)", tr: "eGFR (CKD-EPI 2021)", de: "eGFR (CKD-EPI 2021)", fr: "DFGe (CKD-EPI 2021)", es: "TFGe (CKD-EPI 2021)" } as Record<Lang, string>,
  subtitle: { en: "Kidney function and CKD staging", ru: "Функция почек и стадия ХБП", ar: "وظائف الكلى وتصنيف مرض الكلى المزمن", tr: "Böbrek fonksiyonu ve KBH evrelemesi", de: "Nierenfunktion und CKD-Stadienbestimmung", fr: "Fonction rénale et stadification de l'IRC", es: "Función renal y estadificación de ERC" } as Record<Lang, string>,
  category: { en: "Nephrology", ru: "Нефрология", ar: "أمراض الكلى", tr: "Nefroloji", de: "Nephrologie", fr: "Néphrologie", es: "Nefrología" } as Record<Lang, string>,
  icon: "🫘",
};

export default function CalculatorPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const { locale, setLocale } = useI18n();
  const lang = locale as string;

  const validSlugs: readonly string[] = CALC_SLUGS;
  if (!validSlugs.includes(slug)) notFound();

  const calc = getCalc(slug);
  const isEgfr = slug === "egfr-ckd-epi";

  const name = isEgfr ? t(EGFR_META.name, lang) : t(calc!.nameI18n, lang);
  const subtitle = isEgfr ? t(EGFR_META.subtitle, lang) : t(calc!.subtitle, lang);
  const category = isEgfr ? t(EGFR_META.category, lang) : t(calc!.categoryI18n, lang);
  const icon = isEgfr ? EGFR_META.icon : calc!.icon;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "MedicalWebPage",
    name: `${name} — MedMind AI`,
    description: isEgfr
      ? "eGFR calculator using CKD-EPI 2021 equation. Estimates kidney function and determines CKD stage. Free, multilingual."
      : t(calc!.seoDescription, "en"),
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
