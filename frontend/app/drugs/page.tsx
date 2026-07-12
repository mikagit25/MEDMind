import type { Metadata } from "next";
import { cookies, headers } from "next/headers";
import { DrugBrowserClient } from "@/components/drugs/DrugBrowserClient";
import { DrugPageTitle } from "@/components/drugs/DrugPageTitle";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export const dynamic = "force-dynamic";

const SUPPORTED_LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

const DRUGS_TITLES: Record<string, string> = {
  en: "Drug Reference Database — MedMind AI",
  ru: "База препаратов — MedMind AI",
  de: "Medikamentendatenbank — MedMind AI",
  fr: "Base de données des médicaments — MedMind AI",
  es: "Base de datos de medicamentos — MedMind AI",
  tr: "İlaç Veritabanı — MedMind AI",
  ar: "قاعدة بيانات الأدوية — MedMind AI",
};

export async function generateMetadata(): Promise<Metadata> {
  const xLocale = headers().get("x-locale");
  const cookieLocale = cookies().get("medmind_locale")?.value;
  const locale = (xLocale ?? cookieLocale ?? "en");
  const validLocale = SUPPORTED_LOCALES.includes(locale) ? locale : "en";
  const canonical = validLocale === "en" ? `${SITE_URL}/drugs` : `${SITE_URL}/${validLocale}/drugs`;
  return {
    title: DRUGS_TITLES[validLocale] ?? DRUGS_TITLES.en,
    description:
      "Browse 300+ drugs with mechanisms, dosing, side effects, interactions and monitoring. Available in 7 languages for medical students, residents, and physicians.",
    keywords:
      "drug database, pharmacology, medication reference, drug interactions, clinical pharmacology, dosing calculator",
    openGraph: {
      title: DRUGS_TITLES[validLocale] ?? DRUGS_TITLES.en,
      description: "Comprehensive pharmacology reference: 300+ drugs in 7 languages.",
      type: "website",
      url: canonical,
    },
    alternates: {
      canonical,
      languages: {
        "x-default": `${SITE_URL}/drugs`,
        ...Object.fromEntries(
          SUPPORTED_LOCALES.map((l) => [l, l === "en" ? `${SITE_URL}/drugs` : `${SITE_URL}/${l}/drugs`])
        ),
      },
    },
    robots: { index: true, follow: true },
  };
}

type Drug = {
  id: string; name: string; generic_name?: string; drug_class?: string;
  mechanism?: string; indications?: string[]; contraindications?: string[];
  adverse_effects?: Record<string, string[]>; dosing?: Record<string, string>;
  is_high_yield?: boolean; is_nti?: boolean; is_veterinary?: boolean; image_url?: string;
};

type BrowseResult = { items: Drug[]; total: number; page: number; pages: number; limit: number };

async function fetchInitialDrugs(lang: string): Promise<BrowseResult> {
  try {
    const res = await fetch(
      `${API_URL}/drugs/browse?page=1&limit=24&lang=${encodeURIComponent(lang)}`,
      { cache: "no-store" }
    );
    if (!res.ok) return { items: [], total: 0, page: 1, pages: 0, limit: 24 };
    return res.json();
  } catch {
    return { items: [], total: 0, page: 1, pages: 0, limit: 24 };
  }
}

async function fetchClasses(): Promise<{ drug_class: string; count: number }[]> {
  try {
    const res = await fetch(`${API_URL}/drugs/classes`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function DrugsPage() {
  const cookieStore = cookies();
  const lang = cookieStore.get("medmind_locale")?.value ?? "en";

  const [initial, classes] = await Promise.all([
    fetchInitialDrugs(lang),
    fetchClasses(),
  ]);

  return (
    <div className="min-h-screen bg-bg">
      <ArticleNav />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Title follows user locale client-side; falls back to server-detected lang */}
        <DrugPageTitle serverLang={lang} total={initial.total} />

        {/* All interactive browsing is in the client component */}
        <DrugBrowserClient initial={initial} classes={classes} initialLang={lang} />
      </div>

      <PublicFooter locale={lang} />
    </div>
  );
}
