import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 86400;

type TermDetail = {
  term: string;
  simple_definition: string;
  slug: string;
  lesson_title: string;
  lesson_id: string;
  module_code: string;
  module_title: string;
  module_slug: string;
  lay_summary_excerpt: string | null;
  related_terms: { term: string; slug: string; lesson_title: string; module_code: string }[];
  disclaimer: string;
};

async function fetchTerm(slug: string): Promise<TermDetail | null> {
  try {
    const res = await fetch(`${API_URL}/public/glossary/${slug}`, {
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
  params: { term: string };
}): Promise<Metadata> {
  const data = await fetchTerm(params.term);
  if (!data) return { title: "Term Not Found" };
  return {
    title: `${data.term} — Medical Definition`,
    description: data.simple_definition,
    alternates: { canonical: `${SITE_URL}/learn/glossary/${data.slug}` },
    openGraph: {
      title: `${data.term} — MedMind Glossary`,
      description: data.simple_definition,
      url: `${SITE_URL}/learn/glossary/${data.slug}`,
      type: "website",
    },
  };
}

export default async function GlossaryTermPage({
  params,
}: {
  params: { term: string };
}) {
  const data = await fetchTerm(params.term);
  if (!data) notFound();

  return (
    <>
      {/* JSON-LD DefinedTerm */}
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "DefinedTerm",
            name: data.term,
            description: data.simple_definition,
            url: `${SITE_URL}/learn/glossary/${data.slug}`,
            inDefinedTermSet: {
              "@type": "DefinedTermSet",
              name: "MedMind Medical Glossary",
              url: `${SITE_URL}/learn/glossary`,
            },
          }),
        }}
      />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 font-serif text-xs text-ink-3 mb-8">
          <Link href="/learn/glossary" className="hover:text-ink transition-colors">
            Glossary
          </Link>
          <span>/</span>
          <span className="text-ink">{data.term}</span>
        </nav>

        {/* Term card */}
        <div className="bg-surface border border-border rounded-2xl p-8 mb-8">
          <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink mb-4">
            {data.term}
          </h1>
          <p className="font-serif text-base text-ink-2 leading-relaxed mb-6">
            {data.simple_definition}
          </p>

          {/* Disclaimer */}
          <div className="bg-amber-light border border-amber/20 rounded-xl px-4 py-3">
            <p className="font-serif text-xs text-amber">
              ⚕️ {data.disclaimer}
            </p>
          </div>
        </div>

        {/* From module */}
        {data.lay_summary_excerpt && (
          <div className="bg-surface border border-border rounded-2xl p-6 mb-8">
            <p className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">
              From the lesson: {data.lesson_title}
            </p>
            <p className="font-serif text-sm text-ink-2 leading-relaxed">
              {data.lay_summary_excerpt}
              {data.lay_summary_excerpt.length >= 300 && "…"}
            </p>
            <Link
              href={`/learn/topics/${data.module_slug}`}
              className="inline-block mt-4 font-syne font-bold text-sm text-accent hover:underline"
            >
              Read full topic: {data.module_title} →
            </Link>
          </div>
        )}

        {/* Related terms */}
        {data.related_terms.length > 0 && (
          <section className="mb-10">
            <h2 className="font-syne font-black text-xl text-ink mb-4">
              Related Terms
            </h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {data.related_terms.map((rt) => (
                <Link
                  key={rt.slug}
                  href={`/learn/glossary/${rt.slug}`}
                  className="group block bg-surface border border-border rounded-xl p-4 hover:border-ink hover:shadow-sm transition-all"
                >
                  <div className="font-syne font-bold text-sm text-ink group-hover:text-accent">
                    {rt.term}
                  </div>
                  <div className="mt-1 font-serif text-xs text-ink-3/60">
                    {rt.module_code}
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* CTA */}
        <div className="text-center bg-surface border border-border rounded-2xl p-8">
          <h2 className="font-syne font-black text-xl text-ink mb-2">
            Learn More With MedMind
          </h2>
          <p className="font-serif text-sm text-ink-3 mb-5">
            Interactive lessons, AI tutor, flashcards, and 800+ clinical topics.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link
              href="/register"
              className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
            >
              Start Learning Free →
            </Link>
            <Link
              href="/learn/glossary"
              className="inline-block px-6 py-3 rounded-xl border border-border text-ink font-syne font-bold text-sm hover:border-ink transition-colors"
            >
              Back to Glossary
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
