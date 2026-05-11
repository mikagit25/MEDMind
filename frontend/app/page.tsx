"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";
import { useT, useI18n } from "@/lib/i18n";

export default function RootPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const t = useT();
  const { locale, setLocale } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated) router.replace("/dashboard");
  }, [isAuthenticated, router]);

  if (isAuthenticated) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="font-syne text-ink-3 text-sm animate-pulse">Loading…</div>
      </div>
    );
  }

  const features = t("landing.features") as unknown as { icon: string; title: string; desc: string }[];
  const plans    = t("landing.pricing_plans") as unknown as { name: string; price: string; period: string; features: string[]; cta: string; highlight: boolean }[];
  const specs    = t("landing.specialties") as unknown as { icon: string; name: string; count: number }[];
  const specArticle: Record<string, string> = { Cardiology: "cardiology", Neurology: "neurology", Surgery: "surgery", Pediatrics: "pediatrics", Кардиология: "cardiology", Неврология: "neurology", Хирургия: "surgery", Педиатрия: "pediatrics" };

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

            <Link href="/login" className="hidden sm:block font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {t("landing.nav_sign_in")}
            </Link>
            <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-3 sm:px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">
              {t("landing.nav_register")}
            </Link>

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
              { href: "/articles",     label: t("landing.nav_articles") },
              { href: "/pricing",      label: t("landing.nav_pricing") },
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
          <Link href="/register" className="font-syne font-bold text-base bg-ink text-white px-6 sm:px-8 py-3.5 rounded hover:bg-red transition-colors text-center">
            {t("landing.hero_cta")}
          </Link>
          <Link href="/login" className="font-syne font-semibold text-base border border-border-2 text-ink-2 px-6 sm:px-8 py-3.5 rounded hover:border-ink hover:text-ink transition-colors text-center">
            {t("landing.hero_cta2")}
          </Link>
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
          {(Array.isArray(features) ? features : []).map((f, i) => (
            <div key={i} className="bg-surface border border-border rounded-lg p-5 sm:p-6 hover:border-border-2 transition-colors">
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="font-syne font-bold text-base text-ink mb-2">{f.title}</h3>
              <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
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

      {/* Specialties */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("landing.specialties_title")}</h2>
        <p className="text-ink-3 text-center mb-10 sm:mb-12 text-sm">{t("landing.specialties_subtitle")}</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
          {(Array.isArray(specs) ? specs : []).map((s, i) => (
            <Link key={i} href={specArticle[s.name] ? `/articles/category/${specArticle[s.name]}` : "/register"}
              className="bg-surface border border-border rounded-lg p-4 text-center hover:border-border-2 hover:shadow-sm transition-all">
              <div className="text-2xl mb-2">{s.icon}</div>
              <div className="font-syne font-bold text-sm text-ink leading-tight">{s.name}</div>
              <div className="text-ink-3 text-xs mt-1">{s.count} {t("landing.specialties_modules")}</div>
            </Link>
          ))}
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
