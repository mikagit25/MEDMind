import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { RegionalPriceBadge } from "@/components/exam/RegionalPriceBadge";

export interface StudyModule {
  id: string;
  code: string;
  title: string;
  order: number;
  level: string;
  duration_hours: number;
  lesson_count: number;
  jurisdiction: string | null;
  blueprint_categories: string[];
}

export interface ExamDefinition {
  slug: string;
  name: string;
  country: string;
  regulatory_body: string;
  question_count: number;
  duration_min: number;
  pass_threshold: number;
  passing_score_label: string;
  blueprint_source: string;
  blueprint_verified_at: string | null;
  status: "active" | "draft";
  locale: string;
  family: string;
  options_per_question: number;
  categories: string[] | null;
  disclaimer: string | null;
  marketing_ready?: boolean;
}

const CATEGORY_LABELS: Record<string, string> = {
  fundamentals_nursing:    "Fundamentals of Nursing",
  medical_surgical:        "Medical-Surgical Nursing",
  critical_care:           "Critical Care Nursing",
  pharmacology:            "Pharmacology & Medications",
  maternal_newborn:        "Maternal & Newborn Nursing",
  pediatrics:              "Pediatric Nursing",
  mental_health:           "Mental Health Nursing",
  community_public_health: "Community & Public Health",
  leadership_management:   "Leadership & Management",
};

const FEATURES = [
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    ),
    title: "Exam-Format Questions",
    desc: "Every question matches the Prometric 4-option MCQ format with clinical scenarios — no recalled items, all original.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    title: "AI Explanation for Every Question",
    desc: "Detailed rationale after each answer — why the correct option is right and why each distractor is wrong.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
      </svg>
    ),
    title: "Category Performance Tracking",
    desc: "See your exact score per blueprint category after each mock exam — identify weak areas and focus your study.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
    title: "Personalised Study Plan",
    desc: "Set your exam date and get a daily study schedule that adapts to your performance and time remaining.",
  },
];

const LEVEL_LABELS: Record<string, string> = {
  beginner:     "Foundation",
  intermediate: "Core",
  advanced:     "Advanced",
};

