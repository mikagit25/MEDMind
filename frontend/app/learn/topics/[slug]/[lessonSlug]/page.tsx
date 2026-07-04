import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { headers } from "next/headers";
import { getLearnT, interpolate } from "@/lib/learn-i18n";

function localePath(path: string, locale: string) {
  return locale !== "en" ? `/${locale}${path}` : path;
}

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export const revalidate = 86400;

type Section = { title: string; text: string };
type GlossaryEntry = { term: string; slug: string; simple_definition: string };
type LessonDetail = {
  module_code: string;
  module_slug: string;
  module_title: string;
  specialty: string | null;
  lesson_code: string;
  lesson_slug: string;
  title: string;
  estimated_minutes: number | null;
  intro: string;
  sections: Section[];
  key_points: string[];
  lay_glossary: GlossaryEntry[];
  prev_lesson: { title: string; slug: string } | null;
  next_lesson: { title: string; slug: string } | null;
  total_lessons: number;
  lesson_number: number;
  disclaimer: string;
};

async function fetchLesson(
  slug: string,
  lessonSlug: string
): Promise<LessonDetail | null> {
  try {
    const res = await fetch(
      `${API_URL}/public/topics/${slug}/lessons/${lessonSlug}`,
      { next: { revalidate: 86400 } }
    );
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string; lessonSlug: string };
}): Promise<Metadata> {
  const data = await fetchLesson(params.slug, params.lessonSlug);
  if (!data) return { title: "Lesson Not Found" };

  const desc = data.intro ? data.intro.slice(0, 160) : data.module_title;
  return {
    title: `${data.title} — ${data.module_title}`,
    description: desc,
    alternates: {
      canonical: `${SITE_URL}/learn/topics/${data.module_slug}/${data.lesson_slug}`,
    },
    openGraph: {
      title: `${data.title} — MedMind`,
      description: desc,
      url: `${SITE_URL}/learn/topics/${data.module_slug}/${data.lesson_slug}`,
      type: "article",
    },
  };
}

