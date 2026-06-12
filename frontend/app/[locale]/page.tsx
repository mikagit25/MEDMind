/**
 * Localized landing pages: /ru, /de, /fr, /es, /tr, /ar
 * Each renders the same landing page with the locale pre-set.
 * /en redirects to / (canonical).
 */
import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import LandingPage from "@/app/LandingPage";
import type { MiniQuizQuestion } from "@/components/ui/MiniQuiz";

export const dynamic = "force-dynamic";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

const SUPPORTED = ["en", "ru", "ar", "tr", "de", "fr", "es"] as const;
type Locale = (typeof SUPPORTED)[number];

// Page meta strings per locale (static, no API needed)
const META: Record<Locale, { title: string; description: string }> = {
  en: { title: "MedMind AI — Medical Education Platform", description: "AI-powered medical learning for doctors, students, and patients." },
  ru: { title: "MedMind AI — Медицинская образовательная платформа", description: "ИИ-тьютор для врачей, ординаторов, студентов и пациентов. Доказательная медицина на русском." },
  de: { title: "MedMind AI — Medizinische Lernplattform", description: "KI-gestütztes medizinisches Lernen für Ärzte, Studenten und Patienten auf Deutsch." },
  fr: { title: "MedMind AI — Plateforme d'éducation médicale", description: "Apprentissage médical par IA pour médecins, étudiants et patients en français." },
  es: { title: "MedMind AI — Plataforma de educación médica", description: "Aprendizaje médico impulsado por IA para médicos, estudiantes y pacientes en español." },
  tr: { title: "MedMind AI — Tıp Eğitim Platformu", description: "Doktorlar, öğrenciler ve hastalar için Türkçe yapay zeka destekli tıp eğitimi." },
  ar: { title: "MedMind AI — منصة التعليم الطبي", description: "التعلم الطبي بالذكاء الاصطناعي للأطباء والطلاب والمرضى باللغة العربية." },
};

type ArticlePreview = {
  id: string; slug: string; title: string; excerpt: string;
  category: string; reading_time_minutes: number;
  cover_image: string | null; published_at: string | null;
};
type PlatformStats = { articles: number; modules: number; languages: number };
type QuizData = { slug: string; questions: MiniQuizQuestion[] } | null;

async function fetchAll(locale: Locale): Promise<{
  articles: ArticlePreview[];
  stats: PlatformStats;
  miniQuiz: QuizData;
}> {
  const [artRes, statsRes, quizListRes] = await Promise.allSettled([
    fetch(`${API_URL}/articles?limit=24&locale=${locale}`, { next: { revalidate: 1800 } }),
    fetch(`${API_URL}/public/stats`, { next: { revalidate: 3600 } }),
    fetch(`${API_URL}/public/quiz?limit=5`, { next: { revalidate: 3600 } }),
  ]);

  // Articles
  let articles: ArticlePreview[] = [];
  if (artRes.status === "fulfilled" && artRes.value.ok) {
    const data = await artRes.value.json();
    const all: ArticlePreview[] = data.articles ?? [];
    const seen: Record<string, number> = {};
    articles = all.filter((a) => { seen[a.category] = (seen[a.category] ?? 0) + 1; return seen[a.category] <= 3; }).slice(0, 10);
  }

  // Stats
  let stats: PlatformStats = { articles: 600, modules: 82, languages: 7 };
  if (statsRes.status === "fulfilled" && statsRes.value.ok) {
    stats = await statsRes.value.json();
  }

  // Mini quiz
  let miniQuiz: QuizData = null;
  if (quizListRes.status === "fulfilled" && quizListRes.value.ok) {
    const list: { slug: string }[] = await quizListRes.value.json();
    if (list.length) {
      try {
        const qRes = await fetch(`${API_URL}/public/quiz/${list[0].slug}`, { next: { revalidate: 3600 } });
        if (qRes.ok) {
          const quiz = await qRes.json();
          const questions: MiniQuizQuestion[] = (quiz.questions ?? [])
            .filter((q: { question: string; options: string[] }) => q.question && q.options?.length >= 2)
            .slice(0, 3)
            .map((q: { question: string; options: string[]; correct_index: number; explanation: string }) => ({
              question: q.question,
              options: q.options,
              correct_index: q.correct_index ?? 0,
              explanation: q.explanation ?? "",
            }));
          if (questions.length) miniQuiz = { slug: list[0].slug, questions };
        }
      } catch { /* ignore */ }
    }
  }

  return { articles, stats, miniQuiz };
}

export async function generateStaticParams() {
  // Pre-render all non-en locales at build time
  return SUPPORTED.filter((l) => l !== "en").map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: { locale: string };
}): Promise<Metadata> {
  const loc = params.locale as Locale;
  if (!SUPPORTED.includes(loc)) return { title: "Not found" };
  if (loc === "en") return { title: META.en.title, description: META.en.description };

  const meta = META[loc];
  const canonical = `${SITE_URL}/${loc}`;

  return {
    title: meta.title,
    description: meta.description,
    alternates: {
      canonical,
      languages: {
        "x-default": SITE_URL,
        ...Object.fromEntries(SUPPORTED.map((l) => [l, l === "en" ? SITE_URL : `${SITE_URL}/${l}`])),
      },
    },
    openGraph: {
      title: meta.title,
      description: meta.description,
      url: canonical,
      siteName: "MedMind AI",
      type: "website",
    },
  };
}

export default async function LocalePage({
  params,
}: {
  params: { locale: string };
}) {
  const loc = params.locale as Locale;

  // Validate locale
  if (!SUPPORTED.includes(loc)) notFound();
  // Canonical English lives at /
  if (loc === "en") redirect("/");

  const { articles, stats, miniQuiz } = await fetchAll(loc);

  return (
    <LandingPage
      articles={articles}
      stats={stats}
      miniQuiz={miniQuiz}
      initialLocale={loc}
    />
  );
}
