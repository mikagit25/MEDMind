import type { Metadata } from "next";
import Link from "next/link";
import { getLearnT } from "@/lib/learn-i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Learn Medicine — Plain Language Health Guides for Everyone",
  description:
    "Understand medicine without a medical degree. Explore topics, drug guides, and a medical glossary — written in plain language for patients, students, and curious minds.",
  alternates: { canonical: `${SITE_URL}/learn` },
  openGraph: {
    title: "Learn Medicine — MedMind",
    description:
      "Plain-language health guides for everyone. Topics, drugs, glossary — no medical degree required.",
    url: `${SITE_URL}/learn`,
    type: "website",
  },
};

type Stats = {
  topics: number;
  glossary_terms: number;
  drugs: number;
};

async function fetchStats(): Promise<Stats> {
  try {
    const [topicsRes, glossaryRes, drugsRes] = await Promise.allSettled([
      fetch(`${API_URL}/public/topics?limit=200`, { next: { revalidate: 3600 } }),
      fetch(`${API_URL}/public/glossary?limit=1`, { next: { revalidate: 3600 } }),
      fetch(`${API_URL}/public/drugs?limit=1`, { next: { revalidate: 3600 } }),
    ]);

    const topics =
      topicsRes.status === "fulfilled" && topicsRes.value.ok
        ? ((await topicsRes.value.json()) as unknown[]).length
        : 0;

    const glossary =
      glossaryRes.status === "fulfilled" && glossaryRes.value.ok
        ? ((await glossaryRes.value.json()) as { total: number }).total ?? 0
        : 0;

    const drugs =
      drugsRes.status === "fulfilled" && drugsRes.value.ok
        ? ((await drugsRes.value.json()) as unknown[]).length
        : 0;

    return { topics, glossary_terms: glossary, drugs };
  } catch {
    return { topics: 0, glossary_terms: 0, drugs: 0 };
  }
}

