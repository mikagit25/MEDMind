import type { Metadata } from "next";
import Link from "next/link";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export const revalidate = 86400;

export const metadata: Metadata = {
  title: "Drug Guide — Plain Language Medication Information",
  description:
    "Plain-language guides for common medications — what they do, how they work, and important safety information. No dosing advice; always consult a healthcare provider.",
  alternates: { canonical: `${SITE_URL}/learn/drugs` },
  openGraph: {
    title: "Drug Guide — MedMind Learn",
    description: "Understand common medications in plain language.",
    url: `${SITE_URL}/learn/drugs`,
    type: "website",
  },
};

type Drug = {
  id: string;
  slug: string;
  name: string;
  generic_name: string | null;
  drug_class: string | null;
  mechanism: string | null;
  indications: string[] | null;
  is_high_yield: boolean;
  is_nti: boolean;
  black_box_warning: string | null;
};

async function fetchDrugs(search?: string): Promise<Drug[]> {
  try {
    const params = new URLSearchParams({ limit: "200" });
    if (search) params.set("search", search);
    const res = await fetch(`${API_URL}/public/drugs?${params}`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export default async function DrugsIndexPage({
  searchParams,
}: {
  searchParams: { search?: string; class?: string };
}) {
  const drugs = await fetchDrugs(searchParams.search);

  // Group by drug class
  const grouped: Record<string, Drug[]> = {};
  for (const drug of drugs) {
    const key = drug.drug_class ?? "Other";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(drug);
  }
  const classes = Object.keys(grouped).sort();

  return (
    <>
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "MedicalWebPage",
            name: "Drug Guide",
            description: "Plain-language medication guides for patients",
            url: `${SITE_URL}/learn/drugs`,
            audience: { "@type": "Patient" },
          }),
        }}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        {/* Hero */}
        <div className="text-center mb-10">
          <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink mb-3">
            Drug Guide
          </h1>
          <p className="font-serif text-ink-3 text-base max-w-xl mx-auto mb-1">
            {drugs.length > 0
              ? `${drugs.length} medications explained in plain language.`
              : "Plain-language medication guides for patients and curious minds."}
          </p>
          <p className="font-serif text-xs text-amber mt-2">
            ⚕️ This is educational information only — no dosing advice. Always consult your doctor or pharmacist.
          </p>
        </div>

        {/* Search */}
        <form method="GET" className="mb-8 flex gap-2 max-w-lg mx-auto">
          <input
            type="text"
            name="search"
            defaultValue={searchParams.search ?? ""}
            placeholder="Search medications…"
            className="flex-1 px-4 py-2.5 rounded-xl border border-border bg-surface font-serif text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:border-ink"
          />
          <button
            type="submit"
            className="px-5 py-2.5 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
          >
            Search
          </button>
        </form>

        {drugs.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">💊</div>
            <p className="font-syne font-bold text-ink text-lg mb-2">
              {searchParams.search ? "No results found" : "Drug guides coming soon"}
            </p>
            <p className="font-serif text-ink-3 text-sm mb-6">
              {searchParams.search
                ? `No medications matched "${searchParams.search}". Try a different term.`
                : "We're building plain-language guides for all major medications."}
            </p>
            {searchParams.search && (
              <Link
                href="/learn/drugs"
                className="inline-block px-5 py-2 rounded-xl border border-border font-syne font-semibold text-sm text-ink hover:border-ink transition-colors"
              >
                Clear search
              </Link>
            )}
          </div>
        ) : (
          <>
            {/* Class nav */}
            {classes.length > 2 && (
              <div className="flex flex-wrap gap-2 justify-center mb-8">
                {classes.map((cls) => (
                  <a
                    key={cls}
                    href={`#cls-${cls.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                    className="px-3 py-1 rounded-lg bg-surface border border-border font-syne font-semibold text-xs text-ink-2 hover:bg-ink hover:text-white hover:border-ink transition-colors"
                  >
                    {cls}
                    <span className="ml-1.5 text-ink-3 font-normal">{grouped[cls].length}</span>
                  </a>
                ))}
              </div>
            )}

            <div className="space-y-10">
              {classes.map((cls) => (
                <section
                  key={cls}
                  id={`cls-${cls.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                >
                  <h2 className="font-syne font-black text-xl text-ink mb-4 border-b border-border pb-2">
                    {cls}
                  </h2>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {grouped[cls].map((drug) => (
                      <Link
                        key={drug.id}
                        href={`/learn/drugs/${drug.slug}`}
                        className="group block bg-surface border border-border rounded-xl p-4 hover:border-ink hover:shadow-sm transition-all"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="font-syne font-bold text-sm text-ink group-hover:text-accent leading-snug">
                              {drug.name}
                            </div>
                            {drug.generic_name && drug.generic_name !== drug.name && (
                              <div className="font-serif text-xs text-ink-3 mt-0.5">
                                {drug.generic_name}
                              </div>
                            )}
                          </div>
                          <div className="flex gap-1 ml-2 shrink-0">
                            {drug.is_high_yield && (
                              <span className="text-xs bg-amber/10 text-amber border border-amber/20 px-1.5 py-0.5 rounded font-syne font-semibold">
                                HY
                              </span>
                            )}
                            {drug.black_box_warning && (
                              <span className="text-xs bg-red-50 text-red-600 border border-red-200 px-1.5 py-0.5 rounded font-syne font-semibold">
                                ⚠
                              </span>
                            )}
                          </div>
                        </div>
                        {drug.indications && drug.indications.length > 0 && (
                          <p className="font-serif text-xs text-ink-3 line-clamp-2 leading-relaxed">
                            {drug.indications.slice(0, 2).join(", ")}
                          </p>
                        )}
                      </Link>
                    ))}
                  </div>
                </section>
              ))}
            </div>

            {/* CTA */}
            <div className="mt-14 text-center bg-surface border border-border rounded-2xl p-8">
              <h2 className="font-syne font-black text-xl text-ink mb-2">
                Need full clinical details?
              </h2>
              <p className="font-serif text-sm text-ink-3 mb-5">
                Dosing, interactions, adverse effects, and clinical pearls — available for healthcare professionals.
              </p>
              <Link
                href="/register"
                className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
              >
                Create Free Account →
              </Link>
            </div>
          </>
        )}
      </div>
    </>
  );
}
