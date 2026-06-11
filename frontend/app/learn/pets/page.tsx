import type { Metadata } from "next";
import Link from "next/link";

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

export default async function PetHealthPage() {
  const modules = await fetchPetModules();

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
          Pet Health Guides
        </h1>
        <p className="font-serif text-ink-2 text-base leading-relaxed">
          Evidence-based health information for dog and cat owners — written in plain language by veterinary professionals.
          No jargon, no dosing advice, just what you actually need to know.
        </p>
      </div>

      {/* Disclaimer */}
      <div className="bg-amber-light border border-amber/30 rounded-lg p-4 mb-8 flex gap-3">
        <span className="text-lg flex-shrink-0">⚠️</span>
        <p className="font-serif text-sm text-amber-dark">
          This content is for educational purposes only and does not constitute veterinary advice.
          If your pet is unwell, <strong>contact a veterinarian immediately</strong>.
        </p>
      </div>

      {/* Module grid */}
      {modules.length === 0 ? (
        <p className="font-serif text-ink-3 text-center py-12">Content coming soon.</p>
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
                    {mod.lesson_count} lesson{mod.lesson_count !== 1 ? "s" : ""}
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

      {/* CTA */}
      <div className="mt-12 card p-6 text-center">
        <p className="font-syne font-bold text-base text-ink mb-1">Veterinary students & professionals</p>
        <p className="font-serif text-sm text-ink-3 mb-4">
          Access full clinical modules, drug dosing, MCQs, and spaced repetition flashcards.
        </p>
        <Link href="/register" className="btn-primary inline-block">
          Explore Pro Content
        </Link>
      </div>
    </main>
  );
}