export default async function LearnHubPage({
  searchParams,
}: {
  searchParams?: { lang?: string };
}) {
  const [stats, t] = await Promise.all([
    fetchStats(),
    Promise.resolve(getLearnT(searchParams?.lang)),
  ]);

  const SECTIONS = [
    {
      href: "/learn/topics",
      icon: "📚",
      title: t.card_topics_title,
      subtitle: t.card_topics_subtitle,
      description: t.card_topics_desc,
      cta: t.card_topics_cta,
      color: "border-blue-200 hover:border-blue-400",
      badge: "topics",
    },
    {
      href: "/learn/drugs",
      icon: "💊",
      title: t.card_drugs_title,
      subtitle: t.card_drugs_subtitle,
      description: t.card_drugs_desc,
      cta: t.card_drugs_cta,
      color: "border-green-200 hover:border-green-400",
      badge: "drugs",
    },
    {
      href: "/learn/glossary",
      icon: "🔤",
      title: t.card_glossary_title,
      subtitle: t.card_glossary_subtitle,
      description: t.card_glossary_desc,
      cta: t.card_glossary_cta,
      color: "border-purple-200 hover:border-purple-400",
      badge: "glossary",
    },
    {
      href: "/learn/pets",
      icon: "🐾",
      title: t.card_pets_title,
      subtitle: t.card_pets_subtitle,
      description: t.card_pets_desc,
      cta: t.card_pets_cta,
      color: "border-amber-200 hover:border-amber-400",
      badge: null,
    },
    {
      href: "/learn/vet",
      icon: "🩺",
      title: t.card_vet_title,
      subtitle: t.card_vet_subtitle,
      description: t.card_vet_desc,
      cta: t.card_vet_cta,
      color: "border-green-200 hover:border-green-400",
      badge: null,
    },
  ];

  const SPECIALTIES = [
    { name: t.spec_cardiology, icon: "❤️", href: "/learn/topics#spec-кардиология" },
    { name: t.spec_neurology, icon: "🧠", href: "/learn/topics#spec-неврология" },
    { name: t.spec_internal, icon: "🩺", href: "/learn/topics#spec-терапия" },
    { name: t.spec_pharmacology, icon: "💊", href: "/learn/topics#spec-фармакология" },
    { name: t.spec_pediatrics, icon: "👶", href: "/learn/topics#spec-педиатрия" },
    { name: t.spec_surgery, icon: "🔬", href: "/learn/topics#spec-хирургия" },
    { name: t.spec_obstetrics, icon: "🤱", href: "/learn/topics#spec-акушерство-и-гинекология" },
    { name: t.spec_psychiatry, icon: "🧩", href: "/learn/topics#spec-психиатрия" },
  ];

  return (
    <>
      {/* JSON-LD */}
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "EducationalOrganization",
            name: "MedMind Learn",
            description: "Plain-language medical education for patients, students, and curious minds",
            url: `${SITE_URL}/learn`,
            audience: { "@type": "Patient" },
          }),
        }}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
        {/* Hero */}
        <div className="text-center py-14 sm:py-20">
          <div className="inline-block px-3 py-1 rounded-full bg-blue-50 border border-blue-100 font-syne font-semibold text-xs text-blue-600 mb-5">
            {t.hub_badge}
          </div>
          <h1 className="font-syne font-black text-4xl sm:text-5xl text-ink mb-4 leading-tight">
            {t.hub_h1}<br className="hidden sm:block" />
            <span className="text-accent"> {t.hub_h1_accent}</span>
          </h1>
          <p className="font-serif text-ink-3 text-lg max-w-2xl mx-auto mb-8 leading-relaxed">
            {t.hub_subtitle}
          </p>

          {/* Stats */}
          {(stats.topics > 0 || stats.drugs > 0) && (
            <div className="flex flex-wrap items-center justify-center gap-6 mb-8">
              {stats.topics > 0 && (
                <div className="text-center">
                  <div className="font-syne font-black text-3xl text-ink">{stats.topics}+</div>
                  <div className="font-serif text-xs text-ink-3">{t.hub_stat_topics}</div>
                </div>
              )}
              {stats.drugs > 0 && (
                <div className="w-px h-8 bg-border hidden sm:block" />
              )}
              {stats.drugs > 0 && (
                <div className="text-center">
                  <div className="font-syne font-black text-3xl text-ink">{stats.drugs}+</div>
                  <div className="font-serif text-xs text-ink-3">{t.hub_stat_drugs}</div>
                </div>
              )}
              {stats.glossary_terms > 0 && (
                <>
                  <div className="w-px h-8 bg-border hidden sm:block" />
                  <div className="text-center">
                    <div className="font-syne font-black text-3xl text-ink">{stats.glossary_terms}+</div>
                    <div className="font-serif text-xs text-ink-3">{t.hub_stat_glossary}</div>
                  </div>
                </>
              )}
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/learn/topics"
              className="px-7 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
            >
              {t.hub_btn_browse}
            </Link>
            <Link
              href="/register"
              className="px-7 py-3 rounded-xl border border-border bg-surface font-syne font-bold text-sm text-ink hover:border-ink transition-colors"
            >
              {t.hub_btn_signup}
            </Link>
          </div>
        </div>

        {/* Quick specialty nav */}
        <div className="mb-12">
          <h2 className="font-syne font-black text-xl text-ink mb-4 text-center">{t.hub_by_specialty}</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {SPECIALTIES.map((s) => (
              <Link
                key={s.href}
                href={s.href}
                className="group flex items-center gap-3 bg-surface border border-border rounded-xl p-4 hover:border-ink hover:shadow-sm transition-all"
              >
                <span className="text-xl">{s.icon}</span>
                <span className="font-syne font-semibold text-sm text-ink-2 group-hover:text-ink leading-tight">
                  {s.name}
                </span>
              </Link>
            ))}
          </div>
        </div>

        {/* Section cards */}
        <div className="grid sm:grid-cols-2 gap-5 mb-14">
          {SECTIONS.map((s) => (
            <Link
              key={s.href}
              href={s.href}
              className={`group block bg-surface border-2 rounded-2xl p-6 hover:shadow-md transition-all ${s.color}`}
            >
              <div className="flex items-start justify-between mb-3">
                <span className="text-3xl">{s.icon}</span>
                {s.badge === "topics" && stats.topics > 0 && (
                  <span className="font-serif text-xs text-ink-3/60 bg-bg-2 px-2 py-0.5 rounded border border-border">
                    {stats.topics} {t.hub_stat_topics}
                  </span>
                )}
                {s.badge === "drugs" && stats.drugs > 0 && (
                  <span className="font-serif text-xs text-ink-3/60 bg-bg-2 px-2 py-0.5 rounded border border-border">
                    {stats.drugs} {t.hub_stat_drugs}
                  </span>
                )}
                {s.badge === "glossary" && stats.glossary_terms > 0 && (
                  <span className="font-serif text-xs text-ink-3/60 bg-bg-2 px-2 py-0.5 rounded border border-border">
                    {stats.glossary_terms} {t.hub_stat_glossary}
                  </span>
                )}
              </div>
              <div className="font-syne font-black text-xl text-ink mb-1">{s.title}</div>
              <div className="font-serif text-xs text-ink-3/60 mb-3 uppercase tracking-wide">{s.subtitle}</div>
              <p className="font-serif text-sm text-ink-3 leading-relaxed mb-4">{s.description}</p>
              <div className="font-syne font-semibold text-sm text-ink-2 group-hover:text-ink transition-colors">
                {s.cta}
              </div>
            </Link>
          ))}
        </div>

        {/* For professionals CTA */}
        <div className="bg-ink rounded-2xl p-8 text-center">
          <div className="font-syne font-black text-2xl text-white mb-2">
            {t.pro_h2}
          </div>
          <p className="font-serif text-sm text-white/70 mb-5 max-w-xl mx-auto">
            {t.pro_desc}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/register"
              className="px-7 py-3 rounded-xl bg-white text-ink font-syne font-bold text-sm hover:bg-gray-100 transition-colors"
            >
              {t.pro_start}
            </Link>
            <Link
              href="/how-it-works"
              className="px-7 py-3 rounded-xl border border-white/20 text-white font-syne font-bold text-sm hover:border-white/60 transition-colors"
            >
              {t.pro_how}
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
