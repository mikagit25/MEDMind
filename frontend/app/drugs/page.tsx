import type { Metadata } from "next";
import { cookies } from "next/headers";
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

export const metadata: Metadata = {
  title: "Drug Reference Database — MedMind AI",
  description:
    "Browse 833+ drugs with mechanisms, dosing, side effects, interactions and monitoring. Available in 7 languages for medical students, residents, and physicians.",
  keywords:
    "drug database, pharmacology, medication reference, drug interactions, clinical pharmacology, dosing calculator",
  openGraph: {
    title: "Drug Reference Database — MedMind AI",
    description: "Comprehensive pharmacology reference: 833+ drugs in 7 languages.",
    type: "website",
    url: `${SITE_URL}/drugs`,
  },
  alternates: {
    canonical: `${SITE_URL}/drugs`,
    languages: {
      ru: `${SITE_URL}/drugs?lang=ru`,
      ar: `${SITE_URL}/drugs?lang=ar`,
      de: `${SITE_URL}/drugs?lang=de`,
      fr: `${SITE_URL}/drugs?lang=fr`,
      es: `${SITE_URL}/drugs?lang=es`,
      tr: `${SITE_URL}/drugs?lang=tr`,
    },
  },
  robots: { index: true, follow: true },
};

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
