"use client";
import { useState } from "react";
import { useT, useI18n } from "@/lib/i18n";
import Link from "next/link";

const LANGS = [
  { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" },
  { value: "de", flag: "🇩🇪" }, { value: "fr", flag: "🇫🇷" },
  { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" },
  { value: "es", flag: "🇪🇸" },
] as const;

export default function HowItWorksPage() {
  const t = useT();
  const { locale, setLocale } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);

  const steps   = t("how_it_works_page.steps")   as unknown as { number: string; title: string; description: string; detail: string; icon: string }[];
  const roles   = t("how_it_works_page.roles")   as unknown as { role: string; icon: string; description: string; features: string[] }[];
  const tech    = t("how_it_works_page.tech")    as unknown as { title: string; desc: string; icon: string }[];
  const faq     = t("how_it_works_page.faq")     as unknown as { q: string; a: string }[];
  const cmpRows = t("how_it_works_page.cmp_rows") as unknown as string[][];

  return (
    <div className="min-h-screen bg-bg">

      {/* ── Nav ──────────────────────────────────────────────────────────── */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            <Link href="/how-it-works" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t("how_it_works_page.nav_how")}</Link>
            <Link href="/articles"     className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t("how_it_works_page.nav_articles")}</Link>
            <Link href="/pricing"      className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t("how_it_works_page.nav_pricing")}</Link>
          </div>

          <div className="flex items-center gap-2">
            <select value={locale} onChange={e => setLocale(e.target.value as any)}
              className="hidden sm:block text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none" aria-label="Language">
              {LANGS.map(l => <option key={l.value} value={l.value}>{l.flag}</option>)}
            </select>
            <Link href="/login" className="hidden sm:block font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t("how_it_works_page.nav_sign_in")}</Link>
            <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-3 sm:px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">{t("how_it_works_page.nav_register")}</Link>
            <button onClick={() => setMenuOpen(v => !v)} className="md:hidden p-2 rounded text-ink-2 hover:text-ink hover:bg-surface-2 transition-colors" aria-label="Menu">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {menuOpen ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
              </svg>
            </button>
          </div>
        </div>
        {menuOpen && (
          <div className="md:hidden border-t border-border bg-surface px-4 py-3 space-y-1">
            {[
              { href: "/how-it-works", label: t("how_it_works_page.nav_how") },
              { href: "/articles",     label: t("how_it_works_page.nav_articles") },
              { href: "/pricing",      label: t("how_it_works_page.nav_pricing") },
              { href: "/login",        label: t("how_it_works_page.nav_sign_in") },
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

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-16 sm:pt-20 pb-12 sm:pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-6 sm:mb-8">
          <span className="w-2 h-2 rounded-full bg-blue animate-pulse inline-block" />
          {t("how_it_works_page.hero_badge")}
        </div>
        <h1 className="font-syne font-extrabold text-4xl sm:text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-5 sm:mb-6">
          {t("how_it_works_page.hero_title_1")}<br />
          <span className="text-red">{t("how_it_works_page.hero_title_2")}</span>
        </h1>
        <p className="text-ink-2 text-base sm:text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-4 px-2">
          {t("how_it_works_page.hero_desc")}
        </p>
        <p className="text-ink-3 text-sm max-w-xl mx-auto leading-relaxed mb-8 sm:mb-10 px-2">
          {t("how_it_works_page.hero_desc2")}
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center px-4 sm:px-0">
          <Link href="/register" className="font-syne font-bold text-base bg-ink text-white px-8 sm:px-10 py-3.5 rounded hover:bg-red transition-colors text-center">
            {t("how_it_works_page.cta_btn")}
          </Link>
          <Link href="/pricing" className="font-syne font-semibold text-base border border-border-2 text-ink-2 px-8 sm:px-10 py-3.5 rounded hover:border-ink hover:text-ink transition-colors text-center">
            {t("how_it_works_page.nav_pricing")}
          </Link>
        </div>
        <p className="text-ink-3 text-xs mt-4 font-syne">{t("how_it_works_page.hero_note")}</p>
      </section>

      {/* ── Steps ─────────────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("how_it_works_page.steps_title")}</h2>
        <p className="text-ink-3 text-center mb-12 sm:mb-16 text-sm">{t("how_it_works_page.steps_note")}</p>
        <div className="space-y-10 sm:space-y-12">
          {(Array.isArray(steps) ? steps : []).map((step, i) => (
            <div key={step.number} className={`flex flex-col md:flex-row gap-6 sm:gap-8 items-start ${i % 2 === 1 ? "md:flex-row-reverse" : ""}`}>
              <div className="flex-shrink-0 w-full md:w-56 bg-surface border border-border rounded-xl p-6 sm:p-8 text-center">
                <div className="text-4xl sm:text-5xl mb-4">{step.icon}</div>
                <div className="font-syne font-extrabold text-3xl sm:text-4xl text-border-2 mb-1">{step.number}</div>
              </div>
              <div className="flex-1 pt-2 sm:pt-4">
                <h3 className="font-syne font-bold text-xl sm:text-2xl text-ink mb-3">{step.title}</h3>
                <p className="text-ink-2 text-sm sm:text-base leading-relaxed mb-4">{step.description}</p>
                <div className="inline-flex items-center gap-2 bg-surface border border-border rounded-lg px-4 py-2">
                  <span className="text-green-2 text-sm">→</span>
                  <span className="text-ink-3 text-sm font-syne">{step.detail}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Who it's for ──────────────────────────────────────────────────── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("how_it_works_page.roles_section_title")}</h2>
          <p className="text-ink-3 text-center mb-10 sm:mb-12 text-sm">{t("how_it_works_page.roles_subtitle")}</p>
          <div className="grid sm:grid-cols-2 gap-5 sm:gap-6">
            {(Array.isArray(roles) ? roles : []).map((r) => (
              <div key={r.role} className="bg-bg border border-border rounded-xl p-5 sm:p-6 hover:border-border-2 transition-colors">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">{r.icon}</span>
                  <h3 className="font-syne font-bold text-base sm:text-lg text-ink">{r.role}</h3>
                </div>
                <p className="text-ink-2 text-sm leading-relaxed mb-4">{r.description}</p>
                <ul className="space-y-2">
                  {r.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-ink-3">
                      <span className="text-green-2 mt-0.5 flex-shrink-0">✓</span>{f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Technology ────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("how_it_works_page.tech_title")}</h2>
        <p className="text-ink-3 text-center mb-10 sm:mb-12 text-sm">{t("how_it_works_page.tech_subtitle")}</p>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-5 sm:gap-6">
          {(Array.isArray(tech) ? tech : []).map((f) => (
            <div key={f.title} className="bg-surface border border-border rounded-lg p-5 sm:p-6 hover:border-border-2 transition-colors">
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-syne font-bold text-base text-ink mb-2">{f.title}</h3>
              <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Comparison table ──────────────────────────────────────────────── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-2 sm:mb-3">{t("how_it_works_page.cmp_title")}</h2>
          <p className="text-ink-3 text-center mb-10 sm:mb-12 text-sm">{t("how_it_works_page.cmp_subtitle")}</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 pr-6 font-syne font-bold text-ink-2 w-48">{t("how_it_works_page.cmp_feature")}</th>
                  <th className="py-3 px-4 font-syne font-bold text-red text-center">{t("how_it_works_page.cmp_medmind")}</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">{t("how_it_works_page.cmp_chatbot")}</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">{t("how_it_works_page.cmp_anki")}</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">{t("how_it_works_page.cmp_textbook")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(Array.isArray(cmpRows) ? cmpRows : []).map((row, i) => (
                  <tr key={i}>
                    <td className="py-3 pr-6 font-syne text-ink-2 text-xs sm:text-sm">{row[0]}</td>
                    {row.slice(1).map((v, j) => (
                      <td key={j} className={`py-3 px-4 text-center text-xs sm:text-sm ${j === 0 ? "text-green-2 font-bold" : "text-ink-3"}`}>{v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-10 sm:mb-12">{t("how_it_works_page.faq_title")}</h2>
        <div className="space-y-4 sm:space-y-6">
          {(Array.isArray(faq) ? faq : []).map((item, i) => (
            <div key={i} className="bg-surface border border-border rounded-xl p-5 sm:p-6">
              <h3 className="font-syne font-bold text-base text-ink mb-2">{item.q}</h3>
              <p className="text-ink-2 text-sm leading-relaxed">{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────────────────────── */}
      <section className="bg-ink text-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">{t("how_it_works_page.cta_title")}</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">{t("how_it_works_page.cta_subtitle")}</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/register" className="inline-block font-syne font-bold text-base bg-white text-ink px-8 sm:px-10 py-4 rounded hover:bg-red hover:text-white transition-colors text-center">
              {t("how_it_works_page.cta_btn")}
            </Link>
            <Link href="/pricing" className="inline-block font-syne font-semibold text-base border border-white/30 text-white/80 px-8 sm:px-10 py-4 rounded hover:border-white hover:text-white transition-colors text-center">
              {t("how_it_works_page.nav_pricing")}
            </Link>
          </div>
          <p className="text-white/40 text-xs mt-4 font-syne">{t("how_it_works_page.hero_note")}</p>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-syne font-extrabold text-lg text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">{t("landing.footer_tagline")}</span>
          </div>
          <div className="flex gap-4 sm:gap-6 flex-wrap justify-center">
            <Link href="/how-it-works" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("how_it_works_page.nav_how")}</Link>
            <Link href="/articles"     className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("how_it_works_page.nav_articles")}</Link>
            <Link href="/pricing"      className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("how_it_works_page.nav_pricing")}</Link>
            <Link href="/investors"    className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.footer_investors")}</Link>
            <Link href="/register"     className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.footer_register")}</Link>
            <Link href="/login"        className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.footer_login")}</Link>
          </div>
          <div className="text-ink-3 text-xs font-syne">{t("how_it_works_page.footer_copy")}</div>
        </div>
      </footer>
    </div>
  );
}
