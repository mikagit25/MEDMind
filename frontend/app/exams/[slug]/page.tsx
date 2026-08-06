import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ExamLandingTemplate, type ExamDefinition } from "@/components/exam/ExamLandingTemplate";

export const dynamic = "force-dynamic";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const BACKEND_URL =
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

async function fetchExam(slug: string): Promise<ExamDefinition | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/exam/definitions/${slug}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function fetchGulfSlugs(): Promise<string[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/exam/definitions?family=gulf&include_draft=true`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data: ExamDefinition[] = await res.json();
    return data.map(e => e.slug);
  } catch {
    return ["snle", "dha", "qchp", "omsb", "nhra", "moh-uae", "haad"];
  }
}

export async function generateStaticParams() {
  const slugs = await fetchGulfSlugs();
  return slugs.map(slug => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const exam = await fetchExam(params.slug);
  if (!exam) return { title: "Exam Not Found" };

  const arSlug = params.slug === "snle" ? "/ar/nclex-snle" : "/ar/gulf";
  return {
    title: `${exam.name} Prep 2025 — Practice Questions & AI Explanations | MedMind AI`,
    description: `Prepare for the ${exam.name} with ${exam.question_count} exam-format questions, AI explanations, and a study plan. ${exam.regulatory_body} — ${exam.country}.`,
    alternates: {
      canonical: `${SITE_URL}/exams/${params.slug}`,
      languages: {
        "en": `${SITE_URL}/exams/${params.slug}`,
        "ar": `${SITE_URL}${arSlug}`,
        "x-default": `${SITE_URL}/exams/${params.slug}`,
      },
    },
    openGraph: {
      title: `${exam.name} Prep — MedMind AI`,
      description: `${exam.question_count} questions · ${exam.duration_min} min · Pass: ${exam.passing_score_label} · ${exam.country}`,
      url: `${SITE_URL}/exams/${params.slug}`,
      siteName: "MedMind AI",
      type: "website",
    },
    robots: exam.marketing_ready
      ? { index: true, follow: true }
      : { index: false, follow: true },
  };
}

export default async function ExamPage({ params }: { params: { slug: string } }) {
  const exam = await fetchExam(params.slug);
  if (!exam) notFound();
  return <ExamLandingTemplate exam={exam} />;
}
