// SYNC-GROUP: gulf-landing
// This page is part of a multilingual set. When content changes here,
// update all sibling pages to stay in sync:
//   /exams/gulf (EN)   /ar/gulf  (AR)   /ru/gulf  (RU)
//   /tr/gulf  (TR)     /de/gulf  (DE)   /fr/gulf  (FR)
//   /es/gulf  (ES) ← you are here
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Exámenes de Enfermería del Golfo 2025 — SNLE, DHA, QCHP, OMSB, NHRA | MedMind AI",
  description:
    "Prepárate para los exámenes de licencia de enfermería del Golfo Pérsico: SNLE Arabia Saudita, DHA Dubái, QCHP Qatar, OMSB Omán, NHRA Baréin. Preguntas Prometric con explicaciones de IA.",
  alternates: {
    canonical: `${SITE_URL}/es/gulf`,
    languages: {
      en: `${SITE_URL}/exams/gulf`,
      ru: `${SITE_URL}/ru/gulf`,
      ar: `${SITE_URL}/ar/gulf`,
      es: `${SITE_URL}/es/gulf`,
      "x-default": `${SITE_URL}/exams/gulf`,
    },
  },
  openGraph: {
    title: "Exámenes de Enfermería del Golfo — MedMind AI",
    description: "SNLE · DHA · QCHP · OMSB · NHRA · MOH UAE · DOH — todos en un solo lugar",
    url: `${SITE_URL}/es/gulf`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const EXAMS = [
  { slug: "snle",    name: "SNLE — Arabia Saudita",        body: "Comisión Saudita de Especialidades de Salud (SCHS)" },
  { slug: "dha",     name: "DHA — Dubái, EAU",            body: "Autoridad de Salud de Dubái (DHA)" },
  { slug: "qchp",   name: "QCHP — Qatar",                 body: "Consejo de Profesionales de Salud de Qatar (QCHP)" },
  { slug: "omsb",   name: "OMSB — Omán",                  body: "Junta de Especialidades Médicas de Omán (OMSB)" },
  { slug: "nhra",   name: "NHRA — Baréin",                body: "Autoridad Nacional Regulatoria de Salud (NHRA)" },
  { slug: "moh-uae", name: "MOH UAE — Emirates del Norte", body: "Ministerio de Salud de EAU (MOHAP)" },
  { slug: "haad",   name: "DOH — Abu Dabi, EAU",          body: "Departamento de Salud de Abu Dabi (DOH)" },
];

const CATEGORIES = [
  "Fundamentos de Enfermería",
  "Enfermería Médico-Quirúrgica",
  "Farmacología y Administración de Medicamentos",
  "Enfermería Maternal y Neonatal",
  "Enfermería Pediátrica",
  "Salud Mental",
  "Salud Comunitaria y Pública",
  "Liderazgo y Gestión",
];

export default function SpanishGulfPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />
      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <div className="mb-2 text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
          Región del Golfo · Licencia Prometric
        </div>
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          Exámenes de Enfermería del Golfo — Comparativa Completa
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-6 max-w-3xl">
          Los 7 exámenes de licencia de enfermería Prometric del Golfo en un solo lugar. Muchas enfermeras se preparan para varios exámenes simultáneamente — el país que acepta primero es donde van a trabajar. El Gulf Bundle abre el acceso a los 7 a la vez.
        </p>
        <div className="flex flex-wrap gap-3 mb-8">
          <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            Comenzar gratis →
          </Link>
          <Link href="/exams/gulf" className="font-syne font-bold text-sm border border-border text-ink px-6 py-3 rounded-xl hover:bg-surface transition-colors">
            English
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {[
            { num: "7",    label: "exámenes" },
            { num: "608+", label: "preguntas" },
            { num: "3 h",  label: "duración" },
            { num: "65%",  label: "nota de aprobación" },
          ].map(({ num, label }) => (
            <div key={label} className="bg-surface border border-border rounded-2xl p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">{num}</div>
              <div className="text-xs font-syne text-ink-3 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-5">Exámenes disponibles</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {EXAMS.map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`}
              className="bg-surface border border-border rounded-xl p-5 hover:border-ink/30 hover:shadow-sm transition-all">
              <div className="font-syne font-bold text-sm text-ink mb-1">{e.name}</div>
              <div className="text-xs text-ink-3 mb-3">{e.body}</div>
              <div className="text-xs font-syne text-ink-2">100 preguntas · 3 horas · Aprobación 65%</div>
            </Link>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-4">Ocho categorías del examen</h2>
        <p className="text-sm text-ink-2 mb-5">
          Todos los exámenes Prometric del Golfo cubren las mismas 8 categorías clínicas. Prepararse para el SNLE te prepara en un 80%+ para el DHA, QCHP y los demás.
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
            Para enfermeras que desean trabajar en el Golfo
          </h2>
          <p className="text-sm text-ink-2 leading-relaxed mb-4">
            Todos los exámenes Prometric del Golfo cubren las mismas 8 categorías: fundamentos, médico-quirúrgica, farmacología, salud materna, pediatría, salud mental, salud comunitaria y liderazgo. Un plan de estudio — siete países.
          </p>
          <Link href="/register" className="inline-block font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            Registrarse gratis →
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 pb-10">
        <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-6">
          MedMind AI no está afiliado, respaldado ni asociado con ningún organismo regulador del Golfo ni con Prometric. Los parámetros de los exámenes provienen de fuentes oficiales públicamente disponibles. Verifique siempre los requisitos actuales directamente con la autoridad correspondiente antes de aplicar.
        </p>
      </section>
      <PublicFooter />
    </div>
  );
}
