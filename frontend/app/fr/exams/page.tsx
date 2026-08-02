// SYNC-GROUP: exams-hub
// /exams (EN) · /ar/exams (AR) · /es/exams (ES) · /ru/exams (RU) · /de/exams (DE) · /fr/exams (FR) · /tr/exams (TR) ← you are here: FR
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Préparation aux examens d'autorisation infirmière — NCLEX, Golfe, UKMLA | MedMind AI",
  description:
    "Préparez-vous à tout examen d'autorisation infirmière : NCLEX-RN, SNLE, DHA, QCHP, OMSB, NHRA, MOH UAE, HAAD et UKMLA. Questions avec IA et plans d'étude personnalisés.",
  alternates: {
    canonical: `${SITE_URL}/fr/exams`,
    languages: {
      "en":        `${SITE_URL}/exams`,
      "ar":        `${SITE_URL}/ar/exams`,
      "es":        `${SITE_URL}/es/exams`,
      "ru":        `${SITE_URL}/ru/exams`,
      "de":        `${SITE_URL}/de/exams`,
      "fr":        `${SITE_URL}/fr/exams`,
      "tr":        `${SITE_URL}/tr/exams`,
      "x-default": `${SITE_URL}/exams`,
    },
  },
  openGraph: {
    title: "Préparation aux examens d'autorisation infirmière — MedMind AI",
    description: "Une plateforme pour tous les grands examens d'autorisation infirmière.",
    url: `${SITE_URL}/fr/exams`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const EXAM_FAMILIES = [
  {
    family: "NCLEX",
    flag: "🇺🇸",
    headline: "NCLEX-RN / NCLEX-PN",
    desc: "Simulation CAT adaptive (75–145 questions), SATA, NGN, explications IA pour les 7 catégories Client Needs. La référence américaine pour la licence infirmière.",
    href: "/fr/nclex",
    cta: "Prép. NCLEX →",
    color: "border-blue-200 bg-blue-50",
    exams: ["NCLEX-RN", "NCLEX-PN"],
  },
  {
    family: "Gulf",
    flag: "🌍",
    headline: "Gulf Prometric — 7 examens",
    desc: "Tous les examens de licence infirmière Prometric du Golfe : SNLE (Arabie Saoudite), DHA (Dubaï), QCHP (Qatar), OMSB (Oman), NHRA (Bahreïn), MOH UAE, DOH/HAAD (Abu Dabi). Un bundle — tous les pays.",
    href: "/fr/gulf",
    cta: "Examens du Golfe →",
    color: "border-amber-200 bg-amber-50",
    exams: ["SNLE", "DHA", "QCHP", "OMSB", "NHRA", "MOH UAE", "DOH/HAAD"],
  },
  {
    family: "UK",
    flag: "🇬🇧",
    headline: "UKMLA / MLA",
    desc: "UK Medical Licensing Assessment — questions de connaissance clinique alignées sur le blueprint MLA. Pour les infirmières et médecins étrangers s'inscrivant au Royaume-Uni.",
    href: "/nurses",
    cta: "UKMLA →",
    color: "border-purple-200 bg-purple-50",
    exams: ["UKMLA", "MLA"],
  },
];

const GULF_EXAMS = [
  { slug: "snle",    label: "SNLE",     country: "Arabie Saoudite" },
  { slug: "dha",     label: "DHA",      country: "Dubaï, EAU" },
  { slug: "qchp",   label: "QCHP",     country: "Qatar" },
  { slug: "omsb",   label: "OMSB",     country: "Oman" },
  { slug: "nhra",   label: "NHRA",     country: "Bahreïn" },
  { slug: "moh-uae", label: "MOH UAE", country: "EAU (Émirats du Nord)" },
  { slug: "haad",   label: "DOH/HAAD", country: "Abu Dabi, EAU" },
];

export default function FrenchExamsHubPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />

      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          Préparation aux examens d&apos;autorisation en soins infirmiers
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-10 max-w-2xl">
          Une plateforme pour tous les grands examens d&apos;autorisation infirmière — pratique adaptative, explications IA et plans d&apos;étude calés sur votre date d&apos;examen.
        </p>

        <div className="space-y-5 mb-14">
          {EXAM_FAMILIES.map(f => (
            <div key={f.family} className={`border ${f.color} rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center gap-5`}>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl">{f.flag}</span>
                  <span className="font-syne font-black text-lg text-ink">{f.headline}</span>
                </div>
                <p className="text-sm text-ink-2 leading-relaxed mb-3">{f.desc}</p>
                <div className="flex flex-wrap gap-2">
                  {f.exams.map(e => (
                    <span key={e} className="text-xs font-syne font-bold bg-white/80 border border-border px-2 py-0.5 rounded-full text-ink-2">
                      {e}
                    </span>
                  ))}
                </div>
              </div>
              <Link href={f.href}
                className="font-syne font-bold text-sm bg-ink text-white px-5 py-2.5 rounded-xl hover:bg-red transition-colors flex-shrink-0 text-center">
                {f.cta}
              </Link>
            </div>
          ))}
        </div>

        <h2 className="font-syne font-bold text-xl text-ink mb-5">Gulf Prometric — Examens individuels</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-12">
          {GULF_EXAMS.map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`}
              className="bg-surface border border-border rounded-xl p-4 hover:border-ink/30 hover:shadow-sm transition-all">
              <div className="font-syne font-bold text-sm text-ink">{e.label}</div>
              <div className="text-xs text-ink-3 mt-0.5">{e.country}</div>
            </Link>
          ))}
          <Link href="/fr/gulf"
            className="bg-ink text-white rounded-xl p-4 hover:bg-red transition-colors">
            <div className="font-syne font-bold text-sm">Tout comparer →</div>
            <div className="text-xs text-white/70 mt-0.5">Gulf Bundle</div>
          </Link>
        </div>

        <div className="text-center">
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-4 rounded-xl hover:bg-red transition-colors">
            Commencer gratuitement — 10 questions de pratique →
          </Link>
          <p className="text-xs font-serif text-ink-3 mt-3">Sans carte bancaire</p>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