export default async function LessonPage({
  params,
}: {
  params: { slug: string; lessonSlug: string };
}) {
  const locale = headers().get("x-locale") ?? "en";
  const t = getLearnT(locale);
  const data = await fetchLesson(params.slug, params.lessonSlug);
  if (!data) notFound();

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
            description: data.intro?.slice(0, 200) ?? "",
            url: `${SITE_URL}/learn/topics/${data.module_slug}/${data.lesson_slug}`,
            isPartOf: {
              "@type": "MedicalWebPage",
              name: data.module_title,
              url: `${SITE_URL}/learn/topics/${data.module_slug}`,
            },
            audience: { "@type": "Patient" },
            specialty: data.specialty ?? undefined,
          }),
        }}
      />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 font-serif text-xs text-ink-3 mb-8 flex-wrap">
          <Link href={localePath("/learn/topics", locale)} className="hover:text-ink transition-colors">
            {t.breadcrumb_topics}
          </Link>
          <span>/</span>
          <Link
            href={localePath(`/learn/topics/${data.module_slug}`, locale)}
            className="hover:text-ink transition-colors"
          >
            {data.module_title}
          </Link>
          <span>/</span>
          <span className="text-ink">{data.title}</span>
        </nav>

        {/* Header */}
        <div className="mb-8">
          {data.specialty && (
            <span className="inline-block mb-3 px-2.5 py-1 rounded-md bg-bg-2 font-syne font-semibold text-xs text-ink-3">
              {data.specialty}
            </span>
          )}
          <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink mb-3 leading-tight">
            {data.title}
          </h1>
          <div className="flex items-center gap-4 font-serif text-xs text-ink-3">
            <span>
              {interpolate(t.lesson_of, { n: data.lesson_number, total: data.total_lessons })}
            </span>
            {data.estimated_minutes && (
              <span>{interpolate(t.min_read, { n: data.estimated_minutes })}</span>
            )}
          </div>
        </div>

        {/* Intro */}
        {data.intro && (
          <p className="font-serif text-base text-ink-2 leading-relaxed mb-10 border-l-4 border-accent pl-5">
            {data.intro}
          </p>
        )}

        {/* Sections */}
        {data.sections.length > 0 && (
          <div className="space-y-8 mb-10">
            {data.sections.map((section, idx) => (
              <section key={idx}>
                {section.title && (
                  <h2 className="font-syne font-bold text-xl text-ink mb-3">
                    {section.title}
                  </h2>
                )}
                <p className="font-serif text-sm text-ink-2 leading-relaxed">
                  {section.text}
                </p>
              </section>
            ))}
          </div>
        )}

        {/* Key points */}
        {data.key_points.length > 0 && (
          <div className="bg-surface border border-border rounded-2xl p-6 mb-10">
            <h2 className="font-syne font-black text-lg text-ink mb-4">
              {t.key_takeaways}
            </h2>
            <ul className="space-y-2">
              {data.key_points.map((kp, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="mt-1 shrink-0 w-5 h-5 rounded-full bg-accent/10 flex items-center justify-center">
                    <span className="text-accent font-syne font-bold text-xs">
                      {idx + 1}
                    </span>
                  </span>
                  <span className="font-serif text-sm text-ink-2 leading-relaxed">
                    {kp}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Glossary */}
        {data.lay_glossary.length > 0 && (
          <div className="mb-10">
            <h2 className="font-syne font-black text-lg text-ink mb-4">
              {t.key_terms}
            </h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {data.lay_glossary.map((term) => (
                <Link
                  key={term.slug}
                  href={localePath(`/learn/glossary/${term.slug}`, locale)}
                  className="group block bg-surface border border-border rounded-xl p-3 hover:border-ink transition-all"
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
          </div>
        )}

        {/* Prev / Next navigation */}
        <div className="flex gap-4 mb-10">
          {data.prev_lesson ? (
            <Link
              href={localePath(`/learn/topics/${data.module_slug}/${data.prev_lesson.slug}`, locale)}
              className="flex-1 group block bg-surface border border-border rounded-xl p-4 hover:border-ink transition-all"
            >
              <div className="font-serif text-xs text-ink-3 mb-1">
                {t.prev_lesson}
              </div>
              <div className="font-syne font-bold text-sm text-ink group-hover:text-accent leading-snug">
                {data.prev_lesson.title}
              </div>
            </Link>
          ) : (
            <div className="flex-1" />
          )}
          {data.next_lesson ? (
            <Link
              href={localePath(`/learn/topics/${data.module_slug}/${data.next_lesson.slug}`, locale)}
              className="flex-1 group block bg-surface border border-border rounded-xl p-4 hover:border-ink transition-all text-right"
            >
              <div className="font-serif text-xs text-ink-3 mb-1">
                {t.next_lesson}
              </div>
              <div className="font-syne font-bold text-sm text-ink group-hover:text-accent leading-snug">
                {data.next_lesson.title}
              </div>
            </Link>
          ) : (
            <div className="flex-1" />
          )}
        </div>

        {/* Disclaimer */}
        <div className="bg-amber-light border border-amber/20 rounded-xl px-4 py-3 mb-8">
          <p className="font-serif text-xs text-amber">⚕️ {t.disclaimer}</p>
        </div>

        {/* CTA */}
        <div className="text-center bg-surface border border-border rounded-2xl p-8">
          <h2 className="font-syne font-black text-xl text-ink mb-2">
            {interpolate(t.cta_title, { topic: data.module_title })}
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
              href={localePath(`/learn/topics/${data.module_slug}`, locale)}
              className="inline-block px-6 py-3 rounded-xl border border-border text-ink font-syne font-bold text-sm hover:border-ink transition-colors"
            >
              {interpolate(t.cta_back, { topic: data.module_title })}
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
