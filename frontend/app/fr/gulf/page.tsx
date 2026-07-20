// SYNC-GROUP: gulf-landing
// This page is part of a multilingual set. When content changes here,
// update all sibling pages to stay in sync:
//   /exams/gulf (EN)   /ar/gulf  (AR)   /ru/gulf  (RU)
//   /tr/gulf  (TR)     /de/gulf  (DE)   /es/gulf  (ES)
//   /fr/gulf  (FR) ← you are here
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Examens Infirmiers du Golfe 2025 — SNLE, DHA, QCHP, OMSB, NHRA | MedMind AI",
  description:
    "Préparez les examens de licence infirmière du Golfe Persique : SNLE Arabie Saoudite, DHA Dubaï, QCHP Qatar, OMSB Oman, NHRA Bahreïn. Questions Prometric avec explications IA.",
  alternates: {
    canonical: `${SITE_URL}/fr/gulf`,
    languages: {
      en: `${SITE_URL}/exams/gulf`,
      ru: `${SITE_URL}/ru/gulf`,
      ar: `${SITE_URL}/ar/gulf`,
      fr: `${SITE_URL}/fr/gulf`,
      "x-default": `${SITE_URL}/exams/gulf`,
    },
  },
  openGraph: {
    title: "Examens Infirmiers du Golfe — MedMind AI",
    description: "SNLE · DHA · QCHP · OMSB · NHRA · MOH UAE · DOH — tous au même endroit",
    url: `${SITE_URL}/fr/gulf`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const EXAMS = [
  { slug: "snle",    name: "SNLE — Arabie Saoudite",       body: "Commission saoudienne des spécialités de santé (SCHS)" },
  { slug: "dha",     name: "DHA — Dubaï, EAU",            body: "Autorité sanitaire de Dubaï (DHA)" },
  { slug: "qchp",   name: "QCHP — Qatar",                 body: "Conseil des professionnels de santé du Qatar (QCHP)" },
  { slug: "omsb",   name: "OMSB — Oman",                  body: "Conseil des spécialités médicales d'Oman (OMSB)" },
  { slug: "nhra",   name: "NHRA — Bahreïn",               body: "Autorité nationale de réglementation sanitaire (NHRA)" },
  { slug: "moh-uae", name: "MOH UAE — Émirats du Nord",   body: "Ministère de la Santé des EAU (MOHAP)" },
  { slug: "haad",   name: "DOH — Abou Dabi, EAU",         body: "Département de la Santé d'Abou Dabi (DOH)" },
];

const CATEGORIES = [
  "Fondamentaux des soins infirmiers",
  "Soins médico-chirurgicaux",
  "Pharmacologie et administration des médicaments",
  "Soins maternels et néonatals",
  "Soins pédiatriques",
  "Santé mentale",
  "Santé communautaire et publique",
  "Leadership et management",
];

export default function FrenchGulfPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />
      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <div className="mb-2 text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
          Région du Golfe · Licence Prometric
        </div>
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          Examens infirmiers du Golfe — Comparatif complet
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-6 max-w-3xl">
          Les 7 examens de licence infirmière Prometric du Golfe réunis en un seul endroit. De nombreuses infirmières préparent plusieurs examens simultanément — le pays qui accepte en premier devient le lieu de travail. Le Gulf Bundle ouvre l'accès aux 7 à la fois.
        </p>
        <div className="flex flex-wrap gap-3 mb-8">
          <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            Commencer gratuitement →
          </Link>
          <Link href="/exams/gulf" className="font-syne font-bold text-sm border border-border text-ink px-6 py-3 rounded-xl hover:bg-surface transition-colors">
            English
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {[
            { num: "7",    label: "examens" },
            { num: "608+", label: "questions" },
            { num: "3 h",  label: "durée" },
            { num: "65%",  label: "note de passage" },
          ].map(({ num, label }) => (
            <div key={label} className="bg-surface border border-border rounded-2xl p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">{num}</div>
              <div className="text-xs font-syne text-ink-3 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-5">Examens disponibles</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {EXAMS.map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`}
              className="bg-surface border border-border rounded-xl p-5 hover:border-ink/30 hover:shadow-sm transition-all">
              <div className="font-syne font-bold text-sm text-ink mb-1">{e.name}</div>
              <div className="text-xs text-ink-3 mb-3">{e.body}</div>
              <div className="text-xs font-syne text-ink-2">100 questions · 3 heures · Passage 65%</div>
            </Link>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-4">Huit catégories d'examen</h2>
        <p className="text-sm text-ink-2 mb-5">
          Tous les examens Prometric du Golfe couvrent les mêmes 8 catégories cliniques. Se préparer au SNLE vous prépare à 80%+ pour le DHA, le QCHP et les autres.
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
            Pour les infirmières souhaitant travailler dans le Golfe
          </h2>
          <p className="text-sm text-ink-2 leading-relaxed mb-4">
            Tous les examens Prometric du Golfe couvrent les mêmes 8 catégories : fondamentaux, médico-chirurgical, pharmacologie, santé maternelle, pédiatrie, santé mentale, santé communautaire et leadership. Un plan d'étude — sept pays.
          </p>
          <Link href="/register" className="inline-block font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            S'inscrire gratuitement →
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 pb-10">
        <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-6">
          MedMind AI n'est pas affilié, approuvé ou associé à un organisme de réglementation du Golfe ou à Prometric. Les paramètres des examens proviennent de sources officielles publiquement disponibles. Vérifiez toujours les exigences actuelles auprès de l'autorité compétente avant de postuler.
        </p>
      </section>
      <PublicFooter />
    </div>
  );
}
