import type { Metadata } from "next";
import Link from "next/link";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 86400;

export const metadata: Metadata = {
  title: "Medical Topics — Plain Language Health Guides",
  description:
    "Browse 80+ medical topics explained in plain language. Cardiology, neurology, pharmacology, surgery, and more — for patients and curious minds.",
  alternates: { canonical: `${SITE_URL}/learn/topics` },
  openGraph: {
    title: "Medical Topics — MedMind",
    description: "Plain-language health guides for everyone.",
    url: `${SITE_URL}/learn/topics`,
    type: "website",
  },
};

type PublicTopic = {
  module_code: string;
  slug: string;
  title: string;
  description: string | null;
  lay_summary: string | null;
  lesson_count: number;
  specialty: string | null;
};

async function fetchTopics(): Promise<PublicTopic[]> {
  try {
    const res = await fetch(`${API_URL}/public/topics?limit=200`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

const SPECIALTY_ORDER = [
  "Cardiology",
  "Neurology",
  "Internal Medicine",
  "Surgery",
  "Pediatrics",
  "Obstetrics & Gynecology",
  "Pharmacology",
  "Respiratory Medicine",
  "Laboratory Diagnostics",
  "Oncology",
  "Dermatology",
  "Psychiatry",
  "Anesthesiology",
  "Veterinary",
];

export default async function TopicsPage() {
  const topics = await fetchTopics();

  // Group by specialty
  const grouped: Record<string, PublicTopic[]> = {};
  for (const topic of topics) {
    const key = topic.specialty ?? "Other";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(topic);
  }

  // Sort specialties by predefined order, then alphabetically
  const specialties = Object.keys(grouped).sort((a, b) => {
    const ia = SPECIALTY_ORDER.indexOf(a);
    const ib = SPECIALTY_ORDER.indexOf(b);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.localeCompare(b);
  });

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
            name: "Medical Topics",
            description: "Plain-language health guides covering major medical specialties",
            url: `${SITE_URL}/learn/topics`,
            audience: { "@type": "Patient" },
            medicalAudience: [{ "@type": "MedicalAudience", audienceType: "Patient" }],
          }),
        }}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        {/* Hero */}
        <div className="text-center mb-10">
          <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink mb-3">
            Medical Topics
          </h1>
          <p className="font-serif text-ink-3 text-base max-w-xl mx-auto">
            {topics.length > 0
              ? `${topics.length} topics across ${specialties.length} specialties — explained in plain language.`
              : "Plain-language health guides for patients, students, and curious minds."}
          </p>
        </div>

        {topics.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">🔬</div>
            <p className="font-syne font-bold text-ink text-lg mb-2">Topics coming soon</p>
            <p className="font-serif text-ink-3 text-sm mb-6">
              We&apos;re generating plain-language summaries for all our medical content.
            </p>
            <Link
              href="/register"
              className="inline-block px-6 py-2.5 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
            >
              Get notified when it&apos;s ready
            </Link>
          </div>
        ) : (
          <>
            {/* Specialty nav */}
            <div className="flex flex-wrap gap-2 justify-center mb-10">
              {specialties.map((spec) => (
                <a
                  key={spec}
                  href={`#spec-${spec.toLowerCase().replace(/\s+/g, "-")}`}
                  className="px-3 py-1.5 rounded-lg bg-surface border border-border font-syne font-semibold text-xs text-ink-2 hover:bg-ink hover:text-white hover:border-ink transition-colors"
                >
                  {spec}
                  <span className="ml-1.5 text-ink-3 font-normal">
                    {grouped[spec].length}
                  </span>
                </a>
              ))}
            </div>

            {/* Topics by specialty */}
            <div className="space-y-12">
              {specialties.map((spec) => (
                <section
                  key={spec}
                  id={`spec-${spec.toLowerCase().replace(/\s+/g, "-")}`}
                >
                  <h2 className="font-syne font-black text-2xl text-ink mb-5 border-b border-border pb-2">
                    {spec}
                  </h2>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {grouped[spec].map((topic) => (
                      <Link
                        key={topic.slug}
                        href={`/learn/topics/${topic.slug}`}
                        className="group block bg-surface border border-border rounded-xl p-5 hover:border-ink hover:shadow-sm transition-all"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="font-syne font-bold text-sm text-ink group-hover:text-accent leading-snug">
                            {topic.title}
                          </div>
                          <span className="ml-2 shrink-0 font-serif text-xs text-ink-3/60 bg-bg-2 px-2 py-0.5 rounded">
                            {topic.lesson_count}
                          </span>
                        </div>
                        {topic.lay_summary && (
                          <p className="font-serif text-xs text-ink-3 line-clamp-3 leading-relaxed">
                            {topic.lay_summary}
                          </p>
                        )}
                        <div className="mt-3 font-serif text-xs text-ink-3/50">
                          {topic.module_code}
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
                Ready to go deeper?
              </h2>
              <p className="font-serif text-sm text-ink-3 mb-5">
                Full lessons, AI tutor, flashcards, and clinical cases — for students, physicians, and curious minds.
              </p>
              <Link
                href="/register"
                className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
              >
                Start Learning Free →
              </Link>
            </div>
          </>
        )}
      </div>
    </>
  );
}
