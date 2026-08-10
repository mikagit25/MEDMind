import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getLearnT } from "@/lib/learn-i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const dynamic = "force-dynamic";

interface Lesson {
  slug: string;
  title: string;
  lay_summary: string | null;
  lay_glossary: { term: string; simple_definition: string }[];
  key_points: string[];
}

interface PetModule {
  module_code: string;
  slug: string;
  title: string;
  lessons: Lesson[];
  glossary: { term: string; simple_definition: string }[];
  disclaimer: string;
}

async function fetchModule(slug: string): Promise<PetModule | null> {
  try {
    const res = await fetch(`${API_URL}/public/pets/${slug}`, { next: { revalidate: 86400 } });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function fetchAllModules(): Promise<{ slug: string; title: string }[]> {
  try {
    const res = await fetch(`${API_URL}/public/pets`, { next: { revalidate: 86400 } });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.modules ?? []).map((m: { slug: string; title: string }) => ({ slug: m.slug, title: m.title }));
  } catch {
    return [];
  }
}

export async function generateStaticParams() {
  const modules = await fetchAllModules();
  return modules.map((m) => ({ slug: m.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const mod = await fetchModule(params.slug);
  if (!mod) return { title: "Pet Health Guide | MedMind" };

  const firstSummary = mod.lessons[0]?.lay_summary?.slice(0, 160) ?? "";
  return {
    title: `${mod.title} | Pet Health Guide — MedMind`,
    description: firstSummary || `Plain-language guide: ${mod.title}`,
    alternates: { canonical: `${SITE_URL}/learn/pets/${params.slug}` },
    openGraph: {
      title: mod.title,
      description: firstSummary,
      url: `${SITE_URL}/learn/pets/${params.slug}`,
      type: "article",
    },
  };
}

export default async function PetModulePage({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams?: { lang?: string };
}) {
  const [mod, t] = await Promise.all([
    fetchModule(params.slug),
    Promise.resolve(getLearnT(searchParams?.lang)),
  ]);
  if (!mod) notFound();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "MedicalWebPage",
    name: mod.title,
    description: mod.lessons[0]?.lay_summary?.slice(0, 200) ?? "",
    url: `${SITE_URL}/learn/pets/${params.slug}`,
    audience: { "@type": "Audience", audienceType: "Pet owners" },
    publisher: { "@type": "Organization", name: "MedMind AI", url: SITE_URL },
    medicalAudience: { "@type": "MedicalAudience", audienceType: "Patient" },
  };

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Breadcrumb */}
      <p className="font-serif text-sm text-ink-3 mb-6">
        <Link href="/learn" className="hover:text-ink">Learn</Link>
        {" / "}
        <Link href="/learn/pets" className="hover:text-ink">{t.pets_h1}</Link>
        {" / "}
        <span>{mod.title}</span>
      </p>

      <h1 className="font-syne font-black text-3xl text-ink mb-3">{mod.title}</h1>

      {/* Disclaimer banner */}
      <div className="bg-amber-light border border-amber/30 rounded-lg p-4 mb-8 flex gap-3">
        <span className="text-lg flex-shrink-0">⚠️</span>
        <p className="font-serif text-sm text-amber-dark">{mod.disclaimer}</p>
      </div>

      {/* Lessons */}
      <div className="space-y-10">
        {mod.lessons.map((lesson, i) => (
          <section key={lesson.slug} id={lesson.slug}>
            <h2 className="font-syne font-bold text-xl text-ink mb-4">
              <span className="text-ink-3 font-normal mr-2">{i + 1}.</span>
              {lesson.title}
            </h2>

            {lesson.lay_summary && (
              <div className="font-serif text-base text-ink-2 leading-relaxed space-y-3 mb-5">
                {lesson.lay_summary.split("\n\n").map((para, j) => (
                  <p key={j} dangerouslySetInnerHTML={{ __html: para.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") }} />
                ))}
              </div>
            )}

            {lesson.key_points?.length > 0 && (
              <div className="bg-bg-2 rounded-lg p-4 mb-4">
                <p className="font-syne font-semibold text-sm text-ink mb-2">{t.pets_key_points}</p>
                <ul className="space-y-1.5">
                  {lesson.key_points.map((pt, j) => (
                    <li key={j} className="font-serif text-sm text-ink-2 flex items-start gap-2">
                      <span className="text-ink-3 flex-shrink-0 mt-0.5">✓</span>
                      {pt}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {lesson.lay_glossary?.length > 0 && (
              <details className="border border-border rounded-lg">
                <summary className="cursor-pointer px-4 py-3 font-syne font-semibold text-sm text-ink select-none">
                  {t.pets_glossary_section} ({lesson.lay_glossary.length})
                </summary>
                <div className="px-4 pb-4 pt-2 space-y-2">
                  {lesson.lay_glossary.map((g) => (
                    <div key={g.term}>
                      <span className="font-syne font-bold text-sm text-ink">{g.term}: </span>
                      <span className="font-serif text-sm text-ink-2">{g.simple_definition}</span>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </section>
        ))}
      </div>

      {/* Full glossary */}
      {mod.glossary?.length > 0 && (
        <section className="mt-12 pt-8 border-t border-border">
          <h2 className="font-syne font-bold text-lg text-ink mb-4">{t.pets_glossary_full}</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {mod.glossary.map((g) => (
              <div key={g.term} className="card p-3">
                <p className="font-syne font-bold text-sm text-ink">{g.term}</p>
                <p className="font-serif text-xs text-ink-3 mt-0.5">{g.simple_definition}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Back nav */}
      <div className="mt-10">
        <Link
          href="/learn/pets"
          className="font-serif text-sm text-ink-3 hover:text-ink transition-colors"
        >
          {t.pets_back}
        </Link>
      </div>

      {/* Vet professional CTA — links to /learn/vet */}
      <div className="mt-8 card p-6 text-center">
        <p className="font-syne font-bold text-base text-ink mb-1">{t.pets_vet_h2}</p>
        <p className="font-serif text-sm text-ink-3 mb-4">{t.pets_vet_desc}</p>
        <Link href="/learn/vet" className="btn-primary inline-block">
          {t.pets_vet_btn}
        </Link>
      </div>

      {/* Footer disclaimer */}
      <div className="mt-8 p-4 bg-bg-2 rounded-lg">
        <p className="font-serif text-xs text-ink-3 text-center">
          ℹ️ {t.pets_footer_note}
        </p>
      </div>
    </main>
  );
}
