import type { Metadata } from "next";
import LandingPage from "./LandingPage";
import type { MiniQuizQuestion } from "@/components/ui/MiniQuiz";

export const dynamic = "force-dynamic";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const SUPPORTED_LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

// Hreflang is shared across / and all /{locale} (middleware rewrites /ar → /?lang=ar
// so this page handles both the English homepage and every locale landing page).
const LOCALE_HREFLANG = {
  "x-default": SITE_URL,
  ...Object.fromEntries(
    SUPPORTED_LOCALES.map((l) => [l, l === "en" ? SITE_URL : `${SITE_URL}/${l}`])
  ),
};

export async function generateMetadata({
  searchParams,
}: {
  searchParams?: { lang?: string };
}): Promise<Metadata> {
  // Middleware rewrites /ar → /?lang=ar; detect locale from that param.
  const lang = searchParams?.lang;
  const locale = lang && SUPPORTED_LOCALES.includes(lang) && lang !== "en" ? lang : "en";
  const canonical = locale === "en" ? SITE_URL : `${SITE_URL}/${locale}`;
  return {
    alternates: {
      canonical,
      languages: LOCALE_HREFLANG,
    },
  };
}

const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

type ArticlePreview = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  reading_time_minutes: number;
  cover_image: string | null;
  published_at: string | null;
};

type PlatformStats = { articles: number; modules: number; drugs: number; flashcards: number; languages: number };
type QuizData = { slug: string; questions: MiniQuizQuestion[] } | null;

async function fetchFeaturedArticles(): Promise<ArticlePreview[]> {
  try {
    const res = await fetch(`${API_URL}/articles?limit=24`, {
      next: { revalidate: 1800 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    const articles: ArticlePreview[] = data.articles ?? [];
    const seen: Record<string, number> = {};
    return articles
      .filter((a) => {
        seen[a.category] = (seen[a.category] ?? 0) + 1;
        return seen[a.category] <= 3;
      })
      .slice(0, 10);
  } catch {
    return [];
  }
}

async function fetchStats(): Promise<PlatformStats> {
  try {
    const res = await fetch(`${API_URL}/public/stats`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return { articles: 600, modules: 125, drugs: 800, flashcards: 1000, languages: 7 };
    return await res.json();
  } catch {
    return { articles: 600, modules: 125, drugs: 800, flashcards: 1000, languages: 7 };
  }
}

async function fetchMiniQuiz(): Promise<QuizData> {
  try {
    // Fetch the first active public quiz
    const listRes = await fetch(`${API_URL}/public/quiz?limit=5`, {
      next: { revalidate: 3600 },
    });
    if (!listRes.ok) return null;
    const list: { slug: string }[] = await listRes.json();
    if (!list.length) return null;

    const quizRes = await fetch(`${API_URL}/public/quiz/${list[0].slug}`, {
      next: { revalidate: 3600 },
    });
    if (!quizRes.ok) return null;
    const quiz = await quizRes.json();

    const raw: { question: string; options: string[]; correct_index: number; explanation: string }[] =
      quiz.questions ?? [];

    // Take first 3 questions that have explanation
    const questions: MiniQuizQuestion[] = raw
      .filter((q) => q.question && q.options?.length >= 2)
      .slice(0, 3)
      .map((q) => ({
        question: q.question,
        options: q.options,
        correct_index: q.correct_index ?? 0,
        explanation: q.explanation ?? "",
      }));

    if (!questions.length) return null;
    return { slug: list[0].slug, questions };
  } catch {
    return null;
  }
}

export default async function Page({
  searchParams,
}: {
  searchParams?: { lang?: string };
}) {
  const lang = searchParams?.lang;
  const locale = (lang && SUPPORTED_LOCALES.includes(lang) && lang !== "en" ? lang : "en") as string;

  const [articles, stats, miniQuiz] = await Promise.all([
    fetchFeaturedArticles(),
    fetchStats(),
    fetchMiniQuiz(),
  ]);
  return <LandingPage articles={articles} stats={stats} miniQuiz={miniQuiz} initialLocale={locale} />;
}
