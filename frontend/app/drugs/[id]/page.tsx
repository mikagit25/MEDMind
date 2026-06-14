import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { DrugDetailTabs } from "@/components/drugs/DrugDetailTabs";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export const dynamic = "force-dynamic";

type Drug = {
  id: string; name: string; generic_name?: string; drug_class?: string;
  mechanism?: string; indications?: string[]; contraindications?: string[];
  adverse_effects?: Record<string, any>; dosing?: Record<string, any>;
  monitoring?: string[]; black_box_warning?: string; interactions?: string[];
  is_high_yield?: boolean; is_nti?: boolean; is_veterinary?: boolean;
  image_url?: string; available_langs?: string[];
};

type Alternative = {
  id: string; name: string; generic_name?: string; drug_class?: string;
  is_high_yield?: boolean; reason: string; image_url?: string;
};

async function fetchDrug(id: string, lang: string): Promise<Drug | null> {
  try {
    const res = await fetch(
      `${API_URL}/drugs/${encodeURIComponent(id)}?lang=${encodeURIComponent(lang)}`,
      { cache: "no-store" }
    );
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch {
    return null;
  }
}

async function fetchAlternatives(id: string): Promise<Alternative[]> {
  try {
    const res = await fetch(`${API_URL}/drugs/${encodeURIComponent(id)}/alternatives`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data?.alternatives ?? [];
  } catch {
    return [];
  }
}

async function fetchSpecies(): Promise<any[]> {
  try {
    const res = await fetch(`${API_URL}/veterinary/species`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { lang?: string };
}): Promise<Metadata> {
  const lang = searchParams.lang ?? "en";
  const drug = await fetchDrug(params.id, lang);
  if (!drug) return { title: "Drug Not Found — MedMind AI" };

  const title = `${drug.name}${drug.generic_name && drug.generic_name !== drug.name ? ` (${drug.generic_name})` : ""} — MedMind AI`;
  const description = drug.mechanism
    ? `${drug.name}: ${drug.mechanism.slice(0, 155)}`
    : `Pharmacology, dosing, side effects, and interactions for ${drug.name}${drug.drug_class ? ` — ${drug.drug_class}` : ""}.`;
  const canonicalUrl = `${SITE_URL}/drugs/${params.id}${lang !== "en" ? `?lang=${lang}` : ""}`;

  const availableLangs = ["en", ...(drug.available_langs ?? [])];
  const langAlternates: Record<string, string> = {};
  for (const l of availableLangs) {
    langAlternates[l] = `${SITE_URL}/drugs/${params.id}${l !== "en" ? `?lang=${l}` : ""}`;
  }
  langAlternates["x-default"] = `${SITE_URL}/drugs/${params.id}`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "article",
      url: canonicalUrl,
      ...(drug.image_url ? { images: [{ url: drug.image_url, alt: drug.name }] } : {}),
    },
    alternates: { canonical: canonicalUrl, languages: langAlternates },
    robots: { index: true, follow: true },
  };
}

const SUPPORTED_LANGS = ["en", "ru", "ar", "de", "fr", "es", "tr"];

export default async function DrugDetailPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { lang?: string };
}) {
  const cookieStore = cookies();
  const cookieLang = cookieStore.get("medmind_locale")?.value ?? "en";
  const rawLang = searchParams.lang ?? cookieLang;
  const lang = SUPPORTED_LANGS.includes(rawLang) ? rawLang : "en";
  const [drug, alternatives, allSpecies] = await Promise.all([
    fetchDrug(params.id, lang),
    fetchAlternatives(params.id),
    fetchSpecies(),
  ]);

  if (!drug) notFound();

  const BACK_LABELS: Record<string, string> = {
    en: "← Drug Database", ru: "← База препаратов", ar: "← قاعدة الأدوية",
    de: "← Arzneimittel-DB", fr: "← Base de données", es: "← Base de datos", tr: "← İlaç Veritabanı",
  };

  return (
    <div className="min-h-screen bg-bg">
      <ArticleNav />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        {/* Back link */}
        <Link
          href="/drugs"
          className="inline-flex items-center gap-1 font-syne text-xs text-ink-3 hover:text-ink mb-6 transition-colors"
        >
          {BACK_LABELS[lang] ?? BACK_LABELS.en}
        </Link>

        {/* Drug header — always in initial HTML for SEO */}
        <div className="flex items-start gap-4 mb-4 flex-wrap sm:flex-nowrap">
          {drug.image_url ? (
            <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-xl border border-border bg-white overflow-hidden flex-shrink-0">
              <img
                src={drug.image_url}
                alt={drug.name}
                className="w-full h-full object-contain p-1"
              />
            </div>
          ) : (
            <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-xl border border-border bg-bg-2 flex items-center justify-center flex-shrink-0">
              <span className="text-4xl">💊</span>
            </div>
          )}

          <div className="flex-1 min-w-0">
            <h1 className="font-syne font-black text-xl sm:text-2xl text-ink leading-tight">
              {drug.name}
            </h1>
            {drug.generic_name && drug.generic_name !== drug.name && (
              <p className="font-serif text-ink-3 text-sm mt-0.5">{drug.generic_name}</p>
            )}
            {drug.drug_class && (
              <p className="font-serif text-ink-3 text-xs mt-1">{drug.drug_class}</p>
            )}
            <div className="flex gap-2 flex-wrap mt-2">
              {drug.is_high_yield && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full font-syne font-semibold text-xs bg-amber-light text-amber">
                  ⭐ High Yield
                </span>
              )}
              {drug.is_nti && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full font-syne font-semibold text-xs bg-red-light text-red">
                  ⚠ NTI Drug
                </span>
              )}
              {drug.is_veterinary && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full font-syne font-semibold text-xs bg-green-light text-green">
                  🐾 Veterinary
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Black box warning — server-side for SEO */}
        {drug.black_box_warning && (
          <div className="mb-5 p-4 rounded-lg border border-red/40 bg-red-light flex gap-3">
            <span className="text-red text-lg flex-shrink-0">⬛</span>
            <div>
              <div className="font-syne font-bold text-xs text-red uppercase mb-1">
                Black Box Warning
              </div>
              <p className="font-serif text-sm text-ink leading-relaxed">
                {drug.black_box_warning}
              </p>
            </div>
          </div>
        )}

        {/* JSON-LD schema */}
        <script
          type="application/ld+json"
          suppressHydrationWarning
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Drug",
              name: drug.name,
              ...(drug.generic_name ? { nonproprietaryName: drug.generic_name } : {}),
              ...(drug.drug_class ? { drugClass: drug.drug_class } : {}),
              ...(drug.mechanism ? { mechanismOfAction: drug.mechanism } : {}),
              ...(drug.black_box_warning
                ? { warning: drug.black_box_warning }
                : {}),
              url: `${SITE_URL}/drugs/${drug.id}`,
            }),
          }}
        />

        {/* Interactive tabs — client component */}
        <DrugDetailTabs
          drug={drug}
          alternatives={alternatives}
          allSpecies={allSpecies}
          lang={lang}
        />
      </div>

      <PublicFooter locale={lang} />
    </div>
  );
}
