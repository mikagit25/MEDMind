import type { Metadata } from "next";
import Link from "next/link";
import { getLearnT } from "@/lib/learn-i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 86400;

export const metadata: Metadata = {
  title: "Pet Health Guides — Dogs & Cats | MedMind",
  description:
    "Plain-language pet health guides for dog and cat owners. Learn about toxic foods, emergency warning signs, vaccinations, parasites, and dental care — written by veterinary experts.",
  alternates: { canonical: `${SITE_URL}/learn/pets` },
  openGraph: {
    title: "Pet Health Guides — MedMind",
    description: "Evidence-based pet health information for dog and cat owners.",
    url: `${SITE_URL}/learn/pets`,
    type: "website",
  },
  keywords: [
    "pet health", "dog health", "cat health", "toxic foods dogs", "toxic foods cats",
    "pet emergency", "pet vaccination", "flea prevention", "pet dental care",
  ],
};

const MODULE_ICONS: Record<string, string> = {
  "PET-001": "☠️",
  "PET-002": "🚨",
  "PET-003": "🛡️",
};

interface PetModule {
  module_code: string;
  slug: string;
  title: string;
  lesson_count: number;
  lessons: { slug: string; title: string; lay_summary_preview: string | null }[];
}

async function fetchPetModules(): Promise<PetModule[]> {
  try {
    const res = await fetch(`${API_URL}/public/pets`, { next: { revalidate: 86400 } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.modules ?? [];
  } catch {
    return [];
  }
}

export default async function PetHealthPage({
  searchParams,
}: {
  searchParams?: { lang?: string };
}) {
  const [modules, t] = await Promise.all([
    fetchPetModules(),
    Promise.resolve(getLearnT(searchParams?.lang)),
  ]);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Pet Health Guides",
    description: "Plain-language pet health guides for dog and cat owners",
    url: `${SITE_URL}/learn/pets`,
    numberOfItems: modules.length,
    itemListElement: modules.map((m, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: m.title,
      url: `${SITE_URL}/learn/pets/${m.slug}`,
    })),
  };

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Header */}
      <div className="mb-8">
        <p className="font-serif text-sm text-ink-3 mb-1">
          <Link href="/learn" className="hover:text-ink transition-colors">Learn</Link>
          {" / "}Pets
        </p>
        <h1 className="font-syne font-black text-3xl text-ink mb-3">
          {t.pets_h1}
        </h1>
        <p className="font-serif text-ink-2 text-base leading-relaxed">
          {t.pets_subtitle}
        </p>
      </div>

      {/* Disclaimer */}
      <div className="bg-amber-light border border-amber/30 rounded-lg p-4 mb-8 flex gap-3">
        <span className="text-lg flex-shrink-0">⚠️</span>
        <p className="font-serif text-sm text-amber-dark">
          {t.pets_disclaimer}
        </p>
      </div>

      {/* Module grid */}
      {modules.length === 0 ? (
        <p className="font-serif text-ink-3 text-center py-12">{t.pets_empty}</p>
      ) : (
        <div className="space-y-6">
          {modules.map((mod) => (
            <Link
              key={mod.module_code}
              href={`/learn/pets/${mod.slug}`}
              className="block card p-6 hover:shadow-md transition-shadow group"
            >
              <div className="flex items-start gap-4">
                <span className="text-3xl flex-shrink-0">{MODULE_ICONS[mod.module_code] ?? "🐾"}</span>
                <div className="flex-1 min-w-0">
                  <h2 className="font-syne font-bold text-lg text-ink group-hover:text-ink-2 transition-colors mb-1">
                    {mod.title}
                  </h2>
                  <p className="font-serif text-sm text-ink-3 mb-3">
                    {mod.lesson_count} {mod.lesson_count === 1 ? t.pets_lesson_singular : t.pets_lesson_plural}
                  </p>
                  <ul className="space-y-1">
                    {mod.lessons.slice(0, 3).map((l) => (
                      <li key={l.slug} className="font-serif text-sm text-ink-2 flex items-center gap-2">
                        <span className="text-ink-3">›</span>
                        {l.title}
                      </li>
                    ))}
                  </ul>
                </div>
                <span className="font-syne text-ink-3 group-hover:text-ink text-lg flex-shrink-0">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Separator */}
      <div className="mt-12 pt-8 border-t border-border" />

      {/* Vet professional CTA — now links to /learn/vet */}
      <div className="card p-6 text-center bg-surface border-2 border-ink/10">
        <div className="text-3xl mb-3">🩺</div>
        <p className="font-syne font-bold text-base text-ink mb-1">{t.pets_pro_h2}</p>
        <p className="font-serif text-sm text-ink-3 mb-4">{t.pets_pro_desc}</p>
        <Link href="/learn/vet" className="btn-primary inline-block">
          {t.pets_pro_btn}
        </Link>
      </div>
    </main>
  );
}
