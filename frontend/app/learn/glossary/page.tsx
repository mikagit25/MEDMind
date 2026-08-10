import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getLearnT, interpolate } from "@/lib/learn-i18n";

const GLOSSARY_TITLES: Record<string, string> = {
  en: "Medical Glossary — Plain Language Definitions",
  ru: "Медицинский глоссарий — простые определения",
  de: "Medizinisches Glossar — verständliche Definitionen",
  fr: "Glossaire médical — définitions simples",
  es: "Glosario médico — definiciones sencillas",
  tr: "Tıbbi Sözlük — Basit Tanımlar",
  ar: "المسرد الطبي — تعريفات بسيطة",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const SUPPORTED_LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const locale = headers().get("x-locale") ?? "en";
  const canonical = locale === "en" ? `${SITE_URL}/learn/glossary` : `${SITE_URL}/${locale}/learn/glossary`;
  return {
    title: GLOSSARY_TITLES[locale] ?? GLOSSARY_TITLES.en,
    description:
      "Plain-language definitions of medical terms. Understand what doctors mean without a medical degree. Free, educational, for everyone.",
    alternates: {
      canonical,
      languages: {
        "x-default": `${SITE_URL}/learn/glossary`,
        ...Object.fromEntries(
          SUPPORTED_LOCALES.map((l) => [l, l === "en" ? `${SITE_URL}/learn/glossary` : `${SITE_URL}/${l}/learn/glossary`])
        ),
      },
    },
    openGraph: {
      title: GLOSSARY_TITLES[locale] ?? GLOSSARY_TITLES.en,
      description: "Plain-language medical definitions for everyone.",
      url: canonical,
      type: "website",
    },
  };
}

type GlossaryTerm = {
  term: string;
  simple_definition: string;
  slug: string;
  module_title: string;
};

async function fetchGlossary(locale: string): Promise<GlossaryTerm[]> {
  try {
    const res = await fetch(`${API_URL}/public/glossary?limit=500&locale=${locale}`, {
      next: { revalidate: 86400, tags: [`glossary-${locale}`] },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.terms ?? [];
  } catch {
    return [];
  }
}

// Russian Cyrillic alphabet for letter nav when locale=ru
const ALPHABET_RU = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ".split("");
const ALPHABET_EN = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

export default async function GlossaryPage() {
  const locale = headers().get("x-locale") ?? "en";
  const t = getLearnT(locale);
  const terms = await fetchGlossary(locale);

  // Group by first letter
  const grouped: Record<string, GlossaryTerm[]> = {};
  for (const term of terms) {
    const letter = term.term[0]?.toUpperCase() ?? "#";
    if (!grouped[letter]) grouped[letter] = [];
    grouped[letter].push(term);
  }
  const availableLetters = Object.keys(grouped).sort();
  const ALPHABET = locale === "ru" ? ALPHABET_RU : ALPHABET_EN;

  return (
    <>
      {/* JSON-LD */}
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "MedicalWebPage",
            name: "Medical Glossary",
            description: "Plain-language definitions of medical terms",
            url: `${SITE_URL}/learn/glossary`,
            audience: { "@type": "Patient" },
            medicalAudience: [{ "@type": "MedicalAudience", audienceType: "Patient" }],
          }),
        }}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        {/* Hero */}
        <div className="text-center mb-10">
          <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink mb-3">
            {t.glossary_h1}
          </h1>
          <p className="font-serif text-ink-3 text-base max-w-xl mx-auto">
            {terms.length > 0
              ? interpolate(t.glossary_count, { count: terms.length })
              : t.glossary_empty_desc}
          </p>
        </div>

        {terms.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">📖</div>
            <p className="font-syne font-bold text-ink text-lg mb-2">{t.glossary_coming_soon}</p>
            <p className="font-serif text-ink-3 text-sm mb-6">{t.glossary_coming_desc}</p>
            <Link href="/register" className="inline-block px-6 py-2.5 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors">
              {t.glossary_notify}
            </Link>
          </div>
        ) : (
          <>
            {/* Alphabet nav */}
            <div className="flex flex-wrap gap-1.5 justify-center mb-10">
              {ALPHABET.map((letter) => (
                <a
                  key={letter}
                  href={`#letter-${letter}`}
                  className={`w-8 h-8 rounded-lg flex items-center justify-center font-syne font-bold text-sm transition-colors ${
                    availableLetters.includes(letter)
                      ? "bg-surface border border-border text-ink hover:bg-ink hover:text-white"
                      : "bg-bg-2 text-ink-3 cursor-default"
                  }`}
                >
                  {letter}
                </a>
              ))}
            </div>

            {/* Terms by letter */}
            <div className="space-y-10">
              {availableLetters.map((letter) => (
                <section key={letter} id={`letter-${letter}`}>
                  <h2 className="font-syne font-black text-2xl text-ink mb-4 border-b border-border pb-2">
                    {letter}
                  </h2>
                  <div className="grid sm:grid-cols-2 gap-3">
                    {grouped[letter].map((term) => (
                      <Link
                        key={term.slug}
                        href={`/learn/glossary/${term.slug}`}
                        className="group block bg-surface border border-border rounded-xl p-4 hover:border-ink hover:shadow-sm transition-all"
                      >
                        <div className="font-syne font-bold text-sm text-ink group-hover:text-accent mb-1">
                          {term.term}
                        </div>
                        <p className="font-serif text-xs text-ink-3 line-clamp-2">
                          {term.simple_definition}
                        </p>
                        <div className="mt-2 font-serif text-xs text-ink-3/60">
                          {t.glossary_from} {term.module_title}
                        </div>
                      </Link>
                    ))}
                  </div>
                </section>
              ))}
            </div>

            {/* CTA */}
            <div className="mt-16 text-center bg-surface border border-border rounded-2xl p-8">
              <h2 className="font-syne font-black text-xl text-ink mb-2">
                {t.glossary_cta_h2}
              </h2>
              <p className="font-serif text-sm text-ink-3 mb-5">
                {t.glossary_cta_desc}
              </p>
              <Link
                href="/register"
                className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
              >
                {t.glossary_cta_btn}
              </Link>
            </div>
          </>
        )}
      </div>
    </>
  );
}