export function ExamLandingTemplate({
  exam,
  studyModules = [],
}: {
  exam: ExamDefinition;
  studyModules?: StudyModule[];
}) {
  const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
  const hours = Math.floor(exam.duration_min / 60);
  const mins = exam.duration_min % 60;
  const durationLabel = hours > 0
    ? `${hours}h${mins > 0 ? ` ${mins}min` : ""}`
    : `${mins} min`;

  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-4 pt-16 pb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
            {exam.country}
          </span>
          <span className="text-ink-3">·</span>
          <span className="text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
            {exam.family.toUpperCase()} Prometric
          </span>
        </div>
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          {exam.name} Prep 2025
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-6 max-w-2xl">
          Practice with exam-format questions, AI-powered explanations, and a
          personalised study plan timed to your exam date. Built for nurses
          preparing for Prometric licensing in {exam.country}.
        </p>
        <div className="flex flex-wrap gap-3 mb-8">
          <Link href="/register"
            className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            Start Free →
          </Link>
          <Link href={`/nurses/nclex`}
            className="font-syne font-bold text-sm border border-border text-ink px-6 py-3 rounded-xl hover:bg-surface transition-colors">
            View Demo
          </Link>
        </div>

        {/* Exam specs card */}
        <div className="bg-surface border border-border rounded-2xl p-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Questions", value: exam.question_count.toString() },
            { label: "Duration", value: durationLabel },
            { label: "Pass mark", value: exam.passing_score_label },
            { label: "Format", value: `${exam.options_per_question}-option MCQ` },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="font-syne font-black text-2xl text-ink">{value}</div>
              <div className="text-xs font-syne text-ink-3 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Blueprint categories */}
      {exam.categories && exam.categories.length > 0 && (
        <section className="max-w-4xl mx-auto px-4 py-10">
          <h2 className="font-syne font-bold text-xl text-ink mb-5">Exam Blueprint Categories</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {exam.categories.map(cat => (
              <div key={cat} className="bg-surface border border-border rounded-xl p-3 text-center">
                <div className="font-syne font-semibold text-xs text-ink">
                  {CATEGORY_LABELS[cat] ?? cat}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Study modules */}
      {exam.family === "gulf" && studyModules.length > 0 && (
        <section className="max-w-4xl mx-auto px-4 py-10">
          <h2 className="font-syne font-bold text-xl text-ink mb-2">Study Materials</h2>
          <p className="text-sm text-ink-2 mb-5">
            Free educational modules covering regulations, pharmacology, clinical practice, and cultural care —
            mapped to the {exam.name} blueprint.
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {studyModules.map(mod => (
              <Link
                key={mod.id}
                href={`/modules/${mod.id}`}
                className="group bg-surface border border-border rounded-xl p-4 hover:border-ink/30 hover:shadow-sm transition-all flex gap-4"
              >
                <div className="w-10 h-10 bg-ink/5 rounded-xl flex items-center justify-center flex-shrink-0 text-ink group-hover:bg-ink/10 transition-colors">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-syne font-bold text-sm text-ink mb-0.5 group-hover:text-red transition-colors truncate">
                    {mod.title}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-ink-3">
                    <span>{mod.lesson_count} lesson{mod.lesson_count !== 1 ? "s" : ""}</span>
                    {mod.duration_hours > 0 && (
                      <>
                        <span>·</span>
                        <span>{mod.duration_hours}h</span>
                      </>
                    )}
                    <span>·</span>
                    <span className="capitalize">{LEVEL_LABELS[mod.level] ?? mod.level}</span>
                  </div>
                </div>
                <div className="flex-shrink-0 text-ink-3 group-hover:text-ink transition-colors self-center">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Features */}
      <section className="max-w-4xl mx-auto px-4 py-10">
        <h2 className="font-syne font-bold text-xl text-ink mb-6">What MedMind AI Includes</h2>
        <div className="grid sm:grid-cols-2 gap-5">
          {FEATURES.map(f => (
            <div key={f.title} className="flex gap-4">
              <div className="w-10 h-10 bg-ink/5 rounded-xl flex items-center justify-center flex-shrink-0 text-ink">
                {f.icon}
              </div>
              <div>
                <div className="font-syne font-bold text-sm text-ink mb-1">{f.title}</div>
                <div className="text-sm text-ink-2 leading-relaxed">{f.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Gulf Bundle CTA */}
      <section className="max-w-4xl mx-auto px-4 py-10">
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center gap-5">
          <div className="flex-1">
            <div className="font-syne font-bold text-base text-ink mb-1">
              Preparing for multiple Gulf exams?
            </div>
            <div className="text-sm text-ink-2 leading-relaxed">
              The Gulf Bundle gives you access to all 7 Prometric licensing exams —
              SNLE, DHA, QCHP, OMSB, NHRA, MOH UAE, and DOH/HAAD — in one plan.
              Many nurses sit multiple exams depending on which country accepts them.
            </div>
          </div>
          <div className="flex flex-col gap-2 flex-shrink-0">
            <RegionalPriceBadge plan="gulf_bundle" />
            <Link href="/exams/gulf"
              className="font-syne font-bold text-sm bg-ink text-white px-5 py-2.5 rounded-xl hover:bg-red transition-colors text-center">
              View Gulf Bundle →
            </Link>
          </div>
        </div>
      </section>

      {/* Official source + disclaimer */}
      <section className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-surface border border-border rounded-xl p-5 space-y-3">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <div className="font-syne font-bold text-xs text-ink mb-1">Official exam authority</div>
              <a href={exam.blueprint_source} target="_blank" rel="noopener noreferrer"
                className="text-sm text-ink-2 underline underline-offset-2 hover:text-ink break-all">
                {exam.regulatory_body}
              </a>
            </div>
          </div>
          {exam.disclaimer && (
            <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-3">
              {exam.disclaimer}
            </p>
          )}
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
