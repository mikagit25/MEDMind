import type { Metadata } from "next";
import Link from "next/link";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 300; // 5 min

export const metadata: Metadata = {
  title: "Free Medical Quizzes — Test Your Knowledge",
  description:
    "Free medical knowledge quizzes — no registration required. First aid, anatomy, drug myths, pet health, and more.",
  alternates: { canonical: `${SITE_URL}/quiz/public` },
  openGraph: {
    title: "Free Medical Quizzes — MedMind",
    description: "Test your health knowledge. No signup needed.",
    url: `${SITE_URL}/quiz/public`,
    type: "website",
  },
};

type QuizMeta = {
  slug: string;
  title: string;
  description: string | null;
  category: string;
  play_count: number;
};

const CATEGORY_ICONS: Record<string, string> = {
  "first-aid": "🚑",
  pharmacology: "💊",
  symptoms: "🩺",
  veterinary: "🐾",
  anatomy: "🫀",
  general: "📋",
};

const CATEGORY_LABELS: Record<string, string> = {
  "first-aid": "First Aid",
  pharmacology: "Pharmacology",
  symptoms: "Symptoms & Signs",
  veterinary: "Pet Health",
  anatomy: "Anatomy",
  general: "General",
};

async function fetchQuizzes(): Promise<QuizMeta[]> {
  try {
    const res = await fetch(`${API_URL}/public/quiz`, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export default async function PublicQuizListPage() {
  const quizzes = await fetchQuizzes();

  return (
    <>
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "ItemList",
            name: "MedMind Free Medical Quizzes",
            url: `${SITE_URL}/quiz/public`,
            numberOfItems: quizzes.length,
            itemListElement: quizzes.map((q, i) => ({
              "@type": "ListItem",
              position: i + 1,
              name: q.title,
              url: `${SITE_URL}/quiz/public/${q.slug}`,
            })),
          }),
        }}
      />

      <div className="min-h-screen bg-bg">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
          {/* Hero */}
          <div className="text-center mb-12">
            <h1 className="font-syne font-black text-3xl sm:text-5xl text-ink mb-4">
              Test Your Medical Knowledge
            </h1>
            <p className="font-serif text-ink-3 text-base max-w-xl mx-auto mb-6">
              Free quizzes on first aid, anatomy, drugs, pet health, and more.
              No registration required — just press start.
            </p>
            <p className="font-serif text-xs text-ink-3/60">
              {quizzes.reduce((s, q) => s + q.play_count, 0).toLocaleString()}+ quizzes taken
            </p>
          </div>

          {quizzes.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-5xl mb-4">📋</div>
              <p className="font-syne font-bold text-ink text-lg">Quizzes coming soon</p>
              <p className="font-serif text-ink-3 text-sm mt-2">
                We&apos;re preparing free knowledge tests for everyone.
              </p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-5">
              {quizzes.map((quiz) => (
                <Link
                  key={quiz.slug}
                  href={`/quiz/public/${quiz.slug}`}
                  className="group block bg-surface border border-border rounded-2xl p-6 hover:border-ink hover:shadow-md transition-all"
                >
                  <div className="flex items-start gap-4">
                    <span className="text-3xl shrink-0">
                      {CATEGORY_ICONS[quiz.category] ?? "📋"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-syne font-semibold text-xs text-ink-3 bg-bg-2 px-2 py-0.5 rounded">
                          {CATEGORY_LABELS[quiz.category] ?? quiz.category}
                        </span>
                        {quiz.play_count > 0 && (
                          <span className="font-serif text-xs text-ink-3/60">
                            {quiz.play_count.toLocaleString()} plays
                          </span>
                        )}
                      </div>
                      <h2 className="font-syne font-bold text-base text-ink group-hover:text-accent mb-2 leading-snug">
                        {quiz.title}
                      </h2>
                      {quiz.description && (
                        <p className="font-serif text-xs text-ink-3 line-clamp-2">
                          {quiz.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-end">
                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-ink text-white font-syne font-bold text-xs group-hover:bg-ink-2 transition-colors">
                      Start Quiz →
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {/* CTA */}
          <div className="mt-14 text-center bg-surface border border-border rounded-2xl p-8">
            <h2 className="font-syne font-black text-xl text-ink mb-2">
              Want to track your progress?
            </h2>
            <p className="font-serif text-sm text-ink-3 mb-5">
              Create a free account to save scores, access 800+ clinical lessons, and study with AI.
            </p>
            <Link
              href="/register"
              className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
            >
              Sign Up Free →
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
