import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 86400;

type GlossaryEntry = { term: string; slug: string; simple_definition: string };
type LessonEntry = {
  title: string;
  lay_summary: string | null;
  lay_glossary: GlossaryEntry[];
  order: number;
};

type TopicDetail = {
  module_code: string;
  slug: string;
  title: string;
  description: string | null;
  specialty: string | null;
  lessons: LessonEntry[];
  total_glossary_terms: number;
  disclaimer: string;
};

async function fetchTopic(slug: string): Promise<TopicDetail | null> {
  try {
    const res = await fetch(`${API_URL}/public/topics/${slug}`, {
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
  const data = await fetchTopic(params.slug);
  if (!data) return { title: "Topic Not Found" };
  const desc = data.description ?? data.lessons[0]?.lay_summary?.slice(0, 160) ?? "";
  return {
    title: `${data.title} — Plain Language Guide`,
    description: desc,
    alternates: { canonical: `${SITE_URL}/learn/topics/${data.slug}` },
    openGraph: {
      title: `${data.title} — MedMind`,
      description: desc,
      url: `${SITE_URL}/learn/topics/${data.slug}`,
      type: "article",
    },
  };
}

export default async function TopicDetailPage({
  params,
}: {
  params: { slug: string };
}) {
  const data = await fetchTopic(params.slug);
  if (!data) notFound();

  // Collect all glossary terms for inline linking reference
  const allTerms: GlossaryEntry[] = data.lessons.flatMap((l) => l.lay_glossary);
  const termMap = new Map(allTerms.map((t) => [t.term.toLowerCase(), t]));

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
            name: data.title,
            description: data.description ?? "",
            url: `${SITE_URL}/learn/topics/${data.slug}`,
            audience: { "@type": "Patient" },
            medicalAudience: [{ "@type": "MedicalAudience", audienceType: "Patient" }],
            specialty: data.specialty ?? undefined,
          }),
        }}
      />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 font-serif text-xs text-ink-3 mb-8">
          <Link href="/learn/topics" className="hover:text-ink transition-colors">
            Topics
          </Link>
          <span>/</span>
          {data.specialty && (
            <>
              <span className="hover:text-ink">{data.specialty}</span>
              <span>/</span>
            </>
          )}
          <span className="text-ink">{data.title}</span>
        </nav>

        {/* Hero */}
        <div className="mb-8">
          {data.specialty && (
            <span className="inline-block mb-3 px-2.5 py-1 rounded-md bg-bg-2 font-syne font-semibold text-xs text-ink-3">
              {data.specialty}
            </span>
          )}
          <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink mb-3">
            {data.title}
          </h1>
          {data.description && (
            <p className="font-serif text-base text-ink-2 leading-relaxed">
              {data.description}
            </p>
          )}
          <div className="flex items-center gap-4 mt-4 font-serif text-xs text-ink-3">
            <span>{data.lessons.length} lessons</span>
            {data.total_glossary_terms > 0 && (
              <span>{data.total_glossary_terms} terms defined</span>
            )}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="bg-amber-light border border-amber/20 rounded-xl px-4 py-3 mb-8">
          <p className="font-serif text-xs text-amber">⚕️ {data.disclaimer}</p>
        </div>

        {/* Lessons */}
        <div className="space-y-8">
          {data.lessons.map((lesson, idx) => (
            <section key={idx} className="border-b border-border pb-8 last:border-0">
              <h2 className="font-syne font-bold text-lg text-ink mb-3">
                {lesson.title}
              </h2>

              {lesson.lay_summary && (
                <p className="font-serif text-sm text-ink-2 leading-relaxed mb-4">
                  {lesson.lay_summary}
                </p>
              )}

              {lesson.lay_glossary.length > 0 && (
                <div>
                  <p className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">
                    Key Terms
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {lesson.lay_glossary.map((term) => (
                      <Link
                        key={term.slug}
                        href={`/learn/glossary/${term.slug}`}
                        className="group inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface border border-border hover:border-ink hover:bg-ink hover:text-white transition-all"
                        title={term.simple_definition}
                      >
                        <span className="font-syne font-semibold text-xs text-ink group-hover:text-white">
                          {term.term}
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </section>
          ))}
        </div>

        {/* All terms for this topic (if any) */}
        {allTerms.length > 0 && (
          <section className="mt-10 bg-surface border border-border rounded-2xl p-6">
            <h2 className="font-syne font-black text-xl text-ink mb-1">
              Glossary for This Topic
            </h2>
            <p className="font-serif text-xs text-ink-3 mb-5">
              {allTerms.length} plain-language definitions
            </p>
            <div className="grid sm:grid-cols-2 gap-3">
              {[...new Map(allTerms.map((t) => [t.slug, t])).values()].map((term) => (
                <Link
                  key={term.slug}
                  href={`/learn/glossary/${term.slug}`}
                  className="group block bg-bg border border-border rounded-xl p-3 hover:border-ink transition-all"
                >
                  <div className="font-syne font-bold text-xs text-ink group-hover:text-accent mb-1">
                    {term.term}
                  </div>
                  <p className="font-serif text-xs text-ink-3 line-clamp-2">
                    {term.simple_definition}
                  </p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* CTA */}
        <div className="mt-12 text-center bg-surface border border-border rounded-2xl p-8">
          <h2 className="font-syne font-black text-xl text-ink mb-2">
            Want the full {data.title} course?
          </h2>
          <p className="font-serif text-sm text-ink-3 mb-5">
            Get interactive lessons, AI tutor, flashcards, and clinical cases on MedMind.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link
              href="/register"
              className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
            >
              Start Learning Free →
            </Link>
            <Link
              href="/learn/topics"
              className="inline-block px-6 py-3 rounded-xl border border-border text-ink font-syne font-bold text-sm hover:border-ink transition-colors"
            >
              Browse All Topics
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
