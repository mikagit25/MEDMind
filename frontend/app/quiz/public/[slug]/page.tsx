import type { Metadata } from "next";
import { notFound } from "next/navigation";
import QuizPlayer from "./QuizPlayer";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 300;

type QuizData = {
  slug: string;
  title: string;
  description: string | null;
  category: string;
  question_count: number;
  questions: { question: string; options: Record<string, string> }[];
  play_count: number;
};

async function fetchQuiz(slug: string): Promise<QuizData | null> {
  try {
    const res = await fetch(`${API_URL}/public/quiz/${slug}`, { next: { revalidate: 300 } });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const quiz = await fetchQuiz(params.slug);
  if (!quiz) return { title: "Quiz Not Found" };
  return {
    title: `${quiz.title} — Free Quiz`,
    description: quiz.description ?? `Test your knowledge: ${quiz.title}. ${quiz.question_count} questions, no signup required.`,
    alternates: { canonical: `${SITE_URL}/quiz/public/${quiz.slug}` },
    openGraph: {
      title: `${quiz.title} — MedMind Quiz`,
      description: quiz.description ?? `${quiz.question_count} questions. Free, no signup.`,
      url: `${SITE_URL}/quiz/public/${quiz.slug}`,
      type: "website",
    },
  };
}

export default async function PublicQuizPage({ params }: { params: { slug: string } }) {
  const quiz = await fetchQuiz(params.slug);
  if (!quiz) notFound();

  return <QuizPlayer quiz={quiz} siteUrl={SITE_URL} apiUrl={API_URL} />;
}
