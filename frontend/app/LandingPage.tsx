"use client";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";
import { useT, useI18n } from "@/lib/i18n";
import { getCategoryLabel } from "@/lib/categories";
import { CategoryIcon, SpecialtyIcon, FeatureIcon } from "@/lib/medical-icons";

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

export default function LandingPage({ articles: initialArticles = [] }: { articles: ArticlePreview[] }) {
  const { isAuthenticated } = useAuthStore();
  const t = useT();
  const { locale, setLocale } = useI18n();
  const [menuOpen, setMenuOpen]       = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [articles, setArticles]       = useState<ArticlePreview[]>(initialArticles);
  const [demoAnswer, setDemoAnswer]   = useState<number | null>(null);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "";

  // Reload articles whenever locale changes
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
  const demoOptions = t("landing.demo_options")   as unknown as string[];
  const correctIdx  = t("landing.demo_correct")   as unknown as number;

  const articleCategories = Array.from(new Set(articles.map(a => a.category)));
  const filteredArticles  = activeCategory === "all" ? articles : articles.filter(a => a.category === activeCategory);

  return (
    <div className="min-h-screen bg-bg">

      {/* ── Navigation ───────────────────────────────────────────────────────── */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {[
              { href: "/articles",     label: t("landing.nav_articles") },
              { href: "/how-it-works", label: t("landing.nav_how") },
              { href: "/calculators",  label: t("landing.nav_calculators") },
              { href: "/drugs",        label: t("landing.nav_drugs") },
              { href: "/pricing",      label: t("landing.nav_pricing") },
            ].map(item => (
              <Link key={item.href} href={item.href}
                className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
                {item.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <select value={locale} onChange={e => setLocale(e.target.value as any)}
              className="hidden sm:block text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none"
              aria-label="Language">
              {LANGS.map(l => <option key={l.value} value={l.value}>{l.flag}</option>)}
            </select>

            {isAuthenticated ? (
              <Link href="/dashboard" className="font-syne font-bold text-sm bg-red text-white px-3 sm:px-4 py-2 rounded hover:bg-ink transition-colors whitespace-nowrap">
                Dashboard →
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
              { href: "/articles",     label: t("landing.nav_articles") },
              { href: "/how-it-works", label: t("landing.nav_how") },
              { href: "/calculators",  label: t("landing.nav_calculators") },
              { href: "/drugs",        label: t("landing.nav_drugs") },
              { href: "/pricing",      label: t("landing.nav_pricing") },
              { href: "/login",        label: t("landing.nav_sign_in") },
            ].map(item => (
              <Link key={item.href} href={item.href} onClick={() => setMenuOpen(false)}
                className="block font-syne font-semibold text-sm text-ink-2 hover:text-ink px-3 py-2.5 rounded-lg hover:bg-surface-2 transition-colors">
                {item.label}
              </Link>
            ))}
            <div className="pt-2 flex gap-2 flex-wrap">
              {LANGS.map(l => (
                <button key={l.value} onClick={() => { setLocale(l.value as any); setMenuOpen(false); }}
                  className={`text-lg rounded px-1.5 py-0.5 transition-colors ${locale === l.value ? "bg-ink/10 ring-1 ring-ink/20" : "hover:bg-surface-2"}`}>
                  {l.flag}
                </button>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-20 pb-12 sm:pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-6 sm:mb-8">
          <span className="w-2 h-2 rounded-full bg-green-2 animate-pulse inline-block" />
          {t("landing.hero_badge")}
        </div>
        <h1 className="font-syne font-extrabold text-4xl sm:text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-5 sm:mb-6">
          {t("landing.hero_title")}<br />
          <span className="text-red">{t("landing.hero_title_red")}</span>
        </h1>
        <p className="text-ink-2 text-base sm:text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-8 sm:mb-10 px-2">
          {t("landing.hero_subtitle")}
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center px-4 sm:px-0">
          {isAuthenticated ? (
            <Link href="/dashboard" className="font-syne font-bold text-base bg-red text-white px-6 sm:px-8 py-3.5 rounded hover:bg-ink transition-colors text-center">
              {t("landing.go_to_dashboard") as string}
            </Link>
          ) : (
            <>
              <Link href="/register" className="font-syne font-bold text-base bg-ink text-white px-6 sm:px-8 py-3.5 rounded hover:bg-red transition-colors text-center">
                {t("landing.hero_cta")}
              </Link>
              <Link href="/articles" className="font-syne font-semibold text-base border-2 border-ink text-ink px-6 sm:px-8 py-3.5 rounded hover:bg-ink hover:text-white transition-colors text-center">
                {t("landing.hero_cta2")}
              </Link>
              <Link href="/login" className="hidden sm:block font-syne font-semibold text-base border border-border text-ink-2 px-6 sm:px-8 py-3.5 rounded hover:border-ink hover:text-ink transition-colors text-center">
                {t("landing.hero_cta3")}
              </Link>
            </>
          )}
        </div>
        <p className="text-ink-3 text-xs mt-4 font-syne">{t("landing.hero_note")}</p>
      </section>

      {/* ── Stats bar ────────────────────────────────────────────────────────── */}
      <section className="border-y border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-5 sm:py-6 grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 text-center">
          {[
            { val: "600+",  label: "Medical articles" },
            { val: "7",     label: t("landing.stats_langs") },
            { val: "82+",   label: t("landing.stats_modules") },
            { val: "500+",  label: t("landing.stats_flashcards") },
          ].map((s, i) => (
            <div key={i}>
              <div className="font-syne font-extrabold text-xl sm:text-2xl text-ink">{s.val}</div>
              <div className="text-ink-3 text-[10px] sm:text-xs font-syne uppercase tracking-widest mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Articles (moved up — main content hook) ──────────────────────────── */}
      {articles.length > 0 && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 sm:mb-10">
            <div>
              <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1 rounded-full font-syne font-semibold text-xs text-ink-3 mb-3">
                <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
                {t("landing.articles_badge")}
              </div>
              <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink">
                {t("landing.articles_title")}
              </h2>
              <p className="text-ink-3 text-sm mt-1.5 max-w-lg">
                {articles.length}+ {t("landing.articles_subtitle")}
              </p>
            </div>
            <Link href="/articles"
              className="flex-shrink-0 font-syne font-semibold text-sm border border-border text-ink-2 px-5 py-2.5 rounded-lg hover:border-ink hover:text-ink transition-colors self-start sm:self-auto">
              {t("landing.articles_all")}
            </Link>
          </div>

          {/* Category filter pills */}
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
              {/* Featured article */}
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
                    <p className="text-ink-2 text-sm leading-relaxed line-clamp-3 mb-4">
                      {filteredArticles[0].excerpt}
                    </p>
                    <span className="font-syne font-semibold text-sm text-red group-hover:underline">
                      {t("landing.articles_read")}
                    </span>
                  </div>
                </div>
              </Link>

              {/* Grid */}
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

          {/* Articles CTA */}
          <div className="mt-10 flex flex-col sm:flex-row gap-3 items-center justify-center">
            <Link href="/articles"
              className="inline-flex items-center gap-2 font-syne font-bold text-sm bg-ink text-white px-7 py-3 rounded-lg hover:bg-red transition-colors">
              {t("landing.articles_cta")} <span>→</span>
            </Link>
            {!isAuthenticated && (
              <Link href="/register"
                className="font-syne font-semibold text-sm text-red hover:underline">
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
              {locale === "ru" ? "Клинические инструменты" : locale === "ar" ? "الأدوات السريرية" : locale === "de" ? "Klinische Tools" : locale === "fr" ? "Outils cliniques" : locale === "es" ? "Herramientas clínicas" : locale === "tr" ? "Klinik araçlar" : "Clinical tools"}
            </div>
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink">
              {t("landing.nav_calculators")}
            </h2>
            <p className="text-ink-3 text-sm mt-1.5 max-w-lg">
              {locale === "ru" ? "Доказательные шкалы, которыми врачи пользуются каждый день. Бесплатно, на вашем языке." : locale === "ar" ? "أدوات تقييم قائمة على الأدلة يستخدمها الأطباء يومياً. مجانية، بلغتك." : locale === "de" ? "Evidenzbasierte Scoring-Tools, täglich von Klinikern eingesetzt. Kostenlos, in Ihrer Sprache." : locale === "fr" ? "Outils de scoring validés utilisés quotidiennement. Gratuit, dans votre langue." : locale === "es" ? "Herramientas de puntuación usadas diariamente por clínicos. Gratis, en tu idioma." : locale === "tr" ? "Klinisyenlerin günlük kullandığı kanıta dayalı puanlama araçları. Ücretsiz, dilinizde." : "Evidence-based scoring tools used daily by clinicians worldwide. Free, in your language."}
            </p>
          </div>
          <Link href="/calculators" className="font-syne font-bold text-sm text-red hover:underline whitespace-nowrap flex-shrink-0">
            {locale === "ru" ? "Все калькуляторы →" : locale === "ar" ? "جميع الآلات الحاسبة →" : locale === "de" ? "Alle Rechner →" : locale === "fr" ? "Tous les calculateurs →" : locale === "es" ? "Todas las calculadoras →" : locale === "tr" ? "Tüm hesap makineleri →" : "All calculators →"}
          </Link>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { slug: "cha2ds2-vasc", icon: "❤️", cat: locale === "ru" ? "Кардиология" : locale === "ar" ? "أمراض القلب" : locale === "de" ? "Kardiologie" : locale === "fr" ? "Cardiologie" : locale === "es" ? "Cardiología" : locale === "tr" ? "Kardiyoloji" : "Cardiology", name: "CHA₂DS₂-VASc", desc: locale === "ru" ? "Риск инсульта при фибрилляции предсердий" : locale === "ar" ? "خطر السكتة الدماغية في الرجفان الأذيني" : locale === "de" ? "Schlaganfallrisiko bei Vorhofflimmern" : locale === "fr" ? "Risque d'AVC dans la fibrillation auriculaire" : locale === "es" ? "Riesgo de ictus en fibrilación auricular" : locale === "tr" ? "Atriyal fibrilasyonda inme riski" : "Stroke risk in atrial fibrillation" },
            { slug: "curb-65", icon: "🫁", cat: locale === "ru" ? "Пульмонология" : locale === "ar" ? "أمراض الرئة" : locale === "de" ? "Pneumologie" : locale === "fr" ? "Pneumologie" : locale === "es" ? "Neumología" : locale === "tr" ? "Pulmonoloji" : "Pulmonology", name: "CURB-65", desc: locale === "ru" ? "Тяжесть внебольничной пневмонии" : locale === "ar" ? "شدة الالتهاب الرئوي المكتسب من المجتمع" : locale === "de" ? "Schweregrad der ambulant erworbenen Pneumonie" : locale === "fr" ? "Sévérité de la pneumonie communautaire" : locale === "es" ? "Gravedad de la neumonía comunitaria" : locale === "tr" ? "Toplum kökenli pnömoni şiddeti" : "Community-acquired pneumonia severity" },
            { slug: "egfr-ckd-epi", icon: "🫘", cat: locale === "ru" ? "Нефрология" : locale === "ar" ? "أمراض الكلى" : locale === "de" ? "Nephrologie" : locale === "fr" ? "Néphrologie" : locale === "es" ? "Nefrología" : locale === "tr" ? "Nefroloji" : "Nephrology", name: "eGFR (CKD-EPI 2021)", desc: locale === "ru" ? "Функция почек и стадия ХБП" : locale === "ar" ? "وظائف الكلى وتصنيف مرض الكلى المزمن" : locale === "de" ? "Nierenfunktion und CKD-Stadium" : locale === "fr" ? "Fonction rénale et stadification de l'IRC" : locale === "es" ? "Función renal y estadio de ERC" : locale === "tr" ? "Böbrek fonksiyonu ve KBH evresi" : "Kidney function and CKD staging" },
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
                {locale === "ru" ? "Открыть →" : locale === "ar" ? "فتح →" : locale === "de" ? "Öffnen →" : locale === "fr" ? "Ouvrir →" : locale === "es" ? "Abrir →" : locale === "tr" ? "Aç →" : "Open →"}
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* ── Interactive demo ─────────────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1 rounded-full font-syne font-semibold text-xs text-ink-3 mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
            {t("landing.demo_badge")}
          </div>
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">{t("landing.demo_title")}</h2>
          <p className="text-ink-3 text-sm">{t("landing.demo_subtitle")}</p>
        </div>

        <div className="bg-surface border border-border rounded-xl p-6 sm:p-8">
          {/* Question */}
          <div className="flex gap-3 mb-6">
            <div className="w-8 h-8 rounded-lg bg-red flex items-center justify-center flex-shrink-0 text-white text-sm font-bold font-syne">?</div>
            <p className="text-ink font-syne font-semibold text-base leading-relaxed">{t("landing.demo_question")}</p>
          </div>

          {/* Options */}
          <div className="grid sm:grid-cols-2 gap-3 mb-6">
            {(Array.isArray(demoOptions) ? demoOptions : []).map((opt, i) => {
              const isSelected = demoAnswer === i;
              const isCorrect  = i === correctIdx;
              const revealed   = demoAnswer !== null;
              let cls = "border border-border bg-bg text-ink-2 hover:border-ink hover:text-ink cursor-pointer";
              if (revealed && isCorrect)  cls = "border-2 border-green-2 bg-green-2/10 text-ink";
              else if (revealed && isSelected && !isCorrect) cls = "border-2 border-red bg-red/10 text-ink";
              else if (revealed) cls = "border border-border bg-bg text-ink-3 opacity-60";
              return (
                <button key={i} onClick={() => { if (demoAnswer === null) setDemoAnswer(i); }}
                  className={`w-full text-left rounded-lg px-4 py-3 font-syne font-semibold text-sm transition-all ${cls}`}>
                  <span className="text-ink-3 mr-2">{["A", "B", "C", "D"][i]}.</span>
                  {opt}
                  {revealed && isCorrect  && <span className="float-right text-green-2">✓</span>}
                  {revealed && isSelected && !isCorrect && <span className="float-right text-red">✗</span>}
                </button>
              );
            })}
          </div>

          {/* Explanation */}
          {demoAnswer !== null && (
            <div className={`rounded-lg p-4 mb-5 border ${demoAnswer === correctIdx ? "bg-green-2/10 border-green-2/30" : "bg-surface-2 border-border"}`}>
              <p className="text-ink text-sm leading-relaxed font-syne">
                {demoAnswer === correctIdx
                  ? t("landing.demo_explanation") as string
                  : t("landing.demo_wrong") as string}
              </p>
            </div>
          )}

          {/* CTA after answer */}
          {demoAnswer !== null && !isAuthenticated && (
            <div className="text-center pt-2">
              <Link href="/register"
                className="inline-flex items-center gap-2 font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-lg hover:bg-red transition-colors">
                {t("landing.demo_more")}
              </Link>
            </div>
          )}

          {demoAnswer === null && (
            <p className="text-ink-3 text-xs font-syne text-center">Select an answer above</p>
          )}
        </div>
      </section>

      {/* ── What's inside (feature preview) ─────────────────────────────────── */}
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

          {/* Mock dashboard preview */}
          <div className="relative rounded-2xl border border-border bg-bg overflow-hidden shadow-xl mb-12">
            {/* Browser chrome */}
            <div className="flex items-center gap-1.5 px-4 py-3 bg-surface border-b border-border">
              <span className="w-3 h-3 rounded-full bg-red/60" />
              <span className="w-3 h-3 rounded-full bg-yellow-400/60" />
              <span className="w-3 h-3 rounded-full bg-green-2/60" />
              <div className="mx-auto bg-bg border border-border rounded px-4 py-1 text-xs text-ink-3 font-syne">medmind.pro/dashboard</div>
            </div>
            {/* Dashboard layout */}
            <div className="flex h-64 sm:h-80">
              {/* Sidebar */}
              <div className="hidden sm:flex w-48 border-r border-border bg-surface flex-col py-4 px-3 gap-1 flex-shrink-0">
                {["Dashboard", "AI Tutor", "Flashcards", "Cases", "Modules", "Articles", "Drugs"].map((item, i) => (
                  <div key={i} className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-xs font-syne font-semibold ${i === 1 ? "bg-red text-white" : "text-ink-3"}`}>
                    <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60" />
                    {item}
                  </div>
                ))}
              </div>
              {/* Main content */}
              <div className="flex-1 p-4 sm:p-6 overflow-hidden">
                <div className="text-xs font-syne font-semibold text-ink-3 uppercase tracking-widest mb-3">AI Medical Tutor</div>
                {/* Fake chat */}
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <div className="w-6 h-6 rounded-full bg-surface-2 border border-border flex-shrink-0" />
                    <div className="bg-surface border border-border rounded-lg rounded-tl-none px-3 py-2 text-xs text-ink-2 font-syne max-w-xs leading-relaxed">
                      What are the signs of increased intracranial pressure?
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <div className="bg-ink rounded-lg rounded-tr-none px-3 py-2 text-xs text-white font-syne max-w-xs leading-relaxed">
                      Classic triad: headache (worse in morning), papilloedema, and vomiting. Late signs include Cushing's triad: hypertension, bradycardia, irregular respirations. <span className="text-white/50">[PubMed: 34521890]</span>
                    </div>
                    <div className="w-6 h-6 rounded-full bg-red flex-shrink-0 flex items-center justify-center text-white text-[10px] font-bold">AI</div>
                  </div>
                  <div className="flex gap-2">
                    <div className="w-6 h-6 rounded-full bg-surface-2 border border-border flex-shrink-0" />
                    <div className="bg-surface border border-border rounded-lg rounded-tl-none px-3 py-2 text-xs text-ink-2 font-syne max-w-xs">
                      Show me a related flashcard
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 6 feature cards */}
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
          <p className="text-white/60 mb-8 text-base leading-relaxed max-w-xl mx-auto">{t("landing.cta_subtitle")}</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/register"
              className="inline-block font-syne font-bold text-base bg-white text-ink px-8 sm:px-10 py-4 rounded hover:bg-red hover:text-white transition-colors">
              {t("landing.cta_btn")}
            </Link>
            <Link href="/articles"
              className="inline-block font-syne font-semibold text-base border border-white/30 text-white/80 px-8 sm:px-10 py-4 rounded hover:border-white hover:text-white transition-colors">
              Browse articles →
            </Link>
          </div>
          <p className="text-white/30 text-xs mt-5 font-syne">{t("landing.hero_note")}</p>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-syne font-extrabold text-lg text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">{t("landing.footer_tagline")}</span>
          </div>
          <div className="flex gap-4 sm:gap-6 flex-wrap justify-center">
            {[
              { href: "/articles",     label: t("landing.nav_articles") },
              { href: "/how-it-works", label: t("landing.nav_how") },
              { href: "/calculators",  label: t("landing.nav_calculators") },
              { href: "/drugs",        label: t("landing.nav_drugs") },
              { href: "/pricing",      label: t("landing.nav_pricing") },
              { href: "/investors",    label: t("landing.footer_investors") },
              { href: "/register",     label: t("landing.footer_register") },
              { href: "/login",        label: t("landing.footer_login") },
            ].map(item => (
              <Link key={item.href} href={item.href} className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">
                {item.label}
              </Link>
            ))}
          </div>
          <div className="text-ink-3 text-xs font-syne">{t("landing.footer_copy")}</div>
        </div>
      </footer>
    </div>
  );
}
