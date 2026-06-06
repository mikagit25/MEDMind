"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { CalculatorsIndex } from "@/components/calculators/CalculatorWidget";
import { INDEX_T } from "@/components/calculators/data";
import type { Lang } from "@/components/calculators/data";

const LANGS = [
  { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" }, { value: "de", flag: "🇩🇪" },
  { value: "fr", flag: "🇫🇷" }, { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" }, { value: "es", flag: "🇪🇸" },
] as const;

function t(obj: Record<Lang, string>, lang: string): string {
  return (obj as Record<string, string>)[lang] ?? obj.en;
}

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "MedicalWebPage",
  name: "Clinical Calculators — MedMind AI",
  description: "Free evidence-based clinical calculators: CHA₂DS₂-VASc, CURB-65, Wells DVT, HEART Score, eGFR. Available in 7 languages.",
  url: "https://medmind.pro/calculators",
  audience: { "@type": "MedicalAudience", audienceType: "Clinician" },
  medicalAudience: { "@type": "MedicalAudience", audienceType: "Clinician" },
};

export default function CalculatorsPage() {
  const { locale, setLocale } = useI18n();
  const lang = locale as string;

  return (
    <div className="min-h-screen bg-bg">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />

      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <Link href="/how-it-works" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {locale === "ru" ? "Как работает" : locale === "ar" ? "كيف يعمل" : locale === "de" ? "So funktionierts" : locale === "fr" ? "Comment ça marche" : locale === "es" ? "Cómo funciona" : locale === "tr" ? "Nasıl çalışır" : "How it works"}
            </Link>
            <Link href="/articles" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {locale === "ru" ? "Статьи" : locale === "ar" ? "مقالات" : locale === "de" ? "Artikel" : locale === "fr" ? "Articles" : locale === "es" ? "Artículos" : locale === "tr" ? "Makaleler" : "Articles"}
            </Link>
            <Link href="/calculators" className="font-syne font-semibold text-sm text-ink hover:text-red transition-colors px-3 py-2">
              {locale === "ru" ? "Калькуляторы" : locale === "ar" ? "آلات حاسبة" : locale === "de" ? "Rechner" : locale === "fr" ? "Calculateurs" : locale === "es" ? "Calculadoras" : locale === "tr" ? "Hesap makineleri" : "Calculators"}
            </Link>
            <Link href="/symptoms" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {locale === "ru" ? "Чекер симптомов" : locale === "ar" ? "فاحص الأعراض" : locale === "de" ? "Symptom-Checker" : locale === "fr" ? "Symptômes" : locale === "es" ? "Síntomas" : locale === "tr" ? "Semptomlar" : "Symptoms"}
            </Link>
            <Link href="/news" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {locale === "ru" ? "Новости" : locale === "ar" ? "أخبار" : locale === "de" ? "Nachrichten" : locale === "fr" ? "Actualités" : locale === "es" ? "Noticias" : locale === "tr" ? "Haberler" : "News"}
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

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-14 pb-10 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-6">
          <span className="w-2 h-2 rounded-full bg-green-2 inline-block" />
          {locale === "ru" ? "Открытый доступ · 5 инструментов · 7 языков" :
           locale === "ar" ? "وصول مفتوح · 5 أدوات · 7 لغات" :
           locale === "de" ? "Kostenlos · 5 Werkzeuge · 7 Sprachen" :
           locale === "fr" ? "Accès libre · 5 outils · 7 langues" :
           locale === "es" ? "Acceso libre · 5 herramientas · 7 idiomas" :
           locale === "tr" ? "Açık erişim · 5 araç · 7 dil" :
           "Open access · 5 tools · 7 languages"}
        </div>
        <h1 className="font-syne font-extrabold text-4xl md:text-5xl text-ink leading-tight tracking-tight mb-4">
          {t(INDEX_T.hero_title, lang)}
        </h1>
        <p className="text-ink-2 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
          {t(INDEX_T.hero_sub, lang)}
        </p>
      </section>

      {/* Calculator grid */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
        <CalculatorsIndex />

        {/* Footer note */}
        <p className="text-ink-3 text-xs text-center leading-relaxed border border-border rounded-lg p-4 bg-surface max-w-3xl mx-auto">
          {t(INDEX_T.footer_note, lang)}
        </p>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="font-syne font-extrabold text-base text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">AI Education Platform</span>
          </div>
          <div className="flex gap-4 flex-wrap justify-center text-xs font-syne">
            <Link href="/articles" className="text-ink-3 hover:text-ink transition-colors">Articles</Link>
            <Link href="/calculators" className="text-ink-3 hover:text-ink transition-colors">Calculators</Link>
            <Link href="/pricing" className="text-ink-3 hover:text-ink transition-colors">Pricing</Link>
            <Link href="/how-it-works" className="text-ink-3 hover:text-ink transition-colors">How it works</Link>
          </div>
          <div className="text-ink-3 text-xs font-syne">© 2026 MedMind AI.</div>
        </div>
      </footer>
    </div>
  );
}
