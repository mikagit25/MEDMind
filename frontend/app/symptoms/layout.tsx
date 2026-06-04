import type { Metadata } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: { absolute: "Symptom Checker — MedMind AI" },
  description:
    "AI-powered symptom checker: describe your symptoms and get a structured differential diagnosis with urgency guidance. Available in 7 languages. Not a substitute for professional care.",
  keywords: [
    "symptom checker", "medical symptom checker", "AI symptom analysis", "differential diagnosis",
    "online symptom checker", "free symptom checker", "медицинские симптомы", "symptômes médicaux",
  ],
  alternates: {
    canonical: `${SITE_URL}/symptoms`,
  },
  openGraph: {
    title: "Symptom Checker — MedMind AI",
    description: "Describe your symptoms, get AI-powered differential diagnosis with urgency guidance in 7 languages.",
    url: `${SITE_URL}/symptoms`,
    siteName: "MedMind AI",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Symptom Checker — MedMind AI",
    description: "AI-powered symptom checker in 7 languages. Instant differential diagnosis with urgency guidance.",
  },
  robots: { index: true, follow: true },
};

export default function SymptomsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
