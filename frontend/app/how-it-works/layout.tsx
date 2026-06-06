import type { Metadata } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: { absolute: "How It Works — MedMind AI" },
  description:
    "Discover how MedMind AI uses Claude AI and PubMed to deliver evidence-based medical education. Spaced repetition, clinical cases, AI tutor, drug database — all in one platform.",
  keywords: ["how medmind works", "AI medical education", "spaced repetition medicine", "clinical cases AI", "medical AI platform"],
  alternates: {
    canonical: `${SITE_URL}/how-it-works`,
    languages: Object.fromEntries(
      ["en", "ru", "ar", "tr", "de", "fr", "es"].map((l) => [l, `${SITE_URL}/${l}/how-it-works`])
    ),
  },
  openGraph: {
    title: "How It Works — MedMind AI",
    description: "AI-powered medical education built on Claude AI and PubMed. Learn how MedMind helps doctors, students and veterinarians master medicine.",
    url: `${SITE_URL}/how-it-works`,
    siteName: "MedMind AI",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "How MedMind AI Works",
    description: "Evidence-based AI medical education — spaced repetition, clinical cases, drug database and AI tutor.",
  },
};

export default function HowItWorksLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
