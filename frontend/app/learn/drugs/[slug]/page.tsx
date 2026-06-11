import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 86400;

type PublicDrug = {
  id: string;
  slug: string;
  name: string;
  generic_name: string | null;
  drug_class: string | null;
  mechanism: string | null;
  indications: string[];
  contraindications: string[];
  black_box_warning: string | null;
  is_high_yield: boolean;
  is_nti: boolean;
  image_url: string | null;
  disclaimer: string;
};

async function fetchDrug(slug: string): Promise<PublicDrug | null> {
  try {
    const res = await fetch(`${API_URL}/public/drugs/${slug}`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const drug = await fetchDrug(params.slug);
  if (!drug) return { title: "Drug Not Found" };

  const desc = drug.mechanism
    ? `${drug.name} — ${drug.mechanism.slice(0, 140)}`
    : `${drug.name}: indications, mechanism, and contraindications explained in plain language.`;

  return {
    title: `${drug.name} — Drug Information`,
    description: desc,
    alternates: { canonical: `${SITE_URL}/learn/drugs/${drug.slug}` },
    openGraph: {
      title: `${drug.name} — MedMind Drug Reference`,
      description: desc,
      url: `${SITE_URL}/learn/drugs/${drug.slug}`,
      type: "website",
      images: drug.image_url ? [{ url: drug.image_url }] : undefined,
    },
  };
}

export default async function PublicDrugPage({
  params,
}: {
  params: { slug: string };
}) {
  const drug = await fetchDrug(params.slug);
  if (!drug) notFound();

  return (
    <>
      {/* JSON-LD Drug */}
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Drug",
            name: drug.name,
            nonproprietaryName: drug.generic_name ?? undefined,
            description: drug.mechanism ?? undefined,
            url: `${SITE_URL}/learn/drugs/${drug.slug}`,
            image: drug.image_url ?? undefined,
            drugClass: drug.drug_class ?? undefined,
          }),
        }}
      />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 font-serif text-xs text-ink-3 mb-8">
          <Link href="/drugs" className="hover:text-ink transition-colors">
            Drug Database
          </Link>
          <span>/</span>
          <span className="text-ink">{drug.name}</span>
        </nav>

        {/* Drug header */}
        <div className="flex items-start gap-6 mb-8">
          {drug.image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={drug.image_url}
              alt={drug.name}
              className="w-20 h-20 rounded-xl object-contain bg-surface border border-border shrink-0"
            />
          )}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap gap-2 mb-2">
              {drug.is_high_yield && (
                <span className="px-2 py-0.5 rounded-md bg-amber-light border border-amber/20 font-syne font-bold text-xs text-amber">
                  High Yield
                </span>
              )}
              {drug.is_nti && (
                <span className="px-2 py-0.5 rounded-md bg-red-50 border border-red-200 font-syne font-bold text-xs text-red-600">
                  Narrow Therapeutic Index
                </span>
              )}
            </div>
            <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink mb-1">
              {drug.name}
            </h1>
            {drug.generic_name && drug.generic_name !== drug.name && (
              <p className="font-serif text-sm text-ink-3">
                Generic: {drug.generic_name}
              </p>
            )}
            {drug.drug_class && (
              <p className="font-serif text-sm text-ink-3 mt-0.5">
                Class: {drug.drug_class}
              </p>
            )}
          </div>
        </div>

        {/* Black box warning */}
        {drug.black_box_warning && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
            <p className="font-syne font-bold text-xs text-red-700 uppercase tracking-widest mb-1">
              ⚠ Black Box Warning
            </p>
            <p className="font-serif text-sm text-red-700">{drug.black_box_warning}</p>
          </div>
        )}

        {/* Mechanism */}
        {drug.mechanism && (
          <section className="bg-surface border border-border rounded-2xl p-6 mb-5">
            <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">
              How It Works
            </h2>
            <p className="font-serif text-sm text-ink-2 leading-relaxed">{drug.mechanism}</p>
          </section>
        )}

        {/* Indications */}
        {drug.indications.length > 0 && (
          <section className="bg-surface border border-border rounded-2xl p-6 mb-5">
            <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">
              Used For (Indications)
            </h2>
            <ul className="space-y-2">
              {drug.indications.map((ind, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent shrink-0">•</span>
                  <span className="font-serif text-sm text-ink-2">{ind}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Contraindications */}
        {drug.contraindications.length > 0 && (
          <section className="bg-surface border border-border rounded-2xl p-6 mb-5">
            <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">
              Do Not Use If (Contraindications)
            </h2>
            <ul className="space-y-2">
              {drug.contraindications.map((ci, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-0.5 text-red-500 shrink-0">✕</span>
                  <span className="font-serif text-sm text-ink-2">{ci}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Dosing excluded notice */}
        <div className="bg-surface border border-border rounded-xl px-4 py-3 mb-6 flex items-start gap-3">
          <span className="text-lg shrink-0">ℹ️</span>
          <p className="font-serif text-xs text-ink-3 leading-relaxed">
            <strong className="font-syne font-bold text-ink">Dosing information is not shown here.</strong>{" "}
            Prescribing decisions, dosing, and treatment planning must be made by a licensed healthcare provider.
            MedMind students can access full dosing in the{" "}
            <Link href="/register" className="text-accent hover:underline">
              Drug Database
            </Link>.
          </p>
        </div>

        {/* Disclaimer */}
        <div className="bg-amber-light border border-amber/20 rounded-xl px-4 py-3 mb-8">
          <p className="font-serif text-xs text-amber">⚕️ {drug.disclaimer}</p>
        </div>

        {/* CTA */}
        <div className="text-center bg-surface border border-border rounded-2xl p-8">
          <h2 className="font-syne font-black text-xl text-ink mb-2">
            Full Drug Reference on MedMind
          </h2>
          <p className="font-serif text-sm text-ink-3 mb-5">
            Access dosing, adverse effects, drug interactions, and clinical pearls — for students and clinicians.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link
              href="/register"
              className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
            >
              Access Full Database Free →
            </Link>
            <Link
              href="/drugs"
              className="inline-block px-6 py-3 rounded-xl border border-border text-ink font-syne font-bold text-sm hover:border-ink transition-colors"
            >
              Drug Database
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
