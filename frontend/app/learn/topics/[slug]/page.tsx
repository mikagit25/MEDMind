import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { headers } from "next/headers";
import { getLearnT, interpolate } from "@/lib/learn-i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const dynamic = "force-dynamic";

function localePath(path: string, locale: string) {
  return locale !== "en" ? `/${locale}${path}` : path;
}

type GlossaryEntry = { term: string; slug: string; simple_definition: string };
type Section = { title: string; text: string };
type LessonEntry = {
  title: string;
  lesson_code: string;
  lesson_slug: string;
  estimated_minutes: number | null;
  intro: string | null;
  sections: Section[];
  key_points: string[];
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
  const locale = headers().get("x-locale") ?? "en";
  const t = getLearnT(locale);
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
          <Link href={localePath("/learn/topics", locale)} className="hover:text-ink transition-colors">
            {t.breadcrumb_topics}
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
            <span>{data.lessons.length} {t.pets_lesson_plural}</span>
            {data.total_glossary_terms > 0 && (
              <span>{data.total_glossary_terms} {t.nav_glossary.toLowerCase()}</span>
            )}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="bg-amber-light border border-amber/20 rounded-xl px-4 py-3 mb-8">
          <p className="font-serif text-xs text-amber">⚕️ {t.disclaimer}</p>
        </div>

        {/* Lessons */}
        <div className="space-y-6">
          {data.lessons.map((lesson, idx) => (
            <Link
              key={idx}
              href={localePath(`/learn/topics/${data.slug}/${lesson.lesson_slug}`, locale)}
              className="group block border border-border rounded-2xl p-6 bg-surface hover:border-ink hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <span className="font-serif text-xs text-ink-3/60 mb-1 block">
                    {interpolate(t.lesson_of, { n: idx + 1, total: data.lessons.length })}
                    {lesson.estimated_minutes ? ` · ${interpolate(t.min_read, { n: lesson.estimated_minutes })}` : ""}
                  </span>
                  <h2 className="font-syne font-bold text-lg text-ink group-hover:text-accent transition-colors leading-snug">
                    {lesson.title}
                  </h2>
                </div>
                <span className="shrink-0 mt-1 font-serif text-xs text-ink-3/50 bg-bg-2 px-2 py-0.5 rounded">
                  {lesson.sections.length > 0 ? `${lesson.sections.length} sections` : ""}
                </span>
              </div>

              {lesson.intro && (
                <p className="font-serif text-sm text-ink-3 leading-relaxed mb-4 line-clamp-3">
                  {lesson.intro}
                </p>
              )}

              {lesson.key_points.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {lesson.key_points.slice(0, 3).map((kp, ki) => (
                    <span
                      key={ki}
                      className="inline-block px-2.5 py-1 rounded-lg bg-bg-2 border border-border font-serif text-xs text-ink-3 line-clamp-1"
                    >
                      {kp.length > 60 ? kp.slice(0, 60) + "…" : kp}
                    </span>
                  ))}
                </div>
              )}

              {lesson.lay_glossary.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {lesson.lay_glossary.slice(0, 5).map((term) => (
                    <span
                      key={term.slug}
                      className="inline-flex items-center px-2.5 py-1 rounded-lg bg-bg border border-border font-syne font-semibold text-xs text-ink-3"
                    >
                      {term.term}
                    </span>
                  ))}
                </div>
              )}
            </Link>
          ))}
        </div>

        {/* All terms for this topic (if any) */}
        {allTerms.length > 0 && (
          <section className="mt-10 bg-surface border border-border rounded-2xl p-6">
            <h2 className="font-syne font-black text-xl text-ink mb-1">
              {t.key_terms}
            </h2>
            <p className="font-serif text-xs text-ink-3 mb-5">
              {allTerms.length} {t.nav_glossary.toLowerCase()}
            </p>
            <div className="grid sm:grid-cols-2 gap-3">
              {[...new Map(allTerms.map((entry) => [entry.slug, entry])).values()].map((term) => (
                <Link
                  key={term.slug}
                  href={localePath(`/learn/glossary/${term.slug}`, locale)}
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
            {interpolate(t.cta_title, { topic: data.title })}
          </h2>
          <p className="font-serif text-sm text-ink-3 mb-5">
            {t.cta_desc}
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link
              href={localePath("/register", locale)}
              className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
            >
              {t.cta_start}
            </Link>
            <Link
              href={localePath("/learn/topics", locale)}
              className="inline-block px-6 py-3 rounded-xl border border-border text-ink font-syne font-bold text-sm hover:border-ink transition-colors"
            >
              {t.nav_topics}
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
