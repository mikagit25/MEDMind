// SYNC-GROUP: nclex-landing
// /nclex (EN) · /ar/nclex (AR) · /es/nclex (ES) · /ru/nclex (RU) · /de/nclex (DE) · /fr/nclex (FR) · /tr/nclex (TR) ← you are here: FR
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Préparation NCLEX-RN 2025 — Simulations CAT adaptatives et explications IA | MedMind AI",
  description:
    "Préparez-vous au NCLEX-RN avec des simulations CAT adaptatives (75–145 questions), SATA, NGN et des explications IA pour chaque question. Suivez vos résultats dans les 7 catégories NCLEX. Commencez gratuitement.",
  alternates: {
    canonical: `${SITE_URL}/fr/nclex`,
    languages: {
      "en":        `${SITE_URL}/nclex`,
      "ar":        `${SITE_URL}/ar/nclex`,
      "es":        `${SITE_URL}/es/nclex`,
      "ru":        `${SITE_URL}/ru/nclex`,
      "de":        `${SITE_URL}/de/nclex`,
      "fr":        `${SITE_URL}/fr/nclex`,
      "tr":        `${SITE_URL}/tr/nclex`,
      "x-default": `${SITE_URL}/nclex`,
    },
  },
  openGraph: {
    title: "Préparation NCLEX-RN — MedMind AI",
    description: "Simulation CAT adaptive · explications IA · analyse par catégorie · 600+ questions",
    url: `${SITE_URL}/fr/nclex`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const MODES = [
  { id: "Démo",           questions: "10",    tag: "Gratuit — sans compte",      desc: "10 questions de toutes les catégories avec des explications IA complètes — sans inscription.", free: true },
  { id: "NCLEX-RN 75",   questions: "75",    tag: "Longueur minimale",           desc: "Simulation adaptative standard. L'examen se termine ici si la performance est clairement réussie ou échouée.", free: false },
  { id: "NCLEX-RN 85",   questions: "85",    tag: "Simulation étendue",          desc: "Traversez la zone limite. Questions plus difficiles — évaluation plus précise de la préparation.", free: false },
  { id: "NCLEX-RN 145",  questions: "145",   tag: "Longueur maximale",           desc: "Simulation complète. Toutes les catégories en profondeur. Idéal pour la dernière semaine de révision.", free: false },
  { id: "Par catégorie", questions: "10–30", tag: "Pratique ciblée",             desc: "Choisissez l'une des 7 catégories Client Needs et entraînez-vous spécifiquement dessus.", free: false },
];

const FEATURES = [
  { title: "Simulation CAT adaptive",            desc: "Vraie logique NCLEX-RN : l'examen ajuste la difficulté après chaque réponse. Choisissez 75, 85 ou 145 questions — même format que Pearson VUE." },
  { title: "Explication IA pour chaque question", desc: "Après chaque réponse, obtenez une analyse clinique complète : pourquoi la bonne réponse est correcte et pourquoi chaque distracteur est faux." },
  { title: "7 catégories Client Needs",           desc: "Chaque question est associée à l'une des 7 catégories NCLEX. Après l'examen, voyez votre score exact par catégorie." },
  { title: "Suivi des compétences CJMM",          desc: "Suivez votre maîtrise des 6 compétences de jugement clinique NCSBN : reconnaître les indices, les analyser, prioriser les hypothèses, générer des solutions, agir, évaluer les résultats." },
  { title: "Révision des questions ratées",       desc: "Après chaque session, lancez une séance de révision ciblée avec uniquement les questions que vous avez ratées." },
  { title: "SATA, calculs et NGN",                desc: "Pas seulement du MCQ standard. Entraînez-vous au Sélectionnez tout ce qui s'applique, aux calculs de perfusion IV, aux réponses ordonnées et aux questions Next Generation NCLEX." },
];

const FAQ = [
  {
    q: "La démo est vraiment gratuite ?",
    a: "Oui. La démo de 10 questions ne nécessite pas de compte. Vous obtenez des explications IA complètes et la répartition de vos scores — sans carte bancaire ni email.",
  },
  {
    q: "Les questions sont-elles en français ?",
    a: "Les questions de pratique sont en anglais (le vrai examen aussi), mais les explications IA sont disponibles en français. Cela vous permet de comprendre les concepts dans votre langue tout en vous familiarisant avec la terminologie anglaise nécessaire pour l'examen.",
  },
  {
    q: "Les questions sont-elles à jour pour NCLEX 2024/2025 ?",
    a: "Oui. La banque de questions inclut les types Next Generation NCLEX (NGN) introduits en 2023 — SATA, réponses ordonnées et calculs. L'algorithme adaptatif reproduit la logique CAT de Pearson VUE.",
  },
  {
    q: "MedMind AI est-il affilié au NCSBN ou au NCLEX ?",
    a: "Non. MedMind AI est une plateforme de préparation indépendante, sans aucune affiliation avec le NCSBN ou le programme NCLEX.",
  },
];

export default function FrenchNclexPage() {
  return (
    <>
      <ArticleNav />

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-12 sm:pb-16">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-red/10 border border-red/20 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
              NCLEX-RN 2025
            </div>
            <h1 className="font-syne font-extrabold text-3xl sm:text-4xl lg:text-5xl text-ink mb-4 leading-tight">
              Réussissez le NCLEX-RN<br />du premier coup.
            </h1>
            <p className="text-ink-2 text-base sm:text-lg leading-relaxed mb-8 max-w-lg">
              Simulations CAT adaptatives, analyse du raisonnement clinique par IA, et analyses de performance dans toutes les catégories Client Needs du NCLEX — conçu pour la façon dont les infirmières apprennent vraiment.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/register"
                className="inline-block font-syne font-bold text-base bg-red text-white px-8 py-4 rounded-xl hover:bg-ink transition-colors">
                Commencer gratuitement →
              </Link>
              <Link href="/login"
                className="inline-block font-syne font-semibold text-base border border-border text-ink-2 px-8 py-4 rounded-xl hover:border-ink hover:text-ink transition-colors">
                Se connecter
              </Link>
            </div>
            <p className="text-xs text-ink-3 mt-4 font-syne">Compte gratuit · 5 questions IA/jour · Sans carte bancaire</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { value: "600+", label: "questions NCLEX", sub: "SATA · CAT · NGN · calculs" },
              { value: "12",   label: "modules de soins", sub: "contenu fondé sur les preuves" },
              { value: "7",    label: "catégories Client Needs", sub: "couverture complète" },
              { value: "6",    label: "compétences CJMM", sub: "jugement clinique" },
            ].map((s) => (
              <div key={s.label} className="bg-surface border border-border rounded-xl p-5 flex flex-col gap-1">
                <span className="font-syne font-extrabold text-3xl sm:text-4xl text-ink">{s.value}</span>
                <span className="font-syne font-semibold text-sm text-ink leading-tight">{s.label}</span>
                <span className="text-xs text-ink-3">{s.sub}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Exam modes */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
          <div className="mb-8">
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Cinq modes d&apos;entraînement</h2>
            <p className="text-ink-3 text-sm">Du démo gratuit de 10 questions à la simulation complète de 145 questions.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODES.map((m) => (
              <div key={m.id} className={`rounded-xl border p-5 flex flex-col gap-3 ${m.free ? "border-red/30 bg-red/5" : "border-border bg-bg"}`}>
                <div className="flex items-start justify-between gap-2">
                  <span className="font-syne font-extrabold text-xl text-ink">{m.questions}</span>
                  <span className={`text-xs font-syne font-semibold px-2 py-0.5 rounded-full border ${m.free ? "bg-red/10 border-red/20 text-red" : "bg-surface border-border text-ink-3"}`}>
                    {m.tag}
                  </span>
                </div>
                <div>
                  <h3 className="font-syne font-bold text-base text-ink mb-1">{m.id}</h3>
                  <p className="text-ink-3 text-sm leading-snug">{m.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="mb-10">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Tout ce qu&apos;il faut pour réussir</h2>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex flex-col gap-3">
              <div>
                <h3 className="font-syne font-bold text-base text-ink mb-1">{f.title}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-8 text-center">Questions fréquentes</h2>
          <div className="space-y-6">
            {FAQ.map((item) => (
              <div key={item.q} className="border-b border-border pb-6 last:border-0 last:pb-0">
                <h3 className="font-syne font-bold text-base text-ink mb-2">{item.q}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="bg-ink text-white">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">Prêt à commencer ?</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            Essayez le démo gratuit maintenant — 10 questions, explications IA complètes, sans compte. Créez un compte pour accéder aux simulations CAT complètes et aux analyses personnalisées.
          </p>
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-white text-ink px-8 py-4 rounded-xl hover:bg-red hover:text-white transition-colors">
            Commencer gratuitement →
          </Link>
          <p className="text-white/30 text-xs mt-5 font-syne">Sans carte bancaire · Plan gratuit : 5 questions IA/jour</p>
        </div>
      </section>

      <PublicFooter />
    </>
  );
}
