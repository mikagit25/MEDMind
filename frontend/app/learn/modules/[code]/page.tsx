import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

// Layout uses headers() → all /learn/* pages must be dynamic
export const dynamic = "force-dynamic";

// ── Types ────────────────────────────────────────────────────────────────────

type LessonContent = {
  intro?: string;
  sections?: { heading: string; text: string }[];
  clinical_pearl?: string;
  key_points?: string[];
};

type PublicLesson = {
  id: string;
  title: string;
  lesson_order: number;
  estimated_minutes: number;
  content?: LessonContent;
};

type PublicModule = {
  id: string;
  code: string;
  title: string;
  description: string | null;
  level_label: string | null;
  duration_hours: number | null;
  lesson_count: number;
  mcq_count: number;
  flashcard_count: number;
  exam_slugs: string[];
  jurisdiction: string | null;
  lessons: PublicLesson[];
};

// ── Exam slug labels ─────────────────────────────────────────────────────────

const EXAM_LABELS: Record<string, string> = {
  snle:    "SNLE — Saudi Arabia",
  dha:     "DHA — Dubai",
  haad:    "DOH/HAAD — Abu Dhabi",
  qchp:    "QCHP — Qatar",
  omsb:    "OMSB — Oman",
  nhra:    "NHRA — Bahrain",
  mohuae:  "MOH — UAE",
  moh_kw:  "MOH-KW — Kuwait",
};

const EXAM_SHORT: Record<string, string> = {
  snle:    "SNLE",
  dha:     "DHA",
  haad:    "DOH/HAAD",
  qchp:    "QCHP",
  omsb:    "OMSB",
  nhra:    "NHRA",
  mohuae:  "MOH UAE",
  moh_kw:  "MOH-KW",
};

// ── Data fetcher ─────────────────────────────────────────────────────────────

