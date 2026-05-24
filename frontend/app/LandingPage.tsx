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

export default function LandingPage({ articles: initialArticles = [] }: { articles: ArticlePreview[] }) {
  const { isAuthenticated } = useAuthStore();
  const t = useT();
  const { locale, setLocale } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [articles, setArticles] = useState<ArticlePreview[]>(initialArticles);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "";

  useEffect(() => {
    if (locale === "en") {
      setArticles(initialArticles);
      return;
    }
    const seen: Record<string, number> = {};
    fetch(`${API}/api/v1/articles?limit=24&locale=${locale}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data?.articles) return;
        const filtered = (data.articles as ArticlePreview[]).filter(a => {
          seen[a.category] = (seen[a.category] ?? 0) + 1;
          return seen[a.category] <= 3;
        }).slice(0, 10);
        setArticles(filtered);
      })
      .catch(() => {});
  }, [locale]);

  const features = t("landing.features") as unknown as { icon: string; title: string; desc: string }[];
  const plans    = t("landing.pricing_plans") as unknown as { name: string; price: string; period: string; features: string[]; cta: string; highlight: boolean }[];
  const specs    = t("landing.specialties") as unknown as { icon: string; name: string; count: number }[];
  const specArticle: Record<string, string> = { Cardiology: "cardiology", Neurology: "neurology", Surgery: "surgery", Pediatrics: "pediatrics", Кардиология: "cardiology", Неврология: "neurology", Хирургия: "surgery", Педиатрия: "pediatrics" };

  // Derive unique categories from articles for filter pills
  const articleCategories = Array.from(new Set(articles.map(a => a.category)));
  const filteredArticles = activeCategory === "all"
    ? articles
    : articles.filter(a => a.category === activeCategory);

  const LANGS = [
    { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" },
    { value: "de", flag: "🇩🇪" }, { value: "fr", flag: "🇫🇷" },
    { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" },
    { value: "es", flag: "🇪🇸" },
  ] as const;

  return (
    <div className="min-h-screen bg-bg">
      {/* Navigation */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            <Link href="/how-it-works" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {t("landing.nav_how")}
            </Link>
            <Link href="/articles" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {t("landing.nav_articles")}
            </Link>
            <Link href="/drugs" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2 hidden md:block">
              {t("landing.nav_drugs")}
            </Link>
            <Link href="/imaging" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2 hidden md:block">
              {t("landing.nav_imaging")}
            </Link>
            <Link href="/pricing" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {t("landing.nav_pricing")}
            </Link>
          </div>

          {/* Right side — always visible */}
          <div className="flex items-center gap-2">
            {/* Language switcher */}
            <select
              value={locale}
              onChange={e => setLocale(e.target.value as any)}
              className="hidden sm:block text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none"
              aria-label="Language"
            >
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

            {/* Hamburger — mobile only */}
            <button
              onClick={() => setMenuOpen(v => !v)}
              className="md:hidden p-2 rounded text-ink-2 hover:text-ink hover:bg-surface-2 transition-colors"
              aria-label="Menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {menuOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                }
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {menuOpen && (
          <div className="md:hidden border-t border-border bg-surface px-4 py-3 space-y-1">
            {[
              { href: "/how-it-works", label: t("landing.nav_how") },
              { href: "/articles", label: t("landing.nav_articles") },
              { href: "/drugs",    label: t("landing.nav_drugs") },
              { href: "/imaging",  label: t("landing.nav_imaging") },
              { href: "/pricing",  label: t("landing.nav_pricing") },
              { href: "/login",        label: t("landing.nav_sign_in") },
            ].map(item => (
              <Link key={item.href} href={item.href}
                onClick={() => setMenuOpen(false)}
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

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-20 pb-12 sm:pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-6 sm:mb-8">
          <span className="w-2 h-2 rounded-full bg-green-2 animate-pulse inline-block" />
          {t("landing.hero_badge")}
        </div>
        <h1 className="font-syne font-extrabold text-4xl sm:text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-5 sm:mb-6">
          {t("landing.hero_title").split(" with AI")[0]}<br />
          <span className="text-red">{t("landing.hero_title").includes(" with AI") ? "with AI" : ""}</span>
        </h1>
        <p className="text-ink-2 text-base sm:text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-8 sm:mb-10 px-2">
          {t("landing.hero_subtitle")}
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center px-4 sm:px-0">
          {isAuthenticated ? (
            <Link href="/dashboard" className="font-syne font-bold text-base bg-red text-white px-6 sm:px-8 py-3.5 rounded hover:bg-ink transition-colors text-center">
              {t("landing.go_to_dashboard") as string || "Open Dashboard →"}
            </Link>
          ) : (
            <>
              <Link href="/register" className="font-syne font-bold text-base bg-ink text-white px-6 sm:px-8 py-3.5 rounded hover:bg-red transition-colors text-center">
                {t("landing.hero_cta")}
              </Link>
              <Link href="/login" className="font-syne font-semibold text-base border border-border-2 text-ink-2 px-6 sm:px-8 py-3.5 rounded hover:border-ink hover:text-ink transition-colors text-center">
                {t("landing.hero_cta2")}
              </Link>
            </>
          )}
        </div>
        <p className="text-ink-3 text-xs mt-4 font-syne">{t("landing.hero_note")}</p>
      </section>

      {/* Stats */}
      <section className="border-y border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-5 sm:py-6 grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 text-center">
          {[
            { val: "97+", label: t("landing.stats_modules") },
            { val: "7",   label: t("landing.stats_langs") },
            { val: "500+",label: t("landing.stats_flashcards") },
            { val: t("landing.stats_realtime"), label: t("landing.stats_realtime_label") },
          ].map((s, i) => (
            <div key={i}>
              <div className="font-syne font-extrabold text-xl sm:text-2xl text-ink">{s.val}</div>
              <div className="text-ink-3 text-[10px] sm:text-xs font-syne uppercase tracking-widest mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("landing.features_title")}</h2>
        <p className="text-ink-3 text-center mb-10 sm:mb-12 text-sm">{t("landing.features_subtitle")}</p>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-5 sm:gap-6">
          {(Array.isArray(features) ? features : []).map((f, i) => {
            const featureKeys = ["tutor","flashcards","cases","modules","pubmed","veterinary"];
            return (
              <div key={i} className="bg-surface border border-border rounded-lg p-5 sm:p-6 hover:border-border-2 transition-colors group">
                <div className="w-10 h-10 rounded-lg bg-bg flex items-center justify-center mb-4 text-red group-hover:bg-red group-hover:text-white transition-colors">
                  <FeatureIcon name={featureKeys[i] ?? "tutor"} size={20} strokeWidth={1.75} />
                </div>
                <h3 className="font-syne font-bold text-base text-ink mb-2">{f.title}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Specialties */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("landing.specialties_title")}</h2>
        <p className="text-ink-3 text-center mb-10 sm:mb-12 text-sm">{t("landing.specialties_subtitle")}</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
          {(Array.isArray(specs) ? specs : []).map((s, i) => (
            <Link key={i} href={specArticle[s.name] ? `/articles/category/${specArticle[s.name]}` : "/register"}
              className="bg-surface border border-border rounded-lg p-4 text-center hover:border-ink hover:shadow-sm transition-all group">
              <div className="w-12 h-12 rounded-xl bg-bg mx-auto flex items-center justify-center mb-3 text-ink-3 group-hover:bg-red group-hover:text-white transition-colors">
                <SpecialtyIcon name={s.name} size={24} strokeWidth={1.5} />
              </div>
              <div className="font-syne font-bold text-sm text-ink leading-tight">{s.name}</div>
              <div className="text-ink-3 text-xs mt-1">{s.count} {t("landing.specialties_modules")}</div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── Medical Articles ─────────────────────────────────────────────────── */}
      {articles.length > 0 && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          {/* Header */}
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
            <Link
              href="/articles"
              className="flex-shrink-0 font-syne font-semibold text-sm border border-border text-ink-2 px-5 py-2.5 rounded-lg hover:border-ink hover:text-ink transition-colors self-start sm:self-auto"
            >
              {t("landing.articles_all")}
            </Link>
          </div>

          {/* Category filter pills */}
          {articleCategories.length > 1 && (
            <div className="flex flex-wrap gap-2 mb-8">
              <button
                onClick={() => setActiveCategory("all")}
                className={`font-syne font-semibold text-xs px-3.5 py-1.5 rounded-full border transition-colors ${
                  activeCategory === "all"
                    ? "bg-ink text-white border-ink"
                    : "border-border text-ink-2 hover:border-ink hover:text-ink bg-surface"
                }`}
              >
                {t("landing.articles_all_topics")}
              </button>
              {articleCategories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`inline-flex items-center gap-1.5 font-syne font-semibold text-xs px-3.5 py-1.5 rounded-full border transition-colors ${
                    activeCategory === cat
                      ? "bg-ink text-white border-ink"
                      : "border-border text-ink-2 hover:border-ink hover:text-ink bg-surface"
                  }`}
                >
                  <CategoryIcon category={cat} size={11} strokeWidth={2} />
                  {getCategoryLabel(cat, locale === "en" ? "en" : locale)}
                </button>
              ))}
            </div>
          )}

          {/* Featured article (first one) + grid */}
          {filteredArticles.length > 0 && (
            <>
              {/* Featured — large card */}
              <Link
                href={`/articles/${filteredArticles[0].slug}`}
                className="group block mb-6 bg-surface border border-border rounded-xl overflow-hidden hover:border-ink hover:shadow-lg transition-all"
              >
                <div className="flex flex-col md:flex-row">
                  {filteredArticles[0].cover_image ? (
                    <div className="md:w-2/5 h-52 md:h-auto overflow-hidden bg-surface-2 flex-shrink-0">
                      <img
                        src={filteredArticles[0].cover_image}
                        alt={filteredArticles[0].title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="eager"
                      />
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

              {/* Grid — remaining articles */}
              {filteredArticles.length > 1 && (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  {filteredArticles.slice(1, 7).map(article => (
                    <Link
                      key={article.id}
                      href={`/articles/${article.slug}`}
                      className="group flex flex-col bg-surface border border-border rounded-xl overflow-hidden hover:border-ink hover:shadow-md transition-all"
                    >
                      {article.cover_image ? (
                        <div className="h-36 overflow-hidden bg-surface-2">
                          <img
                            src={article.cover_image}
                            alt={article.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            loading="lazy"
                          />
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
                        <p className="text-ink-3 text-xs leading-relaxed line-clamp-2">
                          {article.excerpt}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Bottom CTA */}
          <div className="mt-10 text-center">
            <Link
              href="/articles"
              className="inline-flex items-center gap-2 font-syne font-bold text-sm bg-ink text-white px-7 py-3 rounded-lg hover:bg-red transition-colors"
            >
              {t("landing.articles_cta")}
              <span>→</span>
            </Link>
            <p className="text-ink-3 text-xs mt-3 font-syne">
              {t("landing.articles_stats")}
            </p>
          </div>
        </section>
      )}

      {/* Pricing — placed after articles for better conversion flow */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("landing.pricing_title")}</h2>
          <p className="text-ink-3 text-center mb-10 sm:mb-12 text-sm">{t("landing.pricing_subtitle")}</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
            {(Array.isArray(plans) ? plans : []).map((p, i) => (
              <div key={i} className={`rounded-lg p-5 sm:p-6 border ${p.highlight ? "border-red bg-red-light" : "border-border bg-bg"}`}>
                {p.highlight && (
                  <div className="font-syne font-bold text-xs text-red uppercase tracking-widest mb-3">{t("landing.pricing_most_popular")}</div>
                )}
                <div className="font-syne font-extrabold text-xl text-ink mb-1">{p.name}</div>
                <div className="flex items-baseline gap-1 mb-4">
                  <span className="font-syne font-bold text-3xl text-ink">{p.price}</span>
                  <span className="text-ink-3 text-sm">{p.period}</span>
                </div>
                <ul className="space-y-2 mb-6">
                  {p.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-ink-2">
                      <span className="text-green-2 mt-0.5 flex-shrink-0">✓</span>{f}
                    </li>
                  ))}
                </ul>
                <Link href="/register" className={`block text-center font-syne font-semibold text-sm py-2.5 rounded transition-colors ${p.highlight ? "bg-ink text-white hover:bg-red" : "border border-border-2 text-ink-2 hover:border-ink hover:text-ink"}`}>
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-ink text-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">{t("landing.cta_title")}</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">{t("landing.cta_subtitle")}</p>
          <Link href="/register" className="inline-block font-syne font-bold text-base bg-white text-ink px-8 sm:px-10 py-4 rounded hover:bg-red hover:text-white transition-colors">
            {t("landing.cta_btn")}
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-syne font-extrabold text-lg text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">{t("landing.footer_tagline")}</span>
          </div>
          <div className="flex gap-4 sm:gap-6 flex-wrap justify-center">
            <Link href="/how-it-works" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.nav_how")}</Link>
            <Link href="/articles"     className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.nav_articles")}</Link>
            <Link href="/drugs"        className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.nav_drugs")}</Link>
            <Link href="/imaging"      className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.nav_imaging")}</Link>
            <Link href="/pricing"      className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.nav_pricing")}</Link>
            <Link href="/investors"    className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.footer_investors")}</Link>
            <Link href="/register"     className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.footer_register")}</Link>
            <Link href="/login"        className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.footer_login")}</Link>
          </div>
          <div className="text-ink-3 text-xs font-syne">{t("landing.footer_copy")}</div>
        </div>
      </footer>
    </div>
  );
}
