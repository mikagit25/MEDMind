// SYNC-GROUP: gulf-landing
// This page is part of a multilingual set. When content changes here,
// update all sibling pages to stay in sync:
//   /exams/gulf (EN)   /ar/gulf  (AR)   /ru/gulf  (RU)
//   /tr/gulf  (TR)     /fr/gulf  (FR)   /es/gulf  (ES)
//   /de/gulf  (DE) ← you are here
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Pflegeexamen Golf-Region 2025 — SNLE, DHA, QCHP, OMSB, NHRA | MedMind AI",
  description:
    "Vorbereitung auf Pflegelizenzprüfungen in den Golfstaaten: SNLE Saudi-Arabien, DHA Dubai, QCHP Katar, OMSB Oman, NHRA Bahrain. Prometric-Fragen mit KI-Erklärungen.",
  alternates: {
    canonical: `${SITE_URL}/de/gulf`,
    languages: {
      en: `${SITE_URL}/exams/gulf`,
      ru: `${SITE_URL}/ru/gulf`,
      ar: `${SITE_URL}/ar/gulf`,
      de: `${SITE_URL}/de/gulf`,
      "x-default": `${SITE_URL}/exams/gulf`,
    },
  },
  openGraph: {
    title: "Golf-Pflegeprüfungen — MedMind AI",
    description: "SNLE · DHA · QCHP · OMSB · NHRA · MOH UAE · DOH — alle an einem Ort",
    url: `${SITE_URL}/de/gulf`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const EXAMS = [
  { slug: "snle",    name: "SNLE — Saudi-Arabien",       body: "Saudi Commission for Health Specialties (SCHS)" },
  { slug: "dha",     name: "DHA — Dubai, VAE",           body: "Dubai Health Authority (DHA)" },
  { slug: "qchp",   name: "QCHP — Katar",               body: "Qatar Council for Healthcare Practitioners (QCHP)" },
  { slug: "omsb",   name: "OMSB — Oman",                body: "Oman Medical Specialty Board (OMSB)" },
  { slug: "nhra",   name: "NHRA — Bahrain",             body: "National Health Regulatory Authority (NHRA)" },
  { slug: "moh-uae", name: "MOH UAE — Nördliche Emirate", body: "Ministry of Health UAE (MOHAP)" },
  { slug: "haad",   name: "DOH — Abu Dhabi, VAE",       body: "Department of Health Abu Dhabi (DOH)" },
];

const CATEGORIES = [
  "Pflegegrundlagen",
  "Medizinisch-chirurgische Pflege",
  "Pharmakologie & Medikamentenverabreichung",
  "Mütterliche und neonatale Pflege",
  "Kinderkrankenpflege",
  "Psychiatrische Pflege",
  "Gemeinde- und Volksgesundheit",
  "Führung und Management",
];

export default function GermanGulfPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />
      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <div className="mb-2 text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
          Golfregion · Prometric-Lizenzierung
        </div>
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          Pflegeprüfungen der Golfstaaten — Vollständiger Vergleich
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-6 max-w-3xl">
          Alle 8 Gulf-Prometric-Pflegelizenzprüfungen an einem Ort. Viele Pflegekräfte bereiten sich gleichzeitig auf mehrere Prüfungen vor — das Land, das zuerst zusagt, wird zum Arbeitsort. Das Gulf Bundle öffnet den Zugang zu allen 8 auf einmal.
        </p>
        <div className="flex flex-wrap gap-3 mb-8">
          <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            Kostenlos starten →
          </Link>
          <Link href="/exams/gulf" className="font-syne font-bold text-sm border border-border text-ink px-6 py-3 rounded-xl hover:bg-surface transition-colors">
            English
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {[
            { num: "7",    label: "Prüfungen" },
            { num: "608+", label: "Fragen" },
            { num: "3 Std", label: "Dauer" },
            { num: "65%",  label: "Bestehensgrenze" },
          ].map(({ num, label }) => (
            <div key={label} className="bg-surface border border-border rounded-2xl p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">{num}</div>
              <div className="text-xs font-syne text-ink-3 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-5">Verfügbare Prüfungen</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {EXAMS.map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`}
              className="bg-surface border border-border rounded-xl p-5 hover:border-ink/30 hover:shadow-sm transition-all">
              <div className="font-syne font-bold text-sm text-ink mb-1">{e.name}</div>
              <div className="text-xs text-ink-3 mb-3">{e.body}</div>
              <div className="text-xs font-syne text-ink-2">100 Fragen · 3 Stunden · Bestehen 65%</div>
            </Link>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-4">Acht Prüfungskategorien</h2>
        <p className="text-sm text-ink-2 mb-5">
          Alle Gulf-Prometric-Prüfungen decken dieselben 8 klinischen Kategorien ab. Wer sich auf SNLE vorbereitet, ist zu 80%+ auch auf DHA, QCHP und andere vorbereitet.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {CATEGORIES.map(cat => (
            <div key={cat} className="bg-surface border border-border rounded-xl p-3 text-center">
              <div className="font-syne font-semibold text-xs text-ink">{cat}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-10">
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
          <h2 className="font-syne font-bold text-base text-ink mb-2">
            Für Pflegekräfte, die in den Golfstaaten arbeiten möchten
          </h2>
          <p className="text-sm text-ink-2 leading-relaxed mb-4">
            Alle Gulf-Prometric-Pflegeprüfungen decken dieselben 8 Kategorien ab: Grundlagen, medizinisch-chirurgisch, Pharmakologie, Müttergesundheit, Pädiatrie, psychiatrische Pflege, Gemeindegesundheit und Führung. Ein Lernplan — sieben Länder.
          </p>
          <Link href="/register" className="inline-block font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            Kostenlos registrieren →
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 pb-10">
        <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-6">
          MedMind AI ist nicht mit einer Golfregion-Regulierungsbehörde oder Prometric verbunden, von diesen empfohlen oder mit ihnen assoziiert. Prüfungsparameter stammen aus öffentlich zugänglichen offiziellen Quellen. Überprüfen Sie aktuelle Anforderungen direkt bei der zuständigen Behörde.
        </p>
      </section>
      <PublicFooter />
    </div>
  );
}
