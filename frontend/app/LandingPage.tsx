"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";
import { useT, useI18n, LOCALE_LABELS, type Locale } from "@/lib/i18n";
import { getCategoryLabel } from "@/lib/categories";
import { CategoryIcon, SpecialtyIcon, FeatureIcon } from "@/lib/medical-icons";
import { MiniQuiz } from "@/components/ui/MiniQuiz";
import type { MiniQuizQuestion } from "@/components/ui/MiniQuiz";

type ArticlePreview = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  reading_time_minutes: number;
  cover_image: string | null;
  published_at: string | null;
};

type NewsPreview = {
  id: string;
  slug: string;
  source_name: string;
  title: string;
  summary_excerpt: string;
  category: string;
  original_published_at: string | null;
  fetched_at: string;
};

const SPECIALTY_SLUGS: Record<string, string> = {
  Cardiology: "cardiology", Neurology: "neurology", Surgery: "surgery",
  Pediatrics: "pediatrics", "OB/GYN": "obstetrics", Therapy: "therapy",
};

const LANGS = [
  { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" },
  { value: "de", flag: "🇩🇪" }, { value: "fr", flag: "🇫🇷" },
  { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" },
  { value: "es", flag: "🇪🇸" },
] as const;

type PlatformStats = { articles: number; modules: number; drugs: number; flashcards: number; languages: number };

const RTL_LOCALES = new Set(["ar"]);

export default function LandingPage({
  articles: initialArticles = [],
  stats = { articles: 600, modules: 82, drugs: 800, flashcards: 1000, languages: 7 },
  miniQuiz = null,
  initialLocale,
}: {
  articles: ArticlePreview[];
  stats?: PlatformStats;
  miniQuiz?: { slug: string; questions: MiniQuizQuestion[] } | null;
  initialLocale?: string;
}) {
  const { isAuthenticated } = useAuthStore();
  const t = useT();
  const { locale, setLocale } = useI18n();
  const router = useRouter();

  useEffect(() => {
    if (initialLocale && initialLocale !== "en" && initialLocale !== locale) {
      setLocale(initialLocale as Parameters<typeof setLocale>[0]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialLocale]);

  const isRTL = RTL_LOCALES.has(locale);
  const [menuOpen, setMenuOpen]             = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [articles, setArticles]             = useState<ArticlePreview[]>(initialArticles);
  const [news, setNews]                     = useState<NewsPreview[]>([]);
  const [searchQuery, setSearchQuery]       = useState("");

  const API = process.env.NEXT_PUBLIC_API_URL ?? "";

  useEffect(() => {
    fetch(`${API}/news?locale=${locale}&limit=6`)
      .then(r => r.ok ? r.json() : [])
      .then(data => { if (Array.isArray(data)) setNews(data); })
      .catch(() => {});
  }, [locale]);

  useEffect(() => {
    const seen: Record<string, number> = {};
    const url = locale === "en"
      ? `${API}/articles?limit=24`
      : `${API}/articles?limit=24&locale=${locale}`;
    fetch(url)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data?.articles) return;
        setArticles(
          (data.articles as ArticlePreview[])
            .filter(a => { seen[a.category] = (seen[a.category] ?? 0) + 1; return seen[a.category] <= 3; })
            .slice(0, 10)
        );
      })
      .catch(() => {});
  }, [locale]);

  const features = t("landing.preview_features") as unknown as { icon: string; title: string; desc: string }[];
  const specs    = t("landing.specialties")       as unknown as { icon: string; name: string; count: number }[];

  const articleCategories = Array.from(new Set(articles.map(a => a.category)));
  const filteredArticles  = activeCategory === "all" ? articles : articles.filter(a => a.category === activeCategory);

  const loc = (en: string, ru: string, es: string, ar: string, de: string, fr: string, tr: string) =>
    locale === "ru" ? ru : locale === "es" ? es : locale === "ar" ? ar :
    locale === "de" ? de : locale === "fr" ? fr : locale === "tr" ? tr : en;

  return (
    <div className="min-h-screen bg-bg" dir={isRTL ? "rtl" : "ltr"}>

      {/* ── Navigation ───────────────────────────────────────────────────────── */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {[
              { href: "/nurses/nclex",    label: loc("Exams", "Экзамены", "Exámenes", "الامتحانات", "Prüfungen", "Examens", "Sınavlar") },
              { href: "/how-it-works",    label: t("landing.nav_how") },
              { href: "/articles",        label: t("landing.nav_articles") },
              { href: "/calculators",     label: t("landing.nav_calculators") },
              { href: "/drugs",           label: t("landing.nav_drugs") },
              { href: "/pricing",         label: t("landing.nav_pricing") },
            ].map(item => (
              <Link key={item.href} href={item.href}
                className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2 whitespace-nowrap">
                {item.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <select value={locale} onChange={e => setLocale(e.target.value as Locale)}
              className="hidden sm:block text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none"
              aria-label="Language">
              {LANGS.map(l => <option key={l.value} value={l.value}>{l.flag} {LOCALE_LABELS[l.value as Locale]}</option>)}
            </select>

            {isAuthenticated ? (
              <Link href="/dashboard" className="font-syne font-bold text-sm bg-red text-white px-3 sm:px-4 py-2 rounded hover:bg-ink transition-colors whitespace-nowrap">
                {t("landing.go_to_dashboard")}
              </Link>
            ) : (
              <>
                <Link href="/login" className="hidden sm:block font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
                  {t("landing.nav_sign_in")}
                </Link>
                <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-3 sm:px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">
                  {t("landing.nav_register")}
                </Link>
              </>
            )}

            <button onClick={() => setMenuOpen(v => !v)}
              className="md:hidden p-2 rounded text-ink-2 hover:text-ink hover:bg-surface-2 transition-colors" aria-label="Menu">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {menuOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
              </svg>
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="md:hidden border-t border-border bg-surface px-4 py-3 space-y-1">
            {[
              { href: "/nurses/nclex", label: loc("Exams", "Экзамены", "Exámenes", "الامتحانات", "Prüfungen", "Examens", "Sınavlar") },
              { href: "/how-it-works", label: t("landing.nav_how") },
              { href: "/articles",     label: t("landing.nav_articles") },
              { href: "/news",         label: t("landing.nav_news") },
              { href: "/calculators",  label: t("landing.nav_calculators") },
              { href: "/drugs",        label: t("landing.nav_drugs") },
              { href: "/pricing",      label: t("landing.nav_pricing") },
              { href: "/bots",         label: "Telegram Bot" },
              { href: "/login",        label: t("landing.nav_sign_in") },
            ].map(item => (
              <Link key={item.href} href={item.href} onClick={() => setMenuOpen(false)}
                className="block font-syne font-semibold text-sm text-ink-2 hover:text-ink px-3 py-2.5 rounded-lg hover:bg-surface-2 transition-colors">
                {item.label}
              </Link>
            ))}
            <div className="pt-2 flex gap-2 flex-wrap">
              {LANGS.map(l => (
                <button key={l.value} onClick={() => { setLocale(l.value as Locale); setMenuOpen(false); }}
                  className={`flex items-center gap-1 text-sm rounded px-2 py-1 transition-colors ${locale === l.value ? "bg-ink/10 ring-1 ring-ink/20 font-syne font-bold" : "hover:bg-surface-2 text-ink-2"}`}>
                  <span className="text-base">{l.flag}</span>
                  <span className="text-xs font-syne">{l.value.toUpperCase()}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-14 sm:pt-20 pb-10 sm:pb-14 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-6">
          <span className="w-2 h-2 rounded-full bg-green-2 animate-pulse inline-block" />
          {t("landing.hero_badge")}
        </div>

        <h1 className="font-syne font-extrabold text-4xl sm:text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-3">
          {t("landing.hero_v4_title") as string}
        </h1>
        <p className="font-syne font-extrabold text-3xl sm:text-4xl md:text-5xl text-ink-2 leading-tight tracking-tight mb-6">
          {t("landing.hero_v4_title2") as string}
        </p>
        <p className="text-ink-2 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed mb-10 px-2">
          {t("landing.hero_v4_sub") as string}
        </p>

        {isAuthenticated ? (
          <Link href="/dashboard"
            className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-3.5 rounded-xl hover:bg-ink/80 transition-colors">
            {t("landing.go_to_dashboard") as string}
          </Link>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
            <Link href="/register"
              className="group flex flex-col gap-2 bg-ink text-white rounded-2xl p-6 text-start hover:bg-ink/90 transition-colors">
              <span className="text-2xl">🩺</span>
              <span className="font-syne font-bold text-lg leading-snug">{t("landing.audience_pro_title") as string}</span>
              <span className="text-white/60 text-sm">{t("landing.audience_pro_sub") as string}</span>
              <span className="mt-auto text-sm font-syne font-semibold text-white/80 group-hover:text-white">{t("landing.audience_pro_cta") as string}</span>
            </Link>
            <Link href="/learn"
              className="group flex flex-col gap-2 bg-surface border-2 border-border rounded-2xl p-6 text-start hover:border-ink transition-colors">
              <span className="text-2xl">🌿</span>
              <span className="font-syne font-bold text-lg text-ink leading-snug">{t("landing.audience_patient_title") as string}</span>
              <span className="text-ink-3 text-sm">{t("landing.audience_patient_sub") as string}</span>
              <span className="mt-auto text-sm font-syne font-semibold text-ink-2 group-hover:text-ink">{t("landing.audience_patient_cta") as string}</span>
            </Link>
          </div>
        )}
        <p className="text-ink-3 text-xs mt-5 font-syne">{t("landing.hero_note")}</p>
      </section>

      {/* ── Stats bar ────────────────────────────────────────────────────────── */}
      <section className="border-y border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-5 sm:py-6 grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 text-center">
          {[
            { val: `${stats.articles > 0 ? `${stats.articles}+` : "600+"}`, label: t("landing.pipeline_stat_articles") as string },
            { val: `${stats.modules > 0 ? `${stats.modules}+` : "82+"}`,   label: t("landing.stats_modules") as string },
            { val: `${stats.drugs > 0 ? `${stats.drugs}+` : "800+"}`,       label: t("landing.stats_drugs") as string },
            { val: `${stats.flashcards > 0 ? `${stats.flashcards}+` : "1000+"}`, label: t("landing.stats_flashcards") as string },
          ].map((s, i) => (
            <div key={i}>
              <div className="font-syne font-extrabold text-xl sm:text-2xl text-ink">{s.val}</div>
              <div className="text-ink-3 text-[10px] sm:text-xs font-syne uppercase tracking-widest mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── NCLEX + Gulf Exam Hub teaser ─────────────────────────────────────── */}
      <section className="bg-surface border-b border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-red/10 border border-red/20 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-4">
                <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
                {loc("Nursing Exams", "Сестринские экзамены", "Exámenes de Enfermería", "امتحانات التمريض", "Pflegeprüfungen", "Examens infirmiers", "Hemşirelik Sınavları")}
              </div>
              <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-3 leading-tight">
                {loc(
                  "Pass NCLEX-RN & Gulf Exams on your first attempt.",
                  "Сдайте NCLEX-RN и экзамены Залива с первого раза.",
                  "Aprueba NCLEX-RN y exámenes del Golfo a la primera.",
                  "اجتز NCLEX-RN وامتحانات الخليج من المحاولة الأولى.",
                  "Bestehe NCLEX-RN & Gulf-Prüfungen beim ersten Versuch.",
                  "Réussissez NCLEX-RN & examens du Golfe dès le premier essai.",
                  "NCLEX-RN ve Körfez Sınavlarını ilk denemede geçin."
                )}
              </h2>
              <p className="text-ink-2 text-sm leading-relaxed mb-6 max-w-md">
                {loc(
                  "Adaptive CAT simulations, AI-powered error analysis, full analytics. NCLEX-RN · SNLE · DHA · QCHP · OMSB · HAAD and more. 600+ questions including SATA, calculations, and NGN format.",
                  "Адаптивные CAT-симуляции, ИИ-разбор ошибок, полная аналитика. NCLEX-RN · SNLE · DHA · QCHP · OMSB · HAAD и другие. 600+ вопросов: SATA, расчёты, NGN-формат.",
                  "Simulaciones CAT adaptativas, análisis de errores con IA. NCLEX-RN · SNLE · DHA · QCHP y más. 600+ preguntas incluyendo SATA, cálculos y NGN.",
                  "محاكاة CAT تكيفية، تحليل الأخطاء بالذكاء الاصطناعي. NCLEX-RN · SNLE · DHA · QCHP والمزيد. أكثر من 600 سؤال.",
                  "Adaptive CAT-Simulationen, KI-Fehleranalyse. NCLEX-RN · SNLE · DHA · QCHP und mehr. 600+ Fragen.",
                  "Simulations CAT adaptatives, analyse IA. NCLEX-RN · SNLE · DHA · QCHP et plus. 600+ questions.",
                  "Uyarlanabilir CAT simülasyonları, yapay zeka analizi. NCLEX-RN · SNLE · DHA · QCHP ve daha fazlası."
                )}
              </p>
              <ul className="space-y-2.5 mb-8">
                {[
                  loc("Adaptive CAT: 75–145 questions, just like the real NCLEX", "Адаптивный CAT: 75–145 вопросов, как на реальном NCLEX", "CAT adaptativo: 75–145 preguntas", "CAT تكيفي: 75–145 سؤال", "Adaptiver CAT: 75–145 Fragen", "CAT adaptatif: 75–145 questions", "Uyarlanabilir CAT: 75–145 soru"),
                  loc("Gulf full simulations: SNLE 200q · DHA/QCHP/OMSB 100q", "Gulf полные симуляции: SNLE 200q · DHA/QCHP/OMSB 100q", "Simulaciones Gulf: SNLE 200q · DHA/QCHP 100q", "محاكاة الخليج: SNLE 200 سؤال · DHA/QCHP 100 سؤال", "Gulf-Simulationen: SNLE 200q · DHA/QCHP 100q", "Simulations Gulf: SNLE 200q · DHA/QCHP 100q", "Gulf simülasyonları: SNLE 200q · DHA/QCHP 100q"),
                  loc("AI explanation for every wrong answer with clinical reasoning", "ИИ-объяснение к каждому ошибочному ответу с клинической логикой", "Explicación IA para cada error", "شرح ذكاء اصطناعي لكل خطأ", "KI-Erklärung für jede falsche Antwort", "Explication IA pour chaque erreur", "Her yanlış cevap için yapay zeka açıklaması"),
                  loc("Free demo — no sign-up required", "Бесплатный демо — без регистрации", "Demo gratuito — sin registro", "عرض تجريبي مجاني — بدون تسجيل", "Kostenloses Demo — ohne Anmeldung", "Démo gratuit — sans inscription", "Ücretsiz demo — kayıt gerekmez"),
                ].map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-ink-2">
                    <span className="text-red font-bold mt-0.5 flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-3">
                <Link href="/nurses/nclex"
                  className="inline-block font-syne font-bold text-sm bg-red text-white px-6 py-3 rounded-xl hover:bg-ink transition-colors">
                  {loc("NCLEX Practice →", "NCLEX практика →", "Práctica NCLEX →", "تدريب NCLEX →", "NCLEX Übung →", "Pratique NCLEX →", "NCLEX Pratik →")}
                </Link>
                <Link href="/nurses/gulf"
                  className="inline-block font-syne font-bold text-sm bg-surface border-2 border-ink text-ink px-6 py-3 rounded-xl hover:bg-ink hover:text-white transition-colors">
                  {loc("Gulf Exams 🇸🇦", "Gulf экзамены 🇸🇦", "Exámenes Gulf 🇸🇦", "امتحانات الخليج 🇸🇦", "Gulf Prüfungen 🇸🇦", "Examens Gulf 🇸🇦", "Gulf Sınavları 🇸🇦")}
                </Link>
              </div>
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { value: "600+", label: loc("NCLEX questions", "NCLEX вопросов", "preguntas NCLEX", "أسئلة NCLEX", "NCLEX-Fragen", "questions NCLEX", "NCLEX sorusu"), sub: "SATA · CAT · NGN" },
                { value: "7",    label: loc("Gulf exams", "Gulf экзаменов", "exámenes Gulf", "امتحانات الخليج", "Gulf-Prüfungen", "examens Gulf", "Gulf sınavı"), sub: "SNLE · DHA · QCHP · OMSB" },
                { value: "7",    label: loc("NCLEX categories", "категорий NCLEX", "categorías NCLEX", "فئات NCLEX", "NCLEX-Kategorien", "catégories NCLEX", "NCLEX kategorisi"), sub: "Client Needs" },
                { value: "6",    label: loc("CJMM skills", "навыков CJMM", "habilidades CJMM", "مهارات CJMM", "CJMM-Kompetenzen", "compétences CJMM", "CJMM becerileri"), sub: loc("Clinical Judgment", "Клиническое суждение", "Juicio clínico", "الحكم السريري", "Klinisches Urteil", "Jugement clinique", "Klinik Yargı") },
              ].map((s) => (
                <div key={s.label} className="bg-bg border border-border rounded-xl p-5 flex flex-col gap-1">
                  <span className="font-syne font-extrabold text-3xl text-ink">{s.value}</span>
                  <span className="font-syne font-semibold text-sm text-ink leading-tight">{s.label}</span>
                  <span className="text-xs text-ink-3">{s.sub}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Telegram Bot ─────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-[#229ED9]/10 border border-[#229ED9]/30 px-3 py-1 rounded-full font-syne font-semibold text-xs text-[#229ED9] mb-4">
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 13.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z"/></svg>
              {t("landing.tg_badge")}
            </div>
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-3">
              {t("landing.tg_title")}
            </h2>
            <p className="text-ink-2 mb-6 leading-relaxed">{t("landing.tg_desc")}</p>
            <ul className="space-y-3 mb-8">
              {(t("landing.tg_features") as unknown as { icon: string; title: string; desc: string }[]).map((f) => (
                <li key={f.title} className="flex gap-3 items-start">
                  <span className="text-lg leading-none mt-0.5">{f.icon}</span>
                  <div>
                    <span className="font-syne font-semibold text-sm text-ink">{f.title} — </span>
                    <span className="font-serif text-sm text-ink-3">{f.desc}</span>
                  </div>
                </li>
              ))}
            </ul>
            <div className="flex flex-col sm:flex-row gap-3">
              <a href="https://t.me/Medmindpro_bot" target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 bg-[#229ED9] hover:bg-[#1a8cbf] text-white font-syne font-bold px-6 py-3 rounded-xl transition-colors">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 13.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z"/></svg>
                {t("landing.tg_open")}
              </a>
              <Link href="/bots"
                className="inline-flex items-center justify-center gap-2 border border-border text-ink-2 hover:border-ink hover:text-ink font-syne font-semibold px-6 py-3 rounded-xl transition-colors text-sm">
                {t("landing.tg_learn_more")}
              </Link>
            </div>
          </div>

          {/* Animated chat demo */}
          <div className="relative">
            <div className="bg-[#17212B] rounded-2xl overflow-hidden shadow-2xl border border-white/5 max-w-sm mx-auto">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
                <div className="w-9 h-9 rounded-full bg-[#229ED9] flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">AI</span>
                </div>
                <div>
                  <div className="text-white font-semibold text-sm">MedMind AI</div>
                  <div className="text-white/40 text-xs">@Medmindpro_bot · online</div>
                </div>
              </div>
              <div className="px-4 py-4 space-y-3 min-h-[240px]">
                <div className="flex justify-end">
                  <div className="bg-[#2B5278] text-white text-xs rounded-xl rounded-tr-sm px-3 py-2 max-w-[75%] leading-relaxed">
                    What&apos;s the mechanism of beta-blockers in heart failure?
                  </div>
                </div>
                <div className="flex gap-2">
                  <div className="w-7 h-7 rounded-full bg-[#229ED9] flex items-center justify-center flex-shrink-0 text-white text-[10px] font-bold mt-0.5">AI</div>
                  <div className="bg-[#182533] text-white/90 text-xs rounded-xl rounded-tl-sm px-3 py-2 max-w-[80%] leading-relaxed space-y-1.5">
                    <p><strong>Beta-blockers</strong> block chronic sympathetic overstimulation that damages the myocardium.</p>
                    <p>↓ HR → ↑ diastolic filling · ↓ O₂ demand · Anti-arrhythmic</p>
                    <p className="text-white/40">💡 Start low, go slow — stable patients only.</p>
                  </div>
                </div>
                <div className="flex gap-2 items-end">
                  <div className="w-7 h-7 rounded-full bg-[#229ED9] flex items-center justify-center flex-shrink-0 text-white text-[10px] font-bold">AI</div>
                  <div className="bg-[#182533] rounded-xl rounded-tl-sm px-4 py-3">
                    <div className="flex gap-1 items-center">
                      <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{animationDelay:"0ms"}}/>
                      <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{animationDelay:"150ms"}}/>
                      <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{animationDelay:"300ms"}}/>
                    </div>
                  </div>
                </div>
              </div>
              <div className="px-3 py-3 border-t border-white/10 flex gap-2 items-center">
                <div className="flex-1 bg-[#182533] rounded-full px-4 py-2 text-white/30 text-xs font-syne">
                  {t("landing.tg_placeholder")}
                </div>
                <div className="w-8 h-8 rounded-full bg-[#229ED9] flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                </div>
              </div>
            </div>
            <div className="absolute -bottom-3 -right-3 bg-green-2 text-white text-xs font-syne font-bold px-3 py-1.5 rounded-full shadow-lg">
              {t("landing.tg_free")}
            </div>
          </div>
        </div>
      </section>

      {/* ── Search bar ───────────────────────────────────────────────────────── */}
      <section className="max-w-2xl mx-auto px-4 sm:px-6 py-4 sm:py-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (searchQuery.trim()) router.push(`/articles?search=${encodeURIComponent(searchQuery.trim())}`);
          }}
          className="relative"
        >
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("landing.search_hero_placeholder") as string}
            className="w-full bg-surface border border-border rounded-2xl px-5 py-4 pr-32 font-syne text-ink placeholder-ink-3 text-sm focus:outline-none focus:border-ink transition-colors shadow-sm"
          />
          <button type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-ink text-white font-syne font-semibold text-sm px-4 py-2 rounded-xl hover:bg-ink/80 transition-colors">
            {t("landing.search_hero_btn") as string}
          </button>
        </form>
        <p className="text-center text-ink-3 text-xs mt-2 font-syne">{t("landing.search_hero_hint") as string}</p>
      </section>

      {/* ── Mini Quiz ────────────────────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1 rounded-full font-syne font-semibold text-xs text-ink-3 mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block animate-pulse" />
            {t("landing.demo_badge")}
          </div>
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">
            {t("landing.quiz_title") as string}
          </h2>
          <p className="text-ink-3 text-sm max-w-md mx-auto">{t("landing.quiz_sub") as string}</p>
        </div>
        <div className="bg-surface border border-border rounded-2xl p-6 sm:p-8">
          {miniQuiz ? (
            <MiniQuiz questions={miniQuiz.questions} quizSlug={miniQuiz.slug} />
          ) : (
            <MiniQuiz
              questions={[{
                question: t("landing.demo_question") as string,
                options: t("landing.demo_options") as unknown as string[],
                correct_index: t("landing.demo_correct") as unknown as number,
                explanation: t("landing.demo_explanation") as string,
              }]}
            />
          )}
        </div>
      </section>

      {/* ── Articles ─────────────────────────────────────────────────────────── */}
      {articles.length > 0 && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 sm:mb-10">
            <div>
              <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1 rounded-full font-syne font-semibold text-xs text-ink-3 mb-3">
                <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
                {t("landing.articles_badge")}
              </div>
              <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink">{t("landing.articles_title")}</h2>
              <p className="text-ink-3 text-sm mt-1.5 max-w-lg">{articles.length}+ {t("landing.articles_subtitle")}</p>
            </div>
            <Link href="/articles"
              className="flex-shrink-0 font-syne font-semibold text-sm border border-border text-ink-2 px-5 py-2.5 rounded-lg hover:border-ink hover:text-ink transition-colors self-start sm:self-auto">
              {t("landing.articles_all")}
            </Link>
          </div>

          {articleCategories.length > 1 && (
            <div className="flex flex-wrap gap-2 mb-8">
              <button onClick={() => setActiveCategory("all")}
                className={`font-syne font-semibold text-xs px-3.5 py-1.5 rounded-full border transition-colors ${
                  activeCategory === "all" ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink hover:text-ink bg-surface"
                }`}>
                {t("landing.articles_all_topics")}
              </button>
              {articleCategories.map(cat => (
                <button key={cat} onClick={() => setActiveCategory(cat)}
                  className={`inline-flex items-center gap-1.5 font-syne font-semibold text-xs px-3.5 py-1.5 rounded-full border transition-colors ${
                    activeCategory === cat ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink hover:text-ink bg-surface"
                  }`}>
                  <CategoryIcon category={cat} size={11} strokeWidth={2} />
                  {getCategoryLabel(cat, locale === "en" ? "en" : locale)}
                </button>
              ))}
            </div>
          )}

          {filteredArticles.length > 0 && (
            <>
              <Link href={`/articles/${filteredArticles[0].slug}`}
                className="group block mb-6 bg-surface border border-border rounded-xl overflow-hidden hover:border-ink hover:shadow-lg transition-all">
                <div className="flex flex-col md:flex-row">
                  {filteredArticles[0].cover_image ? (
                    <div className="md:w-2/5 h-52 md:h-auto overflow-hidden bg-surface-2 flex-shrink-0">
                      <img src={filteredArticles[0].cover_image} alt={filteredArticles[0].title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="eager" />
                    </div>
                  ) : (
                    <div className="md:w-2/5 h-52 md:h-auto bg-gradient-to-br from-surface-2 to-surface flex items-center justify-center flex-shrink-0 text-ink-3">
                      <CategoryIcon category={filteredArticles[0].category} size={64} strokeWidth={1} />
                    </div>
                  )}
                  <div className="flex flex-col justify-center p-6 sm:p-8">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-ink-3"><CategoryIcon category={filteredArticles[0].category} size={14} /></span>
                      <span className="font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">
                        {getCategoryLabel(filteredArticles[0].category, locale)}
                      </span>
                      <span className="text-ink-3 text-xs ml-auto">{filteredArticles[0].reading_time_minutes} {t("landing.articles_min_read")}</span>
                    </div>
                    <h3 className="font-syne font-extrabold text-xl sm:text-2xl text-ink mb-3 group-hover:text-red transition-colors leading-snug">
                      {filteredArticles[0].title}
                    </h3>
                    <p className="text-ink-2 text-sm leading-relaxed line-clamp-3 mb-4">{filteredArticles[0].excerpt}</p>
                    <span className="font-syne font-semibold text-sm text-red group-hover:underline">{t("landing.articles_read")}</span>
                  </div>
                </div>
              </Link>

              {filteredArticles.length > 1 && (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  {filteredArticles.slice(1, 7).map(article => (
                    <Link key={article.id} href={`/articles/${article.slug}`}
                      className="group flex flex-col bg-surface border border-border rounded-xl overflow-hidden hover:border-ink hover:shadow-md transition-all">
                      {article.cover_image ? (
                        <div className="h-36 overflow-hidden bg-surface-2">
                          <img src={article.cover_image} alt={article.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
                        </div>
                      ) : (
                        <div className="h-36 bg-gradient-to-br from-surface-2 to-surface flex items-center justify-center text-ink-3">
                          <CategoryIcon category={article.category} size={40} strokeWidth={1} />
                        </div>
                      )}
                      <div className="flex flex-col flex-1 p-4">
                        <div className="flex items-center gap-1.5 mb-2">
                          <span className="font-syne font-semibold text-[10px] text-ink-3 uppercase tracking-wider">
                            {getCategoryLabel(article.category, locale)}
                          </span>
                          <span className="text-ink-3 text-[10px] ml-auto">{article.reading_time_minutes} {t("landing.articles_min_read")}</span>
                        </div>
                        <h3 className="font-syne font-bold text-sm text-ink mb-2 line-clamp-2 group-hover:text-red transition-colors leading-snug flex-1">
                          {article.title}
                        </h3>
                        <p className="text-ink-3 text-xs leading-relaxed line-clamp-2">{article.excerpt}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </>
          )}

          <div className="mt-10 flex flex-col sm:flex-row gap-3 items-center justify-center">
            <Link href="/articles"
              className="inline-flex items-center gap-2 font-syne font-bold text-sm bg-ink text-white px-7 py-3 rounded-lg hover:bg-red transition-colors">
              {t("landing.articles_cta")} <span>→</span>
            </Link>
            {!isAuthenticated && (
              <Link href="/register" className="font-syne font-semibold text-sm text-red hover:underline">
                {t("landing.articles_unlock")}
              </Link>
            )}
          </div>
          <p className="text-ink-3 text-xs mt-3 text-center font-syne">{t("landing.articles_stats")}</p>
        </section>
      )}

      {/* ── Specialties ──────────────────────────────────────────────────────── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("landing.specialties_title")}</h2>
          <p className="text-ink-3 text-center mb-10 sm:mb-12 text-sm">{t("landing.specialties_subtitle")}</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
            {(Array.isArray(specs) ? specs : []).map((s, i) => (
              <Link key={i} href={`/articles?category=${SPECIALTY_SLUGS[s.name] ?? "cardiology"}`}
                className="bg-bg border border-border rounded-lg p-4 text-center hover:border-ink hover:shadow-sm transition-all group">
                <div className="w-12 h-12 rounded-xl bg-surface mx-auto flex items-center justify-center mb-3 text-ink-3 group-hover:bg-red group-hover:text-white transition-colors">
                  <SpecialtyIcon name={s.name} size={24} strokeWidth={1.5} />
                </div>
                <div className="font-syne font-bold text-sm text-ink leading-tight">{s.name}</div>
                <div className="text-ink-3 text-xs mt-1">{s.count} {t("landing.specialties_modules")}</div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Clinical Calculators teaser ──────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1 rounded-full font-syne font-semibold text-xs text-ink-3 mb-3">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-2 inline-block" />
              {loc("Clinical tools", "Клинические инструменты", "Herramientas clínicas", "الأدوات السريرية", "Klinische Tools", "Outils cliniques", "Klinik araçlar")}
            </div>
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink">{t("landing.nav_calculators")}</h2>
            <p className="text-ink-3 text-sm mt-1.5 max-w-lg">
              {loc(
                "Evidence-based scoring tools used daily by clinicians worldwide. Free, in your language.",
                "Доказательные шкалы, которыми врачи пользуются каждый день. Бесплатно, на вашем языке.",
                "Herramientas de puntuación usadas diariamente. Gratis, en tu idioma.",
                "أدوات تقييم قائمة على الأدلة يستخدمها الأطباء يومياً. مجانية، بلغتك.",
                "Evidenzbasierte Scoring-Tools, täglich von Klinikern eingesetzt. Kostenlos.",
                "Outils de scoring validés utilisés quotidiennement. Gratuit.",
                "Klinisyenlerin günlük kullandığı kanıta dayalı puanlama araçları. Ücretsiz."
              )}
            </p>
          </div>
          <Link href="/calculators" className="font-syne font-bold text-sm text-red hover:underline whitespace-nowrap flex-shrink-0">
            {loc("All calculators →", "Все калькуляторы →", "Todas las calculadoras →", "جميع الآلات الحاسبة →", "Alle Rechner →", "Tous les calculateurs →", "Tüm hesap makineleri →")}
          </Link>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { slug: "cha2ds2-vasc", icon: "❤️", cat: loc("Cardiology","Кардиология","Cardiología","أمراض القلب","Kardiologie","Cardiologie","Kardiyoloji"), name: "CHA₂DS₂-VASc", desc: loc("Stroke risk in atrial fibrillation","Риск инсульта при фибрилляции предсердий","Riesgo de ictus en fibrilación auricular","خطر السكتة الدماغية في الرجفان الأذيني","Schlaganfallrisiko bei Vorhofflimmern","Risque d'AVC dans la fibrillation auriculaire","Atriyal fibrilasyonda inme riski") },
            { slug: "curb-65",      icon: "🫁", cat: loc("Pulmonology","Пульмонология","Neumología","أمراض الرئة","Pneumologie","Pneumologie","Pulmonoloji"),   name: "CURB-65",      desc: loc("Community-acquired pneumonia severity","Тяжесть внебольничной пневмонии","Gravedad de la neumonía comunitaria","شدة الالتهاب الرئوي المكتسب من المجتمع","Schweregrad der CAP","Sévérité de la pneumonie","Toplum kökenli pnömoni şiddeti") },
            { slug: "egfr-ckd-epi", icon: "🫘", cat: loc("Nephrology","Нефрология","Nefrología","أمراض الكلى","Nephrologie","Néphrologie","Nefroloji"),        name: "eGFR (CKD-EPI)", desc: loc("Kidney function and CKD staging","Функция почек и стадия ХБП","Función renal y estadio de ERC","وظائف الكلى وتصنيف مرض الكلى المزمن","Nierenfunktion und CKD-Stadium","Fonction rénale et stadification","Böbrek fonksiyonu ve KBH evresi") },
          ].map(c => (
            <Link key={c.slug} href={`/calculators/${c.slug}`}
              className="group bg-surface border border-border rounded-xl p-5 hover:border-ink hover:shadow-sm transition-all flex flex-col gap-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-2xl">{c.icon}</span>
                <span className="text-xs font-syne font-semibold text-ink-3 bg-bg px-2 py-0.5 rounded-full border border-border">{c.cat}</span>
              </div>
              <div>
                <h3 className="font-syne font-bold text-base text-ink group-hover:text-red transition-colors leading-tight mb-1">{c.name}</h3>
                <p className="text-ink-3 text-sm leading-snug">{c.desc}</p>
              </div>
              <span className="text-red font-syne font-semibold text-sm mt-auto">
                {loc("Open →","Открыть →","Abrir →","فتح →","Öffnen →","Ouvrir →","Aç →")}
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* ── News block ───────────────────────────────────────────────────────── */}
      {news.length > 0 && (
        <section className="bg-surface border-y border-border">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 sm:mb-10">
              <div>
                <div className="inline-flex items-center gap-2 bg-bg border border-border px-3 py-1 rounded-full font-syne font-semibold text-xs text-ink-3 mb-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block animate-pulse" />
                  {t("landing.news_badge")}
                </div>
                <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink">{t("landing.news_title")}</h2>
                <p className="text-ink-3 text-sm mt-1.5 max-w-lg">{t("landing.news_subtitle")}</p>
              </div>
              <Link href="/news"
                className="flex-shrink-0 font-syne font-semibold text-sm border border-border text-ink-2 px-5 py-2.5 rounded-lg hover:border-ink hover:text-ink transition-colors self-start sm:self-auto">
                {t("landing.news_all")}
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {news.map(item => (
                <Link key={item.id} href={`/news/${item.slug}`}
                  className="group bg-bg border border-border rounded-xl p-5 hover:border-ink hover:shadow-sm transition-all flex flex-col">
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="text-xs font-syne font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                      {item.source_name}
                    </span>
                    <span className="text-xs text-ink-3 font-syne flex-shrink-0">
                      {(item.original_published_at || item.fetched_at || "").split("T")[0]}
                    </span>
                  </div>
                  <span className="text-xs font-syne font-semibold text-red uppercase tracking-wide mb-2">
                    {getCategoryLabel(item.category, locale) || item.category.replace(/-/g, " ")}
                  </span>
                  <h3 className="font-syne font-bold text-sm text-ink group-hover:text-red transition-colors leading-snug mb-2 line-clamp-3">
                    {item.title}
                  </h3>
                  <p className="text-xs text-ink-2 leading-relaxed line-clamp-3 flex-1">{item.summary_excerpt}</p>
                  <span className="mt-4 text-xs font-syne font-semibold text-red flex items-center gap-1">{t("landing.news_read")}</span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Content pipeline ─────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="text-center mb-12">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">
            {t("landing.pipeline_title") as string}
          </h2>
          <p className="text-ink-3 text-sm">{t("landing.pipeline_sub") as string}</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {([
            { num: "1", title: t("landing.pipeline_step1_title") as string, body: t("landing.pipeline_step1") as string, color: "bg-blue-50 border-blue-200 text-blue-700" },
            { num: "2", title: t("landing.pipeline_step2_title") as string, body: t("landing.pipeline_step2") as string, color: "bg-violet-50 border-violet-200 text-violet-700" },
            { num: "3", title: t("landing.pipeline_step3_title") as string, body: t("landing.pipeline_step3") as string, color: "bg-emerald-50 border-emerald-200 text-emerald-700" },
            { num: "4", title: t("landing.pipeline_step4_title") as string, body: t("landing.pipeline_step4") as string, color: "bg-amber-50 border-amber-200 text-amber-700" },
          ] as const).map((step) => (
            <div key={step.num} className={`rounded-2xl border p-6 ${step.color.split(" ").slice(0, 2).join(" ")}`}>
              <div className={`inline-flex items-center justify-center w-8 h-8 rounded-full border font-syne font-extrabold text-sm mb-4 ${step.color}`}>
                {step.num}
              </div>
              <h3 className="font-syne font-bold text-sm text-ink mb-2">{step.title}</h3>
              <p className="text-ink-3 text-xs leading-relaxed">{step.body}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-6 border-t border-border pt-8">
          <div className="flex gap-8 text-center">
            {[
              { val: `${stats.articles > 0 ? `${stats.articles}+` : "600+"}`, label: t("landing.pipeline_stat_articles") as string },
              { val: `${stats.modules > 0 ? `${stats.modules}+` : "82+"}`,   label: t("landing.pipeline_stat_modules") as string },
              { val: `${stats.drugs > 0 ? `${stats.drugs}+` : "800+"}`,       label: t("landing.stats_drugs") as string },
              { val: `${stats.languages}`,                                      label: t("landing.pipeline_stat_langs") as string },
            ].map((s) => (
              <div key={s.label}>
                <div className="font-syne font-extrabold text-2xl text-ink">{s.val}</div>
                <div className="text-ink-3 text-xs font-syne mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
          <Link href="/editorial-policy"
            className="font-syne font-semibold text-sm text-ink-2 hover:text-ink border border-border rounded-xl px-5 py-2.5 hover:border-ink transition-colors flex-shrink-0">
            {t("landing.pipeline_editorial") as string}
          </Link>
        </div>
      </section>

      {/* ── Platform features ────────────────────────────────────────────────── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <div className="text-center mb-10 sm:mb-14">
            <div className="inline-flex items-center gap-2 bg-bg border border-border px-3 py-1 rounded-full font-syne font-semibold text-xs text-ink-3 mb-3">
              <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
              {t("landing.preview_badge")}
            </div>
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">{t("landing.preview_title")}</h2>
            <p className="text-ink-3 text-sm max-w-xl mx-auto">{t("landing.preview_subtitle")}</p>
          </div>
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-5">
            {(Array.isArray(features) ? features : []).map((f, i) => {
              const links = ["/dashboard", "/dashboard", "/dashboard", "/how-it-works", "/articles", "/drugs"];
              return (
                <Link key={i} href={isAuthenticated ? links[i] : "/register"}
                  className="group flex gap-4 bg-bg border border-border rounded-xl p-5 hover:border-ink hover:shadow-sm transition-all">
                  <div className="w-10 h-10 rounded-lg bg-surface border border-border flex items-center justify-center text-red flex-shrink-0 group-hover:bg-red group-hover:text-white transition-colors">
                    <FeatureIcon name={f.icon} size={20} strokeWidth={1.75} />
                  </div>
                  <div>
                    <h3 className="font-syne font-bold text-sm text-ink mb-1">{f.title}</h3>
                    <p className="text-ink-3 text-xs leading-relaxed">{f.desc}</p>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────────────── */}
      <section className="bg-ink text-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">{t("landing.cta_title")}</h2>
          <p className="text-white/60 mb-3 text-base leading-relaxed max-w-xl mx-auto">{t("landing.cta_subtitle")}</p>
          <p className="text-white/40 text-sm mb-8 font-syne">
            {loc("From $15/mo · Free demo available · No credit card required",
                 "От $15/мес · Бесплатный демо · Карта не нужна",
                 "Desde $15/mes · Demo gratuito · Sin tarjeta",
                 "من $15 شهرياً · عرض تجريبي مجاني",
                 "Ab $15/Monat · Kostenloses Demo",
                 "À partir de $15/mois · Démo gratuit",
                 "$15/ay'dan · Ücretsiz demo")}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/register"
              className="inline-block font-syne font-bold text-base bg-white text-ink px-8 sm:px-10 py-4 rounded hover:bg-red hover:text-white transition-colors">
              {t("landing.cta_btn")}
            </Link>
            <Link href="/articles"
              className="inline-block font-syne font-semibold text-base border border-white/30 text-white/80 px-8 sm:px-10 py-4 rounded hover:border-white hover:text-white transition-colors">
              {t("landing.footer_browse_articles")}
            </Link>
          </div>
          <p className="text-white/30 text-xs mt-5 font-syne">{t("landing.hero_note")}</p>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-6">
            <div>
              <div className="font-syne font-extrabold text-lg text-ink">
                Med<span className="text-red">Mind</span>
              </div>
              <p className="text-ink-3 text-xs mt-0.5 font-syne">{t("landing.footer_tagline")}</p>
            </div>
            <div className="flex gap-4 sm:gap-6 flex-wrap">
              {[
                { href: "/nurses/nclex", label: loc("Exams","Экзамены","Exámenes","الامتحانات","Prüfungen","Examens","Sınavlar") },
                { href: "/how-it-works", label: t("landing.nav_how") },
                { href: "/articles",     label: t("landing.nav_articles") },
                { href: "/calculators",  label: t("landing.nav_calculators") },
                { href: "/drugs",        label: t("landing.nav_drugs") },
                { href: "/pricing",      label: t("landing.nav_pricing") },
                { href: "/bots",         label: "Telegram Bot" },
                { href: "/investors",    label: t("landing.footer_investors") },
              ].map(item => (
                <Link key={item.href} href={item.href} className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-4 pb-5 border-b border-border">
            {[
              { href: "/about",              label: t("landing.footer_about") },
              { href: "/editorial-policy",   label: t("landing.footer_editorial") },
              { href: "/medical-disclaimer", label: t("landing.footer_disclaimer") },
              { href: "/contact",            label: t("landing.footer_contact") },
            ].map(item => (
              <Link key={item.href} href={item.href} className="text-ink-3 text-xs hover:text-ink transition-colors font-syne underline">
                {item.label}
              </Link>
            ))}
          </div>
          <div className="pt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
            <p className="text-ink-3 text-[11px] font-syne max-w-lg">{t("landing.footer_legal")}</p>
            <div className="text-ink-3 text-xs font-syne flex-shrink-0">{t("landing.footer_copy")}</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