async function fetchModule(code: string): Promise<PublicModule | null> {
  try {
    const res = await fetch(`${API_URL}/modules/${encodeURIComponent(code.toUpperCase())}/public`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function fetchGulfModuleCodes(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/exam/gulf-modules-sitemap`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data: { code: string }[] = await res.json();
    return data.map((d) => d.code);
  } catch {
    return [];
  }
}

// ── Static params ────────────────────────────────────────────────────────────

export async function generateStaticParams() {
  const codes = await fetchGulfModuleCodes();
  return codes.map((code) => ({ code }));
}

// ── Metadata ─────────────────────────────────────────────────────────────────

export async function generateMetadata({
  params,
}: {
  params: { code: string };
}): Promise<Metadata> {
  const mod = await fetchModule(params.code);
  if (!mod) return { title: "Module Not Found" };

  const examNames = mod.exam_slugs.map((s) => EXAM_SHORT[s] ?? s.toUpperCase()).join(", ");
  const title = `${mod.title} — Gulf Nursing Study Guide | MedMind AI`;
  const description =
    mod.description ??
    `Free study guide for ${examNames} nursing licensing exam. ${mod.lesson_count} lessons, ${mod.mcq_count} practice MCQs. Covers key regulations, pharmacology, and clinical practice for the Gulf region.`;

  return {
    title,
    description,
    alternates: {
      canonical: `${SITE_URL}/learn/modules/${mod.code}`,
    },
    openGraph: {
      title,
      description,
      url: `${SITE_URL}/learn/modules/${mod.code}`,
      siteName: "MedMind AI",
      type: "article",
    },
    robots: { index: true, follow: true },
  };
}

// ── Schema.org Course ────────────────────────────────────────────────────────

function buildSchema(mod: PublicModule): object {
  const url = `${SITE_URL}/learn/modules/${mod.code}`;
  const examNames = mod.exam_slugs.map((s) => EXAM_LABELS[s] ?? s).join(", ");
  return {
    "@context": "https://schema.org",
    "@type": "Course",
    name: mod.title,
    description:
      mod.description ??
      `Gulf nursing exam study guide covering ${examNames}.`,
    url,
    provider: {
      "@type": "Organization",
      name: "MedMind AI",
      url: SITE_URL,
    },
    educationalLevel: mod.level_label ?? "Intermediate",
    hasCourseInstance: {
      "@type": "CourseInstance",
      courseMode: "online",
      url,
      courseWorkload: mod.duration_hours ? `PT${mod.duration_hours}H` : undefined,
    },
    numberOfCredits: mod.lesson_count,
    about: mod.exam_slugs.map((s) => ({ "@type": "Thing", name: EXAM_LABELS[s] ?? s })),
  };
}

// ── Lesson content renderer ──────────────────────────────────────────────────

function LessonPreview({ lesson }: { lesson: PublicLesson }) {
  const c = lesson.content;
  if (!c) return null;

  return (
    <div className="prose-gulf">
      {c.intro && (
        <p className="font-serif text-ink-2 text-base leading-relaxed mb-5">{c.intro}</p>
      )}

      {(c.sections ?? []).map((sec, i) => (
        <div key={i} className="mb-6">
          <h3 className="font-syne font-bold text-base text-ink mt-6 mb-2">{sec.heading}</h3>
          <p className="font-serif text-ink-2 text-base leading-relaxed">{sec.text}</p>
        </div>
      ))}

      {c.clinical_pearl && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 mb-5 flex gap-3">
          <span className="text-lg flex-shrink-0">💡</span>
          <div>
            <div className="font-syne font-bold text-xs text-amber-800 mb-1 uppercase tracking-wider">
              Clinical Pearl
            </div>
            <p className="font-serif text-sm text-amber-900 leading-relaxed">{c.clinical_pearl}</p>
          </div>
        </div>
      )}

      {c.key_points && c.key_points.length > 0 && (
        <div className="bg-surface border border-border rounded-xl px-5 py-4 mb-5">
          <div className="font-syne font-bold text-xs text-ink-2 mb-3 uppercase tracking-wider">
            Key Points
          </div>
          <ul className="space-y-2">
            {c.key_points.map((pt, i) => (
              <li key={i} className="flex items-start gap-2 font-serif text-sm text-ink-2 leading-relaxed">
                <span className="text-ink-3 mt-0.5 flex-shrink-0">→</span>
                <span>{pt}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function LearnModulePage({
  params,
}: {
  params: { code: string };
}) {
  const mod = await fetchModule(params.code);
  if (!mod) notFound();

  const schema = buildSchema(mod);
  const firstLesson = mod.lessons[0];
  const remainingLessons = mod.lessons.slice(1);
  const examLabels = mod.exam_slugs.map((s) => EXAM_SHORT[s] ?? s.toUpperCase());

  return (
    <div className="font-serif text-ink">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />

      <div className="max-w-4xl mx-auto px-4 py-10">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-xs font-serif text-ink-3 mb-6" aria-label="Breadcrumb">
          <Link href="/exams/gulf" className="hover:text-ink">Gulf Exams</Link>
          <span>/</span>
          <span className="text-ink-2 truncate max-w-xs">{mod.title}</span>
        </nav>

        {/* Exam badges */}
        <div className="flex flex-wrap gap-2 mb-4">
          {examLabels.map((label) => (
            <span
              key={label}
              className="text-xs font-syne font-bold bg-ink text-white rounded-full px-3 py-0.5"
            >
              {label}
            </span>
          ))}
        </div>

        {/* Hero */}
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-3">
          {mod.title}
        </h1>
        {mod.description && (
          <p className="text-base text-ink-2 leading-relaxed mb-5 max-w-2xl">
            {mod.description}
          </p>
        )}

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-4 text-xs font-syne text-ink-3 mb-8 pb-6 border-b border-border">
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            {mod.lesson_count} lesson{mod.lesson_count !== 1 ? "s" : ""}
          </span>
          {mod.duration_hours && mod.duration_hours > 0 && (
            <span>{mod.duration_hours}h study time</span>
          )}
          {mod.level_label && <span className="capitalize">{mod.level_label}</span>}
          {mod.mcq_count > 0 && (
            <span className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              {mod.mcq_count} practice MCQs
            </span>
          )}
          {mod.flashcard_count > 0 && <span>{mod.flashcard_count} flashcards</span>}
          <span className="text-green-700 font-semibold">✓ Free preview</span>
        </div>

        {/* Table of contents */}
        <div className="bg-surface border border-border rounded-xl p-5 mb-8">
          <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">
            In this module
          </div>
          <ol className="space-y-2">
            {mod.lessons.map((lesson, i) => (
              <li key={lesson.id} className="flex items-center gap-3">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-syne font-bold ${
                  i === 0 ? "bg-ink text-white" : "bg-surface-2 border border-border text-ink-3"
                }`}>
                  {i + 1}
                </span>
                <span className={`font-serif text-sm ${i === 0 ? "text-ink font-semibold" : "text-ink-3"}`}>
                  {lesson.title}
                  {i > 0 && (
                    <span className="ml-2 text-[10px] font-syne text-ink-4">
                      🔒 Sign in to access
                    </span>
                  )}
                </span>
                {lesson.estimated_minutes > 0 && (
                  <span className="ml-auto text-[10px] font-syne text-ink-4 flex-shrink-0">
                    ~{lesson.estimated_minutes} min
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>

        {/* Lesson 1 — free preview */}
        {firstLesson && (
          <section className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-7 h-7 rounded-full bg-ink text-white flex items-center justify-center text-xs font-syne font-bold flex-shrink-0">
                1
              </div>
              <h2 className="font-syne font-bold text-xl text-ink">{firstLesson.title}</h2>
            </div>
            <LessonPreview lesson={firstLesson} />
          </section>
        )}

        {/* Paywall gate for remaining lessons */}
        {remainingLessons.length > 0 && (
          <div className="relative mb-10">
            {/* Fade overlay */}
            <div className="pointer-events-none absolute -top-16 inset-x-0 h-16 bg-gradient-to-b from-transparent to-bg" />

            <div className="bg-ink text-white rounded-2xl p-7 text-center">
              <div className="font-syne font-black text-xl mb-2">
                Continue with {remainingLessons.length} more lesson{remainingLessons.length !== 1 ? "s" : ""}
              </div>
              <p className="text-white/70 font-serif text-sm mb-1 leading-relaxed">
                {remainingLessons.map((l) => l.title).join(" · ")}
              </p>
              {mod.mcq_count > 0 && (
                <p className="text-white/50 font-serif text-xs mb-5">
                  Plus {mod.mcq_count} practice MCQs and {mod.flashcard_count} flashcards — all mapped to {examLabels.join(", ")}
                </p>
              )}
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link
                  href="/register"
                  className="font-syne font-bold text-sm bg-white text-ink px-6 py-3 rounded-xl hover:bg-white/90 transition-colors"
                >
                  Start Free — No Credit Card →
                </Link>
                <Link
                  href="/login"
                  className="font-syne font-bold text-sm border border-white/30 text-white/80 px-6 py-3 rounded-xl hover:border-white/60 transition-colors"
                >
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Practice MCQ CTA */}
        {mod.mcq_count > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 mb-8 flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex-1">
              <div className="font-syne font-bold text-base text-ink mb-1">
                Test your knowledge
              </div>
              <p className="text-sm text-ink-2 leading-relaxed">
                {mod.mcq_count} exam-format MCQs mapped to this module, with AI explanations for every question.
                {mod.flashcard_count > 0 && ` Plus ${mod.flashcard_count} flashcards for quick review.`}
              </p>
            </div>
            <Link
              href="/register"
              className="flex-shrink-0 font-syne font-bold text-sm bg-ink text-white px-5 py-2.5 rounded-xl hover:bg-red transition-colors text-center"
            >
              Practice {mod.mcq_count} MCQs →
            </Link>
          </div>
        )}

        {/* Exam links */}
        {mod.exam_slugs.length > 0 && (
          <div className="mb-8">
            <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">
              Covered exams
            </div>
            <div className="flex flex-wrap gap-2">
              {mod.exam_slugs.map((slug) => (
                <Link
                  key={slug}
                  href={`/exams/${slug}`}
                  className="group flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2 hover:border-ink/30 hover:shadow-sm transition-all"
                >
                  <div>
                    <div className="font-syne font-bold text-xs text-ink">{EXAM_SHORT[slug] ?? slug.toUpperCase()}</div>
                    <div className="text-[10px] font-serif text-ink-3">{EXAM_LABELS[slug] ?? slug}</div>
                  </div>
                  <svg className="w-3 h-3 text-ink-4 group-hover:text-ink ml-1 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Medical disclaimer */}
        <div className="bg-surface border border-border rounded-xl px-5 py-5 text-xs font-serif leading-relaxed mb-6">
          <div className="flex items-start gap-3">
            <span className="text-lg flex-shrink-0 mt-0.5">⚕️</span>
            <div>
              <div className="font-syne font-bold text-sm text-ink mb-2">Educational Disclaimer</div>
              <p className="text-ink-2 mb-2">
                <strong>This content is for educational purposes only</strong> and does not constitute
                medical advice, professional diagnosis, or clinical guidance. Always verify drug dosages,
                local regulations, and clinical protocols against current official guidelines and consult
                a licensed healthcare professional before making clinical decisions.
              </p>
              <p className="text-ink-3">
                Regulatory information (licensing requirements, scope of practice, reporting obligations)
                is based on official sources at the time of writing. Requirements change — always verify
                with the relevant regulatory authority before taking action.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
