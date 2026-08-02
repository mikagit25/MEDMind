// SYNC-GROUP: nclex-landing
// /nclex (EN) · /ar/nclex (AR) · /es/nclex (ES) · /ru/nclex (RU) · /de/nclex (DE) · /fr/nclex (FR) · /tr/nclex (TR) ← you are here: DE
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "NCLEX-RN Vorbereitung 2025 — Adaptive CAT-Simulationen & KI-Erklärungen | MedMind AI",
  description:
    "Bereiten Sie sich auf NCLEX-RN vor mit adaptiven CAT-Simulationen (75–145 Fragen), SATA, NGN und KI-Erklärungen für jede Frage. Verfolgen Sie Ihre Leistung in allen 7 NCLEX-Kategorien. Kostenlos starten.",
  alternates: {
    canonical: `${SITE_URL}/de/nclex`,
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
    title: "NCLEX-RN Vorbereitung — MedMind AI",
    description: "Adaptive CAT-Simulation · KI-Erklärungen · Kategorie-Analyse · 600+ Fragen",
    url: `${SITE_URL}/de/nclex`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const MODES = [
  { id: "Demo",          questions: "10",    tag: "Kostenlos — kein Login",  desc: "10 Fragen aus allen Kategorien mit vollständigen KI-Erklärungen — ohne Anmeldung.", free: true },
  { id: "NCLEX-RN 75",  questions: "75",    tag: "Mindest-Prüfungslänge",   desc: "Standard-adaptive Simulation. Die Prüfung endet hier bei klarem Bestehen oder Nichtbestehen.", free: false },
  { id: "NCLEX-RN 85",  questions: "85",    tag: "Erweiterte Simulation",   desc: "Durch die Grenzzone. Schwierigere Fragen — genauere Bewertung der Prüfungsbereitschaft.", free: false },
  { id: "NCLEX-RN 145", questions: "145",   tag: "Maximale Länge",          desc: "Vollständige Simulation. Alle Kategorien in der Tiefe. Ideal für die letzte Vorbereitungswoche.", free: false },
  { id: "Nach Kategorie", questions: "10–30", tag: "Gezieltes Üben",        desc: "Wählen Sie eine der 7 Client Needs-Kategorien und trainieren Sie sie gezielt.", free: false },
];

const FEATURES = [
  { title: "Adaptive CAT-Simulation",         desc: "Echte NCLEX-RN-Logik: Die Prüfung passt die Schwierigkeit nach jeder Antwort an. Wählen Sie 75, 85 oder 145 Fragen — dasselbe Format wie bei Pearson VUE." },
  { title: "KI-Erklärung für jede Frage",    desc: "Nach jeder Antwort erhalten Sie eine vollständige klinische Begründung: warum die richtige Antwort korrekt und jeder Distraktor falsch ist." },
  { title: "7 Client Needs-Kategorien",       desc: "Jede Frage ist einer der 7 NCLEX-Kategorien zugeordnet. Nach der Prüfung sehen Sie Ihre genaue Punktzahl pro Kategorie." },
  { title: "CJMM-Kompetenz-Tracking",         desc: "Verfolgen Sie Ihre Fortschritte in 6 klinischen Urteilskompetenzen: Hinweise erkennen, analysieren, Hypothesen priorisieren, Lösungen generieren, handeln, Ergebnisse bewerten." },
  { title: "Fehlerfragen wiederholen",        desc: "Nach jeder Sitzung starten Sie eine gezielte Wiederholungssitzung mit nur den Fragen, die Sie falsch beantwortet haben." },
  { title: "SATA, Berechnungen & NGN",        desc: "Nicht nur Standard-MCQ. Üben Sie Wähle-alles-was-zutrifft, IV-Berechnungen, geordnete Antworten und Next Generation NCLEX-Fragetypen." },
];

const FAQ = [
  {
    q: "Ist das Demo wirklich kostenlos?",
    a: "Ja. Das 10-Fragen-Demo erfordert keinen Account. Sie erhalten vollständige KI-Erklärungen und die Punkteaufschlüsselung — keine Kreditkarte, keine E-Mail erforderlich.",
  },
  {
    q: "Sind die Fragen auf Deutsch?",
    a: "Die Übungsfragen sind auf Englisch (das echte Examen ist auf Englisch), aber die KI-Erklärungen sind auf Deutsch verfügbar. So verstehen Sie Konzepte in Ihrer Sprache und gewöhnen sich gleichzeitig an die englische Fachterminologie.",
  },
  {
    q: "Sind die Fragen für NCLEX 2024/2025 aktuell?",
    a: "Ja. Die Fragenbank enthält Next Generation NCLEX (NGN)-Fragetypen, die 2023 eingeführt wurden — SATA, geordnete Antworten und Berechnungsfragen. Der adaptive Algorithmus spiegelt die CAT-Logik von Pearson VUE wider.",
  },
  {
    q: "Ist MedMind AI mit NCSBN oder NCLEX verbunden?",
    a: "Nein. MedMind AI ist eine unabhängige Vorbereitungsplattform ohne Verbindung zum NCSBN oder dem NCLEX-Programm.",
  },
];

export default function GermanNclexPage() {
  return (
    <>
      <ArticleNav />

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-12 sm:pb-16">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-red/10 border border-red/20 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
              NCLEX-RN 2025 Vorbereitung
            </div>
            <h1 className="font-syne font-extrabold text-3xl sm:text-4xl lg:text-5xl text-ink mb-4 leading-tight">
              NCLEX-RN bestehen<br />beim ersten Versuch.
            </h1>
            <p className="text-ink-2 text-base sm:text-lg leading-relaxed mb-8 max-w-lg">
              Adaptive CAT-Simulationen, KI-gestützte Analyse des klinischen Denkens und Leistungsanalysen über alle NCLEX Client Needs-Kategorien.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/register"
                className="inline-block font-syne font-bold text-base bg-red text-white px-8 py-4 rounded-xl hover:bg-ink transition-colors">
                Kostenlos starten →
              </Link>
              <Link href="/login"
                className="inline-block font-syne font-semibold text-base border border-border text-ink-2 px-8 py-4 rounded-xl hover:border-ink hover:text-ink transition-colors">
                Anmelden
              </Link>
            </div>
            <p className="text-xs text-ink-3 mt-4 font-syne">Kostenloser Account · 5 KI-Fragen/Tag · Keine Kreditkarte erforderlich</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { value: "600+", label: "NCLEX-Fragen", sub: "SATA · CAT · NGN · Berechnungen" },
              { value: "12",   label: "Pflegemodule", sub: "evidenzbasierter Inhalt" },
              { value: "7",    label: "Client Needs", sub: "vollständige Kategorienabdeckung" },
              { value: "6",    label: "CJMM-Kompetenzen", sub: "klinisches Urteil" },
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
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Fünf Übungsmodi</h2>
            <p className="text-ink-3 text-sm">Vom kostenlosen 10-Fragen-Demo bis zur vollen 145-Fragen-Simulation.</p>
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
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Alles, was Sie zum Bestehen brauchen</h2>
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
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-8 text-center">Häufig gestellte Fragen</h2>
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
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">Bereit anzufangen?</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            Probieren Sie jetzt das kostenlose Demo — 10 Fragen, vollständige KI-Erklärungen, kein Account erforderlich. Erstellen Sie einen Account für vollständige CAT-Simulationen und persönliche Analytik.
          </p>
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-white text-ink px-8 py-4 rounded-xl hover:bg-red hover:text-white transition-colors">
            Kostenlos starten →
          </Link>
          <p className="text-white/30 text-xs mt-5 font-syne">Keine Kreditkarte · Kostenloser Plan: 5 KI-Fragen/Tag</p>
        </div>
      </section>

      <PublicFooter />
    </>
  );
}
